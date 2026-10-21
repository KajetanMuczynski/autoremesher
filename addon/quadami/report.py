# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Turn the remesher's JSON report into rows for the panel. No bpy in here."""

STATUS_TEXT = {
    "ok": "Done",
    "cancelled": "Cancelled",
    "failed": "Failed",
    "invalid_input": "Invalid input",
}


def summary_rows(report):
    """(label, value, is_problem) rows for a report dict from --report-json."""
    rows = []
    output = report.get("output", {})
    target = report.get("parameters", {}).get("target_quads", 0)
    if report.get("status") == "ok":
        quads = output.get("quads", 0)
        ratio = " (%d%%)" % round(100.0 * quads / target) if target else ""
        rows.append(("Quads", "%d of %d target%s" % (quads, target, ratio), False))

        def count(label, value):
            rows.append((label, str(value), value > 0))

        count("Non-quads", output.get("non_quads", 0))
        count("Non-manifold edges", output.get("non_manifold_edges", 0))
        count("Winding flips", output.get("orientation_flips", 0))
        count("Folded faces", output.get("folded_faces", 0))
        # The core's input cleanup: triangles on a zero-length edge it dropped
        # and triangles it turned to match their neighbours.  Not a problem,
        # only reported.
        diagnostics = report.get("diagnostics", {})
        fixes = []
        dropped = int(diagnostics.get("input_dropped_triangles", 0))
        if dropped:
            fixes.append("%d degenerate triangles removed" % dropped)
        flipped = int(diagnostics.get("input_flipped_triangles", 0))
        if flipped:
            fixes.append("%d triangles turned" % flipped)
        if fixes:
            rows.append(("Input cleanup", ", ".join(fixes), False))
    islands = report.get("islands", {})
    empty = islands.get("without_output", 0)
    rows.append(("Empty islands", "%d of %d" % (empty, islands.get("input", 0)), empty > 0))
    seconds = report.get("time", {}).get("total_seconds")
    if seconds is not None:
        rows.append(("Time", "%.1f s" % seconds, False))
    for warning in report.get("warnings", []):
        rows.append(("Warning", warning, True))
    return rows
