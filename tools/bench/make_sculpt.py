#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate the sculpt set: procedural stand-ins for what Blender/ZBrush sculpts look like when they
reach the add-on. Computed from code only (seeded), so no license constraints of their own.

    python make_sculpt.py --out meshes/sculpt [--only a,b]

One creature (body, head, snout, four legs, two horns tapering to a 6 mm tip, a tail) is built as an
implicit surface with sculpted detail: clay-like noise (wavelengths 0.03-0.3), neck wrinkles with a
0.05 wavelength and a sharp V crease along the back. Size about 1.5 x 3.2 x 2.3, area about 9, so a
2000-quad target means quad edges of about 0.07: horn tips, tail tip and wrinkles are below quad size
on purpose, as in real sculpts. The meshes differ in how the surface was tessellated, which is what
sculpting tools leave behind:

  sculpt_voxel      voxel remesh: marching cubes on the implicit, h = 0.0075, ~0.3M triangles,
                    uniform density, marching-cubes slivers.
  sculpt_steps      low-resolution voxel remesh of a voxelised (binary) volume, h = 0.012: one-voxel
                    terraces on gentle slopes (DynaMesh / voxel remesh with no smoothing); welded
                    at 1e-6 with zero-area triangles dropped.
  sculpt_degenerate the same voxelised volume without that cleanup: marching cubes on a binary volume
                    puts vertices exactly on grid corners, so 21 % of the triangles have zero area.
  sculpt_dyntopo    dynamic topology: coarse voxel base (h = 0.03) refined by edge splits to 0.006 on
                    the head, horns and neck only, then projected onto the detailed surface there.
                    Edge length ratio ~5:1 across the mesh, high-valence fans, detail only where
                    "sculpted".
  sculpt_decimated  sculpt_voxel decimated by quadric edge collapse to 60k triangles (ZBrush
                    Decimation Master / Blender Decimate): adaptive, long thin triangles.
  sculpt_parts      voxel creature (h = 0.01) plus separate pieces as a sculptor joins them: two
                    eyeballs sunk into the head (surfaces intersect), six teeth piercing the snout,
                    five crumbs of 0.008-0.02 radius floating near the body (voxel debris, smaller
                    than a quad).
  sculpt_dirty      voxel creature (h = 0.01) with export damage: one hole of ~100 triangles, one
                    missing triangle, a patch with flipped orientation, ten duplicated faces, one
                    fin triangle on an edge (non-manifold edge), one crumb touching the body at one
                    vertex (non-manifold vertex).

Extreme cases (fur cards, single-sided sheets, thousands of islands, million-face self-intersection
soups) are left out on purpose: research/sculpt-inputs note, "out of scope".
"""
import argparse
import heapq
import json
import os

import numpy as np

from make_synthetic import icosphere, sha256, write_obj

LO, HI = np.array([-0.75, -1.65, -1.05]), np.array([0.75, 1.6, 1.3])


# ---- the creature as an implicit --------------------------------------------------------------

def _ellipsoid(P, c, r):
    r = np.asarray(r, float)
    return (np.linalg.norm((P - c) / r, axis=1) - 1) * r.min()


def _cone(P, a, b, ra, rb):
    """Capsule whose radius goes linearly from ra at a to rb at b (approximate distance)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1) - (ra + t * (rb - ra))


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


_rng = np.random.default_rng(7)
_NOISE_W = _rng.normal(size=(24, 3))
_NOISE_W /= np.linalg.norm(_NOISE_W, axis=1, keepdims=True)
_NOISE_L = np.geomspace(0.03, 0.3, 24)  # wavelengths
_NOISE_PHASE = _rng.uniform(0, 2 * np.pi, 24)


def base_sdf(P):
    d = _ellipsoid(P, (0, 0, 0), (0.55, 0.85, 0.5))
    d = _smin(d, _ellipsoid(P, (0, 0.95, 0.35), (0.38, 0.36, 0.36)), 0.15)
    d = _smin(d, _ellipsoid(P, (0, 1.28, 0.26), (0.2, 0.25, 0.16)), 0.08)  # snout
    for s in (-1, 1):
        for y0, y1 in ((0.5, 0.55), (-0.5, -0.6)):
            d = _smin(d, _cone(P, (s * 0.35, y0, -0.2), (s * 0.42, y1, -0.85), 0.13, 0.1), 0.1)  # legs
        d = _smin(d, _cone(P, (s * 0.18, 1.0, 0.62), (s * 0.45, 0.85, 1.2), 0.07, 0.006), 0.04)  # horns
    d = _smin(d, _cone(P, (0, -0.75, 0.1), (0, -1.2, 0.3), 0.08, 0.05), 0.06)  # tail
    d = _smin(d, _cone(P, (0, -1.2, 0.3), (0.2, -1.5, 0.6), 0.05, 0.012), 0.03)
    return d


