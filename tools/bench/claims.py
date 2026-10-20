#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Aggregate the numbers behind each REFERENCE.md claim from the run summaries.

    python claims.py --runs runs        (expects runs/corpus, runs/threads, runs/ladder,
                                         runs/alloc, runs/adaptivity)

Solver and rounding figures come from the core's stage diagnostics. Extractor cleanup rounds
(P3) were measured by the retired probes.patch and are not recorded until TODO 2.4.
"""
import argparse
import json
import os
import statistics as st
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr

CLEANUP_STEPS = ["Splitting seven edge faces", "Splitting six edge faces", "Cleaning up triangles",
                 "Merging shared five edge faces", "Switching high valence edges",
                 "Converting triangle and five edge fans", "Collapsing three valence diagonals",
                 "Merging double shared edge quads", "Merging three and five valence triangles",
                 "Collapsing three valence corners", "Splitting high valence triangle fans",
                 "Collapsing three valence edge pairs"]


def load(path):
    return json.load(open(path)) if os.path.exists(path) else []


def acc(r):
    ph = r.get("phases_ms", {})
    iso = ph.get("Isotropic remesh (accumulated)", 0) + ph.get("Adaptive target length field (accumulated)", 0) \
        + r.get("phase_extra", {}).get("decimate_ms", 0)
    return iso, ph.get("Parameterize (accumulated)", 0), ph.get("Quad extract (accumulated)", 0)


def corpus_section(recs):
    print("## Corpus aggregates\n")
    ok = [r for r in recs if r.get("bench")]
    print("runs: %d, failed: %d" % (len(ok), len(recs) - len(ok)))
    by_t = defaultdict(list)
    for r in ok:
        by_t[r["target"]].append(r)
    print("\n| target | runs | iso % | param % | extract % (mean over meshes) | solves % of total | curl step % of total | "
          "cleanup % of extract | quads/target median [min, max] | peak RSS MB median [max] |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for t in sorted(by_t):
        rs = by_t[t]
        sh = np.array([acc(r) for r in rs], float)
        sh = sh / sh.sum(1, keepdims=True) * 100
        solver = [sum(s["total_ms"] for s in r["stages"]["solver_by_stage"].values()) / (1000 * r["remesh_s_median"])
                  * 100 for r in rs if r.get("stages")] or [float("nan")]
        curl = [r["steps_ms"].get("Correcting field curl", 0) / (1000 * r["remesh_s_median"]) * 100 for r in rs]
        clean = [sum(r["steps_ms"].get(s, 0) for s in CLEANUP_STEPS) / max(acc(r)[2], 1e-9) * 100 for r in rs]
        q = [r["bench"]["result"]["quads"] / t for r in rs]
        rss = [r["bench"]["rss_mb"]["peak"] for r in rs]
        print("| %d | %d | %.0f | %.0f | %.0f | %.0f | %.0f | %.0f | %.2f [%.2f, %.2f] | %.0f [%.0f] |" % (
            t, len(rs), *sh.mean(0), st.mean(solver), st.mean(curl), st.mean(clean), st.median(q), min(q), max(q),
            st.median(rss), max(rss)))

    cores = [r["phase_extra"].get("cores_busy") for r in ok]
    print("\ncores busy across parallel phase: min %.2f max %.2f (islands>1: %s)" % (
        min(cores), max(cores), sorted({(r["mesh"], r["phase_extra"].get("islands"), r["phase_extra"].get("cores_busy"))
                                         for r in ok if r["phase_extra"].get("islands", 1) > 1})))

    rnd = [x for r in ok if r.get("stages") for x in r["stages"]["rounding"]]
    if rnd:
        it = [x["iterations"] for x in rnd]
        print("\nM1 rounding: %d island solves, passes median %d max %d; max |x-round(x)| median %.3f max %.3f; "
              "mean |x-round(x)| median %.3f" % (
                  len(rnd), st.median(it), max(it), st.median(x["max_rounding_shift"] for x in rnd),
                  max(x["max_rounding_shift"] for x in rnd), st.median(x["mean_rounding_shift"] for x in rnd)))

    flips = [r["bench"]["param"]["uv_flipped"] for r in ok]
    pct = [100 * r["bench"]["param"]["uv_flipped"] / max(r["bench"]["param"]["iso_triangles"], 1) for r in ok]
    print("M2 UV flips: runs with >0 flipped param triangles %d/%d; flipped %% median %.2f max %.2f" % (
        sum(f > 0 for f in flips), len(flips), st.median(pct), max(pct)))

    xs = [(100 * r["bench"]["param"]["uv_flipped"] / max(r["bench"]["param"]["iso_triangles"], 1),
           sum(r["steps_ms"].get(s, 0) for s in CLEANUP_STEPS) / max(acc(r)[2], 1e-9),
           r["metrics"]["valence"]["irregular_per_1k_quads"] if r.get("metrics") else np.nan)
          for r in ok]
    a = np.array(xs, float)
    print("P3: cleanup rounds per loop not recorded (probes.patch retired; TODO 2.4)")
    for name, col in (("cleanup share of extract", 1), ("irregular per 1k quads", 2)):
        rho, p = spearmanr(a[:, 0], a[:, col], nan_policy="omit")
        print("   Spearman(UV flipped %%, %s) = %.2f (p=%.3f)" % (name, rho, p))
    # Empirical complexity: log-log slope of stage time against parametrization size.
    n = np.array([r["bench"]["param"]["iso_triangles"] for r in ok], float)
    for name, idx in (("parameterize", 1), ("extract", 2)):
        y = np.array([acc(r)[idx] for r in ok], float)
        m = (n > 0) & (y > 0)
        slope = np.polyfit(np.log(n[m]), np.log(y[m]), 1)[0]
        print("   log-log slope of %s time vs param triangles: %.2f" % (name, slope))
    y = np.array([r["steps_ms"].get("Merging shared five edge faces", 0) for r in ok], float)
    m = (n > 0) & (y > 0)
    print("   log-log slope of merge-5 step time vs param triangles: %.2f" % np.polyfit(np.log(n[m]), np.log(y[m]), 1)[0])
    big = max(ok, key=lambda r: r["steps_ms"].get("Merging shared five edge faces", 0))
    print("   slowest merge-5 step: %s t=%d (%.0f ms in that step, extract %.0f ms)" % (
        big["mesh"], big["target"], big["steps_ms"].get("Merging shared five edge faces", 0), acc(big)[2]))

    # RSS is a high-water mark (glibc rarely returns memory), so attribute the peak to the first
    # step that reaches 95% of it rather than to the last step that still shows it.
    peaks = defaultdict(int)
    for r in ok:
        steps = r["bench"]["step_peak_rss_mb"]
        top = max(s[1] for s in steps)
        peaks[next(s[0] for s in steps if s[1] >= 0.95 * top)] += 1
    print("step where RSS first reaches 95% of its peak:", dict(peaks))

    tot = defaultdict(float)
    for r in ok:
        for k, v in r["steps_ms"].items():
            tot[k] += v
    s = sum(tot.values())
    print("\ntop steps (summed over corpus): " + "; ".join("%s %.0f%%" % (k, 100 * v / s)
                                                           for k, v in sorted(tot.items(), key=lambda kv: -kv[1])[:8]))


def threads_section(recs):
    if not recs:
        return
    print("\n## Threads (P1)\n\n| mesh | islands | 1 thread s | all threads s | speedup | cores busy (all) |\n|---|---|---|---|---|---|")
    by = defaultdict(dict)
    for r in recs:
        by[r["mesh"]][r["tag"]] = r
    for m, d in by.items():
        a, b = d.get("thr1-"), d.get("thr0-")
        if a and b:
            print("| %s | %s | %.2f | %.2f | %.2f | %.2f |" % (m, b["phase_extra"].get("islands"), a["remesh_s_median"],
                                                              b["remesh_s_median"],
                                                              a["remesh_s_median"] / b["remesh_s_median"],
                                                              b["phase_extra"].get("cores_busy")))


def ladder_section(recs):
    if not recs:
        return
    print("\n## Input-size ladder (P4, P6)\n\n| mesh | target | input tris | load OBJ s | decimate s | adaptive field s | "
          "isotropic s | parameterize s | extract s | total s | peak RSS MB |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(recs, key=lambda r: (r["target"], r["bench"]["input_triangles"] if r.get("bench") else 0)):
        if not r.get("bench"):
            print("| %s | %d | failed rc=%s |" % (r["mesh"], r["target"], r["rc"]))
            continue
        ph = r["phases_ms"]
        print("| %s | %d | %d | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.0f |" % (
            r["mesh"], r["target"], r["bench"]["input_triangles"], r["bench"]["time_s"]["load_obj"],
            r["phase_extra"].get("decimate_ms", 0) / 1000, ph.get("Adaptive target length field (accumulated)", 0) / 1000,
            ph.get("Isotropic remesh (accumulated)", 0) / 1000, ph.get("Parameterize (accumulated)", 0) / 1000,
            ph.get("Quad extract (accumulated)", 0) / 1000, r["remesh_s_median"], r["bench"]["rss_mb"]["peak"]))


def alloc_section(recs):
    if not recs:
        return
    print("\n## Allocator (P5)\n\n| mesh | target | glibc s (median of 3) | tbbmalloc s | speedup | same quads |\n|---|---|---|---|---|---|")
    by = defaultdict(dict)
    for r in recs:
        by[(r["mesh"], r["target"])][r["tag"]] = r
    for (m, t), d in sorted(by.items()):
        a, b = d.get("glibc-"), d.get("tbbmalloc-")
        if a and b:
            print("| %s | %d | %.2f | %.2f | %.2f× | %s |" % (m, t, a["remesh_s_median"], b["remesh_s_median"],
                                                         a["remesh_s_median"] / b["remesh_s_median"],
                                                         a["bench"]["result"] == b["bench"]["result"]))


def adapt_section(recs, corpus):
    if not recs:
        return
    base = {(r["mesh"], r["target"]): r for r in corpus if r.get("bench")}
    print("\n## Quad count vs target (M7)\n\n| mesh | target | default quads/target | adaptivity 0 | adaptivity 0, anisotropy 0 |\n|---|---|---|---|---|")
    by = defaultdict(dict)
    for r in recs:
        by[(r["mesh"], r["target"])][r["tag"]] = r
    for (m, t), d in sorted(by.items()):
        b = base.get((m, t))
        f = lambda r: "%.2f" % (r["bench"]["result"]["quads"] / t) if r and r.get("bench") else "–"
        print("| %s | %d | %s | %s | %s |" % (m, t, f(b), f(d.get("adapt0-")), f(d.get("adapt0-aniso0-"))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    a = ap.parse_args()
    corpus = load(os.path.join(a.runs, "corpus", "summary.json"))
    corpus_section(corpus)
    threads_section(load(os.path.join(a.runs, "threads", "summary.json")))
    ladder_section(load(os.path.join(a.runs, "ladder", "summary.json")))
    alloc_section(load(os.path.join(a.runs, "alloc", "summary.json")))
    adapt_section(load(os.path.join(a.runs, "adaptivity", "summary.json")), corpus)


if __name__ == "__main__":
    main()
