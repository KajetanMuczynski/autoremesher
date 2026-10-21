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
#include <AutoRemesher/MapCheck>
#include <AutoRemesher/Predicates>
#include <AutoRemesher/SurfaceMesh>

#include <algorithm>
#include <cmath>
#include <deque>
#include <numeric>
#include <set>
#include <unordered_map>
#include <utility>

namespace AutoRemesher {

namespace {

    // x -> R^k x + t with R the quarter turn (x, y) -> (y, -x), the
    // transitions of the quad cover.
    struct GridMap {
        int k = 0;
        Vector2 t;

        static Vector2 turn(int k, const Vector2& x)
        {
            switch (((k % 4) + 4) % 4) {
            case 1:
                return Vector2(x.y(), -x.x());
            case 2:
                return Vector2(-x.x(), -x.y());
            case 3:
                return Vector2(-x.y(), x.x());
            default:
                return x;
            }
        }
        Vector2 operator()(const Vector2& x) const { return turn(k, x) + t; }
        // (this o other)(x) = this(other(x))
        GridMap after(const GridMap& other) const
        {
            GridMap result;
            result.k = (k + other.k) % 4;
            result.t = turn(k, other.t) + t;
            return result;
        }
        GridMap inverse() const
        {
            GridMap result;
            result.k = (4 - k % 4) % 4;
            result.t = turn(result.k, Vector2(-t.x(), -t.y()));
            return result;
        }
    };

    struct UnionFind {
        std::vector<size_t> parent;
        explicit UnionFind(size_t n)
            : parent(n)
        {
            std::iota(parent.begin(), parent.end(), 0);
        }
        size_t find(size_t x)
        {
            while (parent[x] != x)
                x = parent[x] = parent[parent[x]];
            return x;
        }
        bool unite(size_t a, size_t b)
        {
            a = find(a), b = find(b);
            if (a == b)
                return false;
            parent[a] = b;
            return true;
        }
    };

    double segmentDistance(const Vector2& p, const Vector2& a, const Vector2& b)
    {
        const Vector2 ab = b - a;
        const double length2 = ab.lengthSquared();
        double s = length2 > 0.0 ? ((p.x() - a.x()) * ab.x() + (p.y() - a.y()) * ab.y()) / length2 : 0.0;
        s = std::max(0.0, std::min(1.0, s));
        return (p - (a + s * ab)).length();
    }

    double triangleDistance(const Vector2& p, const Vector2& a, const Vector2& b, const Vector2& c)
    {
        const int s0 = Predicates::orient2d(a, b, p);
        const int s1 = Predicates::orient2d(b, c, p);
        const int s2 = Predicates::orient2d(c, a, p);
        if ((s0 >= 0 && s1 >= 0 && s2 >= 0) || (s0 <= 0 && s1 <= 0 && s2 <= 0))
            return 0.0;
        return std::min(segmentDistance(p, a, b), std::min(segmentDistance(p, b, c), segmentDistance(p, c, a)));
    }

    bool isInteger(double x)
    {
        return std::fabs(x - std::round(x)) < 1e-6;
    }

