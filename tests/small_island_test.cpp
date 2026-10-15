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

// Every island of the input must come back as a closed quad mesh of the same
// genus, however small its share of the target count (TODO 2.14). Before the
// fix, a body with two eyes lost the eyes: their share was a few triangles,
// the isotropic remesher collapsed each to two triangles glued along their
// edges, and no quads were extracted. A small ring could come back with its
// hole closed. Shapes are procedural so the test needs no data files.

#include <AutoRemesher/AutoRemesher>
#include <cmath>
#include <cstdio>
#include <map>
#include <utility>
#include <vector>

using AutoRemesher::Vector3;

namespace {

struct Mesh {
    std::vector<Vector3> vertices;
    std::vector<std::vector<size_t>> triangles;

    void append(const Mesh& other)
    {
        const size_t offset = vertices.size();
        vertices.insert(vertices.end(), other.vertices.begin(), other.vertices.end());
        for (const auto& t : other.triangles)
            triangles.push_back({ t[0] + offset, t[1] + offset, t[2] + offset });
    }
};

Mesh sphere(int subdivisions, const Vector3& center, double radius)
{
    const double t = (1.0 + std::sqrt(5.0)) / 2.0;
    Mesh mesh;
    mesh.vertices = { { -1, t, 0 }, { 1, t, 0 }, { -1, -t, 0 }, { 1, -t, 0 },
        { 0, -1, t }, { 0, 1, t }, { 0, -1, -t }, { 0, 1, -t },
        { t, 0, -1 }, { t, 0, 1 }, { -t, 0, -1 }, { -t, 0, 1 } };
    for (auto& v : mesh.vertices)
        v.normalize();
    mesh.triangles = { { 0, 11, 5 }, { 0, 5, 1 }, { 0, 1, 7 }, { 0, 7, 10 }, { 0, 10, 11 },
        { 1, 5, 9 }, { 5, 11, 4 }, { 11, 10, 2 }, { 10, 7, 6 }, { 7, 1, 8 },
        { 3, 9, 4 }, { 3, 4, 2 }, { 3, 2, 6 }, { 3, 6, 8 }, { 3, 8, 9 },
        { 4, 9, 5 }, { 2, 4, 11 }, { 6, 2, 10 }, { 8, 6, 7 }, { 9, 8, 1 } };
    for (int s = 0; s < subdivisions; ++s) {
        std::map<std::pair<size_t, size_t>, size_t> midpoints;
        const auto midpoint = [&](size_t a, size_t b) {
            const auto key = std::make_pair(std::min(a, b), std::max(a, b));
            const auto found = midpoints.find(key);
            if (found != midpoints.end())
                return found->second;
            Vector3 m = (mesh.vertices[a] + mesh.vertices[b]) * 0.5;
            m.normalize();
            mesh.vertices.push_back(m);
            midpoints[key] = mesh.vertices.size() - 1;
            return mesh.vertices.size() - 1;
        };
        std::vector<std::vector<size_t>> finer;
        finer.reserve(mesh.triangles.size() * 4);
        for (const auto& f : mesh.triangles) {
            const size_t ab = midpoint(f[0], f[1]), bc = midpoint(f[1], f[2]), ca = midpoint(f[2], f[0]);
            finer.push_back({ f[0], ab, ca });
            finer.push_back({ f[1], bc, ab });
            finer.push_back({ f[2], ca, bc });
            finer.push_back({ ab, bc, ca });
        }
        mesh.triangles.swap(finer);
    }
    for (auto& v : mesh.vertices)
        v = center + v * radius;
    return mesh;
}

Mesh torus(size_t rings, size_t sides, const Vector3& center, double majorRadius, double minorRadius)
{
    Mesh mesh;
    for (size_t i = 0; i < rings; ++i) {
        const double u = 2.0 * M_PI * i / rings;
        for (size_t j = 0; j < sides; ++j) {
            const double v = 2.0 * M_PI * j / sides;
            const double r = majorRadius + minorRadius * std::cos(v);
            mesh.vertices.push_back(center + Vector3(r * std::cos(u), r * std::sin(u), minorRadius * std::sin(v)));
        }
    }
    for (size_t i = 0; i < rings; ++i) {
        for (size_t j = 0; j < sides; ++j) {
            const size_t a = i * sides + j, b = ((i + 1) % rings) * sides + j;
            const size_t c = ((i + 1) % rings) * sides + (j + 1) % sides, d = i * sides + (j + 1) % sides;
            mesh.triangles.push_back({ a, b, c });
            mesh.triangles.push_back({ a, c, d });
        }
    }
    return mesh;
}

struct Component {
    size_t quads = 0;
    size_t boundaryEdges = 0;
    size_t nonManifoldEdges = 0;
    long long eulerCharacteristic = 0;
    Vector3 center;
};

// Connected components of the output, with the edge counts that say whether
// each one is a closed 2-manifold, and its Euler characteristic V - E + F.
std::vector<Component> components(const std::vector<Vector3>& vertices,
    const std::vector<std::vector<size_t>>& faces)
{
    std::vector<size_t> parent(vertices.size());
    for (size_t i = 0; i < parent.size(); ++i)
        parent[i] = i;
    const auto root = [&](size_t v) {
        while (parent[v] != v)
            v = parent[v] = parent[parent[v]];
        return v;
    };
    for (const auto& face : faces) {
        for (size_t i = 1; i < face.size(); ++i)
            parent[root(face[i])] = root(face[0]);
    }
    std::map<size_t, Component> byRoot;
    std::map<size_t, size_t> vertexCount;
    std::map<std::pair<size_t, size_t>, size_t> edgeUse;
    for (const auto& face : faces) {
        Component& component = byRoot[root(face[0])];
        ++component.quads;
        for (size_t i = 0; i < face.size(); ++i) {
            const size_t a = face[i], b = face[(i + 1) % face.size()];
            ++edgeUse[std::make_pair(std::min(a, b), std::max(a, b))];
        }
    }
    for (size_t v = 0; v < vertices.size(); ++v) {
        const auto found = byRoot.find(root(v));
        if (found == byRoot.end())
            continue;
        found->second.center += vertices[v];
        ++vertexCount[found->first];
    }
    for (const auto& it : edgeUse) {
        Component& component = byRoot[root(it.first.first)];
        --component.eulerCharacteristic;
        if (1 == it.second)
            ++component.boundaryEdges;
        else if (it.second > 2)
            ++component.nonManifoldEdges;
    }
    std::vector<Component> result;
    for (auto& it : byRoot) {
        it.second.center = it.second.center * (1.0 / vertexCount[it.first]);
        it.second.eulerCharacteristic += (long long)vertexCount[it.first] + (long long)it.second.quads;
        result.push_back(it.second);
    }
    return result;
}

} // namespace

