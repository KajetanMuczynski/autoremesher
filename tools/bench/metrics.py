#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Quality metrics for a remeshed (quad-dominant) mesh against its input.

    python metrics.py --input in.obj --output out.obj [--target-quads N]
                      [--sym-axis x --sym-center 0] [--samples 200000] [--json m.json]

Needs numpy, scipy and libigl (python bindings, `pip install libigl`).

Reported groups (all lengths relative to the input bounding-box diagonal unless
named *_rel_edge, which are relative to the output mean edge length):
  faces       counts by size, quad fraction, achieved / requested quads
  topology    edges by use (boundary / manifold / non-manifold), inconsistently
              oriented edges, components, Euler characteristic in vs out
  valence     histogram of interior and boundary vertex valence, irregular
              (interior valence != 4) count and per 1k quads
  quads       corner-angle deviation from 90 deg, scaled Jacobian (min over the
              4 corners, w.r.t. the quad's Newell normal; <= 0 means folded or
              non-convex), edge-length aspect ratio
  degenerate  faces with a repeated vertex, near-zero area or near-zero edge
  flipped     output faces whose normal opposes the input normal at the closest
              input point (minority orientation, so a globally reversed output
              counts as reversed, not as all-flipped)
  distance    one-sided mean / max and two-sided Hausdorff on area samples
  symmetry    (with --sym-axis) input reflection error, output geometric
              reflection error, and output *topological* symmetry: distance from
              each reflected output vertex to the nearest output vertex, in mean
              edge lengths (0 for a mirror-symmetric layout)
