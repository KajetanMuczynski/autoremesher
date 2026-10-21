/*
 *  Copyright (C) 2026 Quadami contributors
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */

// The per-face counts of the quality report on hand-made faces. A face is
// folded when a corner turns against the face's area vector (scaled Jacobian
// <= 0), whatever its neighbours and whichever way it faces.

#include <AutoRemesher/MeasureMesh>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

namespace {

AutoRemesher::QualityReport measure(const std::vector<double>& positions,
    const std::vector<std::vector<uint32_t>>& faces)
{
    AutoRemesher::RemeshMesh mesh;
    mesh.positions = positions;
    for (const auto& face : faces) {
        mesh.faceSizes.push_back((uint32_t)face.size());
        mesh.faceIndices.insert(mesh.faceIndices.end(), face.begin(), face.end());
    }
    AutoRemesher::QualityReport report;
    AutoRemesher::measureMesh(mesh, &report);
    return report;
}

}

int main()
{
    struct Case {
        std::string name;
        std::vector<double> positions;
        std::vector<std::vector<uint32_t>> faces;
        size_t folded;
        size_t degenerate;
        size_t flips;
    };
    const std::vector<double> square = { 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0 };
    // A 2 x 2 grid of unit quads, vertex (i, j) at index 3 * j + i.
    std::vector<double> grid;
    for (int j = 0; j < 3; ++j)
        for (int i = 0; i < 3; ++i)
            grid.insert(grid.end(), { (double)i, (double)j, 0.0 });
    const std::vector<Case> cases = {
        { "convex quad", square, { { 0, 1, 2, 3 } }, 0, 0, 0 },
        { "convex quad, reversed", square, { { 3, 2, 1, 0 } }, 0, 0, 0 },
        { "skew quad", { 0, 0, 0, 1, 0, 0.2, 1, 1, 0, 0, 1, 0.2 }, { { 0, 1, 2, 3 } }, 0, 0, 0 },
        { "dart", { 0, 0, 0, 2, 0, 0, 0.5, 0.5, 0, 0, 2, 0 }, { { 0, 1, 2, 3 } }, 1, 0, 0 },
        { "bow-tie", { 0, 0, 0, 3, 1, 0, 3, 0, 0, 0, 2, 0 }, { { 0, 1, 2, 3 } }, 1, 0, 0 },
        { "convex pentagon", { 0, 0, 0, 2, 0, 0, 3, 1, 0, 1, 2, 0, -1, 1, 0 }, { { 0, 1, 2, 3, 4 } }, 0, 0, 0 },
        { "arrow pentagon", { 0, 0, 0, 2, 0, 0, 2, 2, 0, 1, 0.5, 0, 0, 2, 0 }, { { 0, 1, 2, 3, 4 } }, 1, 0, 0 },
        { "repeated corner", square, { { 0, 1, 1, 2 } }, 0, 1, 0 },
        { "zero area", { 0, 0, 0, 1, 0, 0, 2, 0, 0, 3, 0, 0 }, { { 0, 1, 2, 3 } }, 0, 1, 0 },
        // One quad wound the other way: its two inner edges are flips, but
        // no corner of any face turns back, so nothing is folded.
        { "reversed quad in a grid", grid, { { 0, 1, 4, 3 }, { 1, 2, 5, 4 }, { 3, 4, 7, 6 }, { 4, 7, 8, 5 } }, 0, 0, 2 },
    };

    int failures = 0;
    printf("%-24s %13s %17s %11s\n", "case", "folded", "degenerate", "flips");
    for (const auto& c : cases) {
        const AutoRemesher::QualityReport report = measure(c.positions, c.faces);
        const bool ok = report.foldedFaceCount == c.folded && report.degenerateFaceCount == c.degenerate
            && report.orientationFlipCount == c.flips;
        failures += ok ? 0 : 1;
        printf("%-24s %6zu (want %zu) %10zu (want %zu) %4zu (want %zu)%s\n", c.name.c_str(),
            report.foldedFaceCount, c.folded, report.degenerateFaceCount, c.degenerate,
            report.orientationFlipCount, c.flips, ok ? "" : "  FAIL");
    }
    return failures ? 1 : 0;
}
