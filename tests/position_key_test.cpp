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

// PositionKey welds the quad extractor's crossing points: points in the same
// 1e-5 cell share a key, points further apart must not.  The key held the
// scaled coordinates in a long, which is 32 bits under MSVC, so beyond about
// 21,475 units every coordinate wrapped and far points merged into one.  The
// cases below sit beyond that range and beyond the range of a 64-bit integer,
// so they fail on the old key on every platform, not only on Windows.

#include <AutoRemesher/PositionKey>
#include <cstdio>
#include <map>

namespace {

using AutoRemesher::PositionKey;

bool sameKey(const PositionKey& a, const PositionKey& b)
{
    return a == b && !(a < b) && !(b < a);
}

bool distinctKey(const PositionKey& a, const PositionKey& b)
{
    return !(a == b) && ((a < b) != (b < a));
}

bool check(const char* name, bool ok)
{
    std::printf("%s %s\n", ok ? "ok  " : "FAIL", name);
    return ok;
}

// Points one unit apart on three axis-parallel lines near a centre: a map
// keyed by PositionKey must keep every one of them.
bool keepsAllPoints(const char* name, double centre)
{
    std::map<PositionKey, int> points;
    int count = 0;
    for (int i = -2; i <= 2; ++i) {
        points.insert({ PositionKey(centre + i, centre, centre), count++ });
        points.insert({ PositionKey(centre, centre + i, -centre), count++ });
        points.insert({ PositionKey(-centre, -centre, centre + i), count++ });
    }
    // The three lines do not meet, so all 15 points are distinct.
    const bool ok = points.size() == (size_t)count;
    if (!ok)
        std::printf("     %s: %d points, %zu keys\n", name, count, points.size());
    return check(name, ok);
}

}

int main()
{
    int failures = 0;

    // Unit-scale behaviour the extractor relies on: same cell welds, the
    // next cell does not.
    failures += check("same cell welds", sameKey(PositionKey(0.1234561, 2.0, -3.0), PositionKey(0.1234569, 2.0, -3.0))) ? 0 : 1;
    failures += check("next cell stays apart", distinctKey(PositionKey(0.12345, 2.0, -3.0), PositionKey(0.12346, 2.0, -3.0))) ? 0 : 1;
    failures += check("order is by x, then y, then z", PositionKey(0.0, 5.0, 5.0) < PositionKey(1.0, 0.0, 0.0) && PositionKey(1.0, 0.0, 5.0) < PositionKey(1.0, 1.0, 0.0) && PositionKey(1.0, 1.0, 0.0) < PositionKey(1.0, 1.0, 1.0)) ? 0 : 1;

    // Beyond the 32-bit range (MSVC long): about +-21,475 units.
    failures += check("30,000 units: 1 mm apart stays apart", distinctKey(PositionKey(30000.0, 0.0, 0.0), PositionKey(30000.001, 0.0, 0.0))) ? 0 : 1;
    failures += check("-30,000 and 30,000 stay apart", distinctKey(PositionKey(-30000.0, 0.0, 0.0), PositionKey(30000.0, 0.0, 0.0))) ? 0 : 1;
    failures += keepsAllPoints("1e5 centre keeps every point", 1e5) ? 0 : 1;

    // Beyond the 64-bit range: 1e5 * 1e14 exceeds 2^63.
    failures += check("1e14 units: 1 unit apart stays apart", distinctKey(PositionKey(1e14, 0.0, 0.0), PositionKey(1e14 + 1.0, 0.0, 0.0))) ? 0 : 1;
    failures += keepsAllPoints("1e14 centre keeps every point", 1e14) ? 0 : 1;

    return failures ? 1 : 0;
}
