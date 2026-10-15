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

// The pipeline's own diagnostics: the exact orientation predicate, the JSON
// lines writer, and the records a real remesh leaves behind (TODO 1.6,
// 2.1-2.3).  Shapes are procedural so the test needs no data files.

#include <AutoRemesher/AutoRemesher>
#include <AutoRemesher/Diagnostics>
#include <AutoRemesher/Predicates>
#include <AutoRemesher/Remesh>
#include <cmath>
#include <cstdio>
#include <map>
#include <string>
#include <utility>
#include <vector>

using AutoRemesher::DiagnosticRecord;
using AutoRemesher::Vector2;
using AutoRemesher::Vector3;
using AutoRemesher::Predicates::orient2d;

namespace {

int failures = 0;

void check(bool condition, const std::string& what)
{
    if (!condition) {
        std::printf("FAIL: %s\n", what.c_str());
        ++failures;
    }
}

void testOrient2d()
{
    check(orient2d(Vector2(0, 0), Vector2(1, 0), Vector2(0, 1)) == 1, "counter-clockwise is +1");
    check(orient2d(Vector2(0, 0), Vector2(0, 1), Vector2(1, 0)) == -1, "clockwise is -1");
    check(orient2d(Vector2(0, 0), Vector2(1, 1), Vector2(2, 2)) == 0, "collinear is 0");

    // a = (0.5 + i u, 0.5 + j u), b = (12, 12), c = (24, 24) with u = 2^-53:
    // the exact determinant is 12 (j - i) u, so the sign is that of j - i.
    // The plain floating-point formula gets a large share of these wrong.
    const double u = std::ldexp(1.0, -53);
    size_t naiveWrong = 0;
    for (int i = 0; i < 64; ++i) {
        for (int j = 0; j < 64; ++j) {
            const Vector2 a(0.5 + i * u, 0.5 + j * u), b(12, 12), c(24, 24);
            const int expected = j > i ? 1 : (j < i ? -1 : 0);
            const int sign = orient2d(a, b, c);
            if (sign != expected) {
                check(false, "orient2d near-collinear i=" + std::to_string(i) + " j=" + std::to_string(j));
                return;
            }
            check(orient2d(b, c, a) == sign && orient2d(b, a, c) == -sign, "orient2d is cyclic and antisymmetric");
            const double naive = (a.x() - c.x()) * (b.y() - c.y()) - (a.y() - c.y()) * (b.x() - c.x());
            if ((naive > 0 ? 1 : (naive < 0 ? -1 : 0)) != expected)
                ++naiveWrong;
        }
    }
    // Guards the test itself: the cases must be hard enough to need the
    // exact path.
    check(naiveWrong > 0, "near-collinear cases defeat the plain formula");
}

void testOrientationCount()
{
    // One positive, one flipped, one degenerate triangle.
    const std::vector<double> uvs = {
        0, 0, 1, 0, 0, 1,
        0, 0, 0, 1, 1, 0,
        0, 0, 1, 1, 2, 2
    };
    const AutoRemesher::UvOrientation orientation = AutoRemesher::measureUvOrientation(uvs);
    check(orientation.triangles == 3, "orientation counts triangles");
    check(orientation.positive == 1 && orientation.negative == 1 && orientation.degenerate == 1,
        "orientation separates positive, flipped and degenerate");
    check(std::fabs(orientation.negativeArea / orientation.totalArea - 0.5) < 1e-12, "flipped area share");
}

void testJsonLines()
{
    std::vector<DiagnosticRecord> records;
    records.push_back(DiagnosticRecord("run").set("count", 3).set("ratio", 0.1).set("bad", std::nan("")));
    records.push_back(DiagnosticRecord("step", 2).label("name", "a \"quoted\"\\name"));
    const std::string text = AutoRemesher::diagnosticsToJsonLines(records, { { "mesh", "m.obj" } });
    const std::string expected = "{\"schema\":\"autoremesher.stage-diagnostics\",\"version\":1,\"mesh\":\"m.obj\",\"stage\":\"run\",\"count\":3,\"ratio\":0.1,\"bad\":null}\n"
                                 "{\"schema\":\"autoremesher.stage-diagnostics\",\"version\":1,\"mesh\":\"m.obj\",\"stage\":\"step\",\"island\":2,\"name\":\"a \\\"quoted\\\"\\\\name\"}\n";
    check(text == expected, "JSON lines format:\n" + text);
}

struct Mesh {
    std::vector<Vector3> vertices;
    std::vector<std::vector<size_t>> triangles;
};

// Icosphere with a bump, so the cover needs singularities and real rounding.
Mesh bumpySphere(int subdivisions)
{
    const double t = (1.0 + std::sqrt(5.0)) / 2.0;
    Mesh mesh;
    mesh.vertices = { { -1, t, 0 }, { 1, t, 0 }, { -1, -t, 0 }, { 1, -t, 0 },
        { 0, -1, t }, { 0, 1, t }, { 0, -1, -t }, { 0, 1, -t },
        { t, 0, -1 }, { t, 0, 1 }, { -t, 0, -1 }, { -t, 0, 1 } };
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
            mesh.vertices.push_back((mesh.vertices[a] + mesh.vertices[b]) * 0.5);
            midpoints[key] = mesh.vertices.size() - 1;
            return mesh.vertices.size() - 1;
        };
        std::vector<std::vector<size_t>> next;
        for (const auto& f : mesh.triangles) {
            const size_t ab = midpoint(f[0], f[1]), bc = midpoint(f[1], f[2]), ca = midpoint(f[2], f[0]);
            next.push_back({ f[0], ab, ca });
            next.push_back({ f[1], bc, ab });
            next.push_back({ f[2], ca, bc });
            next.push_back({ ab, bc, ca });
        }
        mesh.triangles.swap(next);
    }
    for (auto& v : mesh.vertices) {
        v.normalize();
        v = v * (1.0 + 0.3 * std::exp(-8.0 * ((v.x() - 1) * (v.x() - 1) + v.y() * v.y() + v.z() * v.z())));
    }
    return mesh;
}

