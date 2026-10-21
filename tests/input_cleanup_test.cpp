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

// The input cleanup pre-pass merges the ends of zero-length edges and drops
// the triangles that become degenerate (research/sculpt-inputs-2026-10-21,
// sculpt_degenerate: 21 % such triangles gave 500-777 non-quads and a wrong
// genus).  It must leave a clean mesh alone, keep coincident vertices that no
// edge joins apart, and never change a part's topology.

#include <AutoRemesher/AutoRemesher>
#include <AutoRemesher/Remesh>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <map>
#include <utility>
#include <vector>

using AutoRemesher::Vector3;
using Cleaner = AutoRemesher::AutoRemesher;

namespace {

int failures = 0;

void check(bool ok, const char* what)
{
    printf("%-64s %s\n", what, ok ? "ok" : "FAIL");
    if (!ok)
        ++failures;
}

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

// Splits edge (a, b) at a point `offset` away from a, as marching cubes on a
// binary volume does at a grid corner: two triangles become four, two of them
// of zero area when offset is zero.  Stays a closed 2-manifold.
void splitNearCorner(Mesh& mesh, size_t a, size_t b, const Vector3& offset)
{
    const size_t m = mesh.vertices.size();
    mesh.vertices.push_back(mesh.vertices[a] + offset);
    std::vector<std::vector<size_t>> out;
    for (const auto& f : mesh.triangles) {
        bool split = false;
        for (size_t i = 0; i < 3 && !split; ++i) {
            const size_t p = f[i], q = f[(i + 1) % 3], r = f[(i + 2) % 3];
            if ((p == a && q == b) || (p == b && q == a)) {
                out.push_back({ p, m, r });
                out.push_back({ m, q, r });
                split = true;
            }
        }
        if (!split)
            out.push_back(f);
    }
    mesh.triangles.swap(out);
}

double tolerance(const Mesh& mesh)
{
    return Cleaner::inputCleanupTolerance(mesh.vertices);
}

} // namespace

