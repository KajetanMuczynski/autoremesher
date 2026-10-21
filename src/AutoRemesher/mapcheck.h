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
#ifndef AUTO_REMESHER_MAP_CHECK_H
#define AUTO_REMESHER_MAP_CHECK_H

#include <AutoRemesher/Diagnostics>
#include <AutoRemesher/Vector2>
#include <AutoRemesher/Vector3>
#include <cstddef>
#include <vector>

namespace AutoRemesher {

// Validity of the integer-grid map that quad extraction gets, checked against
// the conditions under which the papers guarantee a valid quad mesh, read
// from the papers (no code taken):
//
//   - every triangle positively oriented (Bommes et al., "Integer-grid maps
//     for reliable quad meshing", SIGGRAPH 2013; Campen, Bommes, Kobbelt,
//     "Quantized global parametrization", SIGGRAPH Asia 2015, Stage I);
//   - cones on grid points and no two critical points on the same one, and
//     boundary loops that keep their width (Lyon, Campen, Bommes, Kobbelt,
//     "Parametrization quantization with free boundaries for trimmed quad
//     meshing", SIGGRAPH 2019, section 5.2: a quantization is valid if it
//     separates all critical entities);
//   - no handle collapsed: a loop around a handle whose transition is the
//     identity cannot have zero translation in a valid map, since the
//     pulled-back grid then has no cell around it.
//
// It only measures; nothing feeds back into the map. Thresholds are in grid
// units, where one unit is one quad edge.
struct MapCheck {
    size_t triangles = 0;
    // Exact orient2d in each triangle's chart.
    size_t flipped = 0;
    size_t degenerate = 0;
    // Flipped or degenerate triangles that share a vertex form one cluster.
    size_t badClusters = 0;
    size_t badClusterLargest = 0;
    size_t badClustersAtCones = 0;
    size_t badClustersAtBoundary = 0;
    // Interior vertices whose field turns are not a multiple of four.
    size_t cones = 0;
    // Cone with a corner off the integer grid (snap kept it unsnapped).
    size_t conesOffGrid = 0;
    // Cone with a flipped or degenerate triangle in its star.
    size_t conesInFolds = 0;
    // Pairs of cones closer than half a quad edge in the unfolded map.
    size_t conePairsColliding = 0;
    // Smallest unfolded distance between two cones, searched up to
    // `searchRadius`, which it is when no pair is closer.
    double coneDistance = 0.0;
    // Tree-cotree loops of the surface with its holes capped: 2 x genus.
    size_t handleLoops = 0;
    // Loops whose transition has no rotation; only their translation is a
    // property of the loop's homotopy class.
    size_t handleLoopsUnrotated = 0;
    // Translations of the unrotated loops of one component add up under
    // concatenation and span a lattice. Components whose lattice has a
    // zero vector (a loop, or a combination of loops, with zero
    // translation): collapsed handles.
    size_t handleLoopsCollapsed = 0;
    // Components whose shortest lattice vector is at most one seam period
    // (two grid units): a ring of at most two quads.
    size_t handleLoopsThin = 0;
    // Shortest lattice vector (max norm) over components; -1 without
    // unrotated loops.
    double handleTranslation = -1.0;
    size_t boundaryLoops = 0;
    // Boundary edges of zero length in the map.
    size_t boundaryEdgesCollapsed = 0;
    // Boundary loops where two of their points, at least one quad edge apart
    // along the loop, are closer than half a quad edge in the unfolded map:
    // the hole has lost its width there.
    size_t boundaryLoopsPinched = 0;
    // Smallest such distance over all loops, searched up to `searchRadius`.
    double boundaryWidth = 0.0;
    // Largest disagreement between the two ends of a shared edge after the
    // transition across it: how far the corners are from one seamless map.
    double transitionResidual = 0.0;

    // Any of the conditions above violated.
    bool valid() const;

    static constexpr double searchRadius = 1.5;
};

// `cornerUvs[f][l]` is the map at corner l of triangle f, `cornerRotations`
// the quarter turns of the transition across each corner's edge (corner
// 3f + l, edge from corner l to corner l + 1, as the quad cover numbers
// them), `cones` the interior singular vertices.
MapCheck checkIntegerGridMap(const std::vector<Vector3>& vertices,
    const std::vector<std::vector<size_t>>& triangles,
    const std::vector<std::vector<Vector2>>& cornerUvs,
    const std::vector<int>& cornerRotations,
    const std::vector<size_t>& cones);

// Appends the check as `map_*` keys.
void appendMapCheck(DiagnosticRecord* record, const MapCheck& check);

}

#endif