double value(const DiagnosticRecord& record, const std::string& key, bool* found = nullptr)
{
    for (const auto& item : record.values)
        if (item.first == key) {
            if (found)
                *found = true;
            return item.second;
        }
    if (found)
        *found = false;
    return std::nan("");
}

void testRemeshRecords()
{
    const Mesh mesh = bumpySphere(4);
    AutoRemesher::AutoRemesher remesher(mesh.vertices, mesh.triangles);
    remesher.setTargetTriangleCount(2000);
    check(remesher.remesh(), "remesh succeeds");

    std::map<std::string, std::vector<const DiagnosticRecord*>> byStage;
    for (const auto& record : remesher.diagnostics())
        byStage[record.stage].push_back(&record);

    check(byStage["run"].size() == 1, "one run record");
    check(!byStage["step"].empty(), "step records");
    check(byStage["island"].size() == 1, "one island record per island");
    for (const char* stage : { "frame_field", "singularity_simplifier", "cover_input",
             "curl_correction", "cover_system", "cover_result" })
        check(byStage[stage].size() == 1, std::string("one ") + stage + " record");
    check(byStage["rounding_iteration"].size() >= 2, "a continuous and at least one rounding pass");
    if (failures > 0)
        return;

    const DiagnosticRecord& run = *byStage["run"][0];
    check(value(run, "output_faces") > 0, "run counts output faces");
    check(value(run, "peak_rss_bytes") > 0, "peak RSS is measured");
    check(byStage["cover_result"][0]->island == 0, "island records carry their island");

    // The first pass fixes nothing (continuous relaxation); later passes
    // round.
    const DiagnosticRecord& first = *byStage["rounding_iteration"][0];
    check(value(first, "newly_fixed") == 0, "first pass is continuous");
    check(value(first, "solve_ok") == 1 && value(first, "solve_n") > 0, "first pass solve stats");
    check(value(*byStage["rounding_iteration"][1], "newly_fixed") > 0, "second pass rounds");

    const DiagnosticRecord& cover = *byStage["cover_result"][0];
    const double islandTriangles = value(*byStage["island"][0], "isotropic_triangles");
    for (const char* map : { "continuous", "rounded", "snapped" }) {
        const std::string prefix = map;
        bool found = false;
        const double triangles = value(cover, prefix + "_triangles", &found);
        check(found && triangles == islandTriangles, prefix + " map covers every triangle");
        const double flipped = value(cover, prefix + "_flipped");
        // A valid map is all positive: flips must be the exception, which
        // also pins the orientation convention.
        check(flipped < 0.25 * triangles, prefix + " map is mostly positively oriented");
    }
    check(value(cover, "converged") == 1, "rounding converged");
    check(value(cover, "iterations") == (double)byStage["rounding_iteration"].size(),
        "cover result counts the rounding passes");
    for (const auto& record : remesher.diagnostics()) {
        std::map<std::string, int> seen;
        for (const auto& item : record.values)
            check(0 == seen[item.first]++, record.stage + " has key " + item.first + " once");
    }
    const double residual = value(cover, "integrality_residual");
    check(residual >= 0 && residual <= 0.5, "integrality residual is a distance to the nearest integer");
    check(value(cover, "constraint_residual") >= 0, "constraint residual is reported");
    check(value(*byStage["frame_field"][0], "solve_solves") == 5, "frame field solves five times");
    check(value(*byStage["frame_field"][0], "solve_factorizations") == 1, "frame field factorises once");

    const std::string text = AutoRemesher::diagnosticsToJsonLines(remesher.diagnostics());
    size_t lines = 0;
    for (size_t start = 0; start < text.size();) {
        const size_t end = text.find('\n', start);
        check(end != std::string::npos && text[start] == '{' && text[end - 1] == '}', "every line is one object");
        if (end == std::string::npos)
            break;
        ++lines;
        start = end + 1;
    }
    check(lines == remesher.diagnostics().size(), "one line per record");

    std::printf("continuous flips %g, rounded flips %g, snapped flips %g of %g; integrality residual %g; constraint residual %g\n",
        value(cover, "continuous_flipped"), value(cover, "rounded_flipped"), value(cover, "snapped_flipped"),
        islandTriangles, residual, value(cover, "constraint_residual"));
}

