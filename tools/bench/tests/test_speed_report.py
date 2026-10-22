# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""speed_report reads ab.py run folders and recovers a memory model from records that follow one.

    python -m unittest discover -s tools/bench/tests -v      (needs numpy, scipy)
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH)
import speed_report  # noqa: E402


def write_run(root, mesh, target, triangles, seconds, rss_mb):
    d = os.path.join(root, "corpus", mesh, f"quality-t{target}", "u0")
    os.makedirs(d)
    json.dump({"mesh": mesh, "target": target, "res": "quality", "rc": 0, "wall": seconds + 0.1,
               "peak_rss_mb": rss_mb, "out_sha": mesh}, open(os.path.join(d, "record.json"), "w"))
    json.dump({"output": {"quads": target}, "time": {"total_seconds": seconds,
               "steps": [{"name": "Rounding cover to integers", "seconds": seconds / 2}]}},
              open(os.path.join(d, "report.json"), "w"))
    stages = [{"stage": "run", "input_triangles": triangles, "islands": 1, "total_ms": seconds * 1000,
               "isotropic_wall_ms": 100, "parameterize_wall_ms": seconds * 800, "output_faces": target},
              {"stage": "island", "resample_ms": 100, "parameterize_ms": seconds * 600, "extract_ms": seconds * 200},
              {"stage": "rounding_iteration", "kernel_integers": 10, "solve_n": 100, "solve_total_ms": seconds * 500},
              {"stage": "cover_result", "rounded_cells": target}]
    with open(os.path.join(d, "stages.jsonl"), "w") as fp:
        fp.write("\n".join(json.dumps(s) for s in stages) + "\n")


class SpeedReportTest(unittest.TestCase):
    def test_memory_model_and_tables(self):
        with tempfile.TemporaryDirectory() as root:
            k = 0
            for tri in (50_000, 400_000, 1_600_000):
                for target in (3000, 10000, 50000):
                    k += 1
                    rss = 0.5 * tri / 1000 + 20 * target / 1000 + 30   # MB: 0.5 MB per 1k triangles, 20 MB per 1k quads
                    write_run(root, f"m{k}", target, tri, 1 + tri / 2e5 + 0.3 * (target / 1000) ** 1.4, rss)
            rows = speed_report.load(root, None)
            self.assertEqual(len(rows), 9)
            self.assertAlmostEqual(rows[0]["round_s"] / rows[0]["total"], 0.5)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                speed_report.stage_tables(rows, 5)
                speed_report.solve_table(rows)
                speed_report.count_table(rows)
                speed_report.models(rows)
            text = out.getvalue()
            self.assertIn("500 MB per million input triangles + 20.0 MB per 1,000 target quads", text)
            self.assertIn("Rounding cover to integers", text)


if __name__ == "__main__":
    unittest.main()
