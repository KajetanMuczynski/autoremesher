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

// Hole filling closes each hole once.  It runs a scored pass and then an
// unscored one on whatever the first left open; the unscored pass used to run
// on holes the first had already closed and add their last quad a second time,
// a duplicate face with four non-manifold edges (Suzanne 5k, Quality).
//
// It also closes every hole it takes on.  Both passes clip quads off the loop
// and refuse one that crosses the rest of it; on a loop that bends around a
// corner they refused every quad and left the hole open (sword 2k, Fast).
// Such a hole is now closed around a new vertex at its center.
//
// The repair step after it drops the faces around a pinched vertex, where two
// pieces of surface touch at a point.  It used to find one only by counting
// the open edges there, so a pinch between two closed fans stayed in the
// output (boat 2k, Quality).

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

Result check(const std::vector<std::vector<size_t>>& faces, size_t before)
{
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

Result fill(Mesh mesh, const std::set<std::array<int, 3>>& removed)
{
    std::vector<std::vector<size_t>> faces;
    for (size_t f = 0; f < mesh.faces.size(); ++f) {
        if (0 == removed.count(mesh.cells[f]))
            faces.push_back(mesh.faces[f]);
    }
    const size_t before = faces.size();
    AutoRemesher::QuadExtractor::fillHoles(&mesh.vertices, &faces);
    return check(faces, before);
}

// Vertices where the faces around them split into more than one fan.
size_t countPinchedVertices(const std::vector<std::vector<size_t>>& faces)
{
    // Around a vertex, the face leaving it towards w and the face arriving
    // from w lie in the same fan.
    std::map<size_t, std::vector<std::pair<size_t, size_t>>> corners; // vertex -> (from, to)
    for (const auto& face : faces) {
        for (size_t i = 0; i < face.size(); ++i)
            corners[face[i]].push_back({ face[(i + face.size() - 1) % face.size()], face[(i + 1) % face.size()] });
    }
    size_t pinched = 0;
    for (const auto& it : corners) {
        const auto& around = it.second;
        std::vector<size_t> fan(around.size());
        for (size_t i = 0; i < fan.size(); ++i)
            fan[i] = i;
        for (bool merged = true; merged;) {
            merged = false;
            for (size_t i = 0; i < around.size(); ++i) {
                for (size_t j = 0; j < around.size(); ++j) {
                    if (around[i].second == around[j].first && fan[i] != fan[j]) {
                        fan[i] = fan[j] = std::min(fan[i], fan[j]);
                        merged = true;
                    }
                }
            }
        }
        if (std::set<size_t>(fan.begin(), fan.end()).size() > 1)
            ++pinched;
    }
    return pinched;
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
        // The three cells at the corner (3, 3, 3), one on each side: a 6-edge
        // loop bent around the corner, which the quad passes can't clip.
        { "corner hole", 3, { { 0, 2, 2 }, { 2, 2, 2 }, { 4, 2, 2 } }, 3 },
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

    // A closed cube with the vertex (1, 1, 0) of its bottom welded to (1, 1, 3)
    // on its top: one surface, pinched at a vertex between two closed fans.
    // The repair takes the pinch out and fills the two holes that leaves, so
    // the result is a closed manifold again.
    {
        Mesh mesh = cube(3);
        size_t top = 0, bottom = 0;
        for (size_t v = 0; v < mesh.vertices.size(); ++v) {
            const auto& p = mesh.vertices[v];
            if (1 == p.x() && 1 == p.y())
                (3 == p.z() ? top : bottom) = v;
        }
        std::vector<std::vector<size_t>> faces = mesh.faces;
        for (auto& face : faces) {
            for (auto& v : face) {
                if (bottom == v)
                    v = top;
            }
        }
        const size_t pinchedBefore = countPinchedVertices(faces);
        AutoRemesher::QuadExtractor::repairSurface(&mesh.vertices, &faces);
        const Result r = check(faces, 0);
        const size_t pinchedAfter = countPinchedVertices(faces);
        const bool ok = 1 == pinchedBefore && 0 == pinchedAfter && 0 == r.duplicateFaces
            && 0 == r.unpairedHalfEdges && !faces.empty();
        failures += ok ? 0 : 1;
        std::printf("\n%-12s %14s %13s %10s %9s\n", "case", "pinched before", "pinched after", "duplicates", "unpaired");
        std::printf("%-12s %14zu %13zu %10zu %9zu%s\n", "pinch", pinchedBefore, pinchedAfter,
            r.duplicateFaces, r.unpairedHalfEdges, ok ? "" : "  FAIL");
    }
    return failures ? 1 : 0;
}
