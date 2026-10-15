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

// The output should have about as many quads as requested, with and without
// curvature adaptivity and at both resolutions: adaptivity moves quads
// between flat and curved regions and the resolution changes the mesh they
// are solved on, but neither may change how many there are. Shapes are
// procedural so the test needs no data files.

#include <AutoRemesher/Remesh>
#include <AutoRemesher/Vector3>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <map>
#include <string>
#include <utility>
#include <vector>

using AutoRemesher::Vector3;

namespace {

struct Mesh {
    std::vector<Vector3> vertices;
    std::vector<std::vector<size_t>> triangles;
};

// Unit icosphere, each vertex then moved to radius(direction) * direction.
Mesh sphere(int subdivisions, const std::function<double(const Vector3&)>& radius)
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
        v = v * radius(v);
    return mesh;
}

Mesh torus(double majorRadius, double minorRadius, size_t around, size_t across)
{
    Mesh mesh;
    for (size_t i = 0; i < around; ++i) {
        const double u = 2.0 * M_PI * i / around;
        for (size_t j = 0; j < across; ++j) {
            const double v = 2.0 * M_PI * j / across;
            const double r = majorRadius + minorRadius * std::cos(v);
            mesh.vertices.push_back({ r * std::cos(u), r * std::sin(u), minorRadius * std::sin(v) });
        }
    }
    for (size_t i = 0; i < around; ++i) {
        for (size_t j = 0; j < across; ++j) {
            const size_t a = i * across + j, b = ((i + 1) % around) * across + j;
            const size_t c = ((i + 1) % around) * across + (j + 1) % across, d = i * across + (j + 1) % across;
            mesh.triangles.push_back({ a, b, c });
            mesh.triangles.push_back({ a, c, d });
        }
    }
    return mesh;
}

Mesh transformed(Mesh mesh, const Vector3& scale, const Vector3& offset)
{
    for (auto& v : mesh.vertices)
        v = Vector3(v.x() * scale.x(), v.y() * scale.y(), v.z() * scale.z()) + offset;
    return mesh;
}

Mesh merged(const Mesh& a, const Mesh& b)
{
    Mesh mesh = a;
    for (const auto& f : b.triangles)
        mesh.triangles.push_back({ f[0] + a.vertices.size(), f[1] + a.vertices.size(), f[2] + a.vertices.size() });
    mesh.vertices.insert(mesh.vertices.end(), b.vertices.begin(), b.vertices.end());
    return mesh;
}

size_t remeshQuads(const Mesh& mesh, size_t targetQuads, double adaptivity,
    AutoRemesher::MeshResolution resolution)
{
    AutoRemesher::RemeshRequest request;
    for (const auto& v : mesh.vertices)
        request.positions.insert(request.positions.end(), { v.x(), v.y(), v.z() });
    for (const auto& f : mesh.triangles)
        request.triangles.insert(request.triangles.end(), { (uint32_t)f[0], (uint32_t)f[1], (uint32_t)f[2] });
    request.parameters.targetQuadCount = (uint32_t)targetQuads;
    request.parameters.adaptivity = adaptivity;
    request.parameters.resolution = resolution;
    const AutoRemesher::RemeshResult result = AutoRemesher::remesh(request);
    return AutoRemesher::RemeshStatus::Ok == result.status ? result.report.quadCount : 0;
}

}

int main()
{
    const auto unit = [](const Vector3&) { return 1.0; };
    // Six smooth bumps: the curvature varies by more than an order of
    // magnitude, so the adaptive field is far from uniform.
    const auto bumps = [](const Vector3& d) {
        const Vector3 centres[] = { { 1, 0, 0 }, { -1, 0, 0 }, { 0, 1, 0 }, { 0, -1, 0 }, { 0, 0, 1 }, { 0, 0, -1 } };
        double r = 1.0;
        for (const auto& c : centres)
            r += 0.3 * std::exp(-(d - c).lengthSquared() / 0.04);
        return r;
    };
    const Mesh ball = sphere(5, unit);
    const std::vector<std::pair<std::string, Mesh>> shapes = {
        { "sphere", ball },
        { "ellipsoid", transformed(ball, { 2.0, 1.0, 0.5 }, { 0, 0, 0 }) },
        { "bumpy", sphere(5, bumps) },
        { "torus", torus(1.0, 0.3, 160, 48) },
        { "two islands", merged(ball, transformed(ball, { 0.5, 0.5, 0.5 }, { 3.0, 0, 0 })) },
    };

    // Rounding the parametrization to integers moves the count by a few
    // percent either way. Sizing errors are larger: the sizing this test was
    // written against gave 0.60-0.87 of the target here without adaptivity
    // and 0.36-0.82 with it.
    const double tolerance = 0.1;
    struct Case {
        std::string shape;
        size_t target;
        double adaptivity;
        AutoRemesher::MeshResolution resolution;
        size_t quads;
    };
    // Every combination at the default resolution; fast only with adaptivity,
    // where the sizing is furthest from uniform, to keep the test short.
    std::vector<Case> cases;
    for (const auto& shape : shapes)
        for (const size_t target : { 1000, 4000 })
            for (const double adaptivity : { 0.0, 1.0 })
                for (const auto resolution : { AutoRemesher::MeshResolution::Quality, AutoRemesher::MeshResolution::Fast }) {
                    if (AutoRemesher::MeshResolution::Fast == resolution && 0.0 == adaptivity)
                        continue;
                    cases.push_back({ shape.first, target, adaptivity, resolution,
                        remeshQuads(shape.second, target, adaptivity, resolution) });
                }

    // The core logs to the console while it runs, so the table comes last.
    int failures = 0;
    printf("\n%-12s %7s %10s %10s %7s %6s\n", "shape", "target", "adaptivity", "resolution", "quads", "ratio");
    for (const auto& c : cases) {
        const double ratio = (double)c.quads / c.target;
        const bool ok = std::fabs(ratio - 1.0) <= tolerance;
        failures += ok ? 0 : 1;
        printf("%-12s %7zu %10.1f %10s %7zu %6.3f%s\n", c.shape.c_str(), c.target, c.adaptivity,
            AutoRemesher::toString(c.resolution), c.quads, ratio, ok ? "" : "  FAIL");
    }
    if (failures)
        printf("%d case(s) outside %.0f%% of the target\n", failures, 100 * tolerance);
    return failures ? 1 : 0;
}
