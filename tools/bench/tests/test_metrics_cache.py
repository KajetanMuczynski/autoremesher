# SPDX-License-Identifier: GPL-3.0-or-later
"""metrics.py gives identical results with and without its input cache (--input-cache).

    python -m unittest discover -s tools/bench/tests -v      (needs numpy, scipy, libigl)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH)
import metrics  # noqa: E402


def torus(n, m, quads, path, bump=0.0):
    """A closed torus (genus 1) as an n x m grid, quads or triangles, with optional noise on one vertex."""
    u, v = np.meshgrid(np.arange(n) * 2 * np.pi / n, np.arange(m) * 2 * np.pi / m, indexing="ij")
    V = np.stack([(1 + 0.3 * np.cos(v)) * np.cos(u), (1 + 0.3 * np.cos(v)) * np.sin(u), 0.3 * np.sin(v)], -1)
    V = V.reshape(-1, 3)
    V[0] += bump
    with open(path, "w") as fp:
        for p in V:
            fp.write("v %.17g %.17g %.17g\n" % tuple(p))
        for i in range(n):
            for j in range(m):
                a, b = i * m + j + 1, ((i + 1) % n) * m + j + 1
                c, d = ((i + 1) % n) * m + (j + 1) % m + 1, i * m + (j + 1) % m + 1
                fp.write(f"f {a} {b} {c} {d}\n" if quads else f"f {a} {b} {c}\nf {a} {c} {d}\n")


class InputCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.inp, self.inp2, self.out = (os.path.join(d, f) for f in ("in.obj", "in2.obj", "out.obj"))
        self.cache = os.path.join(d, "cache")
        torus(96, 48, False, self.inp)
        torus(96, 48, False, self.inp2, bump=0.05)
        torus(40, 16, True, self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def compute(self, inp, cache, **kw):
        return json.dumps(metrics.compute(inp, self.out, 640, samples=5000, cache_dir=cache, **kw), sort_keys=True)

    def test_identical_with_cold_and_warm_cache(self):
        plain = self.compute(self.inp, None)
        self.assertEqual(self.compute(self.inp, self.cache), plain)  # fills the cache
        self.assertEqual(len(os.listdir(self.cache)), 1)
        self.assertEqual(self.compute(self.inp, self.cache), plain)  # reads it
        self.assertEqual(json.loads(plain)["topology"]["euler_input"], 0)

    def test_identical_with_symmetry(self):
        kw = {"sym_axis": "z", "sym_center": 0.0}
        plain = self.compute(self.inp, None, **kw)
        self.compute(self.inp, self.cache, **kw)
        self.assertEqual(self.compute(self.inp, self.cache, **kw), plain)

    def test_keyed_by_input_content(self):
        self.compute(self.inp, self.cache)
        other = self.compute(self.inp2, self.cache)
        self.assertEqual(len(os.listdir(self.cache)), 2)
        self.assertEqual(other, self.compute(self.inp2, None))
        self.assertNotEqual(other, self.compute(self.inp, None))

    def test_prepare_input_fills_the_same_cache(self):
        subprocess.run([sys.executable, os.path.join(BENCH, "metrics.py"), "--input", self.inp,
                        "--input-cache", self.cache, "--prepare-input"], check=True)
        self.assertEqual(len(os.listdir(self.cache)), 1)
        self.assertEqual(self.compute(self.inp, self.cache), self.compute(self.inp, None))


if __name__ == "__main__":
    unittest.main()
