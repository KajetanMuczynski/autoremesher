#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""Where the time and memory of ab.py runs go, and how well input size and target predict them.

    python speed_report.py --runs $AR_WORK/runs/<key> [--runs <other key> ...] [--sets corpus,ladder]
        [--csv out.csv]

Reads only `record.json` and `stages.jsonl` of replicate u0 (no metrics needed; `ab.py run --no-metrics
--jobs 1` is the setting for timing). Prints, per run folder:

- **Stage shares** per target: the core's named steps summed over meshes, as % of the summed run time,
  and the island phases (input preprocessing before the islands: fold check, island split, island
  contexts; resample = decimation and isotropic remeshing; parameterize; extract, which includes the
  projection onto the input) as medians over single-island runs.
- **Solves**: the rounding loop (iterations, integer variables, n and factor time per iteration) and the
  curl system (n, nnz(L), time), the two sparse factorizations that dominate large targets.
- **Quad count**: output quads / target, and where the gap opens: `cells/t` is the parameterization's
  integer-grid cell count (before extraction), `out/cells` what extraction and cleanup keep.
- **Models** over all folders together: peak RSS ~ a * input triangles + b * target + c (least squares,
  with the largest positive residual as margin), and wall time ~ a * Mtri + b * (target/1000)^e + c fitted
  on single-island runs in log space, with the spread of actual/predicted. Multi-island runs are listed
  apart, since islands run in parallel.

