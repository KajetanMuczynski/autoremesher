# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""make_stress builds closed manifold meshes, and stress_report's thickness probe measures them.

    python -m unittest discover -s tools/bench/tests -v      (needs numpy, scipy, libigl)
"""
import collections
import os
import sys
import tempfile
import unittest

import numpy as np

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH)
import make_stress  # noqa: E402
from make_synthetic import write_obj  # noqa: E402
from stress_report import local_thickness  # noqa: E402


def edge_uses(F):
    """Directed-edge counts: a closed, consistently oriented manifold uses every edge once each way."""
    return collections.Counter((int(a), int(b)) for f in F for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])))


class ClosedMeshes(unittest.TestCase):
    def assertClosedOriented(self, V, F, euler=2):
        uses = edge_uses(F)
        self.assertTrue(all(n == 1 for n in uses.values()), "an edge is used twice in one direction")
        self.assertTrue(all((b, a) in uses for a, b in uses), "boundary edge")
        self.assertEqual(len(V) - len(uses) // 2 + len(F), euler)
        # Outward: positive signed volume.
        vol = np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6
        self.assertGreater(vol, 0)

    def test_icosphere(self):
        V, F = make_stress.icosphere(3)
        self.assertEqual(len(F), 20 * 4 ** 3)
        np.testing.assert_allclose(np.linalg.norm(V, axis=1), 1.0)
        self.assertClosedOriented(V, F)

    def test_capsule_and_cone(self):
        for r, L in ((0.002, 1.0), (0.1, 0.25)):
            V, F = make_stress.capsule(r, L)
            self.assertClosedOriented(V, F)
            self.assertAlmostEqual(V[:, 2].max() - V[:, 2].min(), L + 2 * r)
        self.assertClosedOriented(*make_stress.cone(10, 0.6, base_r=0.1))

    def test_slivers_have_no_t_junctions(self):
        _, (V, F), params, _ = next(make_stress.fam_degenerate(None))
        self.assertClosedOriented(V, F)
        self.assertGreater(params["edge_ratio_p99_p1"], 100)


class Thickness(unittest.TestCase):
    def test_capsule_diameter(self):
        """A capsule next to a sphere: the thinnest points are the capsule's diameter, and the
        per-island points find it although it has 0.5 % of the area."""
        r = 0.01
        Vc, Fc = make_stress.capsule(r, 1.0)
        V, F = make_stress.merge(make_stress.icosphere(4), (Vc + np.array([1.5, 0, -0.5]), Fc))
        with tempfile.TemporaryDirectory() as d:
            t, w = local_thickness(write_obj(os.path.join(d, "m.obj"), V, F), n=500)
        # The march takes geometric steps of x1.22, so it overshoots by at most that factor.
        self.assertGreaterEqual(np.min(t), 2 * r * 0.98)
        self.assertLess(np.min(t), 2 * r * 1.22)
        self.assertAlmostEqual(np.median(t[w > 0]), 2.0, delta=0.2)  # the sphere: its diameter


if __name__ == "__main__":
    unittest.main()
