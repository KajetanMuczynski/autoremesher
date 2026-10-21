/*
 *  Copyright (C) 2026 AutoRemesher fork contributors
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

// Feature strips narrower than half a quad (TODO 5.3).
//
// Two square sheets joined by a strip a fifth of a quad wide, folded by 120
// degrees at both of its edges (a Z fold): the folds are hard features on
// parallel isolines. Rounding put both on one integer, so the strip's
// triangles collapsed and stayed pinned through untangling (26 at 1000
// quads before the change). The cover must now release the folds along the
// strip, leave at most a few pinned triangles where the strip meets the
// open sides, and keep the boundary's constraints.

#include <AutoRemesher/AutoRemesher>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

using AutoRemesher::DiagnosticRecord;
using AutoRemesher::Vector3;

namespace {

int failures = 0;

void check(bool condition, const std::string& what)
{
    if (!condition) {
        std::printf("FAIL: %s\n", what.c_str());
        ++failures;
    }
}

double value(const DiagnosticRecord& record, const char* key)
{
    for (const auto& item : record.values)
        if (item.first == key)
            return item.second;
    return 0.0;
}

void zFold(double stripWidth, std::vector<Vector3>* vertices, std::vector<std::vector<size_t>>* triangles)
{
    const size_t n = 60;
    const double turn = 120.0 * M_PI / 180.0;
    const double y = 1.0 + stripWidth * std::cos(turn), z = stripWidth * std::sin(turn);
    for (size_t sheet = 0; sheet < 2; ++sheet)
        for (size_t j = 0; j <= n; ++j)
            for (size_t i = 0; i <= n; ++i)
                vertices->push_back(0 == sheet ? Vector3((double)i / n, (double)j / n, 0.0)
                                               : Vector3((double)i / n, y + (double)j / n, z));
    for (size_t j = 0; j < 2 * n + 1; ++j)
        for (size_t i = 0; i < n; ++i) {
            const size_t a = j * (n + 1) + i, b = a + 1, c = a + n + 2, d = a + n + 1;
            triangles->push_back({ a, b, c });
            triangles->push_back({ a, c, d });
        }
}

} // namespace

int main()
{
    std::vector<Vector3> vertices;
    std::vector<std::vector<size_t>> triangles;
    zFold(0.01, &vertices, &triangles);
    AutoRemesher::AutoRemesher remesher(vertices, triangles);
    remesher.setTargetTriangleCount(2000);
    check(remesher.remesh(), "remesh succeeds");
    double features = 0, released = 0, pinned = 0;
    for (const DiagnosticRecord& record : remesher.diagnostics())
        if (record.stage == "cover_result") {
            features += value(record, "feature_corners");
            released += value(record, "feature_corners_released");
            pinned += value(record, "untangle_pinned_faces");
        }
    std::printf("feature corners %.0f, released %.0f, pinned triangles %.0f\n", features, released, pinned);
    check(released > 0, "the folds' constraints are released along the strip");
    check(released < features, "the boundary keeps its constraints");
    check(pinned <= 5, "at most a few triangles stay pinned");
    std::printf(failures ? "narrow strip test FAILED\n" : "narrow strip test passed\n");
    return failures ? 1 : 0;
}
