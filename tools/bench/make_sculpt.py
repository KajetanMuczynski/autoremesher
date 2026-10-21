#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate the sculpt set: procedural stand-ins for what Blender/ZBrush sculpts look like when they
reach the add-on. Computed from code only (seeded), so no license constraints of their own.

    python make_sculpt.py --out meshes/sculpt [--only a,b]
    python make_sculpt.py --set brush --out meshes/brush [--only a,b]

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
                    smooth eyeballs sunk into the head (surfaces intersect; lumpy before 2026-10-21),
                    six teeth piercing the snout,
                    five crumbs of 0.008-0.02 radius floating near the body (voxel debris, smaller
                    than a quad).
  sculpt_dirty      voxel creature (h = 0.01) with export damage: one hole of ~100 triangles, one
                    missing triangle, a patch with flipped orientation, ten duplicated faces, one
                    fin triangle on an edge (non-manifold edge), one crumb touching the body at one
                    vertex (non-manifold vertex).

The brush set (--set brush, corpus set "brush") puts one brush situation on a unit sphere (icosphere
level 7, 327k triangles, edge 0.0095; quad edge 0.079 at 2k, 0.05 at 5k), each at several strengths
from clean to over-strong, as vertex moves like Blender's sculpt mode and ZBrush apply them. Folded
input (triangles turned over by the stroke) is what all defects of the 2026-10-21 real-sculpt tests
sat on, so the manifest records each mesh's folded triangles (sculpt_report.input_folds):

  brush_clay        Clay Strips: three layers of flat-topped strokes, soft rims. No folds.
  brush_crease      Crease/Pinch lines: V grooves with pinch 0.4, 0.8, 1.0, 1.3; the 1.3 line overshoots,
                    vertices cross it and fold (the crease line on the test head's crown).
  brush_inflate     Inflate: 18 bumps of radius 0.015 (below a quad) to 0.2, grown along their own
                    normals, so the big ones undercut. No folds.
  brush_pits        Deep pits and sunk eyes on one surface: sockets with an eyeball bulge whose rim is a
                    crevice narrower than a quad (eyelid line), nostrils below quad size, a mouth slot.
  brush_spikes      Snake Hook without dyntopo: five horns of stretched slivers, tips far below a quad,
                    one hooked back over the surface (the test cube's spike).
  brush_layers      Fold/Layer drapery: sine wrinkles, wavelength 0.06-0.12, pushed sideways from 0.5x
                    to 1.5x the overhang limit; the stiffer half pleats over itself.
  brush_noise       Noise and skin pores: wavelengths 0.004-0.03 and 1500 pore dimples, all below a quad.
  brush_mask_extrude Mask extrusions of 0.03, 0.08, 0.15 with a one-to-two-ring mask blur: steep walls
                    of stretched triangles with sharp rims.
  brush_twist       Rotate brush / swirl: 1/4, 1, 2 and 3 turns at the centre; past one turn the rings
                    fold over (the test head's eye-socket swirls).
  brush_grab        Grab without dyntopo: long slivers, one drag sideways (sheared flank).
  brush_dyntopo_strokes  Dyntopo: coarse base (edge 0.06), two strokes refined to 0.006 (10:1) with a
                    crease and a ridge on them only.
  brush_box_relief  Hard-surface box (40 x 40 per side, slightly rounded): pinched relief groove that
                    folds, crumpled edge, one-vertex spike (the test cube's groove vortex, star pole
                    and spike).

Extreme cases (fur cards, single-sided sheets, thousands of islands, million-face self-intersection
soups) are left out on purpose: research/sculpt-inputs note, "out of scope".
"""
import argparse
import heapq
import json
import os

import numpy as np
from scipy.spatial import cKDTree

from make_synthetic import icosphere, sha256, write_obj
from sculpt_report import input_folds

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


def _blob(level, center, radii, seed, lumpy=True):
    v, f = icosphere(level)
    rng = np.random.default_rng(seed)
    v = v * (1 + 0.15 * rng.normal(size=(len(v), 1)) * (level > 1) * lumpy)
    return v * np.asarray(radii) + np.asarray(center), f


def sculpt_parts():
    parts = [creature(0.01)]
    for s in (-1, 1):
        # Eyeballs, half sunk, smooth. Until 2026-10-21 they had the crumbs' 15 % radial noise, which at
        # this level (edge 0.0145, noise sd 0.011) made them crumpled balls; that, not the sinking, opened
        # them (research/sculpt-defects-2026-10-21.md: topology right 2/6 -> 6/6 at 5k with smooth ones).
        parts.append(_blob(4, (s * 0.17, 1.2, 0.47), (0.075,) * 3, 0, lumpy=False))
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


# ---- the brush set ----------------------------------------------------------------------------
#
# Stand-ins for what single brush strokes leave on a mesh, as Blender's sculpt mode and ZBrush apply
# them: moves of existing vertices, not an implicit, so over-strong strokes fold triangles over the
# way real ones do (the eye swirls and crease lines of the 2026-10-21 test head were folded input).
# Base: unit sphere, icosphere level 7 (327k triangles, edge 0.0095); at 5k quads the quad edge is
# 0.05, so 5 triangle edges. Every mesh carries one brush situation at several strengths, from clean
# to over-strong, so that a defect can be read against the stroke that caused it.

def vertex_normals(V, F):
    N = np.zeros_like(V)
    A = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    for k in range(3):
        np.add.at(N, F[:, k], A)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-300)


def falloff(d, r):
    """Blender's default smooth falloff: 1 at the centre, 0 at r, zero slope at both ends."""
    t = np.clip(d / r, 0, 1)
    return 1 - 3 * t ** 2 + 2 * t ** 3


def on_sphere(theta, phi):
    return np.array([np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)])


def stroke_points(a, b, spacing):
    """Great-circle stroke from a to b (unit vectors), one dab per `spacing`."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ang = np.arccos(np.clip(a @ b, -1, 1))
    n = max(2, int(ang / spacing) + 1)
    t = np.linspace(0, 1, n)
    P = np.sin((1 - t)[:, None] * ang) * a + np.sin(t[:, None] * ang) * b
    return P / np.sin(ang)


def dab(V, c, r):
    d = np.linalg.norm(V - c, axis=1)
    sel = np.flatnonzero(d < r)
    return sel, falloff(d[sel], r)


def brush_base(level=7):
    return icosphere(level)


def brush_clay():
    """Clay Strips buildup: overlapping flat-topped strokes (width 0.08-0.2, height 0.01-0.03), the
    second and third layer over the first; plateaus with soft rims, as blocking out forms leaves."""
    V, F = brush_base()
    rng = np.random.default_rng(11)
    for layer in range(3):
        for _ in range(10):
            a = on_sphere(rng.uniform(0.3, 2.8), rng.uniform(0, 2 * np.pi))
            b = a + rng.normal(scale=0.5, size=3)
            b /= np.linalg.norm(b)
            r, hgt = rng.uniform(0.04, 0.1), rng.uniform(0.004, 0.01)
            for c in stroke_points(a, b, r / 3):
                sel, w = dab(V, c, r)
                if not len(sel):
                    continue
                near = F[np.isin(F, sel).any(1)]  # the faces that make up sel's vertex normals
                n = vertex_normals(V, near)[sel].mean(0)
                n /= np.linalg.norm(n)
                plane = (V[sel] - c) @ n
                top = hgt * (layer + 1)
                V[sel] += (np.clip(top - plane, 0, None) * np.minimum(1, 2 * w))[:, None] * n * 0.5
    return V, F


def brush_crease():
    """Crease / pinch lines: V grooves cut along strokes while the pinch pulls vertices toward the
    line. Pinch per stroke 0.4, 0.8, 1.0 and 1.3 (overshoot: vertices cross the line and their
    triangles fold over, as a repeated Crease stroke or a strong Pinch does); depth 0.01-0.03."""
    V, F = brush_base()
    lines = [((0.4, 0.0), (1.2, 0.6), 0.4, 0.01), ((0.6, 1.5), (1.4, 2.3), 0.8, 0.02),
             ((1.5, 3.2), (2.3, 3.9), 1.0, 0.025), ((1.8, 4.6), (2.6, 5.6), 1.3, 0.03)]
    for (t0, p0), (t1, p1), pinch, depth in lines:
        P = stroke_points(on_sphere(t0, p0), on_sphere(t1, p1), 0.005)
        r = 0.04
        sel = np.flatnonzero(np.min(np.stack([np.linalg.norm(V - c, axis=1) for c in P[::4]]), 0) < r)
        d, nearest = cKDTree(P).query(V[sel])
        w = falloff(d, r)
        n = V[sel] / np.linalg.norm(V[sel], axis=1, keepdims=True)
        V[sel] += (P[nearest] - V[sel]) * (pinch * w)[:, None] - (depth * w ** 2)[:, None] * n
    return V, F


def brush_inflate():
    """Inflate bumps: blobs grown along their own normals in steps (so big ones bulge into an
    undercut), radii 0.015 (below a quad) to 0.2, heights up to 0.12."""
    V, F = brush_base()
    rng = np.random.default_rng(5)
    for k in range(18):
        c = on_sphere(rng.uniform(0.2, 2.9), rng.uniform(0, 2 * np.pi))
        r = float(np.geomspace(0.015, 0.2, 18)[k])
        steps = 8
        for _ in range(steps):
            sel, w = dab(V, c, r)
            V[sel] += (0.6 * r / steps * w)[:, None] * vertex_normals(V, F)[sel]
    return V, F


def brush_pits():
    """Deep pits and sunk eyes on one surface: two eye sockets (radius 0.14, depth 0.12) each with an
    eyeball bulge whose rim leaves a crevice narrower than a quad (the eyelid line), two nostrils
    (radius 0.025, depth 0.06: below quad size) and a mouth slot."""
    V, F = brush_base()
    n = V.copy()
    for s in (-1, 1):
        c = on_sphere(1.25, np.pi / 2 + s * 0.35)
        d = np.linalg.norm(V - c, axis=1)
        V -= (0.12 * falloff(d, 0.14))[:, None] * n  # socket
        ball = 0.11 * np.sqrt(np.clip(1 - (d / 0.085) ** 2, 0, None))
        V += ball[:, None] * n  # eyeball bulge, steep rim: the crevice around it
        c = on_sphere(1.55, np.pi / 2 + s * 0.08)
        V -= (0.06 * falloff(np.linalg.norm(V - c, axis=1), 0.025))[:, None] * n  # nostril
    c0, c1 = on_sphere(1.85, np.pi / 2 - 0.25), on_sphere(1.85, np.pi / 2 + 0.25)
    for c in stroke_points(c0, c1, 0.004):
        sel, w = dab(V, c, 0.02)
        V[sel] -= (0.004 * w)[:, None] * n[sel]  # mouth slot, built up by many dabs
    return V, F


def brush_spikes():
    """Thin spikes and tips: Snake Hook pulls without dyntopo, so a few vertices are dragged out into
    horns of stretched slivers; lengths 0.1-0.5, tips far below quad size; one hooked spike bends
    back over the surface."""
    V, F = brush_base()
    pulls = [((0.5, 0.3), 0.1, 0.0), ((0.9, 1.7), 0.2, 0.0), ((1.4, 3.0), 0.35, 0.0),
             ((2.0, 4.4), 0.5, 0.0), ((2.5, 5.5), 0.4, 1.2)]
    for (t, p), length, hook in pulls:
        c = on_sphere(t, p)
        tangent = np.cross(c, [0, 0, 1])
        tangent /= np.linalg.norm(tangent)
        steps = 20
        for i in range(steps):
            r = 0.05 * (1 - 0.7 * i / steps)
            sel, w = dab(V, c, r)
            direction = c * np.cos(hook * i / steps) + tangent * np.sin(hook * i / steps)
            move = (length / steps) * direction
            V[sel] += w[:, None] * move
            c = c + move
    return V, F


def brush_layers():
    """Layered folds: drapery made by Fold/Layer strokes, sine wrinkles (wavelength 0.06-0.12) whose
    tangential push grows from 0.5x to 1.5x the fold slope limit across the band, so the stiffer
    folds overhang and their triangles fold over (cloth pleats)."""
    V, F = brush_base()
    n = V.copy()
    z = V[:, 2]
    band = np.clip(1 - np.abs(z) / 0.45, 0, 1)
    phi = np.arctan2(V[:, 1], V[:, 0])
    wavelength = 0.06 + 0.06 * (phi + np.pi) / (2 * np.pi)
    k = 2 * np.pi / wavelength
    amp = 0.012 * band
    over = 0.5 + 1.0 * (phi + np.pi) / (2 * np.pi)  # tangential push in units of the fold limit 1/k
    up = np.stack([-V[:, 0] * V[:, 2], -V[:, 1] * V[:, 2], 1 - V[:, 2] ** 2], 1)
    up /= np.maximum(np.linalg.norm(up, axis=1, keepdims=True), 1e-12)
    V = V + (amp * np.sin(k * z))[:, None] * n + (over * band * np.cos(k * z) / k)[:, None] * up
    return V, F


def brush_noise():
    """Noise and skin pores: displacement with wavelengths 0.004-0.03 (all below a 5k quad) and
    amplitude 0.001-0.003 over the whole sphere, plus pore dimples of radius 0.006 on one half."""
    V, F = brush_base()
    rng = np.random.default_rng(9)
    W = rng.normal(size=(32, 3))
    W /= np.linalg.norm(W, axis=1, keepdims=True)
    L = np.geomspace(0.004, 0.03, 32)
    ph = rng.uniform(0, 2 * np.pi, 32)
    d = (L * 0.08) @ np.sin((2 * np.pi / L)[:, None] * (W @ V.T) + ph[:, None]) / 4
    n = V.copy()
    V = V + d[:, None] * n
    for c in rng.normal(size=(1500, 3)):
        c = np.abs(c) * [1, 1, 1] / np.linalg.norm(c)
        sel, w = dab(V, c, 0.006)
        V[sel] -= (0.002 * w)[:, None] * n[sel]
    return V, F


def brush_mask_extrude():
    """Mask extrusions: three masked regions moved out along the normal by 0.03, 0.08 and 0.15 with a
    mask blurred over one or two triangle rings, so the walls are steep strips of stretched
    triangles with a sharp rim at top and bottom (Mask + Grab/Inflate, or a mask extract fused back)."""
    V, F = brush_base()
    n = V.copy()
    for (t, p), r, h in (((0.7, 0.5), 0.12, 0.03), ((1.6, 2.5), 0.18, 0.08), ((2.3, 4.5), 0.1, 0.15)):
        c = on_sphere(t, p)
        d = np.linalg.norm(V - c, axis=1)
        mask = np.clip((r - d) / 0.012 + 0.5, 0, 1)
        V += (h * mask)[:, None] * n
    return V, F


def brush_twist():
    """Twist: the Rotate brush (or a swirl stroke) spun 1/4, 1, 2 and 3 turns at the centre over radii
    0.05-0.12, with a little inward pull; past about one turn the inner rings shear over the outer
    ones and fold, the swirl seen in the test head's eye sockets."""
    V, F = brush_base()
    for (t, p), r, turns in (((0.6, 0.2), 0.1, 0.25), ((1.2, 1.8), 0.12, 1.0), ((1.9, 3.4), 0.08, 2.0),
                             ((2.4, 5.0), 0.05, 3.0)):
        c = on_sphere(t, p)
        sel, w = dab(V, c, r)
        rel = V[sel] - c
        ang = 2 * np.pi * turns * w
        # rotation about the axis c through c (Rodrigues)
        k = c
        cos, sin = np.cos(ang)[:, None], np.sin(ang)[:, None]
        rot = rel * cos + np.cross(k, rel) * sin + np.outer(rel @ k, k) * (1 - cos)
        V[sel] = c + rot * (1 - 0.15 * w)[:, None]
    return V, F


def brush_grab():
    """Grab drags without dyntopo: big pulls (0.3-0.4 over radius 0.25-0.3) that stretch triangles into
    long slivers, one dragged sideways so one flank is sheared and the other compressed."""
    V, F = brush_base()
    for (t, p), r, move in (((0.8, 0.0), 0.3, (0, 0, 0.35)), ((1.6, 2.1), 0.25, None), ((2.2, 4.2), 0.25, "side")):
        c = on_sphere(t, p)
        sel, w = dab(V, c, r)
        if move is None:
            m = c * 0.4
        elif move == "side":
            tng = np.cross(c, [0, 0, 1])
            m = 0.3 * tng / np.linalg.norm(tng) + 0.1 * c
        else:
            m = np.asarray(move, float)
        V[sel] += (w ** 0.5)[:, None] * m
    return V, F


def brush_dyntopo_strokes():
    """Dyntopo-style uneven triangles: coarse base (edge 0.06) where nothing was sculpted, strokes
    refined by edge splits to 0.006 (10:1) with crease and inflate detail on them only."""
    V, F = icosphere(5)
    P = np.concatenate([stroke_points(on_sphere(0.6, 0.0), on_sphere(1.6, 1.4), 0.01),
                        stroke_points(on_sphere(1.4, 3.0), on_sphere(2.4, 4.0), 0.01)])
    tree = cKDTree(P)
    V, F = split_edges(V, F, lambda m: 0.006 if tree.query(m)[0] < 0.06 else 1e9)
    V = V / np.linalg.norm(V, axis=1, keepdims=True)
    d, _ = tree.query(V)
    n = V.copy()
    V = V - (0.015 * falloff(d, 0.015))[:, None] * n + (0.02 * falloff(np.abs(d - 0.035), 0.012))[:, None] * n
    return V, F


def brush_box_relief():
    """Hard-surface sculpt like the test cube: a box (side 2, edges rounded by 0.05) sculpted with a
    relief groove pinched on one face, a crumpled edge (random jitter of 0.6 edge lengths) and a
    single-vertex spike on top, from a 40 x 40 grid per face (coarse, like a cube subdivided a few times)."""
    import igl
    n = 40
    g = np.linspace(-1, 1, n + 1)
    Vs, Fs, off = [], [], 0
    for axis in range(3):
        for sgn in (-1, 1):
            U, W = np.meshgrid(g, g, indexing="ij")
            P = np.zeros((U.size, 3))
            o = [a for a in range(3) if a != axis]
            P[:, axis] = sgn
            P[:, o[0]], P[:, o[1]] = U.ravel(), W.ravel()
            idx = np.arange(U.size).reshape(n + 1, n + 1)
            q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
            if sgn * (1 if axis != 1 else -1) < 0:
                q = q[:, ::-1]
            Fs.append(np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]]) + off)
            Vs.append(P)
            off += len(P)
    V, F = np.concatenate(Vs), np.concatenate(Fs)
    V, _, _, F = igl.remove_duplicate_vertices(V, np.asfortranarray(F, np.int32), 1e-9)
    V, F = np.asarray(V, float), np.asarray(F, np.int64)
    # orient outward
    C = V[F].mean(1)
    N = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    flip = np.einsum("ij,ij->i", N, C) < 0
    F[flip] = F[flip][:, ::-1]
    # round the edges a little: pull toward a superellipsoid
    p = 12
    V = V / (np.sum(np.abs(V) ** p, axis=1) ** (1 / p))[:, None]
    rng = np.random.default_rng(4)
    e = 2 / n
    # relief groove on +x: pinched V line along a wavy path
    P = np.stack([np.ones(200), np.linspace(-0.7, 0.7, 200), 0.3 * np.sin(np.linspace(0, 3 * np.pi, 200))], 1)
    tree = cKDTree(P)
    top = np.flatnonzero(V[:, 0] > 0.9)
    d, near = tree.query(V[top])
    w = falloff(d, 0.12)
    V[top] += (P[near] - V[top]) * (1.1 * w)[:, None] * [0, 1, 1]
    V[top, 0] -= 0.08 * w ** 2
    # crumpled edge: jitter around the edge x = -1, y = -1
    crum = np.flatnonzero((V[:, 0] < -0.85) & (V[:, 1] < -0.85))
    V[crum] += rng.normal(scale=0.6 * e, size=(len(crum), 3))
    # spike on top: one vertex pulled out (Snake Hook on a coarse mesh)
    tip = np.argmin(np.linalg.norm(V - (0.3, 0.2, 1.0), axis=1))
    V[tip] += (0, 0, 0.35)
    return V, F


