# SPDX-License-Identifier: GPL-3.0-or-later
"""sculpt_report.input_folds finds folded-over input (the brush set's twists and pleats) and nothing on
smooth or creased surfaces.

    python -m unittest discover -s tools/bench/tests -v      (needs numpy, scipy)
"""
import os
import sys
import unittest

import numpy as np

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH)
from make_synthetic import icosphere  # noqa: E402
from sculpt_report import input_folds  # noqa: E402


def grid(n, height):
    """Unit square as an n x n triangle grid, z = height(x, y), normals up."""
    x, y = np.meshgrid(np.linspace(0, 1, n + 1), np.linspace(0, 1, n + 1), indexing="ij")
    V = np.stack([x.ravel(), y.ravel(), height(x.ravel(), y.ravel())], 1)
    F = []
    for a in range(n):
        for b in range(n):
            p, q, r, s = a * (n + 1) + b, (a + 1) * (n + 1) + b, (a + 1) * (n + 1) + b + 1, a * (n + 1) + b + 1
            F += [[p, q, r], [p, r, s]]
    return V, np.array(F)


class InputFolds(unittest.TestCase):
    def test_sphere_has_none(self):
        V, F = icosphere(3)
        self.assertEqual(int(input_folds(V, F).sum()), 0)

    def test_sharp_crease_is_not_a_fold(self):
        V, F = grid(40, lambda x, y: 0.3 * np.abs(x - 0.5))  # 33 degree V ridge: sharp, not folded
        self.assertEqual(int(input_folds(V, F, 0.05).sum()), 0)

    def test_pleat_is_found_where_it_is(self):
        V, F = grid(60, lambda x, y: 0 * x)
        # A pleat narrower than the radius: the band 0.48 < x < 0.52 is turned over in place.
        band = (V[:, 0] > 0.48) & (V[:, 0] < 0.52)
        V[band, 0] = 1.0 - V[band, 0]
        V[band, 2] = 0.01
        folds = input_folds(V, F, 0.05)
        self.assertGreater(int(folds.sum()), 0)
        x = V[F[folds]].mean(1)[:, 0]
        self.assertTrue(np.all(np.abs(x - 0.5) < 0.1))

    def test_thin_sheet_is_not_a_fold(self):
        # Both sides of a closed sheet thinner than the radius face each other at close range.
        V, F = icosphere(4)
        V[:, 2] *= 0.01
        self.assertEqual(int(input_folds(V, F, 0.1).sum()), 0)

    def test_swirl_twisted_past_one_turn_is_found(self):
        V, F = icosphere(5)
        c = np.array([0.0, 0.0, 1.0])
        d = np.linalg.norm(V - c, axis=1)
        sel = d < 0.15
        t = d[sel] / 0.15
        ang = 2 * np.pi * 3 * (1 - 3 * t ** 2 + 2 * t ** 3)
        x, y = V[sel, 0], V[sel, 1]
        V[sel, 0], V[sel, 1] = x * np.cos(ang) - y * np.sin(ang), x * np.sin(ang) + y * np.cos(ang)
        folds = input_folds(V, F)
        self.assertGreater(int(folds.sum()), 0)
        self.assertTrue(np.all(np.linalg.norm(V[F[folds]].mean(1) - c, axis=1) < 0.15))


if __name__ == "__main__":
    unittest.main()