int main()
{
    {
        Mesh mesh = sphere(3, Vector3(0, 0, 0), 1.0);
        const auto before = mesh.triangles;
        const auto stats = Cleaner::cleanInput(mesh.vertices, mesh.triangles, tolerance(mesh));
        check(before == mesh.triangles, "clean sphere: triangles unchanged, same order");
        check(0 == stats.mergedVertices && 0 == stats.droppedTriangles && 0 == stats.zeroAreaTriangles,
            "clean sphere: nothing counted");
    }
    {
        // Ten exact zero-length edges, then one 1e-9 away (below tolerance)
        // and one 1e-3 away (a real, short edge).
        Mesh mesh = sphere(3, Vector3(0, 0, 0), 1.0);
        const size_t originalTriangles = mesh.triangles.size();
        for (size_t k = 0; k < 10; ++k) {
            const auto f = mesh.triangles[k * 37];
            splitNearCorner(mesh, f[0], f[1], Vector3(0, 0, 0));
        }
        auto f = mesh.triangles[500];
        splitNearCorner(mesh, f[0], f[1], Vector3(1e-9, 0, 0));
        f = mesh.triangles[900];
        splitNearCorner(mesh, f[0], f[1], (mesh.vertices[f[1]] - mesh.vertices[f[0]]) * 1e-2);
        const Topology input = topology(mesh.vertices, mesh.triangles);
        const auto stats = Cleaner::cleanInput(mesh.vertices, mesh.triangles, tolerance(mesh));
        const Topology output = topology(mesh.vertices, mesh.triangles);
        check(11 == stats.mergedVertices, "zero-length edges: 11 vertices merged");
        check(22 == stats.droppedTriangles, "zero-length edges: 22 triangles dropped");
        check(originalTriangles + 2 == mesh.triangles.size(), "zero-length edges: only the real split stays");
        check(0 == stats.keptParts && 0 == stats.zeroAreaTriangles, "zero-length edges: no part kept, no zero area left");
        check(0 == output.boundaryEdges && 0 == output.nonManifoldEdges
                && input.eulerCharacteristic == output.eulerCharacteristic && 2 == output.eulerCharacteristic,
            "zero-length edges: still a closed sphere");
    }
    {
        // Two spheres touching at one point through two coincident vertices
        // that no edge joins: a surface touching itself stays as it is.
        Mesh a = sphere(2, Vector3(0, 0, 0), 1.0);
        Mesh b = sphere(2, Vector3(0, 0, 0), 1.0);
        const Vector3 shift = a.vertices[0] - b.vertices[3];
        Mesh mesh = a;
        const size_t base = mesh.vertices.size();
        for (const auto& v : b.vertices)
            mesh.vertices.push_back(v + shift * 1.0);
        for (const auto& t : b.triangles)
            mesh.triangles.push_back({ t[0] + base, t[1] + base, t[2] + base });
        const auto before = mesh.triangles;
        const auto stats = Cleaner::cleanInput(mesh.vertices, mesh.triangles, tolerance(mesh));
        check(before == mesh.triangles && 0 == stats.mergedVertices, "touching spheres: coincident pair kept apart");
    }
    {
        // A lone triangle with a zero-length edge: merging would leave no
        // triangle, so the part is kept as it is, and counted.
        Mesh mesh = sphere(1, Vector3(0, 0, 0), 1.0);
        const size_t base = mesh.vertices.size();
        mesh.vertices.push_back(Vector3(3, 0, 0));
        mesh.vertices.push_back(Vector3(3, 0, 0));
        mesh.vertices.push_back(Vector3(3, 1, 0));
        mesh.triangles.push_back({ base, base + 1, base + 2 });
        const size_t count = mesh.triangles.size();
        const auto stats = Cleaner::cleanInput(mesh.vertices, mesh.triangles, tolerance(mesh));
        check(count == mesh.triangles.size() && 1 == stats.keptParts && 0 == stats.mergedVertices,
            "lone degenerate triangle: part kept, counted");
    }
    {
        // Collinear corners with no short edge (a cap) are only counted.
        Mesh mesh = sphere(1, Vector3(0, 0, 0), 1.0);
        const size_t base = mesh.vertices.size();
        mesh.vertices.push_back(Vector3(3, 0, 0));
        mesh.vertices.push_back(Vector3(4, 0, 0));
        mesh.vertices.push_back(Vector3(5, 0, 0));
        mesh.triangles.push_back({ base, base + 1, base + 2 });
        const auto before = mesh.triangles;
        const auto stats = Cleaner::cleanInput(mesh.vertices, mesh.triangles, tolerance(mesh));
        check(before == mesh.triangles && 1 == stats.zeroAreaTriangles, "cap: left in place, counted");
    }
    {
        // A patch turned against the rest: turned back, the larger side wins.
        Mesh mesh = sphere(3, Vector3(0, 0, 0), 1.0);
        const auto before = mesh.triangles;
        for (size_t t = 0; t < 40; ++t)
            std::swap(mesh.triangles[t][1], mesh.triangles[t][2]);
        Cleaner::InputCleanupStats stats;
        Cleaner::orientInput(mesh.vertices, mesh.triangles, &stats);
        check(40 == stats.flippedTriangles && before == mesh.triangles, "flipped patch: turned back to the sphere's side");
        // All turned: consistent, so left alone.
        for (auto& t : mesh.triangles)
            std::swap(t[1], t[2]);
        const auto inverted = mesh.triangles;
        Cleaner::InputCleanupStats none;
        Cleaner::orientInput(mesh.vertices, mesh.triangles, &none);
        check(0 == none.flippedTriangles && inverted == mesh.triangles, "inside-out sphere: consistent, unchanged");
    }
    {
        // A Moebius strip has no orientation: left as it is, counted.
        Mesh mesh;
        const size_t n = 24;
        for (size_t i = 0; i < n; ++i) {
            const double u = 2.0 * 3.14159265358979323846 * i / n;
            for (const double w : { -0.2, 0.2 }) {
                mesh.vertices.push_back(Vector3((1 + w * std::cos(u / 2)) * std::cos(u),
                    (1 + w * std::cos(u / 2)) * std::sin(u), w * std::sin(u / 2)));
            }
        }
        for (size_t i = 0; i < n; ++i) {
            const size_t a = 2 * i, b = 2 * i + 1;
            size_t c = 2 * ((i + 1) % n), d = c + 1;
            if (i + 1 == n)
                std::swap(c, d);
            mesh.triangles.push_back({ a, c, b });
            mesh.triangles.push_back({ b, c, d });
        }
        const auto before = mesh.triangles;
        Cleaner::InputCleanupStats stats;
        Cleaner::orientInput(mesh.vertices, mesh.triangles, &stats);
        check(1 == stats.nonOrientablePieces && before == mesh.triangles, "Moebius strip: unchanged, counted");
    }
    {
        // Through the interface: the counts reach the quality report.
        Mesh mesh = sphere(3, Vector3(0, 0, 0), 1.0);
        for (size_t k = 0; k < 5; ++k) {
            const auto f = mesh.triangles[k * 53];
            splitNearCorner(mesh, f[0], f[1], Vector3(0, 0, 0));
        }
        AutoRemesher::RemeshRequest request;
        for (const auto& v : mesh.vertices) {
            request.positions.push_back(v.x());
            request.positions.push_back(v.y());
            request.positions.push_back(v.z());
        }
        for (const auto& t : mesh.triangles)
            for (const size_t i : t)
                request.triangles.push_back((uint32_t)i);
        request.parameters.targetQuadCount = 200;
        const AutoRemesher::RemeshResult result = AutoRemesher::remesh(request);
        double dropped = -1, merged = -1;
        for (const auto& item : result.report.diagnostics) {
            if (item.first == "input_dropped_triangles")
                dropped = item.second;
            else if (item.first == "input_merged_vertices")
                merged = item.second;
        }
        check(AutoRemesher::RemeshStatus::Ok == result.status, "remesh: ok");
        check(10 == dropped && 5 == merged, "remesh: report has 10 dropped triangles, 5 merged vertices");
        check(0 == result.report.boundaryEdgeCount && 0 == result.report.nonManifoldEdgeCount,
            "remesh: output closed and manifold");
    }
    return failures ? 1 : 0;
}