// The interface carries the records and their summary (interface 1.1).
void testInterface()
{
    const Mesh mesh = bumpySphere(3);
    AutoRemesher::RemeshRequest request;
    for (const auto& v : mesh.vertices) {
        request.positions.push_back(v.x());
        request.positions.push_back(v.y());
        request.positions.push_back(v.z());
    }
    for (const auto& t : mesh.triangles)
        for (const size_t i : t)
            request.triangles.push_back((uint32_t)i);
    request.parameters.targetQuadCount = 1000;
    const AutoRemesher::RemeshResult result = AutoRemesher::remesh(request);
    check(AutoRemesher::RemeshStatus::Ok == result.status, "interface remesh succeeds");
    check(!result.stageDiagnostics.empty(), "interface carries the stage records");
    bool found = false;
    for (const auto& item : result.report.diagnostics)
        if (item.first == "uv_flipped_triangles")
            found = true;
    check(found, "report diagnostics summarise the flips");
    check(AutoRemesher::toJson(result).find("\"uv_flipped_triangles\"") != std::string::npos,
        "JSON report has the summary");
}

}

int main()
{
    testOrient2d();
    testOrientationCount();
    testJsonLines();
    testRemeshRecords();
    testInterface();
    if (failures > 0) {
        std::printf("%d check(s) failed\n", failures);
        return 1;
    }
    std::printf("all diagnostics checks passed\n");
    return 0;
}
