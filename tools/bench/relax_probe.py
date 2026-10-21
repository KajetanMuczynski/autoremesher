#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline probe for TODO 2.8's tangential relaxation: how much quad shape is there to win
after the surface projection, and what does it cost in fidelity and crease coverage?

Takes the outputs of an `ab.py run` folder, relaxes each one in Python and writes the
relaxed OBJ next to it, then measures both with tools/bench/metrics.py plus the
TARGETS shape and crease rows (G1 SJ 1st percentile, G2 skew 95th percentile, A1).
No core change is needed to answer "is the headroom real". Used for TODO 2.8's relax
(research/surface-relax-2026-10-21.md); the shipped version is SurfaceProjector::relax(),
whose numbers come from ab.py.

Variants (--variant, plus --snap: first move vertices within --lock-dist h of a crease onto it,
--lock-bend: also fix vertices whose quads turn more than that from the vertex normal):
  laplace       uniform Laplacian, tangential part only (the TODO's literal idea; it also
                pulls edge lengths together, which fights sizing and anisotropy)
  parallelogram each quad corner's target is the corner that would make the quad a
                parallelogram (a + c - b); graded and anisotropic grids are fixed points,
                so it straightens angles without undoing the size field

Every variant: boundary vertices, vertices of non-quads and vertices within --lock-dist h of an
input edge sharper than --sharp-deg are fixed; moves are tangential, then the vertex goes to its
closest point on the input (dropped if that is farther than half the local edge); any face whose
scaled Jacobian falls below min(old, 0.1) or whose normal turns more than 60 degrees undoes its
vertices' moves, repeated until no face is bad.

  relax_probe.py --run-dir $AR_WORK/runs/<key> --meshes $AR_WORK/meshes --variant laplace --snap \
      --sharp-deg 90 --out probe.json
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import igl

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import metrics  # noqa: E402


def quad_sj(V, Q):
    P = V[Q]
    nxt = np.roll(P, -1, axis=1) - P
    prv = np.roll(P, 1, axis=1) - P
    n = np.cross(P[:, 2] - P[:, 0], P[:, 3] - P[:, 1])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-300)
    ln, lp = np.linalg.norm(nxt, axis=2), np.linalg.norm(prv, axis=2)
    sj = np.sum(np.cross(nxt, prv) * n[:, None, :], axis=2) / np.maximum(ln * lp, 1e-300)
    return sj.min(1), n


def sharp_edges(Vin, Fin, sharp_deg):
    he = np.concatenate([Fin[:, [0, 1]], Fin[:, [1, 2]], Fin[:, [2, 0]]])
    fid = np.tile(np.arange(len(Fin)), 3)
    key = he.min(1) * len(Vin) + he.max(1)
    order = np.argsort(key, kind="stable")
    key, he, fid = key[order], he[order], fid[order]
    _, start, cnt = np.unique(key, return_index=True, return_counts=True)
    man = cnt == 2
    f1, f2 = fid[start[man]], fid[start[man] + 1]
    n = np.cross(Vin[Fin[:, 1]] - Vin[Fin[:, 0]], Vin[Fin[:, 2]] - Vin[Fin[:, 0]])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-300)
    ang = np.degrees(np.arccos(np.clip(np.sum(n[f1] * n[f2], 1), -1, 1)))
    return he[start[man]][ang > sharp_deg]


def dist_to_segments(P, A, B, h):
    """Distance from each P to the nearest segment AB (exact for segments within ~2 h) and that point."""
    from scipy.spatial import cKDTree
    if len(A) == 0:
        return np.full(len(P), np.inf), P.copy()
    L = np.linalg.norm(B - A, axis=1)
    ns = np.maximum(1, np.ceil(L / (h / 2)).astype(int))
    idx = np.repeat(np.arange(len(A)), ns)
    t = (np.concatenate([np.arange(k) for k in ns]) + 0.5) / ns[idx]
    S = A[idx] + t[:, None] * (B - A)[idx]
    _, nn = cKDTree(S).query(P, k=min(8, len(S)))
    nn = nn.reshape(len(P), -1)
    best = np.full(len(P), np.inf)
    at = P.copy()
    for j in range(nn.shape[1]):
        e = idx[nn[:, j]]
        d = B[e] - A[e]
        tt = np.clip(np.sum((P - A[e]) * d, 1) / np.maximum(np.sum(d * d, 1), 1e-300), 0, 1)
        X = A[e] + tt[:, None] * d
        dist = np.linalg.norm(P - X, axis=1)
        better = dist < best
        best[better] = dist[better]
        at[better] = X[better]
    return best, at


