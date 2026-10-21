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
#ifndef AUTO_REMESHER_PREDICATES_H
#define AUTO_REMESHER_PREDICATES_H

#include <AutoRemesher/Vector2>

namespace AutoRemesher {

// Exact geometric predicates on double coordinates, after Shewchuk's
// "Adaptive Precision Floating-Point Arithmetic and Fast Robust Geometric
// Predicates" (1997): a floating-point filter that settles almost every call,
// and an exact expansion-arithmetic fallback for the rest.  Exact as long as
// no intermediate product underflows, which needs coordinates far below the
// grid units these are used with.
namespace Predicates {

    // Sign of the doubled signed area of (a, b, c): +1 counter-clockwise,
    // -1 clockwise, 0 exactly collinear.
    int orient2d(const Vector2& a, const Vector2& b, const Vector2& c);

}

}

#endif
