#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn runs/<...>/summary.json into Markdown tables (stdout) and a flat CSV.

    python summarize.py runs/corpus/summary.json [--csv runs/corpus/summary.csv]
"""
import argparse
import csv
import json
import math
from collections import defaultdict


def g(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d


def fmt(x, nd=2):
    if x is None:
        return "–"
    if isinstance(x, float):
        if math.isnan(x):
            return "–"
        return ("%." + str(nd) + "f") % x
    return str(x)


def flat(r):
    b, m, ph = r.get("bench", {}), r.get("metrics", {}), r.get("phases_ms", {})
    iso = ph.get("Isotropic remesh (accumulated)", 0) + ph.get("Adaptive target length field (accumulated)", 0) \
        + r.get("phase_extra", {}).get("decimate_ms", 0)
    par, ext = ph.get("Parameterize (accumulated)", 0), ph.get("Quad extract (accumulated)", 0)
    acc = max(iso + par + ext, 1e-9)
    uv_t = g(b, "param", "iso_triangles") or 0
    solver = g(r, "probe", "solver_by_step", default={}) or {}
    cls_ms = sum(s["total_ms"] for s in solver.values())
    fac_ms = sum(s["analyze_ms"] + s["factor_ms"] for s in solver.values())
    rounds = g(r, "probe", "cleanup_rounds", default={}) or {}
    rnd = g(r, "probe", "rounding", default=[]) or []
    return {
        "mesh": r["mesh"], "category": r["category"], "target": r["target"], "tag": r.get("tag", ""),
        "threads": g(b, "params", "threads"), "rc": r["rc"],
        "input_tris": b.get("input_triangles"), "islands": g(r, "phase_extra", "islands"),
        "decimated_to": g(r, "phase_extra", "decimate_out"),
        "time_s": r.get("remesh_s_median"), "load_obj_s": g(b, "time_s", "load_obj"),
        "iso_pct": 100 * iso / acc, "param_pct": 100 * par / acc, "extract_pct": 100 * ext / acc,
        "cores_busy": g(r, "phase_extra", "cores_busy"), "cpu_util": b.get("cpu_utilisation"),
        "peak_rss_mb": g(b, "rss_mb", "peak"),
        "iso_tris": uv_t, "quads": g(b, "result", "quads"), "non_quads": g(b, "result", "non_quads"),
        "quads_over_target": (g(b, "result", "quads") or 0) / r["target"],
        "sing_before": g(r, "singularity_simplifier", "before") if g(r, "singularity_simplifier", "islands") else None, "sing_after": g(b, "param", "singularities"),
        "uv_flipped": g(b, "param", "uv_flipped"), "uv_degenerate": g(b, "param", "uv_degenerate"),
        "uv_flipped_pct": 100.0 * (g(b, "param", "uv_flipped") or 0) / max(uv_t, 1),
        "irregular": g(m, "valence", "irregular_interior"), "irregular_per_1k": g(m, "valence", "irregular_per_1k_quads"),
        "val3": g(m, "valence", "valence3"), "val5": g(m, "valence", "valence5"), "val6p": g(m, "valence", "valence6plus"),
        "angle_dev_mean": g(m, "quads", "angle_dev_mean"), "angle_dev_p95": g(m, "quads", "angle_dev_p95"),
        "sj_lt_05_pct": 100 * (g(m, "quads", "sj_lt_0.5") or 0), "sj_le_0": g(m, "quads", "sj_le_0"),
        "aspect_p95": g(m, "quads", "aspect_p95"),
        "degenerate": g(m, "degenerate", "faces"), "flipped_vs_input": g(m, "flipped", "faces_vs_input"),
        "non_manifold_edges": g(m, "topology", "non_manifold_edges"),
        "inconsistent_edges": g(m, "topology", "inconsistently_oriented_edges"),
        "euler_in": g(m, "topology", "euler_input"), "euler_out": g(m, "topology", "euler_output"),
        "components_in": g(m, "topology", "components_input"), "components_out": g(m, "topology", "components"),
        "hausdorff_pct": 100 * (g(m, "distance", "hausdorff") or float("nan")),
        "mean_dist_pct": 100 * (g(m, "distance", "out_to_in_mean") or float("nan")),
        "in_to_out_p99_pct": 100 * (g(m, "distance", "in_to_out_p99") or float("nan")),
        "sym_topo_mean": g(m, "symmetry", "topo_vertex_rel_edge_mean"),
        "sym_matched_pct": 100 * g(m, "symmetry", "topo_matched_lt_0.1_edge", default=float("nan")),
        "sym_geo_mean_pct": 100 * g(m, "symmetry", "output_reflection_mean", default=float("nan")),
        "param_ms": par, "solver_ms": cls_ms, "factor_ms": fac_ms,
        "solver_pct_of_param": 100 * cls_ms / par if par else None,
        "max_n": max([s["max_n"] for s in solver.values()] or [None]) if solver else None,
        "max_factor_nnz": max([s["max_factor_nnz"] for s in solver.values()] or [None]) if solver else None,
        "int_vars": sum(x["integer_variables"] for x in rnd) if rnd else None,
        "rounding_iterations": max([x["iterations"] for x in rnd] or [None]) if rnd else None,
        "fixed_in_one_pass_pct": (100.0 * sum(max(x["fixed_per_iteration"]) for x in rnd)
                                  / max(sum(x["integer_variables"] for x in rnd), 1)) if rnd else None,
        "max_round_dist": max([x["max_rounding_distance"] for x in rnd] or [None]) if rnd else None,
        "merge5_rounds": g(rounds, "mergeSharedFiveEdgeFaces", "rounds"),
        "cleanup_rounds": sum(v["rounds"] for v in rounds.values()) if rounds else None,
        "cleanup_faces_scanned": sum(v["faces_scanned"] for v in rounds.values()) if rounds else None,
        "extract_ms": ext, "same_result_probe": g(r, "probe", "same_result"),
    }


def table(rows, cols, headers):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(fmt(r.get(c[0]), c[1]) if isinstance(c, tuple) else fmt(r.get(c))
                                    for c in cols) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary")
    ap.add_argument("--csv")
    args = ap.parse_args()
    recs = json.load(open(args.summary))
    rows = [flat(r) for r in recs]
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    print("### Time and memory\n")
    print(table(rows, ["mesh", "target", "input_tris", "islands", ("time_s", 2), ("iso_pct", 0), ("param_pct", 0),
                       ("extract_pct", 0), ("cores_busy", 2), ("peak_rss_mb", 0)],
                ["mesh", "target", "input tris", "islands", "time s", "iso %", "param %", "extract %", "cores busy",
                 "peak RSS MB"]))
    print("\n### Output quality\n")
    print(table(rows, ["mesh", "target", "quads", ("quads_over_target", 2), "non_quads", "irregular",
                       ("irregular_per_1k", 1), ("angle_dev_mean", 1), ("angle_dev_p95", 1), ("sj_lt_05_pct", 2),
                       "sj_le_0", "flipped_vs_input", "degenerate", "non_manifold_edges", ("hausdorff_pct", 2),
                       ("mean_dist_pct", 3)],
                ["mesh", "target", "quads", "quads/target", "non-quads", "irregular v", "irr/1k q",
                 "angle dev mean °", "angle dev p95 °", "SJ<0.5 %", "SJ≤0", "flipped", "degenerate", "non-manifold e",
                 "Hausdorff %diag", "mean dist %diag"]))
    print("\n### Parametrization (M1/M2) and extraction cleanup (P3)\n")
    print(table(rows, ["mesh", "target", "iso_tris", "sing_before", "sing_after", "uv_flipped", ("uv_flipped_pct", 2),
                       "int_vars", "rounding_iterations", ("fixed_in_one_pass_pct", 0), ("max_round_dist", 3),
                       "merge5_rounds", "cleanup_rounds", ("extract_ms", 0)],
                ["mesh", "target", "param tris", "sing. before", "sing. after", "UV flipped", "UV flipped %",
                 "int vars", "rounding iters", "% fixed in one pass", "max |x−round(x)|", "merge-5 rounds",
                 "cleanup rounds", "extract ms"]))
    print("\n### Sparse solves (P2)\n")
    print(table(rows, ["mesh", "target", ("param_ms", 0), ("solver_ms", 0), ("solver_pct_of_param", 0),
                       ("factor_ms", 0), "max_n", "max_factor_nnz"],
                ["mesh", "target", "param ms", "all solves ms", "solves % of param", "analyze+factor ms",
                 "largest n", "largest nnz(L)"]))
    sym = [r for r in rows if r.get("sym_topo_mean") is not None]
    if sym:
        print("\n### Symmetry\n")
        print(table(sym, ["mesh", "target", ("sym_geo_mean_pct", 3), ("sym_topo_mean", 2), ("sym_matched_pct", 1)],
                    ["mesh", "target", "geometric reflection error %diag", "topological error (mean, edge lengths)",
                     "% vertices with mirror partner < 0.1 edge"]))
    # Step-level hot spots summed over runs.
    steps = defaultdict(float)
    for r in recs:
        for k, v in r.get("steps_ms", {}).items():
            steps[k] += v
    total = sum(steps.values()) or 1
    print("\n### Named steps, summed over all runs\n")
    print("| step | total s | share % |\n|---|---|---|")
    for k, v in sorted(steps.items(), key=lambda kv: -kv[1])[:20]:
        print("| %s | %.1f | %.1f |" % (k, v / 1000, 100 * v / total))


if __name__ == "__main__":
    main()