def detail(P):
    """Sculpted detail as an offset of the implicit (positive = carved in)."""
    n = (_NOISE_L * 0.02) @ np.sin((2 * np.pi / _NOISE_L)[:, None] * (_NOISE_W @ P.T) + _NOISE_PHASE[:, None]) / 6
    neck = np.exp(-((P[:, 1] - 0.65) / 0.12) ** 2) * (P[:, 2] > 0)
    wrinkles = 0.006 * np.sin(2 * np.pi * P[:, 1] / 0.05) * neck
    back = (np.abs(P[:, 1]) < 0.6) * (P[:, 2] > 0.25)
    crease = 0.015 * np.exp(-np.abs(P[:, 0]) / 0.006) * back
    return n + wrinkles + crease


def detail_zone(P):
    """1 on the head, horns and neck (where a dyntopo user would have added detail), 0 elsewhere."""
    return np.clip((P[:, 1] - 0.45) / 0.1, 0, 1)


def sdf(P, w=1.0):
    return base_sdf(P) + w * detail(P)


def grid_volume(f, h, chunk=400_000):
    axes = [np.arange(LO[i], HI[i] + h, h) for i in range(3)]
    shape = tuple(len(a) for a in axes)
    out = np.empty(int(np.prod(shape)), np.float32)
    X = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    for s in range(0, len(X), chunk):
        out[s:s + chunk] = f(X[s:s + chunk])
    return out.reshape(shape)


def contour(vol, h, level=0.0):
    from skimage.measure import marching_cubes

    V, F, _, _ = marching_cubes(vol, level, spacing=(h, h, h))
    return V + LO, F[:, ::-1].astype(np.int64)