With several folders of the same mesh set (different refs), a last table gives the geometric mean of the
time ratio per target against the first folder, and whether the outputs are byte-identical.
"""
import argparse
import csv
import glob
import json
import math
import os
from collections import Counter, defaultdict

import numpy as np


def load(folder, sets):
    rows = []
    for rp in sorted(glob.glob(os.path.join(folder, "*", "*", "*", "u0", "record.json"))):
        d = os.path.dirname(rp)
        setname = rp.split(os.sep)[-5]
        if sets and setname not in sets:
            continue
        rec = json.load(open(rp))
        if rec.get("rc") != 0:
            continue
        try:
            stages = [json.loads(line) for line in open(os.path.join(d, "stages.jsonl")) if line.strip()]
            report = json.load(open(os.path.join(d, "report.json")))
        except (OSError, ValueError):
            continue
        run = next((s for s in stages if s.get("stage") == "run"), None)
        if run is None:
            continue
        islands = [s for s in stages if s.get("stage") == "island"]
        rounding = [s for s in stages if s.get("stage") == "rounding_iteration"]
        curl = [s for s in stages if s.get("stage") == "curl_correction"]
        cover = [s for s in stages if s.get("stage") == "cover_result"]
        total = run["total_ms"] / 1000
        pre = (run["total_ms"] - run.get("isotropic_wall_ms", 0) - run.get("parameterize_wall_ms", 0)
               - run.get("merge_ms", 0)) / 1000
        row = {
            "set": setname, "mesh": rec["mesh"], "target": rec["target"], "res": rec["res"],
            "triangles": run["input_triangles"], "islands": run["islands"],
            "wall": rec["wall"], "total": total, "cpu": run.get("cpu_seconds"),
            "peak_rss_mb": rec["peak_rss_mb"], "out_sha": rec.get("out_sha"),
            "quads": (report.get("output") or {}).get("quads"),
            "faces": run.get("output_faces"),
            "cells": sum(s.get("rounded_cells", 0) for s in cover),
            "pre": pre, "fold_check": run.get("fold_repair_ms", 0) / 1000,
            "split": run.get("split_ms", 0) / 1000, "contexts": run.get("build_ms", 0) / 1000,
            "resample": sum(s.get("resample_ms", 0) for s in islands) / 1000,
            "parameterize": sum(s.get("parameterize_ms", 0) for s in islands) / 1000,
            "extract": sum(s.get("extract_ms", 0) for s in islands) / 1000,
            "projection": sum(s.get("seconds", 0) for s in stages if s.get("stage") == "surface_projection"),
            "round_s": sum(s.get("solve_total_ms", 0) for s in rounding) / 1000,
            "round_iters": len(rounding),
            "round_ints": max([s.get("kernel_integers", 0) for s in rounding] or [0]),
            "round_n": max([s.get("solve_n", 0) for s in rounding] or [0]),
            "curl_s": sum(s.get("solve_total_ms", 0) for s in curl) / 1000,
            "curl_n": max([s.get("solve_n", 0) for s in curl] or [0]),
            "curl_nnz_l": sum(s.get("solve_factor_nnz", 0) for s in curl),
            "steps": {s["name"]: s["seconds"] for s in report.get("time", {}).get("steps", [])},
        }
        rows.append(row)
    return rows


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else float("nan")


def stage_tables(rows, top):
    for t in sorted({r["target"] for r in rows}):
        R = [r for r in rows if r["target"] == t]
        total = sum(r["total"] for r in R)
        steps = Counter()
        for r in R:
            steps.update(r["steps"])
        print(f"\n**target {t}** ({len(R)} runs, {total:.0f} s summed, median {med([r['total'] for r in R]):.1f} s, "
              f"peak RSS median {med([r['peak_rss_mb'] for r in R]):.0f} MB, max {max(r['peak_rss_mb'] for r in R):.0f} MB)\n")
        print("| step | s | % of run time |\n|---|---:|---:|")
        for name, s in steps.most_common(top):
            print(f"| {name} | {s:.1f} | {100 * s / total:.1f} |")
        single = [r for r in R if r["islands"] == 1]
        if single:
            shares = {k: med([r[k] / r["total"] for r in single])
                      for k in ("pre", "resample", "parameterize", "extract", "round_s", "curl_s", "projection")}
            print("\nSingle-island medians, share of run time: " + ", ".join(f"{k} {100 * v:.0f} %" for k, v in shares.items()))


def solve_table(rows):
    print("\n| mesh | target | run s | rounding s (%) | iterations | integers | n | factor s/iter | curl s | curl n | nnz(L) curl |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in sorted(rows, key=lambda r: (r["mesh"], r["target"])):
        if not r["round_iters"]:
            continue
        print(f"| {r['mesh']} | {r['target']} | {r['total']:.1f} | {r['round_s']:.1f} ({100 * r['round_s'] / r['total']:.0f}) | "
              f"{r['round_iters']} | {r['round_ints']} | {r['round_n']} | {r['round_s'] / r['round_iters']:.2f} | "
              f"{r['curl_s']:.1f} | {r['curl_n']} | {r['curl_nnz_l'] / 1e6:.1f}M |")


def count_table(rows):
    print("\n| mesh | target | islands | quads/target | cells/target | quads/cells |\n|---|---:|---:|---:|---:|---:|")
    for r in sorted(rows, key=lambda r: (r["mesh"], r["target"])):
        if r["quads"] and r["cells"]:
            print(f"| {r['mesh']} | {r['target']} | {r['islands']} | {r['quads'] / r['target']:.3f} | "
                  f"{r['cells'] / r['target']:.3f} | {r['quads'] / r['cells']:.3f} |")


def models(rows):
    n = np.array([r["triangles"] for r in rows], float) / 1e6
    q = np.array([r["target"] for r in rows], float) / 1e3
    rss = np.array([r["peak_rss_mb"] for r in rows], float)
    A = np.c_[n, q, np.ones_like(n)]
    c, *_ = np.linalg.lstsq(A, rss, rcond=None)
    ratio_rss = rss / (A @ c)
    print(f"\n**Peak RSS** ({len(rows)} runs): {c[0]:.0f} MB per million input triangles + {c[1]:.1f} MB per 1,000 "
          f"target quads + {c[2]:.0f} MB ({c[0] * 1024 / 1e6:.2f} KB/triangle, {c[1] * 1024 / 1e3:.1f} KB/quad); "
          f"actual/predicted {ratio_rss.min():.2f} to {ratio_rss.max():.2f} (p90 {np.percentile(ratio_rss, 90):.2f}), "
          f"so x{ratio_rss.max():.2f} is an upper bound on these runs.")
    worst_rss = np.argsort(-ratio_rss)[:3]
    print("Most above the model: " + ", ".join(f"{rows[i]['mesh']} {rows[i]['target']} x{ratio_rss[i]:.2f}" for i in worst_rss))
    t = np.array([r["wall"] for r in rows], float)
    single = np.array([r["islands"] == 1 for r in rows])
    if single.sum() < 5:
        return
    try:
        from scipy.optimize import minimize
    except ImportError:
        print("time model needs scipy")
        return

    def model(p, n, q):
        return p[0] * n + p[1] * q ** p[2] + p[3]

    def loss(p):
        m = model(p, n[single], q[single])
        return np.inf if np.any(m <= 0) else float(np.sum(np.log(m / t[single]) ** 2))
    p = minimize(loss, [10, 0.5, 1.3, 0.5], method="Nelder-Mead", options={"maxiter": 20000, "xatol": 1e-6}).x
    ratio = t / model(p, n, q)
    s = ratio[single]
    print(f"\n**Wall time**, single-island runs ({int(single.sum())}): {p[0]:.2f} s per million triangles + "
          f"{p[1]:.3f} s x (target/1000)^{p[2]:.2f} + {p[3]:.2f} s; actual/predicted median {np.median(s):.2f}, "
          f"p90 {np.percentile(s, 90):.2f}, min {s.min():.2f}, max {s.max():.2f}.")
    worst = np.argsort(-ratio)
    print("Slowest against the model: " + ", ".join(
        f"{rows[i]['mesh']} {rows[i]['target']} x{ratio[i]:.1f}" for i in worst[:5] if single[i]))
    multi = [(rows[i]["mesh"], rows[i]["target"], rows[i]["islands"], ratio[i]) for i in np.where(~single)[0]]
    if multi:
        print("Multi-island (parallel islands, faster than the model): " + ", ".join(
            f"{m} {tq} ({k} islands) x{rr:.2f}" for m, tq, k, rr in multi))
    print("\nPredicted wall time and peak RSS (upper bound in brackets):\n")
    print("| input triangles | " + " | ".join(f"{k}k quads" for k in (3, 10, 50)) + " |\n|---:|---:|---:|---:|")
    for N in (0.1, 0.5, 1, 2, 5, 10):
        print(f"| {N}M | " + " | ".join(f"{model(p, N, k):.0f} s, {c[0] * N + c[1] * k + c[2]:.0f} MB (<= {ratio_rss.max() * (c[0] * N + c[1] * k + c[2]):.0f})"
                                        for k in (3, 10, 50)) + " |")


def compare(folders, data):
    base = {(r["set"], r["mesh"], r["target"], r["res"]): r for r in data[0]}
    print("\n| folder | target | runs | geo-mean time / first | identical outputs |\n|---|---:|---:|---:|---:|")
    for f, rows in zip(folders[1:], data[1:]):
        for t in sorted({r["target"] for r in rows}):
            pairs = [(base[k], r) for r in rows if r["target"] == t
                     for k in [(r["set"], r["mesh"], r["target"], r["res"])] if k in base]
            if not pairs:
                continue
            g = math.exp(sum(math.log(b["total"] / a["total"]) for a, b in pairs) / len(pairs))
            same = sum(1 for a, b in pairs if a["out_sha"] and a["out_sha"] == b["out_sha"])
            print(f"| {os.path.basename(f.rstrip('/'))} | {t} | {len(pairs)} | {g:.2f} | {same}/{len(pairs)} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", action="append", required=True, help="ab.py run folder; repeat to compare")
    ap.add_argument("--sets", default="", help="comma list of sets (default all)")
    ap.add_argument("--top", type=int, default=10, help="steps listed per target")
    ap.add_argument("--min-target", type=int, default=1000, help="skip runs below this target (build smoke runs)")
    ap.add_argument("--csv", help="write one row per run (all folders)")
    a = ap.parse_args()
    sets = set(a.sets.split(",")) if a.sets else None
    data = [[r for r in load(f, sets) if r["target"] >= a.min_target] for f in a.runs]
    for f, rows in zip(a.runs, data):
        print(f"\n## {f}: {len(rows)} runs")
        if not rows:
            continue
        stage_tables(rows, a.top)
        solve_table(rows)
        count_table(rows)
    allrows = [r for rows in data[:1] for r in rows]
    if allrows:
        models(allrows)
    if len(data) > 1:
        compare(a.runs, data)
    if a.csv:
        keys = [k for k in data[0][0] if k != "steps"] if data and data[0] else []
        with open(a.csv, "w", newline="") as fp:
            w = csv.DictWriter(fp, fieldnames=["folder"] + keys, extrasaction="ignore")
            w.writeheader()
            for f, rows in zip(a.runs, data):
                for r in rows:
                    w.writerow(dict(r, folder=f))


if __name__ == "__main__":
    main()
