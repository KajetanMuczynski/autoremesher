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

// Decimation must keep the topology of the island it simplifies (gap scan
// item 6). On thin closed shells meshopt joined the two sides into
// non-manifold edges, which the isotropic remesher opened into holes: 15 of 52
// decimated runs of the closed A/B set. T is checked after both steps, since a
// defect in T becomes a hole or a wrong genus in the output.

#include <AutoRemesher/AutoRemesher>
#include <algorithm>
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

struct Topology {
    size_t boundaryEdges = 0;
    size_t nonManifoldEdges = 0;
    long long eulerCharacteristic = 0;
};

Topology topology(const std::vector<Vector3>& vertices, const std::vector<std::vector<size_t>>& faces)
{
    Topology result;
    std::map<std::pair<size_t, size_t>, size_t> edgeUse;
    std::vector<bool> used(vertices.size(), false);
    for (const auto& face : faces) {
        for (size_t i = 0; i < face.size(); ++i) {
            used[face[i]] = true;
            const size_t a = face[i], b = face[(i + 1) % face.size()];
            ++edgeUse[std::make_pair(std::min(a, b), std::max(a, b))];
        }
    }
    for (const auto& it : edgeUse) {
        if (1 == it.second)
            ++result.boundaryEdges;
        else if (it.second > 2)
            ++result.nonManifoldEdges;
    }
    result.eulerCharacteristic = (long long)std::count(used.begin(), used.end(), true)
        - (long long)edgeUse.size() + (long long)faces.size();
    return result;
}

bool report(const char* name, const char* step, const Topology& t)
{
    const bool ok = 0 == t.boundaryEdges && 0 == t.nonManifoldEdges && 2 == t.eulerCharacteristic;
    printf("%-22s %-10s boundary %3zu, non-manifold %3zu, Euler %3lld%s\n", name, step,
        t.boundaryEdges, t.nonManifoldEdges, t.eulerCharacteristic, ok ? "" : "  FAIL");
    return ok;
}

} // namespace

int main()
{
    int failures = 0;
    // The thin ellipsoids of the closed set that failed, at a 150 quad target.
    for (const double b : { 0.15, 0.4 }) {
        for (const double c : { 0.003, 0.01 }) {
            Mesh mesh = sphere(5, Vector3(0, 0, 0), 1.0);
            for (auto& v : mesh.vertices)
                v = Vector3(v.x(), v.y() * b, v.z() * c);
            char name[64];
            snprintf(name, sizeof(name), "ellipsoid (1, %g, %g)", b, c);

            AutoRemesher::AutoRemesher remesher(mesh.vertices, mesh.triangles);
            remesher.setTargetTriangleCount(300);
            if (!remesher.remesh()) {
                printf("%-22s remesh failed  FAIL\n", name);
                ++failures;
                continue;
            }
            if (!remesher.decimated()) {
                printf("%-22s not decimated  FAIL\n", name);
                ++failures;
                continue;
            }
            failures += report(name, "decimated", topology(remesher.decimatedVertices(), remesher.decimatedTriangles())) ? 0 : 1;
            failures += report(name, "isotropic", topology(remesher.isotropicVertices(), remesher.isotropicTriangles())) ? 0 : 1;
        }
    }
    return failures ? 1 : 0;
}
