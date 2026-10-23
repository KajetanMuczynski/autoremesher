# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""defect_ledger's input features: thin sheets, tips and folds where they are, and nothing on a sphere.

    python -m unittest discover -s tools/bench/tests -v      (needs numpy, scipy, libigl)
"""
import os
import sys
import tempfile
import unittest

import numpy as np

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from defect_ledger import Surface, input_folds  # noqa: E402
from make_synthetic import icosphere  # noqa: E402
from test_input_folds import grid  # noqa: E402


def surface(V, F, h):
    with tempfile.NamedTemporaryFile("w", suffix=".obj", delete=False) as fp:
        fp.writelines(f"v {x} {y} {z}\n" for x, y, z in V)
        fp.writelines(f"f {a + 1} {b + 1} {c + 1}\n" for a, b, c in F)
    try:
        return Surface(fp.name, h)
    finally:
        os.unlink(fp.name)


class Features(unittest.TestCase):
    def test_sphere_has_no_trigger(self):
        V, F = icosphere(4)
        s = surface(V, F, 0.1)
        for p in V[::40]:
            f = s.features_at(p, 0.1, {})
            self.assertFalse(f["near_fold"] or f["thin"] or f["tip"], (p, f))

    def test_sheet_thinner_than_h_is_thin(self):
        V, F = icosphere(4)
        V[:, 2] *= 0.01
        s = surface(V, F, 0.1)
        self.assertTrue(s.features_at(np.array([0.0, 0.0, 0.01]), 0.1, {})["thin"])
        self.assertTrue(s.features_at(np.array([1.0, 0.0, 0.0]), 0.1, {})["thin"])  # at the rim too

    def test_needle_tip_is_a_tip(self):
        V, F = icosphere(3)
        top = int(np.argmax(V[:, 2]))
        V[top] *= 4.0
        s = surface(V, F, 0.1)
        self.assertTrue(s.features_at(V[top], 0.1, {})["tip"])
        self.assertFalse(s.features_at(-V[top] / 4, 0.1, {})["tip"])

    def test_open_ribbon_narrower_than_h_is_thin(self):
        V, F = grid(40, lambda x, y: 0 * x)
        V[:, 1] *= 0.05  # 1 x 0.05 strip
        s = surface(V, F, 0.1)
        self.assertTrue(s.features_at(np.array([0.5, 0.025, 0.0]), 0.1, {})["thin"])
        V, F = grid(40, lambda x, y: 0 * x)
        s = surface(V, F, 0.1)
        self.assertFalse(s.features_at(np.array([0.5, 0.5, 0.0]), 0.1, {})["thin"])


class Folds(unittest.TestCase):
    """The faster fold detector agrees with sculpt_report's on its test cases."""

    def test_sphere_has_none(self):
        V, F = icosphere(3)
        self.assertEqual(int(input_folds(V, F).sum()), 0)

    def test_pleat_is_found_where_it_is(self):
        V, F = grid(60, lambda x, y: 0 * x)
        band = (V[:, 0] > 0.48) & (V[:, 0] < 0.52)
        V[band, 0] = 1.0 - V[band, 0]
        V[band, 2] = 0.01
        folds = input_folds(V, F, 0.05)
        self.assertGreater(int(folds.sum()), 0)
        self.assertTrue(np.all(np.abs(V[F[folds]].mean(1)[:, 0] - 0.5) < 0.1))

    def test_thin_sheet_is_not_a_fold(self):
        V, F = icosphere(4)
        V[:, 2] *= 0.01
        self.assertEqual(int(input_folds(V, F, 0.1).sum()), 0)


if __name__ == "__main__":
    unittest.main()