int main()
{
    struct Island {
        const char* name;
        Mesh mesh;
        long long eulerCharacteristic;
    };
    // A body and small parts placed apart from it: two eyes of the share that
    // vanished on human_neutral, and a small ring, which needs more quads than
    // a sphere to keep its hole.
    std::vector<Island> islands;
    islands.push_back({ "body", sphere(4, Vector3(0, 0, 0), 1.0), 2 });
    islands.push_back({ "left eye", sphere(3, Vector3(-0.5, 0, 1.5), 0.05), 2 });
    islands.push_back({ "right eye", sphere(3, Vector3(0.5, 0, 1.5), 0.05), 2 });
    islands.push_back({ "ring", torus(48, 16, Vector3(0, 0, -1.5), 0.08, 0.03), 0 });
    Mesh input;
    for (const auto& island : islands)
        input.append(island.mesh);

    int failures = 0;
    for (const size_t targetTriangleCount : { 2000, 10000, 40000 }) {
        AutoRemesher::AutoRemesher remesher(input.vertices, input.triangles);
        remesher.setTargetTriangleCount(targetTriangleCount);
        if (!remesher.remesh()) {
            std::printf("target %zu: remesh failed\n", targetTriangleCount);
            ++failures;
            continue;
        }
        const auto found = components(remesher.remeshedVertices(), remesher.remeshedQuads());
        for (const auto& island : islands) {
            Vector3 center;
            for (const auto& v : island.mesh.vertices)
                center += v;
            center = center * (1.0 / island.mesh.vertices.size());
            size_t matches = 0;
            const Component* match = nullptr;
            for (const auto& component : found) {
                if ((component.center - center).length() < 0.25) {
                    ++matches;
                    match = &component;
                }
            }
            if (1 != matches) {
                std::printf("target %zu: %s: %zu output components, expected 1\n",
                    targetTriangleCount, island.name, matches);
                ++failures;
                continue;
            }
            std::printf("target %zu: %s: %zu quads, %zu boundary and %zu non-manifold edges, Euler characteristic %lld\n",
                targetTriangleCount, island.name, match->quads,
                match->boundaryEdges, match->nonManifoldEdges, match->eulerCharacteristic);
            // Closed, and of the input's genus. A closed quad surface has at
            // least the 6 faces of a cube.
            if (match->quads < 6 || 0 != match->boundaryEdges || 0 != match->nonManifoldEdges
                || island.eulerCharacteristic != match->eulerCharacteristic) {
                std::printf("    not a closed quad mesh of the input's genus\n");
                ++failures;
            }
        }
    }
    if (0 != failures) {
        std::printf("FAILED: %d checks\n", failures);
        return 1;
    }
    std::printf("PASSED\n");
    return 0;
}
