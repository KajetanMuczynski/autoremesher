#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""How well the pre-extraction map check (stage map_check) predicts output defects.

    map_check_eval.py RUN [--set corpus] [--work DIR] [--per-run]

RUN is a run folder of `ab.py run` or a ref (as in `ab.py compare`). Reads every replicate's
record.json (output topology from metrics.py) and stages.jsonl (map_check records, one per island,
of the kept attempt) and prints Markdown tables:

- per failure class (extra handle, lost handle, boundary loop split, boundary loop lost, any wrong
  topology, any non-quad, folded output quad): base rate over replicate-runs and, per predictor,
  precision, recall and lift (precision / base rate) of "predictor fires";
- per continuous predictor and class, the ROC AUC over replicate-runs;
- within runs whose replicates disagree on a class: how often the predictor separates the wrong
  replicates from the right ones (the only test that a gate could act on per run).

Genus per output: g = (2 components - boundary loops - euler) / 2, likewise for the input.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ab  # noqa: E402


def islands(root):
    path = os.path.join(root, "stages.jsonl")
    if not os.path.exists(path):
        return []
    return [r for r in (json.loads(line) for line in open(path) if line.strip()) if r.get("stage") == "map_check"]


def genus(components, loops, euler):
    return (2 * components - loops - euler) / 2


def labels(r):
    t = ((r.get("metrics") or {}).get("topology") or {})
    if not t or r.get("rc") != 0:
        return None
    gi = genus(t["components_input"], t["boundary_loops_input"], t["euler_input"])
    go = genus(t["components"], t["boundary_loops"], t["euler_output"])
    o = r.get("output") or {}
    sj = ((r.get("metrics") or {}).get("quads") or {}).get("sj_le_0") or 0
    return {
        "extra_handle": go > gi,
        "lost_handle": go < gi,
        "loop_split": t["boundary_loops"] > t["boundary_loops_input"],
        "loop_lost": t["boundary_loops"] < t["boundary_loops_input"],
        "wrong_topology": not t.get("same_as_input"),
        "non_quads": (o.get("non_quads") or 0) > 0,
        "folded_quads": sj > 0,
    }


def features(isl):
    s = lambda k: sum(i.get(k, 0) for i in isl)
    mn = lambda k, default: min([i[k] for i in isl if k in i and i[k] >= 0] or [default])
    f = {
        "bad_triangles": s("map_flipped") + s("map_degenerate"),
        "flipped": s("map_flipped"),
        "degenerate": s("map_degenerate"),
        "bad_clusters": s("map_bad_clusters"),
        "bad_clusters_at_cones": s("map_bad_clusters_at_cones"),
        "bad_clusters_at_boundary": s("map_bad_clusters_at_boundary"),
        "cones_in_folds": s("map_cones_in_folds"),
        "cone_pairs_colliding": s("map_cone_pairs_colliding"),
        "cones_off_grid": s("map_cones_off_grid"),
        "handle_loops_collapsed": s("map_handle_loops_collapsed"),
        "handle_loops_thin": s("map_handle_loops_thin"),
        "boundary_loops_pinched": s("map_boundary_loops_pinched"),
        "boundary_edges_collapsed": s("map_boundary_edges_collapsed"),
        "invalid_islands": sum(1 for i in isl if not i.get("map_valid", 1)),
        # Smaller is worse; negated so that larger is worse everywhere.
        "neg_cone_distance": -mn("map_cone_distance", 1.5),
        "neg_boundary_width": -mn("map_boundary_width", 1.5),
        "neg_handle_translation": -mn("map_handle_translation", 99.0),
    }
    return f


# Binary predictors: name -> (feature, threshold); fires when feature > threshold.
BINARY = [
    ("map invalid (any condition)", "invalid_islands", 0),
    ("any flipped/degenerate triangle", "bad_triangles", 0),
    ("fold cluster at a cone", "bad_clusters_at_cones", 0),
    ("fold cluster at the boundary", "bad_clusters_at_boundary", 0),
    ("colliding cone pair", "cone_pairs_colliding", 0),
    ("cone off the grid", "cones_off_grid", 0),
    ("collapsed handle loop", "handle_loops_collapsed", 0),
    ("handle loop <= 1 period", "handle_loops_thin", 0),
    ("pinched boundary loop (< 0.5 q)", "boundary_loops_pinched", 0),
    ("collapsed boundary edge", "boundary_edges_collapsed", 0),
]
CONTINUOUS = ["bad_triangles", "bad_clusters", "bad_clusters_at_cones", "cones_in_folds", "cone_pairs_colliding",
              "neg_cone_distance", "neg_boundary_width", "neg_handle_translation"]
CLASSES = ["extra_handle", "lost_handle", "loop_split", "loop_lost", "wrong_topology", "non_quads", "folded_quads"]


