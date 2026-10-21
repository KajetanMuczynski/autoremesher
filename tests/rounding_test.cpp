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

// Rounding of the quad cover's integers.
//
// Fixing integers holds variables of one factorised system
// (ConstrainedLeastSquares::fixVariables) instead of adding a constraint per
// integer and refactorising from scratch.  Held variables must give the same
// solution as the equivalent constraints, also when constraints tie them to
// other variables.
//
// Rounding is greedy: it fixes the integers closest to their lattice first
// and lets the others adapt before rounding them.  Rounding everything at once
// split strongly coupled integers that sat near half a period, each to its own
// side, which is what tore the map apart around cones.

#include <AutoRemesher/ConstrainedLeastSquares>
#include <AutoRemesher/MixedIntegerLeastSquares>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <utility>
#include <vector>

namespace {

using Terms = std::vector<std::pair<size_t, double>>;

// A chain x0 .. x5 that wants unit steps and stays near x0 = 0, with the
// constraint x4 = 2 x5, so x4 and x5 share one column of the reduced system.
void addChain(AutoRemesher::ConstrainedLeastSquares* system)
{
    for (size_t i = 0; i + 1 < 6; ++i)
        system->addEnergy({ { i + 1, 1.0 }, { i, -1.0 } }, 1.0, 1.0 + 0.5 * i);
    system->addEnergy({ { 0, 1.0 } }, 0.0, 0.1);
    system->addConstraint({ { 4, 1.0 }, { 5, -2.0 } });
}

double maximumDifference(const std::vector<double>& a, const std::vector<double>& b)
{
    if (a.size() != b.size())
        return 1e30;
    double difference = 0.0;
    for (size_t i = 0; i < a.size(); ++i)
        difference = std::max(difference, std::fabs(a[i] - b[i]));
    return difference;
}

// Held values against the same values as constraints on a fresh system.
bool heldMatchesConstrained(const char* name, const Terms& held)
{
    AutoRemesher::ConstrainedLeastSquares fixed(6), constrained(6);
    addChain(&fixed);
    addChain(&constrained);
    std::vector<double> before, withHeld, withConstraints;
    const bool first = fixed.solve(&before);
    fixed.fixVariables(held);
    const bool second = fixed.solve(&withHeld);
    for (const auto& h : held)
        constrained.addConstraint({ { h.first, 1.0 } }, h.second);
    const bool third = constrained.solve(&withConstraints);
    const double difference = maximumDifference(withHeld, withConstraints);
    bool atValue = true;
    for (const auto& h : held)
        atValue = atValue && withHeld.size() == 6 && withHeld[h.first] == h.second;
    // One numeric refactorisation for the held values, no new analysis.
    const bool refactorizedOnce = 2 == fixed.lastSolveStats().factorizations;
    const bool ok = first && second && third && difference < 1e-8 && atValue && refactorizedOnce;
    std::printf("%-26s difference %.2e, held exactly %d, factorisations %zu%s\n", name, difference,
        atValue ? 1 : 0, fixed.lastSolveStats().factorizations, ok ? "" : "  FAIL");
    return ok;
}

bool heldCases()
{
    bool ok = true;
    ok = heldMatchesConstrained("one variable", { { 1, 5.0 } }) && ok;
    ok = heldMatchesConstrained("two variables", { { 1, 5.0 }, { 3, -2.0 } }) && ok;
    // x4 = 2 x5: holding x4 holds the shared column, so x5 follows.
    ok = heldMatchesConstrained("tied variable", { { 4, 4.0 } }) && ok;
    ok = heldMatchesConstrained("tied pair, consistent", { { 4, 4.0 }, { 5, 2.0 } }) && ok;

    // Inconsistent with the constraint x4 = 2 x5: the solve must refuse.
    {
        AutoRemesher::ConstrainedLeastSquares system(6);
        addChain(&system);
        std::vector<double> solution;
        system.fixVariables({ { 4, 4.0 }, { 5, 3.0 } });
        const bool refused = !system.solve(&solution);
        std::printf("%-26s refused %d%s\n", "tied pair, inconsistent", refused ? 1 : 0, refused ? "" : "  FAIL");
        ok = refused && ok;
    }

    // Releasing every held variable gives back the free solution.
    {
        AutoRemesher::ConstrainedLeastSquares system(6);
        addChain(&system);
        std::vector<double> free, held, released;
        system.solve(&free);
        system.fixVariables({ { 2, 7.0 } });
        system.solve(&held);
        system.fixVariables({});
        const bool solved = system.solve(&released);
        const double difference = maximumDifference(free, released);
        const bool good = solved && difference < 1e-12 && std::fabs(held[2] - 7.0) == 0.0;
        std::printf("%-26s difference %.2e%s\n", "released", difference, good ? "" : "  FAIL");
        ok = good && ok;
    }
    return ok;
}

// Two integers near half a period with a stiff spring that wants them 0.12
// apart: the relaxation puts them at 0.40 and 0.52.  Rounding both at once
// sends them to 0 and 1 and stretches the spring by a whole period; greedy
// rounding fixes the closer one, lets the other follow and rounds both to 0.  A third,
// free integer shows that rounding finishes and every integer is integral.
bool greedyKeepsCoupledIntegersTogether()
{
    // Energies go in before finalizeConstraints(), which reduces them onto
    // the kernel.
    AutoRemesher::MixedIntegerLeastSquares t(3);
    for (size_t i = 0; i < 3; ++i)
        t.setVariablePeriod(i, 1);
    t.addEnergy({ { 0, 1.0 } }, 0.40, 1.0);
    t.addEnergy({ { 1, 1.0 } }, 0.52, 1.0);
    t.addEnergy({ { 1, 1.0 }, { 0, -1.0 } }, 0.12, 1000.0);
    t.addEnergy({ { 2, 1.0 } }, 2.3, 1.0);
    t.finalizeConstraints();

    size_t passes = 0;
    bool solved = true;
    while (solved && !t.converged() && passes < 10) {
        solved = t.solveIteration();
        ++passes;
    }
    const double x0 = t.value(0), x1 = t.value(1), x2 = t.value(2);
    const bool ok = solved && t.converged() && x0 == x1 && 0.0 == x0 && 2.0 == x2
        && t.integralityResidual() == 0.0;
    std::printf("%-26s x = (%g, %g, %g) after %zu passes, integrality residual %g%s\n",
        "coupled integers", x0, x1, x2, passes, t.integralityResidual(), ok ? "" : "  FAIL");
    return ok;
}

}

int main()
{
    std::printf("\n");
    int failures = 0;
    failures += heldCases() ? 0 : 1;
    failures += greedyKeepsCoupledIntegersTogether() ? 0 : 1;
    return failures ? 1 : 0;
}