def guarded_apply(V, Vn, move, Q, sj_old, n_old, stats):
    """Undo the moves around every face that a move made worse than min(old, 0.1) or turned > 60 deg."""
    for _guard in range(20):
        sj_new, n_new = quad_sj(Vn, Q)
        bad = (sj_new < np.minimum(sj_old, 0.1)) & (sj_new < sj_old) | (np.sum(n_new * n_old, 1) < 0.5)
        if not bad.any():
            break
        back = np.zeros(len(V), bool)
        back[Q[bad].ravel()] = True
        back &= move
        if not back.any():
            break
        stats["undone"] += int(back.sum())
        Vn[back] = V[back]
        move &= ~back
    return Vn, move


def relax(V, faces, Vin, Fin, variant, iterations, step, sharp_deg, lock_dist, snap, lock_bend=180.0):
    V = V.copy()
    nv = len(V)
    Q = np.array([f for f in faces if len(f) == 4], dtype=np.int64).reshape(-1, 4)
    he = np.array([(f[i], f[(i + 1) % len(f)]) for f in faces for i in range(len(f))], dtype=np.int64)
    key = he.min(1) * nv + he.max(1)
    uniq, counts = np.unique(key, return_counts=True)
    E = np.stack([uniq // nv, uniq % nv], 1)
    h = float(np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1).mean())
    locked = np.ones(nv, bool)
    locked[np.unique(Q)] = False
    for f in faces:
        if len(f) != 4:
            locked[list(f)] = True
    locked[E[counts != 2].ravel()] = True
    sharp = sharp_edges(Vin, Fin, sharp_deg)
    if len(sharp):
        dsharp, onsharp = dist_to_segments(V, Vin[sharp[:, 0]], Vin[sharp[:, 1]], h)
    else:
        dsharp, onsharp = np.full(nv, np.inf), V.copy()
    near = dsharp < lock_dist * h
    stats_snapped = 0
    if snap and near.any():
        # Feature-aware projection: vertices next to an input crease go onto it.
        sj_old, n_old = quad_sj(V, Q)
        move = near & ~locked
        Vn = V.copy()
        Vn[move] = onsharp[move]
        V, move = guarded_apply(V, Vn, move, Q, sj_old, n_old, {"undone": 0})
        stats_snapped = int(move.sum())
    locked |= near
    # Local edge length per vertex (mean of incident edges): the move limit.
    el = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    hv = np.bincount(E.ravel(), np.repeat(el, 2), minlength=nv) / np.maximum(np.bincount(E.ravel(), minlength=nv), 1)
    if lock_bend < 180.0:
        # Output-side feature: a vertex whose quads bend away from its normal by more than lock_bend
        # (a rounded rim the input has no sharp edge for) stays.
        _, qn = quad_sj(V, Q)
        vn = np.zeros_like(V)
        for i in range(4):
            np.add.at(vn, Q[:, i], qn)
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-300)
        mincos = np.ones(nv)
        for i in range(4):
            np.minimum.at(mincos, Q[:, i], np.sum(qn * vn[Q[:, i]], 1))
        locked |= mincos < np.cos(np.radians(lock_bend))
    free = ~locked
    stats = {"vertices": nv, "locked_feature": int(near.sum()), "locked": int(locked.sum()),
             "undone": 0, "far": 0, "snapped": stats_snapped}
    deg = np.bincount(E.ravel(), minlength=nv).astype(float)
    for _ in range(iterations):
        sj_old, n_old = quad_sj(V, Q)
        if variant == "laplace":
            tgt = np.zeros_like(V)
            np.add.at(tgt, E[:, 0], V[E[:, 1]])
            np.add.at(tgt, E[:, 1], V[E[:, 0]])
            tgt /= np.maximum(deg, 1)[:, None]
        else:
            tgt = np.zeros_like(V)
            cnt = np.zeros(nv)
            for i in range(4):
                a, b, c, v = Q[:, (i + 1) % 4], Q[:, (i + 2) % 4], Q[:, (i + 3) % 4], Q[:, i]
                np.add.at(tgt, v, V[a] + V[c] - V[b])
                np.add.at(cnt, v, 1)
            tgt /= np.maximum(cnt, 1)[:, None]
        # Vertex normals from the quads' diagonal normals.
        vn = np.zeros_like(V)
        for i in range(4):
            np.add.at(vn, Q[:, i], n_old)
        vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-300)
        d = step * (tgt - V)
        d -= np.sum(d * vn, 1, keepdims=True) * vn
        cand = V + d
        _, _, C = igl.point_mesh_squared_distance(cand, Vin, Fin)
        far = np.linalg.norm(C - V, axis=1) > 0.5 * hv
        move = free & ~far
        stats["far"] += int((free & far).sum())
        Vn = V.copy()
        Vn[move] = C[move]
        V, _ = guarded_apply(V, Vn, move, Q, sj_old, n_old, stats)
    return V, stats


