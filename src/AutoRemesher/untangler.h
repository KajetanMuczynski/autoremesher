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
#ifndef AUTO_REMESHER_UNTANGLER_H
#define AUTO_REMESHER_UNTANGLER_H

#include <AutoRemesher/Vector2>
#include <array>
#include <cstddef>
#include <utility>
#include <vector>

namespace AutoRemesher {

// Moves a map of triangles into the plane until none is inverted, by
// minimising the foldover-free energy of Garanzha, Kaporin, Kudryavtseva,
// Protais, Ray and Sokolov, "Foldover-free maps in 50 lines of code"
// (SIGGRAPH 2021), re-implemented from the paper:
//
//   F(x, eps) = sum_t w_t (tr(J^T J) + lambda (det^2 J + 1)) / chi(det J, eps),
//   chi(D, eps) = (D + sqrt(eps^2 + D^2)) / 2,
//
// with J the Jacobian of triangle t from its target triangle to the map.
// chi is positive for every D, so F is finite on a tangled map; as eps goes
// to zero, chi(D, eps) tends to D for D > 0 and to 0 for D < 0, so F becomes
// a barrier against inversion. After each minimisation eps shrinks as fast
// as the energy decrease allows (the paper's update, rule (6)). Each
// minimisation takes Newton steps on the Hessian with every triangle's part
// projected onto the positive semidefinite cone, and a backtracking line
// search.
//
// The paper's energy depends on J only through tr(J^T J) and det J, so it
// lets a map rotate freely away from its targets; Options::alignment adds
// alignment * |J - I|^2, which a quad cover needs to keep its isolines
// along the cross field.
//
// The corner coordinates are affine in the variables, so the map can be any
// linear parameterisation with some of its coordinates held: the quad
// cover's kernel with its integers fixed, for one. With coordinates held an
// inversion-free map need not exist. untangle() then keeps the map with the
// fewest inverted triangles, stops once that has not improved for ten
// updates of eps or at its cap, and reports what is left inverted.
class Untangler {
public:
    // constant + sum of coefficient * x[variable] over terms.
    struct Coordinate {
        double constant = 0.0;
        std::vector<std::pair<size_t, double>> terms;
    };

    struct Options {
        // Weight of the area term against the shape term; 1 balances them.
        double lambda = 1.0;
        // Weight of |J - I|^2; 0 is the paper's energy.
        double alignment = 0.0;
        // Updates of eps, each after one minimisation.
        size_t maximumIterations = 60;
        size_t newtonStepsPerIteration = 4;
    };

    struct Stats {
        size_t triangles = 0;
        size_t variables = 0;
        // Triangles with det J <= 0.
        size_t invertedBefore = 0;
        size_t invertedAfter = 0;
        double minimumDeterminantBefore = 0.0;
        double minimumDeterminantAfter = 0.0;
        size_t iterations = 0;
        size_t newtonSteps = 0;
        size_t factorizations = 0;
        // No triangle inverted and the energy no longer decreasing.
        bool converged = false;
        double seconds = 0.0;
    };

    explicit Untangler(size_t variableCount);
    Untangler(size_t variableCount, const Options& options);

    // `target` must be positively oriented; triangles with a degenerate
    // target are ignored. `corners` holds u, v of corner 0, then of corner 1
    // and 2. `weight` scales the triangle's energy, usually its target area.
    void addTriangle(const std::array<Vector2, 3>& target, double weight,
        const std::array<Coordinate, 6>& corners);

    // Starts from `x` and overwrites it. Returns true if no triangle is left
    // inverted.
    bool untangle(std::vector<double>* x, Stats* stats);

private:
    struct Triangle {
        // J = constant + sum_k gradient.col(k) * x[variables[k]], J stored
        // row-major as J00, J01, J10, J11.
        double constant[4];
        size_t firstVariable;
        size_t variableCount;
        double weight;
    };

    void jacobian(const Triangle& triangle, const std::vector<double>& x, double* j) const;
    double energy(const std::vector<double>& x, double eps, double* minimumDeterminant,
        size_t* inverted) const;

    size_t m_variableCount;
    Options m_options;
    std::vector<Triangle> m_triangles;
    // Per triangle, its variables and the 4 x variableCount column-major
    // derivative of J by them.
    std::vector<size_t> m_variables;
    std::vector<double> m_gradients;
};

}

#endif
