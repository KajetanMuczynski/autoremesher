# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""fold_repair.repair untangles a twist locally, keeps the faces, and leaves clean input alone.

    python -m unittest discover -s tools/bench/tests -v      (needs numpy, scipy, libigl)
"""
import os
import sys
import unittest

import numpy as np

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH)
from fold_repair import repair  # noqa: E402
from make_synthetic import icosphere  # noqa: E402
from sculpt_report import input_folds  # noqa: E402


def twisted_sphere(turns):
    V, F = icosphere(5)
    c = np.array([0.0, 0.0, 1.0])
    d = np.linalg.norm(V - c, axis=1)
    sel = d < 0.15
    t = d[sel] / 0.15
    ang = 2 * np.pi * turns * (1 - 3 * t ** 2 + 2 * t ** 3)
    x, y = V[sel, 0], V[sel, 1]
    V[sel, 0], V[sel, 1] = x * np.cos(ang) - y * np.sin(ang), x * np.sin(ang) + y * np.cos(ang)
    return V, F, c


class FoldRepair(unittest.TestCase):
    def test_clean_input_is_untouched(self):
        V, F = icosphere(4)
        V2, rep = repair(V, [list(f) for f in F])
        self.assertEqual(rep["folded_before"], 0)
        self.assertTrue(np.array_equal(V, V2))

    def test_twist_is_untangled_locally_on_the_surface(self):
        V, F, c = twisted_sphere(3)
        faces = [list(f) for f in F]
        before = int(input_folds(V, F).sum())
        V2, rep = repair(V, faces)
        self.assertGreater(before, 0)
        self.assertLess(rep["folded_after"], before // 4)
        moved = np.linalg.norm(V2 - V, axis=1) > 0
        # Only vertices near the twist move, and they stay on the sphere (the twist is tangential).
        self.assertTrue(np.all(np.linalg.norm(V[moved] - c, axis=1) < 0.3))
        self.assertLess(float(np.abs(np.linalg.norm(V2, axis=1) - 1).max()), 0.01)


if __name__ == "__main__":
    unittest.main()