def write_obj(path, V, faces):
    with open(path, "w") as fp:
        for v in V:
            fp.write("v %.9g %.9g %.9g\n" % tuple(v))
        for f in faces:
            fp.write("f " + " ".join(str(i + 1) for i in f) + "\n")


def shape_rows(inp, out):
    m = metrics.compute(inp, out, samples=100000)
    q, d = m.get("quads") or {}, m.get("distance") or {}
    return {"sj_p1": q.get("sj_p1"), "sj_p5": q.get("sj_p5"), "skew_p95": q.get("skew_p95"),
            "normal_dev_mean": (m.get("normal_deviation_deg") or {}).get("mean"),
            "vertex_dist_median": d.get("vertex_to_in_median"),
            "feature_coverage": (m.get("creases") or {}).get("coverage"),
            "sj_le_0": q.get("sj_le_0"), "aspect_mean": q.get("aspect_mean"),
            "edge_cv": (m.get("edge_length") or {}).get("cv"),
            "in_out_mean": d.get("in_to_out_mean"), "in_out_p99": d.get("in_to_out_p99"),
            "flipped_vs_input": (m.get("flipped") or {}).get("faces_vs_input")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--meshes", required=True)
    ap.add_argument("--variant", default="parallelogram", choices=["laplace", "parallelogram", "none"])
    ap.add_argument("--snap", action="store_true", help="first move vertices within --lock-dist h of a crease onto it")
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--sharp-deg", type=float, default=40.0)
    ap.add_argument("--lock-dist", type=float, default=0.25)
    ap.add_argument("--only", default="")
    ap.add_argument("--set", default="*")
    ap.add_argument("--lock-bend", type=float, default=180.0, help="also fix vertices whose quads turn more than this from the vertex normal")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    corpus = {m["id"]: m for m in json.load(open(os.path.join(HERE, "corpus.json")))["meshes"]}
    rows = []
    tag = "%s-i%d-s%g-l%g%s-b%g" % (a.variant, a.iterations, a.step, a.lock_dist, "-snap" if a.snap else "", a.lock_bend)
    for rec in sorted(glob.glob(os.path.join(a.run_dir, a.set, "*", "*", "u0", "record.json"))):
        d = os.path.dirname(rec)
        mesh = d.split(os.sep)[-3]
        if a.only and mesh not in a.only.split(","):
            continue
        out = os.path.join(d, "out.obj")
        if not os.path.exists(out):
            continue
        inp = os.path.join(a.meshes, corpus[mesh]["file"])
        Vin, fin = metrics.read_obj(inp)
        Fin = np.asarray(metrics.triangulate(fin), dtype=np.int64)
        V, faces = metrics.read_obj(out)
        t0 = time.time()
        Vr, st = relax(V, faces, Vin, Fin, a.variant, 0 if a.variant == "none" else a.iterations, a.step, a.sharp_deg,
                       a.lock_dist, a.snap, a.lock_bend)
        dt = time.time() - t0
        rout = os.path.join(d, "relax-%s.obj" % tag)
        write_obj(rout, Vr, faces)
        row = {"mesh": mesh, "run": d.split(os.sep)[-2], "relax_s": dt, **st,
               "base": shape_rows(inp, out), "relaxed": shape_rows(inp, rout)}
        rows.append(row)
        print(json.dumps(row), flush=True)
    json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
