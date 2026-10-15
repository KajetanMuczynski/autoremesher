#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write a unit UV sphere as an OBJ (default 64 stacks x 128 slices = 16,128 triangles).

    python3 ci/make_sphere.py out.obj [--stacks 64] [--slices 128]
"""
import argparse
import math

ap = argparse.ArgumentParser()
ap.add_argument("output")
ap.add_argument("--stacks", type=int, default=64)
ap.add_argument("--slices", type=int, default=128)
args = ap.parse_args()
n, m = args.stacks, args.slices

with open(args.output, "w") as f:
    f.write("v 0.000000 1.000000 0.000000\n")
    for i in range(1, n):
        theta = math.pi * i / n
        for j in range(m):
            phi = 2.0 * math.pi * j / m
            f.write("v %.6f %.6f %.6f\n" % (math.sin(theta) * math.cos(phi), math.cos(theta),
                                             math.sin(theta) * math.sin(phi)))
    f.write("v 0.000000 -1.000000 0.000000\n")
    ring = lambda i, j: 2 + (i - 1) * m + j % m  # 1-based OBJ index of ring i (1..n-1), slice j
    bottom = 2 + (n - 1) * m
    for j in range(m):
        f.write("f 1 %d %d\n" % (ring(1, j + 1), ring(1, j)))
    for i in range(1, n - 1):
        for j in range(m):
            a, b, c, d = ring(i, j), ring(i, j + 1), ring(i + 1, j + 1), ring(i + 1, j)
            f.write("f %d %d %d\nf %d %d %d\n" % (a, b, c, a, c, d))
    for j in range(m):
        f.write("f %d %d %d\n" % (bottom, ring(n - 1, j), ring(n - 1, j + 1)))
