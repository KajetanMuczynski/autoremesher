#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate the procedural part of the AutoRemesher baseline corpus.

Every mesh here is computed from code (or from a downloaded public-domain mesh
plus a seeded perturbation), so it has no license constraints of its own and
can be regenerated bit-for-bit with the same library versions.

    python make_synthetic.py --downloads meshes/downloads --out meshes/synthetic [--ladder]

Meshes (symmetry plane x = 0 where noted):
  csg_bracket      hard-surface CAD part: chamfered plate, holes, boss, ribs (manifold3d);
                   CAD-style triangulation with long thin triangles. Symmetric.
  blob_sym         organic "creature" from a smooth-union implicit, marching cubes. Symmetric.
  cloth_sheet      open single-layer surface with folds and a free boundary (thin shell, open).
  thin_leaf        closed shell 2.0 x 0.9 x 0.012, thinner than the target quad size (thin shell, closed).
  spot_noisy       spot (public domain) + Gaussian displacement along normals, sigma = 0.3% bbox diagonal.
  spot_x8          8 translated copies of spot (8 islands; parallelism test).
  koala_sub{1,2,3} Loop subdivisions of koala (CC BY 3.0) for the input-size ladder (--ladder).
"""
import argparse
import hashlib
import json
import os

import numpy as np


def write_obj(path, V, F):
    with open(path, "w") as f:
        f.write("".join("v %.9g %.9g %.9g\n" % tuple(v) for v in V))
        f.write("".join("f %d %d %d\n" % (a + 1, b + 1, c + 1) for a, b, c in F))
    return path


def read_obj(path):
    """Positions + fan-triangulated faces, indexed by position like tinyobj/AutoRemesher."""
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


def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-300)


def csg_bracket():
    from manifold3d import Manifold

    M = Manifold

    def box(sx, sy, sz, at=(0, 0, 0)):
        return M.cube([sx, sy, sz], True).translate(list(at))

    def chamfered_box(sx, sy, sz, c, at=(0, 0, 0)):
        return M.batch_hull([box(sx - 2 * c, sy - 2 * c, sz, at), box(sx - 2 * c, sy, sz - 2 * c, at),
                             box(sx, sy - 2 * c, sz - 2 * c, at)])

    def cyl(r, h, at, n=64):
        return M.cylinder(h, r, r, n, True).translate(list(at))

    body = chamfered_box(4.0, 2.0, 0.8, 0.1)
    boss = cyl(0.7, 0.8, (0, 0, 0.7))
    ribs = box(0.15, 1.6, 0.5, (0.9, 0, 0.55)) + box(0.15, 1.6, 0.5, (-0.9, 0, 0.55))
    part = body + boss + ribs
    part = part - cyl(0.3, 3.0, (1.5, 0, 0)) - cyl(0.3, 3.0, (-1.5, 0, 0)) - cyl(0.35, 3.0, (0, 0, 0.5))
    part = part - box(2.6, 0.25, 0.3, (0, 0.75, 0.4)) - box(2.6, 0.25, 0.3, (0, -0.75, 0.4))
    mesh = part.to_mesh()
    return np.asarray(mesh.vert_properties[:, :3], float), np.asarray(mesh.tri_verts, np.int64)


def blob_sym(n=161):
    from skimage.measure import marching_cubes

    lin = np.linspace(-1.2, 1.2, n)  # odd n: x = 0 is a grid plane, grid symmetric in x
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")

    def ellipsoid(c, r):
        return (np.sqrt(((X - c[0]) / r[0]) ** 2 + ((Y - c[1]) / r[1]) ** 2 + ((Z - c[2]) / r[2]) ** 2) - 1) * min(r)

    def capsule(a, b, r):
        a, b = np.asarray(a, float), np.asarray(b, float)
        P = np.stack([X, Y, Z], -1)
        ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        return np.linalg.norm(P - (a + t[..., None] * ab), axis=-1) - r

    def smin(a, b, k=0.12):
        h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
        return b * (1 - h) + a * h - k * h * (1 - h)

    d = ellipsoid((0, 0, 0), (0.55, 0.8, 0.45))
    d = smin(d, ellipsoid((0, 0.85, 0.25), (0.32, 0.3, 0.3)))
    for s in (-1, 1):
        d = smin(d, capsule((s * 0.3, 0.45, -0.1), (s * 0.55, 0.5, -0.85), 0.11))
        d = smin(d, capsule((s * 0.3, -0.45, -0.1), (s * 0.5, -0.55, -0.85), 0.12))
        d = smin(d, capsule((s * 0.12, 1.0, 0.5), (s * 0.28, 1.05, 0.85), 0.06), 0.06)  # ears
        d = smin(d, ellipsoid((s * 0.6, 0.1, 0.15), (0.15, 0.35, 0.2)), 0.08)  # flanks
    d = smin(d, capsule((0, -0.75, 0.1), (0, -1.1, 0.45), 0.07), 0.08)  # tail
    verts, faces, _, _ = marching_cubes(d, 0.0, spacing=(lin[1] - lin[0],) * 3)
    verts = verts + lin[0]
    return verts, faces[:, ::-1].astype(np.int64)


def cloth_sheet(n=181):
    u = np.linspace(-1, 1, n)
    X, Y = np.meshgrid(u, u, indexing="ij")
    Z = (0.12 * np.sin(3 * X + 0.5) * np.cos(2 * Y) + 0.18 * np.exp(-((X - 0.3) ** 2 + (Y + 0.2) ** 2) / 0.08)
         + 0.04 * np.sin(14 * (X + 0.35 * Y)) * np.exp(-(Y - 0.4) ** 2 / 0.1))
    V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    idx = np.arange(n * n).reshape(n, n)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    F = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    return V, F


def icosphere(level):
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
                  [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    F = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
                  [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5],
                  [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
    for _ in range(level):
        edges = {}
        verts = list(V)
        newF = []

        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key not in edges:
                edges[key] = len(verts)
                verts.append((verts[i] + verts[j]) / 2)
            return edges[key]

        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            newF += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        V, F = np.array(verts), np.array(newF)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    return V, F.astype(np.int64)


def thin_leaf():
    V, F = icosphere(5)
    V = V * np.array([1.0, 0.45, 0.006])
    V[:, 2] += 0.25 * V[:, 0] ** 2 - 0.15 * V[:, 1] ** 2  # bend, keeps x-symmetry
    return V, F


def spot_noisy(spot_path, sigma_rel=0.003, seed=1):
    V, F = read_obj(spot_path)
    diag = np.linalg.norm(V.max(0) - V.min(0))
    rng = np.random.default_rng(seed)
    V = V + vertex_normals(V, F) * rng.normal(0, sigma_rel * diag, (len(V), 1))
    return V, F


def spot_x8(spot_path):
    V, F = read_obj(spot_path)
    ext = V.max(0) - V.min(0)
    Vs, Fs = [], []
    for k, (i, j, l) in enumerate(np.ndindex(2, 2, 2)):
        Vs.append(V + ext * 1.2 * np.array([i, j, l]))
        Fs.append(F + k * len(V))
    return np.concatenate(Vs), np.concatenate(Fs)


def koala_ladder(koala_path, levels):
    import igl

    V, F = read_obj(koala_path)
    out = {}
    for k in range(1, max(levels) + 1):
        V, F = igl.loop(V, F)
        if k in levels:
            out[k] = (V.copy(), F.copy())
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", required=True, help="folder with spot.obj and koala.obj from fetch_meshes.sh")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ladder", action="store_true", help="also write koala_sub1..3 (0.4M, 1.6M, 6.4M triangles)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    spot = os.path.join(args.downloads, "spot.obj")
    jobs = {
        "csg_bracket": csg_bracket,
        "blob_sym": blob_sym,
        "cloth_sheet": cloth_sheet,
        "thin_leaf": thin_leaf,
        "spot_noisy": lambda: spot_noisy(spot),
        "spot_x8": lambda: spot_x8(spot),
    }
    manifest = {}
    for name, make in jobs.items():
        V, F = make()
        path = write_obj(os.path.join(args.out, name + ".obj"), V, F)
        manifest[name] = {"vertices": int(len(V)), "triangles": int(len(F)), "sha256": sha256(path)}
        print(name, manifest[name])
    if args.ladder:
        for k, (V, F) in koala_ladder(os.path.join(args.downloads, "koala.obj"), [1, 2, 3]).items():
            name = "koala_sub%d" % k
            path = write_obj(os.path.join(args.out, name + ".obj"), V, F)
            manifest[name] = {"vertices": int(len(V)), "triangles": int(len(F)), "sha256": sha256(path)}
            print(name, manifest[name])
    with open(os.path.join(args.out, "synthetic-manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    main()
