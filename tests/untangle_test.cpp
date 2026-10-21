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

// Untangling of a map with some coordinates held (Untangler).
//
// A grid with its boundary held and interior vertices dragged across their
// neighbours must come out with every triangle positive, the same way on
// every run. A triangle that is inverted by its held coordinates alone
// cannot be fixed; the rest must still improve and the call must say that
// it did not succeed.

#include <AutoRemesher/Predicates>
#include <AutoRemesher/Untangler>
#include <array>
#include <cstdint>
#include <cstdio>
#include <vector>

namespace {

using AutoRemesher::Untangler;
using AutoRemesher::Vector2;

const size_t gridSize = 7;

size_t vertexIndex(size_t i, size_t j) { return j * gridSize + i; }

bool onBoundary(size_t i, size_t j) { return i == 0 || j == 0 || i + 1 == gridSize || j + 1 == gridSize; }

// Interior vertex k has variables 2k, 2k + 1, scaled by `coefficient` in
// its coordinates; boundary vertices are held at their grid positions.
struct Grid {
    std::vector<Vector2> rest;
    std::vector<size_t> variable;
    std::vector<std::array<size_t, 3>> triangles;
    size_t variableCount = 0;
};

Grid makeGrid()
{
    Grid grid;
    grid.variable.assign(gridSize * gridSize, SIZE_MAX);
    for (size_t j = 0; j < gridSize; ++j)
        for (size_t i = 0; i < gridSize; ++i) {
            grid.rest.push_back(Vector2((double)i, (double)j));
            if (!onBoundary(i, j)) {
                grid.variable[vertexIndex(i, j)] = grid.variableCount;
                grid.variableCount += 2;
            }
        }
    for (size_t j = 0; j + 1 < gridSize; ++j)
        for (size_t i = 0; i + 1 < gridSize; ++i) {
            const size_t a = vertexIndex(i, j), b = vertexIndex(i + 1, j), c = vertexIndex(i + 1, j + 1),
                         d = vertexIndex(i, j + 1);
            grid.triangles.push_back({ a, b, c });
            grid.triangles.push_back({ a, c, d });
        }
    return grid;
}

void addGrid(const Grid& grid, double coefficient, Untangler* untangler)
{
    for (const auto& t : grid.triangles) {
        std::array<Untangler::Coordinate, 6> corners;
        for (size_t k = 0; k < 3; ++k)
            for (size_t axis = 0; axis < 2; ++axis) {
                Untangler::Coordinate& coordinate = corners[2 * k + axis];
                if (grid.variable[t[k]] == SIZE_MAX)
                    coordinate.constant = grid.rest[t[k]][axis];
                else
                    coordinate.terms.push_back({ grid.variable[t[k]] + axis, coefficient });
            }
        untangler->addTriangle({ grid.rest[t[0]], grid.rest[t[1]], grid.rest[t[2]] }, 0.5, corners);
    }
}

// Interior vertices at rest, then two of them dragged far across others.
std::vector<double> tangledStart(const Grid& grid, double coefficient)
{
    std::vector<double> x(grid.variableCount);
    for (size_t v = 0; v < grid.rest.size(); ++v)
        if (grid.variable[v] != SIZE_MAX) {
            x[grid.variable[v]] = grid.rest[v].x() / coefficient;
            x[grid.variable[v] + 1] = grid.rest[v].y() / coefficient;
        }
    const size_t dragged[2] = { vertexIndex(2, 2), vertexIndex(4, 3) };
    const Vector2 to[2] = { Vector2(4.6, 3.8), Vector2(1.7, 4.4) };
    for (size_t k = 0; k < 2; ++k) {
        x[grid.variable[dragged[k]]] = to[k].x() / coefficient;
        x[grid.variable[dragged[k]] + 1] = to[k].y() / coefficient;
    }
    return x;
}

size_t invertedTriangles(const Grid& grid, const std::vector<double>& x, double coefficient)
{
    const auto position = [&](size_t v) {
        if (grid.variable[v] == SIZE_MAX)
            return grid.rest[v];
        return Vector2(coefficient * x[grid.variable[v]], coefficient * x[grid.variable[v] + 1]);
    };
    size_t inverted = 0;
    for (const auto& t : grid.triangles)
        if (AutoRemesher::Predicates::orient2d(position(t[0]), position(t[1]), position(t[2])) <= 0)
            ++inverted;
    return inverted;
}

bool untanglesGrid(const char* name, double coefficient)
{
    const Grid grid = makeGrid();
    Untangler untangler(grid.variableCount);
    addGrid(grid, coefficient, &untangler);
    std::vector<double> x = tangledStart(grid, coefficient);
    const size_t before = invertedTriangles(grid, x, coefficient);
    Untangler::Stats stats;
    const bool untangled = untangler.untangle(&x, &stats);
    const size_t after = invertedTriangles(grid, x, coefficient);

    // The same input gives the same output, bit for bit.
    Untangler again(grid.variableCount);
    addGrid(grid, coefficient, &again);
    std::vector<double> y = tangledStart(grid, coefficient);
    again.untangle(&y, nullptr);
    const bool repeatable = x == y;

    const bool ok = untangled && before >= 4 && 0 == after && 0 == stats.invertedAfter && stats.converged
        && repeatable;
    std::printf("%-26s inverted %zu -> %zu, %zu iterations, %zu Newton steps, repeatable %d%s\n", name, before,
        after, stats.iterations, stats.newtonSteps, repeatable ? 1 : 0, ok ? "" : "  FAIL");
    return ok;
}

// The grid plus one triangle inverted by held coordinates only.
bool reportsWhatCannotBeFixed()
{
    const Grid grid = makeGrid();
    Untangler untangler(grid.variableCount);
    addGrid(grid, 1.0, &untangler);
    std::array<Untangler::Coordinate, 6> held;
    const double corners[6] = { 10.0, 0.0, 10.0, 1.0, 11.0, 0.0 };
    for (size_t k = 0; k < 6; ++k)
        held[k].constant = corners[k];
    untangler.addTriangle({ Vector2(10.0, 0.0), Vector2(11.0, 0.0), Vector2(10.0, 1.0) }, 0.5, held);
    std::vector<double> x = tangledStart(grid, 1.0);
    const size_t before = invertedTriangles(grid, x, 1.0);
    Untangler::Stats stats;
    const bool untangled = untangler.untangle(&x, &stats);
    const size_t after = invertedTriangles(grid, x, 1.0);
    const bool ok = !untangled && stats.invertedBefore == before + 1 && stats.invertedAfter == after + 1
        && after < before;
    std::printf("%-26s inverted %zu -> %zu besides the held one, untangled %d%s\n", "held inverted triangle",
        before, after, untangled ? 1 : 0, ok ? "" : "  FAIL");
    return ok;
}

}

int main()
{
    std::printf("\n");
    int failures = 0;
    failures += untanglesGrid("folded grid", 1.0) ? 0 : 1;
    // Coordinates that are multiples of their variables, as kernel terms are.
    failures += untanglesGrid("folded grid, scaled terms", 2.5) ? 0 : 1;
    failures += reportsWhatCannotBeFixed() ? 0 : 1;
    return failures ? 1 : 0;
}
