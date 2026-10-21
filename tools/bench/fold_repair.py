#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""Offline prototype of a local fold repair for sculpted input (TODO 2.19 candidate; research, not in the core).

    fold_repair.py IN.obj OUT.obj [--radius R] [--max-rings 8] [--passes 3] [--json report.json]

Folded input (sculpt_report.input_folds: pleats, twists, over-pinched creases) is where nearly all
defects of the 2026-10-21 real-sculpt tests sat. Per fold cluster this moves only the vertices of the
folded faces and k rings around them (k = 1, 2, ... up to --max-rings), in a chart:

  1. project the free vertices and one fixed ring onto the plane of the mean normal N of the surface within the
     detector radius of the fold (the same normal the fold was detected against), keeping each height along N;
  2. untangle the free vertices in 2D with the fixed ring held: Tutte (uniform weights) gives a flip-free
     embedding when the fixed ring is star-shaped enough, and it is checked, not assumed;
  3. blend back towards the original 2D positions as far as every patch triangle stays positive
     (bisection on t in p = tutte + t (orig - tutte)), then pull each vertex back on its own as far as its faces
     stay positive, so a vertex moves as little as the fold allows;
  4. set each moved vertex's height to the original surface's under its new chart position (the unfolded sheet
     nearest its own height), so it stays on the input surface;
  5. re-run the fold detector on the surface around the patch; while it still flags a patch face, try a larger
     patch, and keep the first chart-valid one if none comes out clean (reported as still_flagged).

A patch whose Tutte embedding flips (the fixed ring is not star-shaped enough in the chart), which is not a
disk, or which touches a non-manifold edge gets one more ring, and a neighbouring fold in the fixed ring joins
it; after --max-rings it is skipped and reported. Faces are never added, removed or re-connected: only vertex
positions change, so the OBJ keeps its faces and order.
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from metrics import read_obj  # noqa: E402
from sculpt_report import input_folds  # noqa: E402


MIN_COS = 0.0  # > 0: every patch face also ends within acos(MIN_COS) of the chart normal


def triangulate(faces):
    tris, owner = [], []
    for i, f in enumerate(faces):
        for k in range(1, len(f) - 1):
            tris.append([f[0], f[k], f[k + 1]])
            owner.append(i)
    return np.array(tris, np.int64), np.array(owner)


def vertex_adjacency(F, nv):
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nv, nv)).tocsr()
    A.data[:] = 1
    return A


def edge_use(F):
    E = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    uniq, cnt = np.unique(E, axis=0, return_counts=True)
    return {tuple(e): c for e, c in zip(uniq, cnt)}


def signed_area2(P, T):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    return (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])


