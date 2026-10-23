#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""Per-run cause ledger of output defects over ab.py run folders.

Each defect is located on the surface and given one cause class by measured rules on the input,
the core's per-island records and (with a probe build, see below) the integer-grid map:

  defects   non_quad      faces with other than 4 sides (centroid)
            fold          quads with scaled Jacobian <= 0
            flip          faces whose normal points against the input (minority orientation per output component)
            hole          output boundary loop with its median vertex farther than h/2 from the input's boundary,
                          non-manifold edges and pinched vertices
            dropped       input region farther than h from the output, area >= h^2 (a dropped or thinned part)
            genus         input component whose output genus differs (island level, located at the island;
                          non-manifold input components have no genus and are skipped)
  features  near_fold     an input fold (input_folds below, as sculpt_report's) within 2h
            thin          within distance h another input sheet: not connected to the nearest one inside
                          the h-ball, or two normals in the ball against each other (dot < -0.5): thin plate or tube, gap,
                          self-intersection, a crease sharper than 60 degrees; or two boundary points
                          within h that are more than 3h apart along their loop or on different loops
                          (open ribbon narrower than a quad)
            tip           angle deficit (boundary: turning) of the h-ball patch > pi (needle or cone tip)
            fallback      libQEx gave up on the defect's island and the tracer extracted it
            map_flip      a triangle of T with a flipped or degenerate map (as handed to the extractor) within h
  class     the first feature that holds in the order near_fold, tip, thin, fallback, map_flip (a tip
            is thin too, the more specific wins), else "extractor" (valid map within h, libQEx
            used, no input trigger: the extractor or the passes after it)
  repair    with --fold-repair on, a defect that is near_fold and has no same-kind defect within h in
            the matching run without repair is class "repair" (see summary --pair)

h = sqrt(input area / output faces). The map and island features need run folders of a probe build
that wrote island<k>.txt next to out.obj (AR_PROBE=1; patch in the research note's folder); without
them a run gets the input features only and "extractor" means "no input trigger".

  defect_ledger.py scan RUNDIR [RUNDIR ...] --corpus corpus.json --csv ledger.csv
  defect_ledger.py summary ledger.csv [--pair ledger-repair.csv] > ledger.md
"""

import argparse
import csv
import glob
import json
import math
import os
import sys
from collections import Counter, defaultdict, deque

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import point_to_mesh, read_obj, triangulate  # noqa: E402
from sculpt_report import face_adjacency, scaled_jacobian  # noqa: E402

KINDS = ["non_quad", "fold", "flip", "hole", "dropped", "genus"]
FEATURES = ["near_fold", "tip", "thin", "fallback", "map_flip"]  # class priority
CLASSES = FEATURES + ["extractor", "repair"]


def components(n, pairs):
    if not len(pairs):
        return np.arange(n)
    pairs = np.asarray(pairs)
    A = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
    return connected_components(A, directed=False)[1]


def boundary_edges(faces):
    """Edges used by one face only, as (a, b) pairs with a < b."""
    if isinstance(faces, np.ndarray):
        a, b = faces.ravel(), np.roll(faces, -1, axis=1).ravel()
    else:
        a = np.fromiter((v for f in faces for v in f), np.int64)
        b = np.fromiter((f[(k + 1) % len(f)] for f in faces for k in range(len(f))), np.int64)
    key = np.sort(np.stack([a, b], 1), 1)
    uniq, count = np.unique(key, axis=0, return_counts=True)
    return [tuple(e) for e in uniq[count == 1].tolist()]


def loops_of(edges):
    """Boundary loops as ordered vertex lists (pinched loops are walked as far as they go)."""
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen, out = set(), []
    for a, b in edges:
        if (a, b) in seen or (b, a) in seen:
            continue
        loop, cur = [a], b
        seen.add((a, b))
        while cur != a:
            loop.append(cur)
            nxt = [w for w in adj[cur] if (cur, w) not in seen and (w, cur) not in seen]
            if not nxt:
                break
            seen.add((cur, nxt[0]))
            cur = nxt[0]
        out.append(loop)
    return out


def input_folds(V, F, radius=None):
    """sculpt_report.input_folds (normal against the area-weighted mean normal within geodesic distance
    radius, default 1 % of the diagonal) with a cheaper candidate step for large meshes: the mean is
    first taken over Euclidean balls around probe points r/2 apart, and faces facing within 60 degrees
    of it are dropped before the geodesic test."""
    import heapq

    if radius is None:
        radius = 0.01 * np.linalg.norm(V.max(0) - V.min(0))
    C = V[F].mean(1)
    A = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]) / 2
    n = A / np.maximum(np.linalg.norm(A, axis=1)[:, None], 1e-300)
    cell = np.floor(C / (radius / 2)).astype(np.int64)
    _, first, inv = np.unique(cell, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    probes = C[first]
    tree = cKDTree(C)
    mean = np.zeros((len(probes), 3))
    for s in range(0, len(probes), 2000):
        for k, nb in enumerate(tree.query_ball_point(probes[s:s + 2000], radius)):
            mean[s + k] = A[nb].sum(0)
    m = mean[inv]
    cand = np.flatnonzero(np.einsum("ij,ij->i", n, m) < 0.5 * np.linalg.norm(m, axis=1))
    out = np.zeros(len(F), bool)
    if not len(cand):
        return out
    adj = face_adjacency([list(f) for f in F])
    adj = (adj + adj.T).tocsr()
    for i in cand:
        dist = {i: 0.0}
        heap = [(0.0, i)]
        acc = np.zeros(3)
        while heap:
            d, f = heapq.heappop(heap)
            if d > dist[f]:
                continue
            acc += A[f]
            for g in adj.indices[adj.indptr[f]:adj.indptr[f + 1]]:
                nd = d + float(np.linalg.norm(C[g] - C[f]))
                if (nd <= radius or f == i) and nd < dist.get(g, np.inf):
                    dist[g] = nd
                    heapq.heappush(heap, (nd, g))
        out[i] = n[i] @ acc < 0
    return out


def upsample(V, F, max_edge):
    """Midpoint 1-to-4 splits until 95 % of the edges are shorter than max_edge (stops at 500k faces)."""
    while len(F) < 500000:
        e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        if np.percentile(np.linalg.norm(V[e[:, 0]] - V[e[:, 1]], axis=1), 95) <= max_edge:
            break
        key = np.sort(e, 1)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        mid = len(V) + inv.ravel().reshape(3, -1).T
        V = np.vstack([V, V[uniq].mean(1)])
        a, b, c = F[:, 0], F[:, 1], F[:, 2]
        ab, bc, ca = mid[:, 0], mid[:, 1], mid[:, 2]
        F = np.concatenate([np.stack([a, ab, ca], 1), np.stack([ab, b, bc], 1),
                            np.stack([ca, bc, c], 1), np.stack([ab, bc, ca], 1)])
    return V, F


class Surface:
    """Input-side features of one mesh at quad size h_min (the smallest of its runs)."""

    def __init__(self, path, h_min):
        V, faces = read_obj(path)
        F = triangulate(faces)
        self.V0, self.F0 = V, F
        self.folds = input_folds(V, F)
        C = V[F].mean(1)
        self.fold_tree = cKDTree(C[self.folds]) if self.folds.any() else None
        A = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
        self.area = float(A.sum())
        V, F = upsample(V, F, h_min / 2)
        self.V, self.F = V, F
        n = len(V)
        # angle deficit (interior) or turning (boundary) per vertex
        ang = np.zeros(n)
        for k in range(3):
            p, q, r = V[F[:, k]], V[F[:, (k + 1) % 3]], V[F[:, (k + 2) % 3]]
            u, w = q - p, r - p
            c = np.einsum("ij,ij->i", u, w) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(w, axis=1), 1e-300)
            np.add.at(ang, F[:, k], np.arccos(np.clip(c, -1, 1)))
        bnd = boundary_edges(F)
        self.is_bnd = np.zeros(n, bool)
        for a, b in bnd:
            self.is_bnd[a] = self.is_bnd[b] = True
        used = np.zeros(n, bool)
        used[F.ravel()] = True
        self.deficit = np.where(self.is_bnd, math.pi, 2 * math.pi) - ang
        self.deficit[~used] = 0
        # boundary loops with arc length per vertex
        self.loop_id = np.full(n, -1)
        self.arc = np.zeros(n)
        self.loop_len = []
        for i, loop in enumerate(loops_of(bnd)):
            s = 0.0
            for j, v in enumerate(loop):
                if j:
                    s += float(np.linalg.norm(V[v] - V[loop[j - 1]]))
                self.loop_id[v], self.arc[v] = i, s
            self.loop_len.append(s + float(np.linalg.norm(V[loop[0]] - V[loop[-1]])))
        e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        e = np.unique(np.sort(e, 1), axis=0)
        self.adj = coo_matrix((np.ones(2 * len(e)), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
        self.comp = components(n, e)
        self.tree = cKDTree(V)
        fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        vn = np.zeros((n, 3))
        for k in range(3):
            np.add.at(vn, F[:, k], fn)
        self.normal = vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-300)
        self.bnd_tree = cKDTree(V[self.is_bnd]) if self.is_bnd.any() else None
        self.bnd_index = np.flatnonzero(self.is_bnd)
        # where the output may legitimately open: boundary and non-manifold edges (the core cuts there)
        ek = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
        eu, ec = np.unique(ek, axis=0, return_counts=True)
        # and pinched vertices: incident edges minus incident faces is 0 inside, 1 on a boundary, more at a pinch
        fans = np.bincount(eu.ravel(), minlength=n) - np.bincount(F.ravel(), minlength=n)
        cut = np.union1d(np.unique(eu[ec != 2]), np.flatnonzero(fans > 1))
        self.cut_tree = cKDTree(V[cut]) if len(cut) else None
        va = np.zeros(n)
        np.add.at(va, F.ravel(), np.repeat(0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 3, 3))
        self.vertex_area = va
        # per input component: Euler characteristic, boundary loops, area, centroid
        self.comp_info = {}
        fcomp = self.comp[F[:, 0]]
        nv = np.bincount(self.comp[used], minlength=n)
        nf = np.bincount(fcomp, minlength=n)
        ne = np.bincount(self.comp[e[:, 0]], minlength=n)
        loops_per = defaultdict(set)
        for v in np.flatnonzero(self.loop_id >= 0):
            loops_per[self.comp[v]].add(self.loop_id[v])
        carea = np.bincount(self.comp, weights=va, minlength=n)
        for c in np.unique(self.comp[used]):
            chi = int(nv[c] - ne[c] + nf[c])
            nb = len(loops_per[c])
            self.comp_info[int(c)] = {"chi": chi, "loops": nb, "genus": (2 - chi - nb) / 2,
                                      "area": float(carea[c]), "centroid": V[self.comp == c].mean(0)}

    def features_at(self, x, h, cache):
        key = (round(float(x[0]), 9), round(float(x[1]), 9), round(float(x[2]), 9), h)
        if key in cache:
            return cache[key]
        f = {}
        f["near_fold"] = bool(self.fold_tree is not None and self.fold_tree.query(x)[0] <= 2 * h)
        _, seed = self.tree.query(x)
        ball = set(self.tree.query_ball_point(self.V[seed], h))
        ball.add(int(seed))
        reached = {int(seed)}
        queue = deque([int(seed)])
        while queue:
            v = queue.popleft()
            for w in self.adj.indices[self.adj.indptr[v]:self.adj.indptr[v + 1]]:
                if w in ball and w not in reached:
                    reached.add(int(w))
                    queue.append(int(w))
        # another sheet: not connected inside the ball, or facing the other way (the two sides of a
        # plate thinner than the ball, joined around its rim)
        N = self.normal[list(ball)]
        N = N[:: max(1, len(N) // 256)]  # pairwise test on at most ~256 normals
        thin = len(reached) < len(ball) or bool((N @ N.T).min() < -0.5)
        if not thin and self.bnd_tree is not None:
            bs = [self.bnd_index[i] for i in self.bnd_tree.query_ball_point(x, h)]
            for i in range(len(bs)):
                for j in range(i + 1, len(bs)):
                    a, b = bs[i], bs[j]
                    if self.loop_id[a] != self.loop_id[b]:
                        thin = True
                    else:
                        d = abs(self.arc[a] - self.arc[b])
                        d = min(d, self.loop_len[self.loop_id[a]] - d)
                        thin = d > 3 * h
                    if thin:
                        break
                if thin:
                    break
        f["thin"] = bool(thin)
        f["tip"] = bool(self.deficit[list(reached)].sum() > math.pi)
        cache[key] = f
        return f


def read_islands(run):
    """Probe dump: per island T vertices, triangles with map orientation, cones."""
    out = {}
    for p in glob.glob(os.path.join(run, "island*.txt")):
        k = int(os.path.basename(p)[6:-4])
        V, flips = [], []
        with open(p) as fp:
            lines = fp.read().splitlines()
        for l in lines:
            if l[0] == "v":
                V.append([float(t) for t in l.split()[1:]])
        V = np.array(V)
        for l in lines:
            if l[0] == "f":
                t = l.split()
                if int(t[4]) <= 0:
                    flips.append(V[[int(t[1]), int(t[2]), int(t[3])]].mean(0))
        out[k] = {"V": V, "flip_tree": cKDTree(np.array(flips)) if flips else None, "flips": len(flips)}
    return out


def scan_run(run, surf, cache):
    rec = json.load(open(os.path.join(run, "record.json")))
    base = {"set": rec["set"], "mesh": rec["mesh"], "res": rec["res"], "target": rec["target"],
            "rep": rec["replicate"], "args": " ".join(rec.get("cli_args", [])), "run": run}
    out_path = os.path.join(run, "out.obj")
    if rec.get("rc") != 0 or not os.path.exists(out_path):
        return [dict(base, kind="failed", cls="failed", x=0, y=0, z=0, h=0, island=-1, **{f: 0 for f in FEATURES})]
    V, faces = read_obj(out_path)
    if not faces:
        return [dict(base, kind="failed", cls="failed", x=0, y=0, z=0, h=0, island=-1, **{f: 0 for f in FEATURES})]
    h = math.sqrt(surf.area / len(faces))
    used = {}
    for l in open(os.path.join(run, "stages.jsonl")):
        d = json.loads(l)
        if d.get("stage") == "extractor":
            used[int(d.get("island", -1))] = d.get("used", "qex")
    islands = read_islands(run)
    iv = [(k, v["V"]) for k, v in islands.items() if len(v["V"])]
    if iv:
        itree = cKDTree(np.vstack([v for _, v in iv]))
        ilabel = np.concatenate([np.full(len(v), k) for k, v in iv])

    def island_of(x):
        return int(ilabel[itree.query(x)[1]]) if iv else -1

    defects = []  # (kind, points used for features, location)
    sizes = np.array([len(f) for f in faces])
    cent = np.array([V[f].mean(0) for f in faces])
    for i in np.flatnonzero(sizes != 4):
        defects.append(("non_quad", [cent[i]], cent[i]))
    sj = scaled_jacobian(V, faces)
    for i in np.flatnonzero(np.nan_to_num(sj, nan=1.0) <= 0):
        defects.append(("fold", [cent[i]], cent[i]))
    # flips against the input, as metrics.py counts them (the minority orientation)
    N = np.array([np.cross(V[f[1]] - V[f[0]], V[f[-1]] - V[f[0]]) + np.cross(V[f[2 % len(f)]] - V[f[1]], V[f[0]] - V[f[1]]) for f in faces])
    _, cf = point_to_mesh(cent, surf.V0, surf.F0)
    F0 = surf.F0
    nin = np.cross(surf.V0[F0[cf, 1]] - surf.V0[F0[cf, 0]], surf.V0[F0[cf, 2]] - surf.V0[F0[cf, 0]])
    dots = np.einsum("ij,ij->i", nin, N)
    # the minority orientation per output component, so a component whose raw input is mis-oriented
    # (the core orients it) does not count as flipped as a whole
    neg = dots < 0
    fcomp_out = components(len(V), np.array([(f[k], f[(k + 1) % len(f)]) for f in faces for k in range(len(f))]))[[f[0] for f in faces]]
    flip = np.zeros(len(faces), bool)
    for c in np.unique(fcomp_out):
        m = fcomp_out == c
        flip[m] = neg[m] if neg[m].sum() <= (~neg[m]).sum() else ~neg[m]
    for i in np.flatnonzero(flip):
        defects.append(("flip", [cent[i]], cent[i]))
    # holes: output boundary loops away from the input boundary
    for loop in loops_of(boundary_edges(faces)):
        P = V[loop]
        if surf.cut_tree is None:
            far = True
        else:
            far = np.median(surf.cut_tree.query(P)[0]) > h / 2
        if far:
            step = max(1, len(P) // 8)
            defects.append(("hole", list(P[::step]), P.mean(0)))
    # dropped or thinned parts: input farther than h from the output
    T = triangulate(faces)
    # distance to the mesh <= distance to its nearest vertex: only the rest needs the exact query
    lost = cKDTree(V).query(surf.V, distance_upper_bound=h)[0] > h
    if lost.any():
        far = np.flatnonzero(lost)
        lost[far] = point_to_mesh(surf.V[far], V, T)[0] > h
    if lost.any():
        idx = np.flatnonzero(lost)
        sub = surf.adj[idx][:, idx].tocoo()
        lab = components(len(idx), np.stack([sub.row, sub.col], 1) if sub.nnz else [])
        for c in np.unique(lab):
            vs = idx[lab == c]
            if surf.vertex_area[vs].sum() >= h * h:
                step = max(1, len(vs) // 8)
                defects.append(("dropped", list(surf.V[vs[::step]]), surf.V[vs].mean(0)))
    # genus per input component
    ocomp = components(len(V), np.array([(f[k], f[(k + 1) % len(f)]) for f in faces for k in range(len(f))]))
    oused = np.zeros(len(V), bool)
    oused[np.concatenate([np.asarray(f) for f in faces])] = True
    obnd = boundary_edges(faces)
    oloops = loops_of(obnd)
    per_in = defaultdict(lambda: {"chi": 0, "loops": 0, "n": 0})
    for c in np.unique(ocomp[oused]):
        vs = np.flatnonzero((ocomp == c) & oused)
        fc = [f for f in faces if ocomp[f[0]] == c]
        ec = {(min(f[k], f[(k + 1) % len(f)]), max(f[k], f[(k + 1) % len(f)])) for f in fc for k in range(len(f))}
        vset = set(vs.tolist())
        nl = sum(1 for lp in oloops if lp[0] in vset)
        _, near = surf.tree.query(V[vs[: min(len(vs), 50)]])
        ic = Counter(surf.comp[near].tolist()).most_common(1)[0][0]
        per_in[ic]["chi"] += len(vs) - len(ec) + len(fc)
        per_in[ic]["loops"] += nl
        per_in[ic]["n"] += 1
    for ic, o in per_in.items():
        info = surf.comp_info.get(ic)
        if info is None:
            continue
        g_out = (2 * o["n"] - o["chi"] - o["loops"]) / 2  # summed over the output components of this input one
        # a non-manifold input component (pinched vertex, T-junction) has no genus: skip it
        g_in = info["genus"]
        if g_in < 0 or g_in != int(g_in):
            continue
        if abs(g_out - g_in) >= 0.5:
            members = surf.V[surf.comp == ic]
            step = max(1, len(members) // 64)
            defects.append(("genus", list(members[::step]), info["centroid"]))

    rows = []
    for kind, pts, loc in defects:
        feats = {f: False for f in FEATURES}
        for p in pts:
            fp = surf.features_at(np.asarray(p), h, cache)
            for k, v in fp.items():
                feats[k] = feats[k] or v
        isl = island_of(loc)
        feats["fallback"] = used.get(isl, "qex") == "trace"
        if isl in islands and islands[isl]["flip_tree"] is not None:
            feats["map_flip"] = any(islands[isl]["flip_tree"].query(np.asarray(p))[0] <= h for p in pts)
        cls = next((f for f in FEATURES if feats[f]), "extractor")
        rows.append(dict(base, kind=kind, cls=cls, x=float(loc[0]), y=float(loc[1]), z=float(loc[2]), h=h,
                         island=isl, **{f: int(feats[f]) for f in FEATURES}))
    # base rate: the same features at 200 random output face centroids
    rng = np.random.default_rng(0)
    for i in rng.choice(len(faces), size=min(200, len(faces)), replace=False):
        feats = surf.features_at(cent[i], h, cache)
        isl = island_of(cent[i])
        fb = used.get(isl, "qex") == "trace"
        mf = bool(isl in islands and islands[isl]["flip_tree"] is not None and islands[isl]["flip_tree"].query(cent[i])[0] <= h)
        rows.append(dict(base, kind="_base", cls="", x=0, y=0, z=0, h=h, island=isl,
                         near_fold=int(feats["near_fold"]), thin=int(feats["thin"]), tip=int(feats["tip"]),
                         fallback=int(fb), map_flip=int(mf)))
    if not defects:
        rows.append(dict(base, kind="none", cls="", x=0, y=0, z=0, h=h, island=-1, **{f: 0 for f in FEATURES}))
    return rows


FIELDS = ["set", "mesh", "res", "target", "rep", "args", "kind", "cls", "x", "y", "z", "h", "island"] + FEATURES + ["run"]


def scan_mesh(job):
    mesh, path, rs = job
    V, faces = read_obj(path)
    F = triangulate(faces)
    area = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1).sum()
    hmin = math.sqrt(area / max(rec["target"] for _, rec in rs) / 1.5)
    surf = Surface(path, hmin)
    cache = {}
    rows = []
    for r, _ in rs:
        rows += scan_run(r, surf, cache)
    print(f"{mesh}: {len(rs)} runs", file=sys.stderr, flush=True)
    return rows


def scan(a):
    from multiprocessing import Pool

    corpus = json.load(open(a.corpus))
    files = {m["id"]: m["file"] for m in corpus["meshes"]}
    runs = []
    for root in a.rundir:
        runs += sorted(os.path.dirname(p) for p in glob.glob(os.path.join(root, "**", "record.json"), recursive=True))
    by_mesh = defaultdict(list)
    for r in runs:
        rec = json.load(open(os.path.join(r, "record.json")))
        if rec["mesh"] in files:
            by_mesh[rec["mesh"]].append((r, rec))
    def source(mesh, rs):
        # the unperturbed input the runs used (replicate 0), else the corpus entry
        for r, rec in rs:
            if rec["replicate"] == 0:
                for line in open(os.path.join(r, "stages.jsonl")):
                    path = json.loads(line).get("input")
                    if path and os.path.exists(path):
                        return path
        return files[mesh] if os.path.isabs(files[mesh]) else os.path.join(a.meshes, files[mesh])

    jobs = [(mesh, source(mesh, rs), rs) for mesh, rs in sorted(by_mesh.items())]
    with open(a.csv, "w", newline="") as fp, Pool(a.jobs) as pool:
        w = csv.DictWriter(fp, fieldnames=FIELDS)
        w.writeheader()
        for rows in pool.imap_unordered(scan_mesh, jobs):
            for row in rows:
                w.writerow({k: row.get(k, "") for k in FIELDS})
            fp.flush()


def summary(a):
    rows = list(csv.DictReader(open(a.csv)))
    if a.pair:
        # repair runs: a near-fold defect with no same-kind defect within h in the run without repair
        off = defaultdict(list)
        for r in csv.DictReader(open(a.pair)):
            if r["kind"] in KINDS:
                off[(r["mesh"], r["res"], r["target"], r["rep"], r["kind"])].append(np.array([float(r["x"]), float(r["y"]), float(r["z"])]))
        for r in rows:
            if r["kind"] in KINDS and r["near_fold"] == "1":
                p = np.array([float(r["x"]), float(r["y"]), float(r["z"])])
                ref = off.get((r["mesh"], r["res"], r["target"], r["rep"], r["kind"]), [])
                if not any(np.linalg.norm(q - p) <= float(r["h"]) for q in ref):
                    r["cls"] = "repair"
    defects = [r for r in rows if r["kind"] in KINDS]
    base = [r for r in rows if r["kind"] == "_base"]
    runs = {(r["set"], r["mesh"], r["res"], r["target"], r["rep"]) for r in rows}
    failed = [r for r in rows if r["kind"] == "failed"]
    print(f"{len(runs)} replicate-runs, {len(failed)} failed, {len(defects)} defects\n")
    sets = sorted({r["set"] for r in rows})
    # 1. defects per kind and class, per set
    for s in sets:
        ds = [r for r in defects if r["set"] == s]
        nr = len({k for k in runs if k[0] == s})
        print(f"### {s} ({nr} replicate-runs, {len(ds)} defects)\n")
        print("| kind | total | " + " | ".join(CLASSES) + " |")
        print("|---|---:|" + "---:|" * len(CLASSES))
        for kind in KINDS:
            dk = [r for r in ds if r["kind"] == kind]
            if not dk:
                continue
            c = Counter(r["cls"] for r in dk)
            print(f"| {kind} | {len(dk)} | " + " | ".join(f"{100 * c[k] / len(dk):.0f} %" if c[k] else "" for k in CLASSES) + " |")
        c = Counter(r["cls"] for r in ds)
        if ds:
            print(f"| **all** | {len(ds)} | " + " | ".join(f"{100 * c[k] / len(ds):.0f} %" if c[k] else "" for k in CLASSES) + " |")
        # mechanism under each input-triggered class: did the map fail there, or the extractor on a valid map
        trig = [k for k in ("near_fold", "tip", "thin") if any(r["cls"] == k for r in ds)]
        if trig:
            print("\n| class | defects | map flip within h | libQEx fallback | valid map, libQEx |")
            print("|---|---:|---:|---:|---:|")
            for k in trig:
                dk = [r for r in ds if r["cls"] == k]
                mf = sum(r["map_flip"] == "1" for r in dk)
                fb = sum(r["map_flip"] != "1" and r["fallback"] == "1" for r in dk)
                print(f"| {k} | {len(dk)} | {100 * mf / len(dk):.0f} % | {100 * fb / len(dk):.0f} % | {100 * (len(dk) - mf - fb) / len(dk):.0f} % |")
        # lift of each feature: share among defects / share among random output points
        bs = [r for r in base if r["set"] == s]
        if ds and bs:
            print("\n| feature | share of defects | share of surface | lift |")
            print("|---|---:|---:|---:|")
            for f in FEATURES:
                sd = np.mean([r[f] == "1" for r in ds])
                sb = np.mean([r[f] == "1" for r in bs])
                print(f"| {f} | {100 * sd:.0f} % | {100 * sb:.1f} % | {sd / sb:.1f} |" if sb > 0 else f"| {f} | {100 * sd:.0f} % | 0 % | - |")
        print()
    # 2. worst meshes
    score = Counter()
    nrun = Counter()
    for k in runs:
        nrun[(k[0], k[1], k[2], k[3])] += 1
    weight = {"non_quad": 1, "fold": 1, "flip": 0.2, "hole": 10, "dropped": 10, "genus": 10}
    for r in defects:
        score[(r["set"], r["mesh"], r["res"], r["target"])] += weight[r["kind"]]
    print("### Worst runs (defect score per replicate-run: non-quads + folds + 0.2 flips + 10 per hole, dropped part, wrong genus)\n")
    print("| set | mesh | res | target | score | top kinds | top classes |")
    print("|---|---|---|---:|---:|---|---|")
    for key, sc in score.most_common(a.top):
        dk = [r for r in defects if (r["set"], r["mesh"], r["res"], r["target"]) == key]
        kinds = ", ".join(f"{k} {n / nrun[key]:.1f}" for k, n in Counter(r["kind"] for r in dk).most_common(3))
        cls = ", ".join(f"{k} {100 * n / len(dk):.0f} %" for k, n in Counter(r["cls"] for r in dk).most_common(3))
        print(f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} | {sc / nrun[key]:.1f} | {kinds} | {cls} |")
    print()
    if failed:
        print("Failed runs: " + ", ".join(sorted({f"{r['mesh']} {r['res']} {r['target']} u{r['rep']}" for r in failed})) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scan")
    s.add_argument("rundir", nargs="+")
    s.add_argument("--corpus", required=True)
    s.add_argument("--meshes", default=os.path.join(os.environ.get("AR_WORK", os.path.expanduser("~/ar-work")), "meshes"))
    s.add_argument("--csv", required=True)
    s.add_argument("--jobs", type=int, default=2, help="meshes scanned at once")
    m = sp.add_parser("summary")
    m.add_argument("csv")
    m.add_argument("--pair", help="ledger of the same runs without repair, for the repair class")
    m.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    scan(a) if a.cmd == "scan" else summary(a)


if __name__ == "__main__":
    main()