def auc(pos, neg):
    """P(a positive scores above a negative), ties half: Mann-Whitney."""
    if not pos or not neg:
        return None
    allv = sorted(pos + neg)
    ranks = {}
    i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j] == allv[i]:
            j += 1
        ranks[allv[i]] = (i + j + 1) / 2
        i = j
    rsum = sum(ranks[v] for v in pos)
    return (rsum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def fmt(x, digits=2):
    return "–" if x is None else f"{x:.{digits}f}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run")
    p.add_argument("--set", default="corpus")
    p.add_argument("--work", default=os.environ.get("AR_WORK", os.path.expanduser("~/ar-work")))
    p.add_argument("--per-run", action="store_true")
    a = p.parse_args()
    path = ab.resolve(a.run, a.work)
    runs = ab.load_runs(path, a.set)
    rows = []  # (run key, replicate, labels, features)
    missing = 0
    for key, reps in sorted(runs.items()):
        for u, r in sorted(reps.items()):
            lab = labels(r)
            root = os.path.join(path, a.set, key[0], f"{key[1]}-t{key[2]}", f"u{u}")
            isl = islands(root)
            if lab is None or not isl:
                missing += 1
                continue
            rows.append((key, u, lab, features(isl)))
    n = len(rows)
    print(f"## Map check vs output defects: {path} set {a.set}\n")
    print(f"{n} replicate-runs over {len(runs)} runs ({missing} without metrics or map_check records).\n")

    print("### Binary predictors\n")
    print("Per class: base rate (share of replicate-runs with the defect), then per predictor "
          "precision / recall / lift. Fires = share of replicate-runs where the predictor fires.\n")
    print("| predictor | fires | " + " | ".join(CLASSES) + " |")
    print("|---|---|" + "---|" * len(CLASSES))
    base = {c: sum(lab[c] for _, _, lab, _ in rows) / n if n else 0 for c in CLASSES}
    print("| *base rate* | | " + " | ".join(f"{base[c]:.3f} ({sum(lab[c] for _, _, lab, _ in rows)})" for c in CLASSES) + " |")
    for name, feat, thr in BINARY:
        fired = [lab for _, _, lab, f in rows if f[feat] > thr]
        cells = []
        for c in CLASSES:
            tp = sum(l[c] for l in fired)
            pos = sum(lab[c] for _, _, lab, _ in rows)
            prec = tp / len(fired) if fired else None
            rec = tp / pos if pos else None
            lift = prec / base[c] if prec is not None and base[c] else None
            cells.append(f"{fmt(prec)} / {fmt(rec)} / {fmt(lift, 1)}")
        print(f"| {name} | {len(fired) / n:.3f} | " + " | ".join(cells) + " |")

    print("\n### ROC AUC of the counts (0.5 = no information)\n")
    print("| feature | " + " | ".join(CLASSES) + " |")
    print("|---|" + "---|" * len(CLASSES))
    for feat in CONTINUOUS:
        cells = []
        for c in CLASSES:
            pos = [f[feat] for _, _, lab, f in rows if lab[c]]
            neg = [f[feat] for _, _, lab, f in rows if not lab[c]]
            cells.append(fmt(auc(pos, neg)))
        print(f"| {feat} | " + " | ".join(cells) + " |")

    print("\n### Within runs whose replicates disagree\n")
    print("Runs where some replicates have the defect and some don't (1-ulp inputs). Pairs = (wrong, right) "
          "replicate pairs in the same run; 'above' = share of pairs where the wrong replicate has the larger "
          "(worse) feature, ties half. 0.5 means the feature cannot tell the replicates apart.\n")
    by_run = {}
    for key, u, lab, f in rows:
        by_run.setdefault(key, []).append((lab, f))
    print("| class | mixed runs | pairs | " + " | ".join(CONTINUOUS) + " |")
    print("|---|---|---|" + "---|" * len(CONTINUOUS))
    for c in CLASSES:
        mixed = [v for v in by_run.values() if 0 < sum(l[c] for l, _ in v) < len(v)]
        pairs = [(fw, fr) for v in mixed for lw, fw in v if lw[c] for lr, fr in v if not lr[c]]
        cells = []
        for feat in CONTINUOUS:
            if not pairs:
                cells.append("–")
                continue
            s = sum(1.0 if fw[feat] > fr[feat] else 0.5 if fw[feat] == fr[feat] else 0.0 for fw, fr in pairs)
            cells.append(fmt(s / len(pairs)))
        print(f"| {c} | {len(mixed)} | {len(pairs)} | " + " | ".join(cells) + " |")

    if a.per_run:
        print("\n### Per run (replicates u0..uk): defects and map check\n")
        print("| mesh | res | target | wrong topology | extra / lost / split | invalid | bad tris | "
              "colliding cones | collapsed handles | pinched loops | min boundary width |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        for key, v in sorted(by_run.items()):
            col = lambda fn: " ".join(str(fn(l, f)) for l, f in v)
            print(f"| {key[0]} | {key[1]} | {key[2]} | {sum(l['wrong_topology'] for l, _ in v)}/{len(v)} | "
                  f"{sum(l['extra_handle'] for l, _ in v)}/{sum(l['lost_handle'] for l, _ in v)}/"
                  f"{sum(l['loop_split'] for l, _ in v)} | {col(lambda l, f: f['invalid_islands'])} | "
                  f"{col(lambda l, f: f['bad_triangles'])} | {col(lambda l, f: f['cone_pairs_colliding'])} | "
                  f"{col(lambda l, f: f['handle_loops_collapsed'])} | {col(lambda l, f: f['boundary_loops_pinched'])} | "
                  f"{col(lambda l, f: round(-f['neg_boundary_width'], 2))} |")


if __name__ == "__main__":
    main()
