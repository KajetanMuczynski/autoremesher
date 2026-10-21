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
#ifndef AUTO_REMESHER_SURFACE_PROJECTOR_H
#define AUTO_REMESHER_SURFACE_PROJECTOR_H

#include <AutoRemesher/Vector3>
#include <cstddef>
#include <memory>
#include <vector>

class AxisAlignedBoudingBox;
class AxisAlignedBoudingBoxTree;

namespace AutoRemesher {

Vector3 closestPointOnTriangle(const Vector3& p, const Vector3& a, const Vector3& b, const Vector3& c);
Vector3 closestPointOnSegment(const Vector3& p, const Vector3& a, const Vector3& b);

// Moves the vertices of a polygon mesh onto a triangle surface (TODO 2.8).
//
// The extractor leaves the output on the isotropic remesh T, whose faces are
// chords of the input M, so the output sits inside convex parts of M by up to
// T's sagitta. Each vertex goes to its closest point on M; a vertex on an
// output boundary goes to the closest input boundary edge instead, so open
// borders stay on the border.
//
// A move is kept only if it is safe:
// - the closest point is searched among faces of M facing the same way as the
//   vertex, so a vertex on a thin part cannot land on the opposite sheet;
// - it is no longer than half the mean output edge (the gap is a fraction of
//   T's edge, so a longer move means the vertex was matched to something else);
// - no face around it turns by more than 60 degrees, comes to face away from
//   the input face one of its vertices lands on (having faced that way before),
//   or drops in scaled Jacobian below min(0.1, its value before), so
//   projection adds no folded or flipped faces. Of a face made worse only the
//   longest move is undone, and the faces around it are checked again;
//   rejected vertices keep their position.
// Only vertex positions change, never the connectivity, so the output's
// topology is the extractor's.
class SurfaceProjector {
public:
    // `triangles` index `vertices`; they may be a subset of a larger mesh (one
    // island of the input). Both must outlive the projector.
    SurfaceProjector(const std::vector<Vector3>* vertices,
        const std::vector<std::vector<size_t>>* triangles);
    ~SurfaceProjector();

    struct Result {
        size_t vertices = 0;
        size_t projected = 0;
        // Not moved: no facing input face (or boundary edge) within reach.
        size_t keptUnmatched = 0;
        // Not moved: the move was longer than half the mean edge.
        size_t keptFar = 0;
        // Not moved: moving would fold or turn a face around it.
        size_t keptFolding = 0;
        // Mean and largest move of the projected vertices, in mean edges.
        double meanMove = 0.0;
        double maxMove = 0.0;
    };

    Result project(std::vector<Vector3>* points, const std::vector<std::vector<size_t>>& faces) const;

private:
    bool closestFacingPoint(const Vector3& position, const Vector3& normal, double maxDistance,
        Vector3* closest, Vector3* closestNormal) const;
    bool closestBoundaryPoint(const Vector3& position, double maxDistance, Vector3* closest) const;

    const std::vector<Vector3>* m_vertices = nullptr;
    const std::vector<std::vector<size_t>>* m_triangles = nullptr;
    std::vector<Vector3> m_triangleNormals;
    std::unique_ptr<std::vector<AxisAlignedBoudingBox>> m_triangleBoxes;
    std::unique_ptr<AxisAlignedBoudingBoxTree> m_triangleTree;
    std::vector<std::pair<size_t, size_t>> m_boundaryEdges;
    std::unique_ptr<std::vector<AxisAlignedBoudingBox>> m_boundaryBoxes;
    std::unique_ptr<AxisAlignedBoudingBoxTree> m_boundaryTree;
};

}

#endif
