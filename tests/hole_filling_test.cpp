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

// Hole filling closes each hole once.  It runs a scored pass and then an
// unscored one on whatever the first left open; the unscored pass used to run
// on holes the first had already closed and add their last quad a second time,
// a duplicate face with four non-manifold edges (Suzanne 5k, Quality).

#include <AutoRemesher/QuadExtractor>
#include <algorithm>
#include <array>
#include <cstdio>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace {

struct Mesh {
    std::vector<AutoRemesher::Vector3> vertices;
    std::vector<std::vector<size_t>> faces;
    // (side, i, j) of each face, to pick the ones to cut out.
    std::vector<std::array<int, 3>> cells;
};

// The surface of the cube [0, n]^3, n x n quads per side, facing outwards.
Mesh cube(int n)
{
    Mesh mesh;
    std::map<std::array<int, 3>, size_t> indices;
    auto vertex = [&](const std::array<int, 3>& p) {
        auto inserted = indices.insert({ p, mesh.vertices.size() });
        if (inserted.second)
            mesh.vertices.emplace_back(p[0], p[1], p[2]);
        return inserted.first->second;
    };
    // Normal axis, its sign, and in-plane axes u, v with u x v along the normal.
    const int sides[6][4] = { { 0, 1, 1, 2 }, { 0, -1, 2, 1 }, { 1, 1, 2, 0 },
        { 1, -1, 0, 2 }, { 2, 1, 0, 1 }, { 2, -1, 1, 0 } };
    for (int s = 0; s < 6; ++s) {
        const int axis = sides[s][0], u = sides[s][2], v = sides[s][3];
        const int level = sides[s][1] > 0 ? n : 0;
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                std::vector<size_t> face;
                const int corners[4][2] = { { i, j }, { i + 1, j }, { i + 1, j + 1 }, { i, j + 1 } };
                for (const auto& corner : corners) {
                    std::array<int, 3> p;
                    p[axis] = level;
                    p[u] = corner[0];
                    p[v] = corner[1];
                    face.push_back(vertex(p));
                }
                mesh.faces.push_back(face);
                mesh.cells.push_back({ s, i, j });
            }
        }
    }
    return mesh;
}

struct Result {
    size_t added = 0;
    size_t duplicateFaces = 0;
    size_t unpairedHalfEdges = 0; // boundary, or used twice in one direction
};

Result fill(Mesh mesh, const std::set<std::array<int, 3>>& removed)
{
    std::vector<std::vector<size_t>> faces;
    for (size_t f = 0; f < mesh.faces.size(); ++f) {
        if (0 == removed.count(mesh.cells[f]))
            faces.push_back(mesh.faces[f]);
    }
    const size_t before = faces.size();
    AutoRemesher::QuadExtractor::fillHoles(mesh.vertices, &faces);

    Result result;
    result.added = faces.size() - before;
    std::map<std::vector<size_t>, size_t> faceCount;
    std::map<std::pair<size_t, size_t>, size_t> halfEdgeCount;
    for (const auto& face : faces) {
        auto key = face;
        std::sort(key.begin(), key.end());
        if (2 == ++faceCount[key])
            ++result.duplicateFaces;
        for (size_t i = 0; i < face.size(); ++i)
            ++halfEdgeCount[{ face[i], face[(i + 1) % face.size()] }];
    }
    for (const auto& it : halfEdgeCount) {
        auto twin = halfEdgeCount.find({ it.first.second, it.first.first });
        if (it.second != 1 || twin == halfEdgeCount.end() || twin->second != 1)
            ++result.unpairedHalfEdges;
    }
    return result;
}

}

int main()
{
    struct Case {
        std::string name;
        int n;
        std::set<std::array<int, 3>> removed; // (side, i, j)
        size_t added; // quads that close the hole
    };
    // Side 4 is the top, z = n.
    const std::vector<Case> cases = {
        { "4-edge hole", 3, { { 4, 1, 1 } }, 1 },
        { "6-edge hole", 3, { { 4, 1, 1 }, { 4, 2, 1 } }, 2 },
        { "8-edge hole", 4, { { 4, 1, 1 }, { 4, 2, 1 }, { 4, 1, 2 }, { 4, 2, 2 } }, 3 },
    };

    int failures = 0;
    std::printf("\n%-12s %6s %6s %10s %9s\n", "case", "added", "expect", "duplicates", "unpaired");
    for (const auto& c : cases) {
        const Result r = fill(cube(c.n), c.removed);
        const bool ok = r.added == c.added && 0 == r.duplicateFaces && 0 == r.unpairedHalfEdges;
        failures += ok ? 0 : 1;
        std::printf("%-12s %6zu %6zu %10zu %9zu%s\n", c.name.c_str(), r.added, c.added,
            r.duplicateFaces, r.unpairedHalfEdges, ok ? "" : "  FAIL");
    }
    return failures ? 1 : 0;
}
