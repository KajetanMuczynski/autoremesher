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

// Target Quads has a ceiling (gap scan item 5): a stray extra zero or two
// asked for millions of quads, about 22 KB of memory each, and the machine ran
// out of memory instead of the remesh failing with a message.

#include <AutoRemesher/Remesh>
#include <cstdio>

int main()
{
    AutoRemesher::RemeshRequest request;
    request.positions = { 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1 };
    request.triangles = { 0, 2, 1, 0, 1, 3, 0, 3, 2, 1, 2, 3 };
    request.parameters.targetQuadCount = AutoRemesher::MaximumTargetQuadCount + 1;
    const AutoRemesher::RemeshResult result = AutoRemesher::remesh(request, {});
    const bool ok = AutoRemesher::RemeshStatus::InvalidInput == result.status
        && result.message.find("maximum") != std::string::npos;
    printf("target %u: %s: %s%s\n", request.parameters.targetQuadCount,
        AutoRemesher::toString(result.status), result.message.c_str(), ok ? "" : "  FAIL");
    return ok ? 0 : 1;
}