BRUSH_JOBS = {"brush_clay": brush_clay, "brush_crease": brush_crease, "brush_inflate": brush_inflate,
              "brush_pits": brush_pits, "brush_spikes": brush_spikes, "brush_layers": brush_layers,
              "brush_noise": brush_noise, "brush_mask_extrude": brush_mask_extrude, "brush_twist": brush_twist,
              "brush_grab": brush_grab, "brush_dyntopo_strokes": brush_dyntopo_strokes,
              "brush_box_relief": brush_box_relief}


JOBS = {"sculpt_voxel": sculpt_voxel, "sculpt_steps": sculpt_steps,
        "sculpt_degenerate": sculpt_degenerate, "sculpt_dyntopo": sculpt_dyntopo,
        "sculpt_decimated": sculpt_decimated, "sculpt_parts": sculpt_parts, "sculpt_dirty": sculpt_dirty}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="comma list of mesh names")
    ap.add_argument("--set", choices=["sculpt", "brush"], default="sculpt",
                    help="sculpt: the seven tessellations (default); brush: the brush stand-ins")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    jobs = BRUSH_JOBS if args.set == "brush" else JOBS
    names = args.only.split(",") if args.only else list(jobs)
    manifest_path = os.path.join(args.out, args.set + "-manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    voxel = None
    for name in names:
        if name == "sculpt_decimated":
            V, F = sculpt_decimated(voxel)
        else:
            V, F = {**JOBS, **BRUSH_JOBS}[name]()
        if name == "sculpt_voxel":
            voxel = (V, F)
        path = write_obj(os.path.join(args.out, name + ".obj"), V, F)
        manifest[name] = {"vertices": int(len(V)), "triangles": int(len(F)), "sha256": sha256(path)}
        if name in BRUSH_JOBS:
            manifest[name]["folded_triangles"] = int(input_folds(V, F).sum())
        print(name, manifest[name], flush=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    main()