def resample_heights(uv0, w, T, Pq, wq):
    """Height of the original surface at the new chart positions Pq: over the patch triangles that are positive
    in the original chart (the unfolded sheet), the one under each point whose height is closest to the vertex's
    own. Keeps a moved vertex on the original surface instead of at its old height above the plane, which on a
    curved patch would leave it by about move^2 / (2 radius). Points over no such triangle keep their height."""
    good = T[signed_area2(uv0, T) > 0]
    a, b, c = uv0[good[:, 0]], uv0[good[:, 1]], uv0[good[:, 2]]
    det = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    out = wq.copy()
    for i, p in enumerate(Pq):
        l1 = ((p[0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (p[1] - a[:, 1]) * (c[:, 0] - a[:, 0])) / det
        l2 = ((b[:, 0] - a[:, 0]) * (p[1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (p[0] - a[:, 0])) / det
        l0 = 1 - l1 - l2
        inside = (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9)
        if inside.any():
            g = good[inside]
            h = l0[inside] * w[g[:, 0]] + l1[inside] * w[g[:, 1]] + l2[inside] * w[g[:, 2]]
            out[i] = h[np.argmin(np.abs(h - wq[i]))]
    return out


def grow_within(V, A, start, radius):
    """Vertices reached from `start` over mesh edges while staying within `radius` of a start vertex."""
    tree = cKDTree(V[start])
    reach = start.copy()
    while True:
        cv = np.flatnonzero((A @ reach.astype(float) > 0) & ~reach)
        cv = cv[tree.query(V[cv])[0] <= radius]
        if not len(cv):
            return reach
        reach[cv] = True


def repair_patch(V, F, vf, A, euse, folds, seed_faces, radius, max_rings, sweeps=20):
    """Try to untangle one fold cluster. Returns (new positions of the free vertices or None, info)."""
    nv = len(V)
    free = np.zeros(nv, bool)
    free[np.unique(F[seed_faces])] = True
    info = {"seed_faces": int(len(seed_faces))}
    best = None
    # Faces within `radius` of the seed, reached over the surface (vertex rings, Euclidean cut-off).
    start = np.zeros(nv, bool)
    start[np.unique(F[seed_faces])] = True
    Fnear = grow_within(V, A, start, radius)[F].all(1)
    for ring in range(1, max_rings + 1):
        free = free | (A @ free.astype(float) > 0)
        fixed = (A @ free.astype(float) > 0) & ~free
        pv = np.flatnonzero(free | fixed)
        # Patch faces: every face with a free vertex (its other corners are free or fixed).
        pf = np.unique(np.concatenate([vf[v] for v in np.flatnonzero(free)]))
        T = F[pf]
        # Disk check: Euler characteristic 1, one boundary loop, no non-manifold edge inside.
        Ep = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1)
        ue, ce = np.unique(Ep, axis=0, return_counts=True)
        if any(euse[tuple(e)] > 2 for e in ue):
            info["reason"] = "non-manifold"
            continue
        nverts = len(np.unique(T))
        if nverts - len(ue) + len(T) != 1:
            info["reason"] = "not a disk"
            continue
        Ar = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        # Chart normal: the detector's mean normal (faces within `radius` of the seed, grown over the surface),
        # or the patch's own if that is larger. A patch smaller than the radius can be a whole flap folded over,
        # whose own mean normal agrees with the flap.
        near = np.flatnonzero(Fnear)
        An = np.cross(V[F[near, 1]] - V[F[near, 0]], V[F[near, 2]] - V[F[near, 0]])
        N = An.sum(0) + Ar.sum(0)
        if np.linalg.norm(N) < 1e-12 * (np.abs(Ar).sum() + np.abs(An).sum()):
            info["reason"] = "no mean normal"
            continue
        N /= np.linalg.norm(N)
        e1 = np.cross(N, [1.0, 0, 0] if abs(N[0]) < 0.9 else [0, 1.0, 0])
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(N, e1)
        c = V[pv].mean(0)
        uv0 = np.stack([(V - c) @ e1, (V - c) @ e2], 1)
        w = (V - c) @ N
        # Faces that keep all corners fixed lie outside the patch and do not move, so their orientation in the
        # chart does not matter; only a neighbouring fold there joins the patch (its vertices become free).
        ring_faces = np.unique(np.concatenate([vf[v] for v in np.flatnonzero(fixed)]))
        ring_faces = ring_faces[~free[F[ring_faces]].any(1) & folds[ring_faces]]
        if len(ring_faces):
            free[np.unique(F[ring_faces])] = True
            info["reason"] = "neighbouring fold"
            if ring < max_rings:
                continue
        # Tutte: L_ff x_f = -L_fb x_b with uniform weights over the patch edges.
        loc = -np.ones(nv, np.int64)
        fr = np.flatnonzero(free)
        loc[fr] = np.arange(len(fr))
        rows, cols, vals = [], [], []
        rhs = np.zeros((len(fr), 2))
        for i, v in enumerate(fr):
            nb = A.indices[A.indptr[v]:A.indptr[v + 1]]
            rows.append(i); cols.append(i); vals.append(float(len(nb)))
            for u in nb:
                if free[u]:
                    rows.append(i); cols.append(loc[u]); vals.append(-1.0)
                else:
                    rhs[i] += uv0[u]
        L = csr_matrix((vals, (rows, cols)), shape=(len(fr), len(fr)))
        tut = uv0.copy()
        tut[fr] = np.column_stack([spsolve(L, rhs[:, 0]), spsolve(L, rhs[:, 1])])
        def ok(P, Tq):
            # Positive in the chart, and not steeper than acos(MIN_COS) against N in 3D: a face that is barely
            # positive in the chart can still point against the detector's normal.
            Q, h = P[Tq], w[Tq]
            X = Q[..., :1] * e1 + Q[..., 1:] * e2 + h[..., None] * N
            cr = np.linalg.norm(np.cross(X[:, 1] - X[:, 0], X[:, 2] - X[:, 0]), axis=1)
            ar = (Q[:, 1, 0] - Q[:, 0, 0]) * (Q[:, 2, 1] - Q[:, 0, 1]) - (Q[:, 1, 1] - Q[:, 0, 1]) * (Q[:, 2, 0] - Q[:, 0, 0])
            return bool((ar > MIN_COS * cr).all())

        if not ok(tut, T):
            info["reason"] = "tutte flipped"
            continue
        lo, hi = 0.0, 1.0
        for _ in range(30):
            t = 0.5 * (lo + hi)
            P = tut + t * (uv0 - tut)
            if ok(P, T):
                lo = t
            else:
                hi = t
        P = tut + lo * (uv0 - tut)
        # Per-vertex pull back towards the original chart position while the vertex's triangles stay
        # positive: vertices far from the fold return (nearly) home, only the fold itself keeps moving.
        for _ in range(sweeps):
            moved = 0.0
            for v in fr:
                Tv = F[vf[v]]
                d = uv0[v] - P[v]
                if d @ d == 0:
                    continue
                old_p = P[v].copy()
                for alpha in (1.0, 0.5, 0.25, 0.125):
                    P[v] = old_p + alpha * d
                    if ok(P, Tv):
                        break
                else:
                    P[v] = old_p
                moved = max(moved, float(np.linalg.norm(P[v] - old_p)))
            if moved < 1e-9 * (np.abs(uv0[pv]).max() + 1):
                break
        wn = resample_heights(uv0, w, T, P[fr], w[fr])
        newV = c + P[fr, :1] * e1 + P[fr, 1:] * e2 + wn[:, None] * N
        # Success is judged by the detector itself, on the surface within twice the radius of the patch: a patch
        # can be flip-free in its chart and still hold a face against the detector's mean normal.
        sub = grow_within(V, A, free, 2 * radius)
        fs = np.flatnonzero(sub[F].all(1))
        Vt = V.copy()
        Vt[fr] = newV
        used, Fs = np.unique(F[fs], return_inverse=True)
        flagged = input_folds(Vt[used], Fs.reshape(-1, 3), radius)
        left = int(flagged[np.isin(fs, pf)].sum())
        if left and ring < max_rings:
            # Keep the first chart-valid result in case no larger patch comes out clean.
            if best is None:
                best = (fr, newV, dict(info, reason="ok", rings=ring, still_flagged=left))
            info["reason"] = "still folded"
            continue
        info.update(reason="ok", still_flagged=left, rings=ring, center=[round(float(x), 3) for x in V[fr].mean(0)], free_vertices=int(len(fr)), t=round(lo, 4),
                    max_move=float(np.linalg.norm(newV - V[fr], axis=1).max()))
        return fr, newV, info
    if best is not None:
        return best
    return None, None, info


def repair(V, faces, radius=None, max_rings=8, passes=3):
    V = V.copy()
    F, _ = triangulate(faces)
    nv = len(V)
    A = vertex_adjacency(F, nv)
    euse = edge_use(F)
    order = np.argsort(F.ravel(), kind="stable")
    starts = np.searchsorted(F.ravel()[order], np.arange(nv + 1))
    vf = [order[starts[v]:starts[v + 1]] // 3 for v in range(nv)]
    diag = float(np.linalg.norm(V.max(0) - V.min(0)))
    if radius is None:
        radius = 0.01 * diag
    report = {"radius": radius, "diag": diag, "passes": []}
    V0 = V.copy()
    for p in range(passes):
        fo = input_folds(V, F, radius)
        if p == 0:
            report["folded_before"] = int(fo.sum())
        if not fo.any():
            break
        # Clusters: folded faces sharing a vertex.
        idx = np.flatnonzero(fo)
        Fi = F[idx]
        M = coo_matrix((np.ones(Fi.size), (np.repeat(np.arange(len(idx)), 3), Fi.ravel())), shape=(len(idx), nv)).tocsr()
        _, lab = connected_components(M @ M.T, directed=False)
        zones = []
        for k in range(lab.max() + 1):
            fr, newV, info = repair_patch(V, F, vf, A, euse, fo, idx[lab == k], radius, max_rings)
            if fr is not None:
                V[fr] = newV
            zones.append(info)
        report["passes"].append({"folded": int(fo.sum()), "clusters": len(zones),
                                 "repaired": sum(z["reason"] == "ok" for z in zones),
                                 "skipped": [z for z in zones if z["reason"] != "ok"]})
    report["folded_after"] = int(input_folds(V, F, radius).sum())
    mv = np.linalg.norm(V - V0, axis=1)
    report.update(moved_vertices=int((mv > 0).sum()), max_move_diag=float(mv.max() / diag),
                  p99_move_diag=float(np.percentile(mv[mv > 0], 99) / diag) if (mv > 0).any() else 0.0)
    return V, report


def write_obj(path, V, faces):
    with open(path, "w") as f:
        for v in V:
            f.write("v %.9g %.9g %.9g\n" % tuple(v))
        for r in faces:
            f.write("f " + " ".join(str(i + 1) for i in r) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--radius", type=float, help="detector radius (default 1 %% of the bbox diagonal)")
    ap.add_argument("--max-rings", type=int, default=8)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--json")
    a = ap.parse_args()
    V, faces = read_obj(a.input)
    V2, rep = repair(np.asarray(V, float), faces, a.radius, a.max_rings, a.passes)
    write_obj(a.output, V2, faces)
    short = {k: v for k, v in rep.items() if k != "passes"}
    short["passes"] = [{k: v for k, v in p.items() if k != "skipped"} | {"skipped": len(p["skipped"])} for p in rep["passes"]]
    print(json.dumps(short))
    if a.json:
        json.dump(rep, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