def keep_largest(V, F):
    """Marching cubes on noise can leave specks; the generators add their islands on purpose."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    n = len(V)
    A = coo_matrix((np.ones(len(F) * 3), (F.ravel(), np.roll(F, 1, 1).ravel())), shape=(n, n))
    _, lab = connected_components(A, directed=False)
    big = np.bincount(lab[F[:, 0]]).argmax()
    F = F[lab[F[:, 0]] == big]
    used = np.unique(F)
    remap = -np.ones(n, np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[F]


def creature(h, w=1.0):
    return keep_largest(*contour(grid_volume(lambda P: sdf(P, w), h), h))


# ---- tessellations ----------------------------------------------------------------------------

def sculpt_voxel():
    return creature(0.0075)


def _steps_raw():
    from scipy.ndimage import uniform_filter

    h = 0.012
    occ = (grid_volume(sdf, h) < 0).astype(np.float32)
    return keep_largest(*contour(uniform_filter(occ, 2), h, 0.5))


def drop_degenerate(V, F, eps=1e-6):
    """Weld vertices closer than eps and drop the triangles that become degenerate."""
    import igl

    V, _, _, F = igl.remove_duplicate_vertices(V, np.asfortranarray(F, np.int32), eps)
    F = np.asarray(F, np.int64)
    ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 2] != F[:, 0]) & (igl.doublearea(V, F) > 1e-12)
    return keep_largest(np.asarray(V, float), F[ok])


def sculpt_steps():
    return drop_degenerate(*_steps_raw())


def sculpt_degenerate():
    return _steps_raw()


def project(P, w, steps=4, eps=1e-5):
    for _ in range(steps):
        f = sdf(P, w)
        g = np.stack([(sdf(P + e, w) - sdf(P - e, w)) / (2 * eps) for e in np.eye(3) * eps], 1)
        P = P - (f / np.maximum((g * g).sum(1), 1e-12))[:, None] * g
    return P


def split_edges(V, F, target):
    """Split every edge longer than target(midpoint) until none is (longest first), like dyntopo's
    subdivide step. Splitting an edge splits both of its triangles, so the mesh stays conforming."""
    V, F = list(map(np.asarray, V)), [list(f) for f in F]
    faces_of = {}
    for i, f in enumerate(F):
        for k in range(3):
            faces_of.setdefault(frozenset((f[k], f[(k + 1) % 3])), []).append(i)
    heap = []

    def push(a, b):
        L = np.linalg.norm(V[a] - V[b])
        if L > target((V[a] + V[b]) / 2):
            heapq.heappush(heap, (-L, a, b))

    for e in faces_of:
        push(*e)
    while heap:
        _, a, b = heapq.heappop(heap)
        e = frozenset((a, b))
        if e not in faces_of:
            continue
        m = len(V)
        V.append((V[a] + V[b]) / 2)
        for fi in faces_of.pop(e):
            f = F[fi]
            k = next(k for k in range(3) if {f[k], f[(k + 1) % 3]} == {a, b})
            p, q, r = f[k], f[(k + 1) % 3], f[(k + 2) % 3]
            F[fi] = [p, m, r]
            nf = len(F)
            F.append([m, q, r])
            qr = faces_of[frozenset((q, r))]
            qr[qr.index(fi)] = nf
            faces_of.setdefault(frozenset((p, m)), []).append(fi)
            faces_of.setdefault(frozenset((m, q)), []).append(nf)
            faces_of.setdefault(frozenset((m, r)), []).extend([fi, nf])
            push(m, r)
        push(a, m)
        push(m, b)
    return np.asarray(V), np.asarray(F, np.int64)


def sculpt_dyntopo():
    V, F = creature(0.03, w=0.0)
    V, F = split_edges(V, F, lambda p: 0.006 if detail_zone(p[None])[0] > 0.5 else 0.03)
    w = detail_zone(V)
    sel = w > 0
    V[sel] = project(V[sel], w[sel])
    return V, F


def sculpt_decimated(voxel=None):
    import igl

    V, F = voxel if voxel is not None else sculpt_voxel()
    U, G, _, _ = igl.qslim(V, np.asfortranarray(F, np.int32), 60_000)
    return np.asarray(U, float), np.asarray(G, np.int64)


def _append(parts):
    V, F, n = [], [], 0
    for v, f in parts:
        V.append(v)
        F.append(f + n)
        n += len(v)
    return np.concatenate(V), np.concatenate(F)


def _blob(level, center, radii, seed):
    v, f = icosphere(level)
    rng = np.random.default_rng(seed)
    v = v * (1 + 0.15 * rng.normal(size=(len(v), 1)) * (level > 1))
    return v * np.asarray(radii) + np.asarray(center), f


def sculpt_parts():
    parts = [creature(0.01)]
    for s in (-1, 1):
        parts.append(_blob(4, (s * 0.17, 1.2, 0.47), (0.075,) * 3, 0))  # eyeballs, half sunk
    for i, x in enumerate(np.linspace(-0.12, 0.12, 6)):
        parts.append(_blob(2, (x, 1.42, 0.17), (0.014, 0.014, 0.045), 0))  # teeth through the snout
    for i, (c, r) in enumerate([((0.7, 0.2, 0.3), 0.02), ((-0.68, -0.4, 0.1), 0.015), ((0.1, 0.3, 0.62), 0.012),
                                ((0.3, -1.0, -0.3), 0.01), ((-0.2, 1.1, 0.9), 0.008)]):
        parts.append(_blob(1 + (r > 0.012), c, (r,) * 3, i))  # crumbs: 80-320 triangles
    return _append(parts)


def sculpt_dirty():
    V, F = creature(0.01)
    rng = np.random.default_rng(3)
    C = V[F].mean(1)
    # A hole of ~100 triangles on the back, one missing triangle on a leg.
    hole = np.linalg.norm(C - V[np.argmin(np.linalg.norm(V - (0, -0.3, 0.6), axis=1))], axis=1) < 0.035
    leg = np.argmin(np.linalg.norm(C - (0.4, 0.5, -0.6), axis=1))
    keep = ~hole
    keep[leg] = False
    # Flipped patch on the flank (inconsistent orientation along its rim).
    flank = np.linalg.norm(C - V[np.argmin(np.linalg.norm(V - (0.6, 0.0, 0.0), axis=1))], axis=1) < 0.06
    F = F.copy()
    F[flank] = F[flank][:, ::-1]
    dup = rng.choice(np.flatnonzero(keep & ~flank), 10, replace=False)
    F = np.concatenate([F[keep], F[dup]])
    # A fin on one edge of the belly: third face on that edge.
    e = F[np.argmin(np.linalg.norm(V[F].mean(1) - (0, 0, -0.5), axis=1))][:2]
    n = len(V)
    tip = V[e].mean(0) + (0, 0, -0.05)
    V = np.vstack([V, tip])
    F = np.vstack([F, [[e[0], e[1], n]]])
    # A crumb touching the body at one shared position (pinch vertex).
    cv, cf = icosphere(1)
    anchor = V[np.argmin(np.linalg.norm(V - (-0.55, 0.0, 0.1), axis=1))]
    cv = cv * 0.02
    cv = cv - cv[0] + anchor  # icosphere vertex 0 lands exactly on a body vertex
    return _append([(V, F), (cv, cf)])


JOBS = {"sculpt_voxel": sculpt_voxel, "sculpt_steps": sculpt_steps,
        "sculpt_degenerate": sculpt_degenerate, "sculpt_dyntopo": sculpt_dyntopo,
        "sculpt_decimated": sculpt_decimated, "sculpt_parts": sculpt_parts, "sculpt_dirty": sculpt_dirty}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="comma list of mesh names")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    names = args.only.split(",") if args.only else list(JOBS)
    manifest_path = os.path.join(args.out, "sculpt-manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    voxel = None
    for name in names:
        if name == "sculpt_decimated":
            V, F = sculpt_decimated(voxel)
        else:
            V, F = JOBS[name]()
        if name == "sculpt_voxel":
            voxel = (V, F)
        path = write_obj(os.path.join(args.out, name + ".obj"), V, F)
        manifest[name] = {"vertices": int(len(V)), "triangles": int(len(F)), "sha256": sha256(path)}
        print(name, manifest[name], flush=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    main()