    // Faces that cannot be part of a valid map's neighbourhood search more
    // than this: a fold can make the unfolded charts overlap without end.
    const size_t maximumUnfoldedFaces = 512;
}

constexpr double MapCheck::searchRadius;

bool MapCheck::valid() const
{
    return 0 == flipped && 0 == degenerate && 0 == conesOffGrid && 0 == conePairsColliding
        && 0 == handleLoopsCollapsed && 0 == boundaryEdgesCollapsed && 0 == boundaryLoopsPinched;
}

MapCheck checkIntegerGridMap(const std::vector<Vector3>& vertices,
    const std::vector<std::vector<size_t>>& triangles,
    const std::vector<std::vector<Vector2>>& cornerUvs,
    const std::vector<int>& cornerRotations,
    const std::vector<size_t>& cones)
{
    MapCheck check;
    const SurfaceMesh mesh(vertices, triangles);
    const size_t faces = mesh.faceCount();
    if (faces != triangles.size() || cornerUvs.size() != faces || cornerRotations.size() != 3 * faces)
        return check;
    for (const auto& uvs : cornerUvs)
        if (uvs.size() != 3)
            return check;
    check.triangles = faces;
    const auto uv = [&](size_t corner) -> const Vector2& { return cornerUvs[corner / 3][corner % 3]; };

    // Transition across the edge of corner c, from the chart of the face
    // opposite to the chart of c's face: uv(c) = R^r uv(next(oc)) + t.
    std::vector<GridMap> transition(3 * faces);
    for (size_t c = 0; c < 3 * faces; ++c) {
        const size_t oc = mesh.oppositeCorner(c);
        if (oc == SurfaceMesh::npos)
            continue;
        GridMap& map = transition[c];
        map.k = ((cornerRotations[c] % 4) + 4) % 4;
        map.t = uv(c) - GridMap::turn(map.k, uv(mesh.nextCorner(oc)));
        const Vector2 other = map(uv(oc)) - uv(mesh.nextCorner(c));
        check.transitionResidual = std::max(check.transitionResidual,
            std::max(std::fabs(other.x()), std::fabs(other.y())));
    }

    std::vector<char> isCone(mesh.vertexCount(), 0);
    for (size_t v : cones)
        if (v < mesh.vertexCount())
            isCone[v] = 1;
    std::vector<char> isBoundary(mesh.vertexCount(), 0);
    for (size_t c = 0; c < 3 * faces; ++c)
        if (mesh.isBoundaryCorner(c)) {
            isBoundary[mesh.cornerVertex(c)] = 1;
            isBoundary[mesh.cornerVertex(mesh.nextCorner(c))] = 1;
        }

    // Orientation and the clusters of bad triangles.
    std::vector<char> bad(faces, 0);
    for (size_t f = 0; f < faces; ++f) {
        const int sign = Predicates::orient2d(uv(3 * f), uv(3 * f + 1), uv(3 * f + 2));
        if (sign < 0)
            ++check.flipped;
        else if (0 == sign)
            ++check.degenerate;
        bad[f] = sign <= 0;
    }
    {
        UnionFind clusters(faces);
        for (size_t v = 0; v < mesh.vertexCount(); ++v) {
            size_t first = SurfaceMesh::npos;
            for (size_t c : mesh.cornersAroundVertex(v)) {
                const size_t f = mesh.cornerFace(c);
                if (!bad[f])
                    continue;
                if (first == SurfaceMesh::npos)
                    first = f;
                else
                    clusters.unite(first, f);
            }
        }
        std::unordered_map<size_t, size_t> size;
        std::set<size_t> atCone, atBoundary;
        for (size_t f = 0; f < faces; ++f) {
            if (!bad[f])
                continue;
            const size_t root = clusters.find(f);
            ++size[root];
            for (size_t l = 0; l < 3; ++l) {
                const size_t v = mesh.cornerVertex(3 * f + l);
                if (isCone[v])
                    atCone.insert(root);
                if (isBoundary[v])
                    atBoundary.insert(root);
            }
        }
        check.badClusters = size.size();
        for (const auto& item : size)
            check.badClusterLargest = std::max(check.badClusterLargest, item.second);
        check.badClustersAtCones = atCone.size();
        check.badClustersAtBoundary = atBoundary.size();
    }

    // Unfolds the faces around corner `start` into its face's chart, as far
    // as `radius` from the corner, and calls visit(corner, unfolded uv) for
    // every corner of every face reached.
    std::vector<size_t> visitedAt(faces, SurfaceMesh::npos);
    std::vector<GridMap> unfolding(faces);
    size_t visitStamp = 0;
    const auto unfold = [&](size_t start, double radius, auto&& visit) {
        ++visitStamp;
        const Vector2 centre = uv(start);
        std::deque<size_t> queue;
        const size_t f0 = mesh.cornerFace(start);
        visitedAt[f0] = visitStamp;
        unfolding[f0] = GridMap();
        queue.push_back(f0);
        size_t reached = 0;
        while (!queue.empty() && reached < maximumUnfoldedFaces) {
            const size_t f = queue.front();
            queue.pop_front();
            ++reached;
            for (size_t l = 0; l < 3; ++l)
                visit(3 * f + l, unfolding[f](uv(3 * f + l)));
            for (size_t l = 0; l < 3; ++l) {
                const size_t c = 3 * f + l, oc = mesh.oppositeCorner(c);
                if (oc == SurfaceMesh::npos)
                    continue;
                const size_t g = mesh.cornerFace(oc);
                if (visitedAt[g] == visitStamp)
                    continue;
                const GridMap map = unfolding[f].after(transition[c]);
                if (triangleDistance(centre, map(uv(3 * g)), map(uv(3 * g + 1)), map(uv(3 * g + 2))) > radius)
                    continue;
                visitedAt[g] = visitStamp;
                unfolding[g] = map;
                queue.push_back(g);
            }
        }
    };

    // Cones: on the grid, in a fold, separated from each other.
    check.coneDistance = MapCheck::searchRadius;
    {
        std::set<std::pair<size_t, size_t>> colliding;
        for (size_t v = 0; v < mesh.vertexCount(); ++v) {
            if (!isCone[v] || mesh.cornersAroundVertex(v).empty())
                continue;
            ++check.cones;
            bool offGrid = false, inFold = false;
            for (size_t c : mesh.cornersAroundVertex(v)) {
                offGrid = offGrid || !isInteger(uv(c).x()) || !isInteger(uv(c).y());
                inFold = inFold || bad[mesh.cornerFace(c)];
            }
            check.conesOffGrid += offGrid;
            check.conesInFolds += inFold;
            const size_t start = mesh.cornersAroundVertex(v).front();
            const Vector2 centre = uv(start);
            unfold(start, MapCheck::searchRadius, [&](size_t corner, const Vector2& at) {
                const size_t w = mesh.cornerVertex(corner);
                if (w == v || !isCone[w])
                    return;
                const double distance = (at - centre).length();
                check.coneDistance = std::min(check.coneDistance, distance);
                if (distance < 0.5)
                    colliding.insert({ std::min(v, w), std::max(v, w) });
            });
        }
        check.conePairsColliding = colliding.size();
    }

    // Boundary loops, by their boundary corners.
    std::vector<std::vector<size_t>> loops;
    {
        std::unordered_map<size_t, size_t> outgoing;
        for (size_t c = 0; c < 3 * faces; ++c)
            if (mesh.isBoundaryCorner(c))
                outgoing.emplace(mesh.cornerVertex(c), c);
        std::vector<char> used(3 * faces, 0);
        for (size_t c = 0; c < 3 * faces; ++c) {
            if (!mesh.isBoundaryCorner(c) || used[c])
                continue;
            std::vector<size_t> loop;
            for (size_t at = c; !used[at];) {
                used[at] = 1;
                loop.push_back(at);
                const auto next = outgoing.find(mesh.cornerVertex(mesh.nextCorner(at)));
                if (next == outgoing.end())
                    break;
                at = next->second;
            }
            loops.push_back(std::move(loop));
        }
    }
    check.boundaryLoops = loops.size();
    check.boundaryWidth = MapCheck::searchRadius;
    {
        // Loop and arc length position of each boundary vertex.
        std::unordered_map<size_t, std::pair<size_t, double>> position;
        std::vector<double> perimeter(loops.size(), 0.0);
        for (size_t i = 0; i < loops.size(); ++i) {
            for (size_t c : loops[i]) {
                position.emplace(mesh.cornerVertex(c), std::make_pair(i, perimeter[i]));
                const double length = (uv(mesh.nextCorner(c)) - uv(c)).length();
                if (!(length > 0.0))
                    ++check.boundaryEdgesCollapsed;
                perimeter[i] += length;
            }
        }
        for (size_t i = 0; i < loops.size(); ++i) {
            bool pinched = false;
            for (size_t c : loops[i]) {
                const double s = position[mesh.cornerVertex(c)].second;
                const Vector2 centre = uv(c);
                unfold(c, MapCheck::searchRadius, [&](size_t corner, const Vector2& at) {
                    const auto found = position.find(mesh.cornerVertex(corner));
                    if (found == position.end() || found->second.first != i)
                        return;
                    const double along = std::fabs(found->second.second - s);
                    if (std::min(along, perimeter[i] - along) < 1.0)
                        return;
                    const double distance = (at - centre).length();
                    check.boundaryWidth = std::min(check.boundaryWidth, distance);
                    if (distance < 0.5)
                        pinched = true;
                });
            }
            check.boundaryLoopsPinched += pinched;
        }
    }

    // Handle loops: tree-cotree on the surface with each hole capped. The
    // dual tree spans the faces through interior edges and takes one edge of
    // each boundary loop for its cap, a leaf; the primal tree takes the other
    // boundary edges first. Every edge left is interior and closes one loop
    // of faces through real faces only.
    {
        std::unordered_map<size_t, size_t> edgeOf;
        std::vector<size_t> edgeCorner;
        for (size_t c = 0; c < 3 * faces; ++c) {
            const size_t oc = mesh.oppositeCorner(c);
            if (oc != SurfaceMesh::npos && oc < c)
                continue;
            edgeOf[c] = edgeCorner.size();
            if (oc != SurfaceMesh::npos)
                edgeOf[oc] = edgeCorner.size();
            edgeCorner.push_back(c);
        }
        std::vector<char> inDualTree(edgeCorner.size(), 0);
        std::vector<GridMap> toRoot(faces);
        std::vector<char> reached(faces, 0);
        std::vector<size_t> component(faces, 0);
        for (size_t root = 0; root < faces; ++root) {
            if (reached[root])
                continue;
            reached[root] = 1;
            component[root] = root;
            std::deque<size_t> queue { root };
            while (!queue.empty()) {
                const size_t f = queue.front();
                queue.pop_front();
                for (size_t l = 0; l < 3; ++l) {
                    const size_t c = 3 * f + l, oc = mesh.oppositeCorner(c);
                    if (oc == SurfaceMesh::npos)
                        continue;
                    const size_t g = mesh.cornerFace(oc);
                    if (reached[g])
                        continue;
                    reached[g] = 1;
                    component[g] = root;
                    inDualTree[edgeOf[c]] = 1;
                    // chart(g) -> chart(f) -> root chart
                    toRoot[g] = toRoot[f].after(transition[c]);
                    queue.push_back(g);
                }
            }
        }
        for (const auto& loop : loops)
            if (!loop.empty())
                inDualTree[edgeOf[loop.front()]] = 1;
        UnionFind primal(mesh.vertexCount());
        const auto join = [&](size_t edge) {
            const size_t c = edgeCorner[edge];
            return primal.unite(mesh.cornerVertex(c), mesh.cornerVertex(mesh.nextCorner(c)));
        };
        for (size_t edge = 0; edge < edgeCorner.size(); ++edge)
            if (!inDualTree[edge] && mesh.isBoundaryCorner(edgeCorner[edge]))
                join(edge);
        // Unrotated loop translations per component: they add up under
        // concatenation, so they span a lattice whose shortest vector is the
        // narrowest ring of quads around any combination of these handles,
        // whichever basis the trees picked.
        std::unordered_map<size_t, std::vector<Vector2>> translations;
        for (size_t edge = 0; edge < edgeCorner.size(); ++edge) {
            const size_t c = edgeCorner[edge];
            if (inDualTree[edge] || mesh.isBoundaryCorner(c) || join(edge))
                continue;
            ++check.handleLoops;
            // Root -> face of oc -> across -> face of c -> root.
            const size_t a = mesh.cornerFace(c), b = mesh.cornerFace(mesh.oppositeCorner(c));
            const GridMap holonomy = toRoot[a].after(transition[c]).after(toRoot[b].inverse());
            if (holonomy.k != 0)
                continue;
            ++check.handleLoopsUnrotated;
            translations[component[a]].push_back(holonomy.t);
        }
        const auto size = [](const Vector2& t) { return std::max(std::fabs(t.x()), std::fabs(t.y())); };
        for (const auto& item : translations) {
            const std::vector<Vector2>& vectors = item.second;
            double shortest = -1.0;
            bool collapsed = false;
            const auto consider = [&](const Vector2& t) {
                if (size(t) < 0.5) {
                    collapsed = true;
                    return;
                }
                if (shortest < 0.0 || size(t) < shortest)
                    shortest = size(t);
            };
            for (size_t i = 0; i < vectors.size(); ++i) {
                consider(vectors[i]);
                for (size_t j = i + 1; j < vectors.size(); ++j) {
                    // Lagrange-Gauss reduction of the pair.
                    Vector2 u = vectors[i], v = vectors[j];
                    if (u.lengthSquared() < v.lengthSquared())
                        std::swap(u, v);
                    for (size_t step = 0; step < 64 && v.lengthSquared() > 0.25; ++step) {
                        const double m = std::round((u.x() * v.x() + u.y() * v.y()) / v.lengthSquared());
                        u = u - m * v;
                        std::swap(u, v);
                        if (v.lengthSquared() >= u.lengthSquared())
                            break;
                    }
                    consider(u);
                    consider(v);
                }
            }
            if (collapsed)
                ++check.handleLoopsCollapsed;
            else if (shortest >= 0.0 && shortest < 2.5)
                ++check.handleLoopsThin;
            const double value = collapsed ? 0.0 : shortest;
            if (value >= 0.0 && (check.handleTranslation < 0.0 || value < check.handleTranslation))
                check.handleTranslation = value;
        }
    }
    return check;
}

void appendMapCheck(DiagnosticRecord* record, const MapCheck& check)
{
    record->set("map_triangles", (double)check.triangles);
    record->set("map_flipped", (double)check.flipped);
    record->set("map_degenerate", (double)check.degenerate);
    record->set("map_bad_clusters", (double)check.badClusters);
    record->set("map_bad_cluster_largest", (double)check.badClusterLargest);
    record->set("map_bad_clusters_at_cones", (double)check.badClustersAtCones);
    record->set("map_bad_clusters_at_boundary", (double)check.badClustersAtBoundary);
    record->set("map_cones", (double)check.cones);
    record->set("map_cones_off_grid", (double)check.conesOffGrid);
    record->set("map_cones_in_folds", (double)check.conesInFolds);
    record->set("map_cone_pairs_colliding", (double)check.conePairsColliding);
    record->set("map_cone_distance", check.coneDistance);
    record->set("map_handle_loops", (double)check.handleLoops);
    record->set("map_handle_loops_unrotated", (double)check.handleLoopsUnrotated);
    record->set("map_handle_loops_collapsed", (double)check.handleLoopsCollapsed);
    record->set("map_handle_loops_thin", (double)check.handleLoopsThin);
    record->set("map_handle_translation", check.handleTranslation);
    record->set("map_boundary_loops", (double)check.boundaryLoops);
    record->set("map_boundary_edges_collapsed", (double)check.boundaryEdgesCollapsed);
    record->set("map_boundary_loops_pinched", (double)check.boundaryLoopsPinched);
    record->set("map_boundary_width", check.boundaryWidth);
    record->set("map_transition_residual", check.transitionResidual);
    record->set("map_valid", check.valid() ? 1.0 : 0.0);
}

}
