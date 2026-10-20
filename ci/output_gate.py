#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Output gate: remesh a small procedural corpus with autoremesher-cli and check the results.

    python3 ci/output_gate.py <autoremesher-cli> <work-dir>

Every mesh is generated here (standard library only), so the gate needs no downloads. For each
case the gate fails on:
  - a non-zero exit status, a status other than "ok", or a missing output;
  - a quad count outside [MIN_RATIO, MAX_RATIO] x target;
  - non-quad faces above MAX_NON_QUAD_SHARE of all faces;
  - any non-manifold edge;
  - an output OBJ whose own counts disagree with the report (so a broken counter can't hide a
    bad mesh).
Folded faces, empty islands, boundary edges and components are reported, not gated, until the
plan sets targets for them (TODO 0.7). The thresholds are wide on purpose: this gate catches
broken output, not small quality changes. A Markdown table goes to $GITHUB_STEP_SUMMARY when set.
"""
import json
import math
import os
import subprocess
import sys
import time

MIN_RATIO, MAX_RATIO = 0.6, 1.5
MAX_NON_QUAD_SHARE = 0.02


class Mesh:
    def __init__(self):
        self.vertices, self.triangles, self._index = [], [], {}

    def vertex(self, key, position):
        """Welded vertex: the same key returns the same index."""
        if key not in self._index:
            self._index[key] = len(self.vertices)
            self.vertices.append(position)
        return self._index[key]

    def quad(self, a, b, c, d):
        self.triangles += [(a, b, c), (a, c, d)]

    def write(self, path):
        with open(path, "w") as f:
            f.writelines("v %.6f %.6f %.6f\n" % v for v in self.vertices)
            f.writelines("f %d %d %d\n" % (a + 1, b + 1, c + 1) for a, b, c in self.triangles)


def add_uv_surface(mesh, tag, nu, nv, point, wrap_u, wrap_v):
    """Grid surface point(u, v), u, v in [0, 1]; wrapped directions are welded."""
    def key(i, j):
        return (tag, i % nu if wrap_u else i, j % nv if wrap_v else j)

    for i in range(nu):
        for j in range(nv):
            corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            ids = [mesh.vertex(key(a, b), point(a / nu, b / nv)) for a, b in corners]
            mesh.quad(*ids)


def sphere(mesh, tag, radius=1.0, center=(0.0, 0.0, 0.0), stacks=48, slices=96):
    """UV sphere with welded poles."""
    def point(u, v):
        theta, phi = math.pi * v, 2.0 * math.pi * u
        return (center[0] + radius * math.sin(theta) * math.cos(phi),
                center[1] + radius * math.cos(theta),
                center[2] + radius * math.sin(theta) * math.sin(phi))

    def key(i, j):
        if j == 0 or j == stacks:
            return (tag, "pole", j)
        return (tag, i % slices, j)

    for i in range(slices):
        for j in range(stacks):
            corners = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            ids = [mesh.vertex(key(a, b), point(a / slices, b / stacks)) for a, b in corners]
            if j == 0:
                mesh.triangles.append((ids[0], ids[1], ids[2]))
            elif j == stacks - 1:
                mesh.triangles.append((ids[0], ids[1], ids[3]))
            else:
                mesh.quad(*ids)


def torus(mesh, tag, major=1.0, minor=0.35, n_major=96, n_minor=48):
    def point(u, v):
        a, b = 2.0 * math.pi * u, 2.0 * math.pi * v
        r = major + minor * math.cos(b)
        return (r * math.cos(a), minor * math.sin(b), r * math.sin(a))

    add_uv_surface(mesh, tag, n_major, n_minor, point, True, True)


def box(mesh, tag, n=24):
    """Unit cube surface, n x n quads per side, with sharp 90-degree edges."""
    for axis in range(3):
        for side in (0, n):
            for i in range(n):
                for j in range(n):
                    ids = []
                    for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                        grid = [0, 0, 0]
                        grid[axis], grid[(axis + 1) % 3], grid[(axis + 2) % 3] = side, a, b
                        ids.append(mesh.vertex((tag,) + tuple(grid), tuple(g / n for g in grid)))
                    if side == 0:
                        ids.reverse()
                    mesh.quad(*ids)


def open_tube(mesh, tag, n_around=96, n_along=48):
    """Cylinder without caps: two open boundary loops."""
    def point(u, v):
        a = 2.0 * math.pi * u
        return (math.cos(a), 2.0 * v, math.sin(a))

    add_uv_surface(mesh, tag, n_around, n_along, point, True, False)


def corpus():
    def single(build):
        mesh = Mesh()
        build(mesh)
        return mesh

    def two_islands(mesh):
        sphere(mesh, "big")
        sphere(mesh, "small", radius=0.35, center=(2.0, 0.0, 0.0), stacks=24, slices=48)

    return [
        ("sphere", single(lambda m: sphere(m, "s")), 2000),
        ("torus", single(lambda m: torus(m, "t")), 2000),
        ("box", single(lambda m: box(m, "b")), 1500),
        ("open_tube", single(lambda m: open_tube(m, "o")), 1500),
        ("two_islands", single(two_islands), 2000),
        # Far from the origin: crossing-point keys once overflowed a 32-bit
        # long (MSVC) beyond about 21,475 units and tore the output on Windows.
        ("far_sphere", single(lambda m: sphere(m, "f", center=(1e5, 1e5, 1e5))), 2000),
    ]


def obj_counts(path):
    """Quads, non-quads and non-manifold edges (edges with more than two faces) of an OBJ."""
    quads = others = 0
    edge_faces = {}
    with open(path) as f:
        for line in f:
            if not line.startswith("f "):
                continue
            ids = [int(t.split("/")[0]) for t in line.split()[1:]]
            if len(ids) == 4:
                quads += 1
            else:
                others += 1
            for a, b in zip(ids, ids[1:] + ids[:1]):
                edge = (min(a, b), max(a, b))
                edge_faces[edge] = edge_faces.get(edge, 0) + 1
    return quads, others, sum(1 for c in edge_faces.values() if c > 2)


def run_case(cli, work, name, mesh, target):
    source = os.path.join(work, name + ".obj")
    output = os.path.join(work, name + "-quads.obj")
    report_path = os.path.join(work, name + "-report.json")
    mesh.write(source)
    start = time.monotonic()
    proc = subprocess.run([cli, "--input", source, "--output", output, "--report-json", report_path,
                           "--target-quads", str(target)], capture_output=True, text=True)
    row = {"case": name, "target": target, "seconds": time.monotonic() - start, "failures": []}
    with open(os.path.join(work, name + ".log"), "w") as f:
        f.write(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        row["failures"].append("exit status %d" % proc.returncode)
    try:
        with open(report_path) as f:
            report = json.load(f)
    except (OSError, ValueError) as e:
        row["failures"].append("no report (%s)" % e)
        return row
    if report["status"] != "ok":
        row["failures"].append("status %s: %s" % (report["status"], report["message"]))
    if not os.path.isfile(output):
        row["failures"].append("no output mesh")
        return row

    out = report["output"]
    quads, others, non_manifold = obj_counts(output)
    row.update(quads=quads, non_quads=others, non_manifold=non_manifold,
               folded=out["folded_faces"], boundary=out["boundary_edges"],
               components=out["components"], empty_islands=report["islands"]["without_output"],
               islands=report["islands"]["input"])
    ratio = quads / target
    if not MIN_RATIO <= ratio <= MAX_RATIO:
        row["failures"].append("quads %.2fx target, allowed [%.2f, %.2f]" % (ratio, MIN_RATIO, MAX_RATIO))
    if others > MAX_NON_QUAD_SHARE * max(1, quads + others):
        row["failures"].append("%d non-quad faces, allowed %.0f%%" % (others, 100 * MAX_NON_QUAD_SHARE))
    if non_manifold:
        row["failures"].append("%d non-manifold edges" % non_manifold)
    for key, mine in (("quads", quads), ("non_quads", others), ("non_manifold_edges", non_manifold)):
        if out[key] != mine:
            row["failures"].append("report says %s = %d, the OBJ has %d" % (key, out[key], mine))
    return row


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cli, work = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(work, exist_ok=True)
    rows = [run_case(cli, work, name, mesh, target) for name, mesh, target in corpus()]

    columns = ["case", "target", "quads", "non_quads", "non_manifold", "folded", "empty_islands",
               "islands", "boundary", "components", "seconds"]
    lines = ["| " + " | ".join(columns) + " | result |", "|" + "---|" * (len(columns) + 1)]
    for row in rows:
        cells = [("%.2f" % row[c]) if c == "seconds" else str(row.get(c, "-")) for c in columns]
        lines.append("| " + " | ".join(cells) + " | " + ("; ".join(row["failures"]) or "pass") + " |")
    table = "\n".join(lines)
    print(table)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("### Output gate (%s)\n\n%s\n\n" % (os.environ.get("RUNNER_OS", "local"), table))
    failed = [row["case"] for row in rows if row["failures"]]
    if failed:
        sys.exit("FAIL: " + ", ".join(failed))
    print("PASS")


if __name__ == "__main__":
    main()