"""
import argparse
import json
import sys

import numpy as np
from scipy.spatial import cKDTree

try:
    import igl
except ImportError:  # pragma: no cover
    sys.exit("metrics.py needs libigl: pip install libigl")


def read_obj(path):
    """Positions and polygon faces (position indices, 0-based), like tinyobj without triangulation."""
    with open(path) as f:
        lines = f.read().splitlines()
    vlines = [l[2:] for l in lines if l.startswith("v ")]
    V = np.array(" ".join(vlines).split(), dtype=float).reshape(-1, 3) if vlines else np.zeros((0, 3))
    faces = []
    for l in lines:
        if l.startswith("f "):
            faces.append([int(t.split("/")[0]) - 1 for t in l.split()[1:]])
    return V, faces


def triangulate(faces):
    tris = []
    for f in faces:
        for k in range(1, len(f) - 1):
            tris.append((f[0], f[k], f[k + 1]))
    return np.asarray(tris, dtype=np.int64).reshape(-1, 3)


def sample_surface(V, F, n, rng):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    if area.sum() <= 0:
        return V.copy()
    idx = rng.choice(len(F), size=n, p=area / area.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    return (1 - s)[:, None] * a[idx] + (s * (1 - r2))[:, None] * b[idx] + (s * r2)[:, None] * c[idx]


def stats(x, prefix=""):
    x = np.asarray(x, float)
    if x.size == 0:
        return {}
    return {prefix + "mean": float(x.mean()), prefix + "p50": float(np.percentile(x, 50)),
            prefix + "p95": float(np.percentile(x, 95)), prefix + "max": float(x.max()), prefix + "min": float(x.min())}


def point_to_mesh(P, V, F, chunk=200000):
    d2 = np.empty(len(P))
    fi = np.empty(len(P), dtype=np.int64)
    for s in range(0, len(P), chunk):
        dd, ii, _ = igl.point_mesh_squared_distance(P[s:s + chunk], V, F)
        d2[s:s + chunk] = dd
        fi[s:s + chunk] = ii
    return np.sqrt(np.maximum(d2, 0)), fi


def newell(V, face):
    p = V[face]
    q = np.roll(p, -1, axis=0)
    return np.array([np.sum((p[:, 1] - q[:, 1]) * (p[:, 2] + q[:, 2])),
                     np.sum((p[:, 2] - q[:, 2]) * (p[:, 0] + q[:, 0])),
                     np.sum((p[:, 0] - q[:, 0]) * (p[:, 1] + q[:, 1]))])


def compute(input_path, output_path, target_quads=None, sym_axis=None, sym_center=0.0, samples=200000, seed=0):
    rng = np.random.default_rng(seed)
    Vin, fin = read_obj(input_path)
    Fin = triangulate(fin)
    used_in = np.unique(Fin)
    diag = float(np.linalg.norm(Vin[used_in].max(0) - Vin[used_in].min(0)))
    V, faces = read_obj(output_path)
    out = {"input": input_path, "output": output_path, "diag": diag}
    if not faces:
        out["ok"] = False
        return out
    out["ok"] = True

    sizes = np.array([len(f) for f in faces])
    nq = int((sizes == 4).sum())
    out["faces"] = {"total": int(len(faces)), "quads": nq, "triangles": int((sizes == 3).sum()),
                    "pentagons": int((sizes == 5).sum()), "other": int((sizes > 5).sum()),
                    "quad_fraction": nq / len(faces), "vertices": int(len(V))}
    if target_quads:
        out["faces"]["target_quads"] = int(target_quads)
        out["faces"]["quads_over_target"] = nq / float(target_quads)

    # Edges and orientation.
    he = np.array([(f[i], f[(i + 1) % len(f)]) for f in faces for i in range(len(f))], dtype=np.int64)
    lo, hi = he.min(1), he.max(1)
    key = lo * len(V) + hi
    uniq, inv, counts = np.unique(key, return_inverse=True, return_counts=True)
    fwd = (he[:, 0] < he[:, 1]).astype(np.int64)
    fwd_count = np.bincount(inv, weights=fwd, minlength=len(uniq))
    manifold = counts == 2
    inconsistent = int(np.sum(manifold & (fwd_count != 1)))
    E = np.stack([uniq // len(V), uniq % len(V)], 1)
    bnd = E[counts == 1]
    used = np.unique(he[:, 0])
    out["topology"] = {"edges": int(len(uniq)), "boundary_edges": int((counts == 1).sum()),
                       "non_manifold_edges": int((counts > 2).sum()), "inconsistently_oriented_edges": inconsistent,
                       "unused_vertices": int(len(V) - len(used))}
    # Components and Euler characteristic (output vs input).
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    def comps(n, edges):
        A = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(n, n))
        return connected_components(A, directed=False)[1]

    lab = comps(len(V), E)
    out["topology"]["components"] = int(len(np.unique(lab[used])))
    out["topology"]["euler_output"] = int(len(used) - len(uniq) + len(faces))
    ein = np.unique(np.sort(np.concatenate([Fin[:, [0, 1]], Fin[:, [1, 2]], Fin[:, [2, 0]]]), axis=1), axis=0)
    out["topology"]["euler_input"] = int(len(used_in) - len(ein) + len(Fin))
    out["topology"]["components_input"] = int(len(np.unique(comps(len(Vin), ein)[used_in])))

    # Valence.
    val = np.bincount(E.ravel(), minlength=len(V))
    is_b = np.zeros(len(V), bool)
    is_b[bnd.ravel()] = True
    interior = used[~is_b[used]]
    boundary = used[is_b[used]]
    hist = lambda x: {str(k): int(v) for k, v in zip(*np.unique(np.minimum(x, 9), return_counts=True))}
    irregular = int(np.sum(val[interior] != 4))
    out["valence"] = {"interior_hist": hist(val[interior]), "boundary_hist": hist(val[boundary]),
                      "interior_vertices": int(len(interior)), "irregular_interior": irregular,
                      "irregular_per_1k_quads": 1000.0 * irregular / max(nq, 1),
                      "valence3": int(np.sum(val[interior] == 3)), "valence5": int(np.sum(val[interior] == 5)),
                      "valence6plus": int(np.sum(val[interior] >= 6)),
                      "irregular_boundary": int(np.sum(val[boundary] != 3))}

    # Per-face geometry.
    normals = np.array([newell(V, f) for f in faces])
    area = 0.5 * np.linalg.norm(normals, axis=1)
    edge_len = np.linalg.norm(V[he[:, 1]] - V[he[:, 0]], axis=1)
    mean_edge = float(edge_len.mean())
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    min_edge = np.minimum.reduceat(edge_len, starts)
    repeated = np.array([len(set(f)) != len(f) for f in faces])
    degenerate = repeated | (area < 1e-10 * diag * diag) | (min_edge < 1e-7 * diag)
    out["degenerate"] = {"faces": int(degenerate.sum()), "repeated_vertex": int(repeated.sum())}
    out["edge_length"] = {"mean_rel_diag": mean_edge / diag, "cv": float(edge_len.std() / mean_edge)}

    quads = np.array([f for f in faces if len(f) == 4], dtype=np.int64).reshape(-1, 4)
    if len(quads):
        P = V[quads]
        n = np.array([newell(V, q) for q in quads])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-300)
        nxt = np.roll(P, -1, axis=1) - P
        prv = np.roll(P, 1, axis=1) - P
        ln, lp = np.linalg.norm(nxt, axis=2), np.linalg.norm(prv, axis=2)
        cosang = np.clip(np.sum(nxt * prv, axis=2) / np.maximum(ln * lp, 1e-300), -1, 1)
        ang = np.degrees(np.arccos(cosang))
        dev = np.abs(ang - 90.0)
        sj = np.sum(np.cross(nxt, prv) * n[:, None, :], axis=2) / np.maximum(ln * lp, 1e-300)
        sjmin = sj.min(1)
        aspect = ln.max(1) / np.maximum(ln.min(1), 1e-300)
        out["quads"] = {**stats(dev.ravel(), "angle_dev_"),
                        "angle_dev_gt30": float(np.mean(dev.max(1) > 30)),
                        "angle_dev_gt45": float(np.mean(dev.max(1) > 45)),
                        "min_angle": float(ang.min()), "max_angle": float(ang.max()),
                        **stats(sjmin, "sj_"),
                        "sj_lt_0.5": float(np.mean(sjmin < 0.5)), "sj_lt_0.2": float(np.mean(sjmin < 0.2)),
                        "sj_le_0": int(np.sum(sjmin <= 0)), **stats(aspect, "aspect_"),
                        "angle_hist_10deg": np.histogram(ang.ravel(), bins=18, range=(0, 180))[0].tolist(),
                        "sj_hist": np.histogram(sjmin, bins=10, range=(-1, 1))[0].tolist()}

    # Flips against the input surface and distances.
    Ftri = triangulate(faces)
    cent = np.array([V[f].mean(0) for f in faces])
    _, cf = point_to_mesh(cent, Vin, Fin)
    nin = np.cross(Vin[Fin[cf, 1]] - Vin[Fin[cf, 0]], Vin[Fin[cf, 2]] - Vin[Fin[cf, 0]])
    dots = np.sum(nin * normals, axis=1)
    neg = int(np.sum(dots < 0))
    out["flipped"] = {"faces_vs_input": min(neg, len(faces) - neg),
                      "output_reversed": bool(neg > len(faces) - neg)}
    Pout = np.concatenate([sample_surface(V, Ftri, samples, rng), V[used]])
    d_out, _ = point_to_mesh(Pout, Vin, Fin)
    Pin = np.concatenate([sample_surface(Vin, Fin, samples, rng), Vin[rng.choice(used_in, min(len(used_in), samples))]])
    d_in, _ = point_to_mesh(Pin, V, Ftri)
    out["distance"] = {"out_to_in_mean": float(d_out.mean() / diag), "out_to_in_max": float(d_out.max() / diag),
                       "in_to_out_mean": float(d_in.mean() / diag), "in_to_out_max": float(d_in.max() / diag),
                       "hausdorff": float(max(d_out.max(), d_in.max()) / diag),
                       "in_to_out_p99": float(np.percentile(d_in, 99) / diag)}

    if sym_axis:
        a = "xyz".index(sym_axis)

        def reflect(P):
            R = P.copy()
            R[:, a] = 2 * sym_center - R[:, a]
            return R

        d_sym_in, _ = point_to_mesh(reflect(Vin[used_in]), Vin, Fin)
        d_sym_geo, _ = point_to_mesh(reflect(V[used]), V, Ftri)
        dv, _ = cKDTree(V[used]).query(reflect(V[used]))
        dv /= mean_edge
        out["symmetry"] = {"axis": sym_axis, "center": sym_center,
                           "input_reflection_max": float(d_sym_in.max() / diag),
                           "output_reflection_mean": float(d_sym_geo.mean() / diag),
                           "output_reflection_max": float(d_sym_geo.max() / diag),
                           **stats(dv, "topo_vertex_rel_edge_"),
                           "topo_matched_lt_0.1_edge": float(np.mean(dv < 0.1))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--target-quads", type=int)
    ap.add_argument("--sym-axis", choices=["x", "y", "z"])
    ap.add_argument("--sym-center", type=float, default=0.0)
    ap.add_argument("--samples", type=int, default=200000)
    ap.add_argument("--json")
    args = ap.parse_args()
    res = compute(args.input, args.output, args.target_quads, args.sym_axis, args.sym_center, args.samples)
    text = json.dumps(res, indent=1)
    if args.json:
        with open(args.json, "w") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
