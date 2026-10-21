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

// Validity check of an integer-grid map (checkIntegerGridMap).
//
// A flat torus mapped onto the grid is valid and both of its handle loops
// have the translation of one turn around it; folded back on itself along
// one direction, its triangles flip and that loop collapses. A strip half
// a quad edge wide has lost the width of its one boundary loop; a strip
// one quad edge wide has not.

#include <AutoRemesher/MapCheck>
#include <cmath>
#include <cstdio>
#include <vector>

namespace {

using AutoRemesher::MapCheck;
using AutoRemesher::Vector2;
using AutoRemesher::Vector3;

int failures = 0;

void expect(bool condition, const char* what)
{
    if (!condition) {
        std::printf("FAIL: %s\n", what);
        ++failures;
    }
}

struct Map {
    std::vector<Vector3> vertices;
    std::vector<std::vector<size_t>> triangles;
    std::vector<std::vector<Vector2>> uvs;
};

// Two triangles per cell of an n x n grid wrapped both ways; `v(j)` gives
// the second map coordinate of row j, unwrapped (j = 0..n).
template <class RowMap>
Map makeTorus(size_t n, RowMap v)
{
    Map map;
    const double pi = std::acos(-1.0);
    for (size_t j = 0; j < n; ++j)
        for (size_t i = 0; i < n; ++i) {
            const double a = 2 * pi * i / n, b = 2 * pi * j / n;
            map.vertices.emplace_back((2 + std::cos(b)) * std::cos(a), (2 + std::cos(b)) * std::sin(a), std::sin(b));
        }
    const auto at = [n](size_t i, size_t j) { return (j % n) * n + i % n; };
    for (size_t j = 0; j < n; ++j)
        for (size_t i = 0; i < n; ++i) {
            const Vector2 p00(i, v(j)), p10(i + 1, v(j)), p11(i + 1, v(j + 1)), p01(i, v(j + 1));
            map.triangles.push_back({ at(i, j), at(i + 1, j), at(i + 1, j + 1) });
            map.uvs.push_back({ p00, p10, p11 });
            map.triangles.push_back({ at(i, j), at(i + 1, j + 1), at(i, j + 1) });
            map.uvs.push_back({ p00, p11, p01 });
        }
    return map;
}

// A strip of m cells, one row high, `width` quad edges wide in the map.
Map makeStrip(size_t m, double width)
{
    Map map;
    for (size_t j = 0; j < 2; ++j)
        for (size_t i = 0; i <= m; ++i)
            map.vertices.emplace_back((double)i, (double)j, 0.0);
    const auto at = [m](size_t i, size_t j) { return j * (m + 1) + i; };
    for (size_t i = 0; i < m; ++i) {
        const Vector2 p00(i, 0), p10(i + 1, 0), p11(i + 1, width), p01(i, width);
        map.triangles.push_back({ at(i, 0), at(i + 1, 0), at(i + 1, 1) });
        map.uvs.push_back({ p00, p10, p11 });
        map.triangles.push_back({ at(i, 0), at(i + 1, 1), at(i, 1) });
        map.uvs.push_back({ p00, p11, p01 });
    }
    return map;
}

MapCheck check(const Map& map)
{
    return AutoRemesher::checkIntegerGridMap(map.vertices, map.triangles, map.uvs,
        std::vector<int>(3 * map.triangles.size(), 0), std::vector<size_t>());
}

}

int main()
{
    const size_t n = 6;
    const MapCheck torus = check(makeTorus(n, [](size_t j) { return (double)j; }));
    expect(torus.valid(), "flat torus is valid");
    expect(torus.flipped == 0 && torus.degenerate == 0, "flat torus has no bad triangle");
    expect(torus.handleLoops == 2 && torus.handleLoopsUnrotated == 2, "torus has two unrotated handle loops");
    expect(std::fabs(torus.handleTranslation - n) < 1e-9, "torus loops translate by one turn");
    expect(torus.transitionResidual < 1e-12, "torus transitions are consistent");

    const MapCheck folded = check(makeTorus(n, [n](size_t j) { return (double)(j <= n / 2 ? j : n - j); }));
    expect(!folded.valid(), "folded torus is invalid");
    expect(folded.flipped == n * n, "half of the folded torus is flipped");
    expect(folded.handleLoopsCollapsed == 1, "folded torus has one collapsed loop");

    const MapCheck narrow = check(makeStrip(8, 0.4));
    expect(narrow.boundaryLoops == 1 && narrow.boundaryLoopsPinched == 1, "narrow strip is pinched");
    expect(std::fabs(narrow.boundaryWidth - 0.4) < 1e-9, "narrow strip width");
    expect(!narrow.valid(), "narrow strip is invalid");

    const MapCheck wide = check(makeStrip(8, 1.0));
    expect(wide.boundaryLoopsPinched == 0 && wide.valid(), "strip one quad wide is valid");

    if (failures)
        return 1;
    std::printf("map check: all passed\n");
    return 0;
}
