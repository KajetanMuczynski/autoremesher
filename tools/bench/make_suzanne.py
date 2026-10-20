#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the "suzanne" A/B set: Blender's Suzanne with Subdivision levels 1-3, triangulated the way
the add-on hands meshes to the CLI (evaluated mesh, loop triangles, float32 positions). Level 2 at
5000 quads is Kajetan's first add-on report (eye sockets: 4 boundary loops).

    python make_suzanne.py --out meshes/suzanne                       # pip install bpy (Python 3.13)
    blender -b --factory-startup -P make_suzanne.py -- --out meshes/suzanne
"""
import argparse
import os
import sys

import bpy
import numpy as np


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for levels in (1, 2, 3):
        bpy.ops.mesh.primitive_monkey_add()
        obj = bpy.context.active_object
        obj.modifiers.new("Subdivision", "SUBSURF").levels = levels
        ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = ev.to_mesh()
        mesh.calc_loop_triangles()
        pos = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", pos)
        tri = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get("vertices", tri)
        ev.to_mesh_clear()
        path = os.path.join(args.out, "suzanne_sub%d.obj" % levels)
        with open(path, "w") as f:
            f.write("".join("v %.9g %.9g %.9g\n" % tuple(p) for p in pos.reshape(-1, 3).astype(np.float64)))
            f.write("".join("f %d %d %d\n" % tuple(t) for t in tri.reshape(-1, 3) + 1))
        print(path, len(pos) // 3, "vertices", len(tri) // 3, "triangles")
        bpy.data.objects.remove(obj)


main()
