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

// The output has as many boundary loops as the input and the same Euler
// characteristic. Hole filling used to cap every output loop of up to 65
// edges, real boundaries included (REFERENCE M15), and then to keep holes
// open that decimation and resampling had made in a closed input.

#include <AutoRemesher/Remesh>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <numeric>
#include <string>
#include <utility>
#include <vector>

namespace {

struct Topology {
    long euler = 0;
    size_t boundaryLoops = 0;
};

size_t findRoot(std::vector<size_t>& parents, size_t vertex)
{
    while (parents[vertex] != vertex)
        vertex = parents[vertex] = parents[parents[vertex]];
    return vertex;
}

// V - E + F over the vertices faces use, and the boundary loops: components
// of the edges that only one face uses.
Topology topology(size_t vertexCount, const std::vector<uint32_t>& faceSizes, const std::vector<uint32_t>& faceIndices)
{
    std::vector<std::pair<uint32_t, uint32_t>> edges;
    std::vector<uint8_t> used(vertexCount, 0);
    size_t offset = 0;
    for (const uint32_t size : faceSizes) {
        for (size_t i = 0; i < size; ++i) {
            const uint32_t a = faceIndices[offset + i];
            const uint32_t b = faceIndices[offset + (i + 1) % size];
            used[a] = 1;
            edges.push_back({ std::min(a, b), std::max(a, b) });
        }
        offset += size;
    }
    std::sort(edges.begin(), edges.end());
    std::vector<size_t> parents(vertexCount);
    std::iota(parents.begin(), parents.end(), (size_t)0);
    std::vector<uint8_t> onBoundary(vertexCount, 0);
    size_t edgeCount = 0;
    for (size_t begin = 0; begin < edges.size();) {
        size_t end = begin + 1;
        while (end < edges.size() && edges[end] == edges[begin])
            ++end;
        ++edgeCount;
        if (1 == end - begin) {
            const auto& edge = edges[begin];
            onBoundary[edge.first] = onBoundary[edge.second] = 1;
            parents[findRoot(parents, edge.first)] = findRoot(parents, edge.second);
        }
        begin = end;
    }
    Topology result;
    result.euler = (long)std::count(used.begin(), used.end(), 1) - (long)edgeCount + (long)faceSizes.size();
    for (size_t vertex = 0; vertex < vertexCount; ++vertex) {
        if (onBoundary[vertex] && findRoot(parents, vertex) == vertex)
            ++result.boundaryLoops;
    }
    return result;
}

// The unit sphere between polar angles `from` and `to` (0 <= from < to <= pi),
// triangulated as `around` columns by `rows` rows, facing outwards. A polar
// angle of 0 or pi closes that end with a single vertex.
AutoRemesher::RemeshRequest sphereBand(double from, double to, uint32_t around, uint32_t rows)
{
    AutoRemesher::RemeshRequest request;
    std::vector<std::vector<uint32_t>> rings(rows + 1);
    for (uint32_t i = 0; i <= rows; ++i) {
        const double theta = from + (to - from) * i / rows;
        const bool pole = (0 == i && 0.0 == from) || (rows == i && M_PI == to);
        for (uint32_t j = 0; j < (pole ? 1 : around); ++j) {
            const double phi = 2.0 * M_PI * j / around;
            rings[i].push_back((uint32_t)(request.positions.size() / 3));
            request.positions.insert(request.positions.end(),
                { std::sin(theta) * std::cos(phi), std::sin(theta) * std::sin(phi), std::cos(theta) });
        }
    }
    const auto add = [&](uint32_t a, uint32_t b, uint32_t c) {
        request.triangles.insert(request.triangles.end(), { a, b, c });
    };
    for (uint32_t i = 0; i < rows; ++i) {
        const auto& upper = rings[i];
        const auto& lower = rings[i + 1];
        for (uint32_t j = 0; j < around; ++j) {
            const uint32_t k = (j + 1) % around;
            if (1 == upper.size()) {
                add(upper[0], lower[j], lower[k]);
            } else if (1 == lower.size()) {
                add(upper[j], lower[0], upper[k]);
            } else {
                add(upper[j], lower[j], lower[k]);
                add(upper[j], lower[k], upper[k]);
            }
        }
    }
    return request;
}

}

int main()
{
    struct Case {
        std::string name;
        AutoRemesher::RemeshRequest request;
        uint32_t target;
        Topology expected;
        bool checkEuler;
    };
    // Each target keeps the output boundary loops below 65 edges, the largest
    // hole the extraction fills.
    std::vector<Case> cases = {
        { "closed", sphereBand(0.0, M_PI, 96, 48), 1000, { 2, 0 }, true },
        { "dome", sphereBand(0.0, 0.45 * M_PI, 96, 24), 400, { 1, 1 }, true },
        { "band", sphereBand(0.25 * M_PI, 0.75 * M_PI, 96, 24), 600, { 0, 2 }, true },
        // A closed ellipsoid thin enough that decimation leaves a non-manifold
        // edge and resampling turns it into a small hole in the mesh the quads
        // are extracted from. That hole must not be taken for the input's
        // boundary. The output has non-manifold edges here, which changes its
        // Euler characteristic, so only the boundary is checked.
        { "thin", sphereBand(0.0, M_PI, 96, 48), 150, { 2, 0 }, false },
    };
    for (size_t i = 0; i < cases.back().request.positions.size(); i += 3) {
        cases.back().request.positions[i + 1] *= 0.15;
        cases.back().request.positions[i + 2] *= 0.003;
    }

    struct Row {
        std::string name;
        Topology input, output;
        bool ok;
    };
    std::vector<Row> rows;
    for (size_t c = 0; c < cases.size(); ++c) {
        auto& request = cases[c].request;
        request.parameters.targetQuadCount = cases[c].target;
        Row row { cases[c].name, {}, {}, false };
        row.input = topology(request.positions.size() / 3,
            std::vector<uint32_t>(request.triangles.size() / 3, 3), request.triangles);
        const AutoRemesher::RemeshResult result = AutoRemesher::remesh(request);
        if (AutoRemesher::RemeshStatus::Ok == result.status) {
            row.output = topology(result.mesh.positions.size() / 3, result.mesh.faceSizes, result.mesh.faceIndices);
            row.ok = row.input.euler == cases[c].expected.euler
                && row.input.boundaryLoops == cases[c].expected.boundaryLoops
                && (!cases[c].checkEuler || row.output.euler == row.input.euler)
                && row.output.boundaryLoops == row.input.boundaryLoops;
        }
        rows.push_back(row);
    }

    // The core logs to the console while it runs, so the table comes last.
    int failures = 0;
    printf("\n%-8s %8s %8s %9s %9s\n", "shape", "chi in", "chi out", "loops in", "loops out");
    for (const auto& row : rows) {
        failures += row.ok ? 0 : 1;
        printf("%-8s %8ld %8ld %9zu %9zu%s\n", row.name.c_str(), row.input.euler, row.output.euler,
            row.input.boundaryLoops, row.output.boundaryLoops, row.ok ? "" : "  FAIL");
    }
    return failures ? 1 : 0;
}
