#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""Score ab.py runs of the stress families (make_stress.py): what broke, and did the report say so.

    python stress_report.py --runs $AR_WORK/runs/<key> --manifest $AR_WORK/meshes/stress/manifest.json \
        [--csv out.csv] [--sets stress_thin,...]

Works on any ab.py set (`--sets corpus,closed`; AR_CORPUS sets too), the manifest only adds the probes.
Per run: exit status (crash, timeout), time, peak RSS, h0 = sqrt(input area / target), islands in and
out, Euler characteristic and boundary loops against the input, non-manifold output, folds, and, where
the generator stored probe points on the feature under test, how much of the feature survived:
`far_1h0`/`far_2h0`: share of the input area (20k seeded samples) farther than 1 / 2 h0 from the output, the
"lost parts" coverage rule; `island_far_1h0` the same for the worst input island (64 extra samples per island);
`far_max_h0` the largest sample distance in h0 (a lost limb or spike is a tiny share of the area). `collapsed_islands`: islands with less than half their planned quads.
`cleanup_kept`: smallest share of libQEx faces an island keeps through the cleanup passes.
`lost` is the fraction of probes farther than max(3 r, h0 / 2) from the output (r the feature's radius
or half-thickness; for crumbs the crumb radius s). A run is a **silent failure** when it has a defect
and the add-on panel (addon/quadami/report.py, run on the same report) shows no red row and no warning:
nothing on screen says anything went wrong. `panel_red` lists the red rows; a defect with only an
unrelated red row (say, non-quads for a lost part) is not silent but is still not named.
"""
import argparse
import csv
import glob
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_synthetic import read_obj  # noqa: E402

# The add-on's own panel logic decides what the user sees (no bpy needed).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                "addon", "quadami"))
import report as panel  # noqa: E402


# An island that keeps less than this share of its planned quads has collapsed (thin parts: 6 of 69;
# 0.25 missed two lost tubes at 0.25 and 0.27).
COLLAPSE_RATIO = 0.5
# Attached limbs vanish below a diameter of about 0.4-0.8 h0 (stress_attached, 2026-10-22).
THIN_H0 = 0.8


def read_quads(path):
    V, F = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                V.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("f "):
                idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
                for k in range(1, len(idx) - 1):
                    F.append([idx[0], idx[k], idx[k + 1]])
    return np.asarray(V, float), np.asarray(F, np.int64)


def feature_scale(params):
    for k in ("r", "s"):
        if k in params:
            return params[k]
    if "t" in params:
        return params["t"] / 2
    return 0.0


def probe_loss(out_obj, probes, scale, h0):
    import igl

    V, F = read_quads(out_obj)
    if len(F) == 0:
        return 1.0, float("inf")
    P = np.asarray(probes, float)
    d2, _, _ = igl.point_mesh_squared_distance(P, V, F)
    d = np.sqrt(d2)
    tol = max(3 * scale, 0.5 * h0)
    return float((d > tol).mean()), float(np.median(d) / h0)


_INPUTS = {}


def input_samples(path, n=20000, per_island=64):
    """Area, seeded samples of an input OBJ and the input island of each (cached per process): n
    area-weighted samples, plus per_island on every island so that small and thin islands are seen."""
    if path not in _INPUTS:
        import igl
        from scipy.sparse.csgraph import connected_components

        V, F = read_obj(path)
        a = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
        comp = connected_components(igl.adjacency_matrix(F), directed=False)[1][F[:, 0]]
        rng = np.random.default_rng(0)
        faces = [rng.choice(len(F), n, p=a / a.sum())]
        for c in np.unique(comp):
            idx = np.flatnonzero(comp == c)
            w = a[idx]
            if w.sum() > 0:
                faces.append(rng.choice(idx, per_island, p=w / w.sum()))
        f = np.concatenate(faces)
        u, v = rng.random(len(f)), rng.random(len(f))
        flip = u + v > 1
        u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
        P = V[F[f, 0]] + u[:, None] * (V[F[f, 1]] - V[F[f, 0]]) + v[:, None] * (V[F[f, 2]] - V[F[f, 0]])
        _INPUTS[path] = (float(a.sum()), P, comp[f], n)
    return _INPUTS[path]


def far_area(out_obj, samples, island, n_area, h0):
    """Coverage of the input by the output, in h0: share of the input area farther than 1 and 2 h0
    (area-weighted samples), the worst island's share farther than 1 h0 (per-island samples), and the
    largest distance of any sample (a limb or spike that is gone shows here, not in the area shares)."""
    import igl

    V, F = read_quads(out_obj)
    if len(F) == 0:
        return 1.0, 1.0, 1.0, float("inf")
    d = np.sqrt(igl.point_mesh_squared_distance(samples, V, F)[0])
    far = d > h0
    per = np.bincount(island, weights=far) / np.maximum(np.bincount(island), 1)
    return float(far[:n_area].mean()), float((d[:n_area] > 2 * h0).mean()), float(per.max()), float(d.max() / h0)


def local_thickness(path, n=4000, per_island=16, steps=48):
    """Pre-run input descriptor: local thickness at seeded points (n area-weighted, plus per_island on
    every island, so a thin part with little area is still sampled), by marching inward along the face
    normal until the generalized winding number drops below 1/2 (the point left the solid). Geometric
    steps from 1e-4 to 1 x the bounding-box diagonal; inf where the march never leaves (open or
    inconsistent surface). Returns (thickness per point, area each point stands for). Cached."""
    key = ("thick", path)
    if key not in _INPUTS:
        import igl
        from scipy.sparse.csgraph import connected_components

        V, F = read_obj(path)
        N = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        a = np.linalg.norm(N, axis=1)
        comp = connected_components(igl.adjacency_matrix(F), directed=False)[1][F[:, 0]]
        rng = np.random.default_rng(1)
        ok = a > 0
        f = [rng.choice(np.flatnonzero(ok), n, p=a[ok] / a[ok].sum())]
        w = [np.full(n, 0.5 * a.sum() / n)]
        for c in np.unique(comp):
            idx = np.flatnonzero((comp == c) & ok)
            if len(idx):
                f.append(rng.choice(idx, per_island, p=a[idx] / a[idx].sum()))
                w.append(np.zeros(per_island))  # extra points: detection only, no area weight
        f, w = np.concatenate(f), np.concatenate(w)
        c = V[F[f]].mean(1)
        nrm = N[f] / a[f, None]
        diag = float(np.linalg.norm(V.max(0) - V.min(0)))
        t = np.full(len(f), np.inf)
        for s in np.geomspace(1e-4, 1.0, steps) * diag:
            todo = np.isinf(t)
            if not todo.any():
                break
            wn = igl.fast_winding_number(V.astype(np.float64), F.astype(np.int64), c[todo] - s * nrm[todo])
            t[np.flatnonzero(todo)[wn < 0.5]] = s
        _INPUTS[key] = (t, w)
    return _INPUTS[key]


def cleanup_loss(run_dir):
    """Smallest share of libQEx's faces an island keeps through the cleanup passes (stage records
    `extractor` qex_faces vs `island` output_faces); None without libQEx records."""
    try:
        recs = [json.loads(line) for line in open(os.path.join(run_dir, "stages.jsonl")) if line.strip()]
    except (OSError, ValueError):
        return None
    qex = {r["island"]: r.get("qex_faces") for r in recs if r.get("stage") == "extractor"
           and r.get("superseded") != "yes" and r.get("used") == "qex"}
    kept = [r["output_faces"] / qex[r["island"]] for r in recs if r.get("stage") == "island"
            and qex.get(r.get("island")) and "output_faces" in r]
    return min(kept) if kept else None


def island_collapse(run_dir, ratio=COLLAPSE_RATIO):
    """Candidate post-run rule: islands whose output has fewer than `ratio` x the quads the core planned
    for them (stage record `island`: target_quads, output_faces). Returns (count, smallest ratio)."""
    try:
        recs = [json.loads(line) for line in open(os.path.join(run_dir, "stages.jsonl")) if line.strip()]
    except (OSError, ValueError):
        return None, None
    ratios = [r["output_faces"] / r["target_quads"] for r in recs
              if r.get("stage") == "island" and isinstance(r.get("target_quads"), (int, float)) and r["target_quads"] > 0
              and "output_faces" in r]
    if not ratios:
        return None, None
    return sum(x < ratio for x in ratios), min(ratios)


def score(rec, man, run_dir):
    m = man.get(rec["mesh"], {})
    target = rec["target"]
    src = (rec.get("metrics") or {}).get("input")
    area, samples, island, n_area = input_samples(src) if src and os.path.exists(src) \
        else (m.get("area", float("nan")), None, None, 0)
    h0 = math.sqrt(area / target)
    row = {"set": rec["set"], "mesh": rec["mesh"], "target": target, "rep": rec["replicate"], "rc": rec["rc"],
           "time": rec.get("time") or rec.get("wall"), "rss_mb": round(rec.get("peak_rss_mb", 0)),
           "h0": h0, "in_tris": m.get("triangles")}
    scale = feature_scale(m.get("params", {}))
    row["feature_over_h0"] = scale / h0 if scale else None
    try:
        rep = json.load(open(os.path.join(run_dir, "report.json")))
    except (OSError, ValueError):
        rep = {}
    out = rep.get("output", {})
    isl = rep.get("islands", {})
    row.update({"quads": out.get("quads"), "non_quads": out.get("non_quads"), "folds": out.get("folded_faces"),
                "nm_edges": out.get("non_manifold_edges"), "nm_verts": out.get("non_manifold_vertices"),
                "islands_in": isl.get("input"), "empty_islands": isl.get("without_output"),
                "holes": isl.get("holes"), "warnings": " | ".join(rep.get("warnings", [])),
                "status": rep.get("status"), "message": rep.get("message")})
    topo = (rec.get("metrics") or {}).get("topology", {})
    row.update({"comp_in": topo.get("components_input"), "comp_out": topo.get("components"),
                "euler_in": topo.get("euler_input"), "euler_out": topo.get("euler_output"),
                "loops_in": topo.get("boundary_loops_input"), "loops_out": topo.get("boundary_loops"),
                "same_topology": topo.get("same_as_input")})
    row["collapsed_islands"], row["min_island_ratio"] = island_collapse(run_dir)
    row["cleanup_kept"] = cleanup_loss(run_dir)
    if src and os.path.exists(src):
        t, w = local_thickness(src)
        # Thinnest point in h0, the points thinner than THIN_H0 x h0, and the area they stand for in h0^2.
        row["thick_min_h0"] = float(t.min() / h0)
        row["thin_points"] = int((t < THIN_H0 * h0).sum())
        row["thin_area_h0sq"] = float(w[t < THIN_H0 * h0].sum() / h0 ** 2)
    out_obj = os.path.join(run_dir, "out.obj")
    if samples is not None and rec["rc"] == 0 and os.path.exists(out_obj):
        row["far_1h0"], row["far_2h0"], row["island_far_1h0"], row["far_max_h0"] = \
            far_area(out_obj, samples, island, n_area, h0)
    if m.get("probes") and rec["rc"] == 0 and os.path.exists(out_obj):
        row["lost"], row["probe_med_h0"] = probe_loss(out_obj, m["probes"], scale, h0)
    defects = []
    if rec["rc"] != 0:
        defects.append("timeout" if rec["rc"] == "timeout" else f"exit {rec['rc']}")
    else:
        if row["comp_out"] is not None and row["comp_in"] is not None and row["comp_out"] < row["comp_in"]:
            defects.append(f"components {row['comp_in']}->{row['comp_out']}")
        if row["same_topology"] is False:
            defects.append(f"chi {row['euler_in']}->{row['euler_out']} loops {row['loops_in']}->{row['loops_out']}")
        if (row.get("lost") or 0) > 0.2:
            defects.append(f"feature lost {row['lost']:.0%}")
        if row["nm_edges"] or row["nm_verts"]:
            defects.append(f"non-manifold e{row['nm_edges']} v{row['nm_verts']}")
    row["defects"] = "; ".join(defects)
    # What the panel shows: its red rows and its warning lines (addon/quadami/report.py).
    red = [label for label, _, problem in panel.summary_rows(rep) if problem] if rep else []
    lines = [text for text, first, problem in panel.warning_lines(rep) if first and problem] if rep else []
    row["panel_red"] = ", ".join(red)
    shown = bool(red) or bool(lines) or rec["rc"] != 0
    row["silent"] = bool(defects) and not shown
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, help="an ab.py run folder: $AR_WORK/runs/<key>")
    ap.add_argument("--manifest", help="make_stress.py's manifest.json (probes, parameters); other sets need none")
    ap.add_argument("--sets", help="comma list; default every stress_* set found")
    ap.add_argument("--csv")
    ap.add_argument("--replicate0", action="store_true", help="only replicate u0 of each run")
    a = ap.parse_args()
    man = json.load(open(a.manifest)) if a.manifest else {}
    sets = a.sets.split(",") if a.sets else sorted(os.path.basename(p) for p in glob.glob(os.path.join(a.runs, "stress_*")))
    rows = []
    for s in sets:
        for path in sorted(glob.glob(os.path.join(a.runs, s, "*", "*", "u*", "record.json"))):
            if a.replicate0 and not path.endswith("/u0/record.json"):
                continue
            rows.append(score(json.load(open(path)), man, os.path.dirname(path)))
    cols = ["set", "mesh", "target", "rep", "rc", "time", "rss_mb", "h0", "feature_over_h0", "quads", "non_quads",
            "folds", "comp_in", "comp_out", "euler_in", "euler_out", "loops_in", "loops_out", "nm_edges", "nm_verts",
            "empty_islands", "holes", "collapsed_islands", "min_island_ratio", "cleanup_kept", "far_1h0", "far_2h0", "island_far_1h0", "far_max_h0", "thick_min_h0", "thin_points", "thin_area_h0sq", "lost", "probe_med_h0", "defects", "silent", "panel_red", "warnings", "message"]
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    def fmt(v):
        if isinstance(v, float):
            return f"{v:.3g}"
        return "" if v is None else str(v)

    short = ["mesh", "target", "rep", "rc", "time", "rss_mb", "feature_over_h0", "quads", "non_quads", "folds",
             "comp_in", "comp_out", "collapsed_islands", "lost", "defects", "silent", "warnings"]
    for s in sets:
        print(f"\n### {s}\n")
        print("| " + " | ".join(short) + " |")
        print("|" + "---|" * len(short))
        for r in rows:
            if r["set"] == s:
                print("| " + " | ".join(fmt(r.get(c)) for c in short) + " |")
    bad = [r for r in rows if r["defects"]]
    print(f"\n{len(rows)} runs, {len(bad)} with a defect, {sum(r['silent'] for r in rows)} silent.")


if __name__ == "__main__":
    main()
