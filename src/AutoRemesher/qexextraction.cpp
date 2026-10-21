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
#include "qexextraction.h"
#include <algorithm>
#include <exception>
#include <map>
#include <qex.h>
#include <string>
#include <utility>

namespace AutoRemesher {

namespace {

    // Faces on an edge more than two faces use, or on a directed edge another
    // face uses too (sheets of a fold touching along an edge): QuadExtractor's
    // repair keys faces by directed edge and misses both, so they are dropped
    // and the hole filling sees an ordinary hole.  Returns how many.
    size_t dropUnrepairableFaces(std::vector<std::vector<size_t>>* polygons)
    {
        std::map<std::pair<size_t, size_t>, size_t> undirected, directed;
        for (const auto& face : *polygons) {
            for (size_t i = 0; i < face.size(); ++i) {
                const size_t a = face[i], b = face[(i + 1) % face.size()];
                ++undirected[std::make_pair(std::min(a, b), std::max(a, b))];
                ++directed[std::make_pair(a, b)];
            }
        }
        std::vector<std::vector<size_t>> kept;
        kept.reserve(polygons->size());
        for (auto& face : *polygons) {
            bool drop = false;
            for (size_t i = 0; i < face.size() && !drop; ++i) {
                const size_t a = face[i], b = face[(i + 1) % face.size()];
                drop = undirected[std::make_pair(std::min(a, b), std::max(a, b))] > 2
                    || directed[std::make_pair(a, b)] > 1;
            }
            if (!drop)
                kept.push_back(std::move(face));
        }
        const size_t dropped = polygons->size() - kept.size();
        *polygons = std::move(kept);
        return dropped;
    }

    // Twice the number of handles of a surface, 2C - chi - B summed over its C
    // components with B boundary loops; a hole cut or filled leaves it as it is.
    // Loops are counted as components of the boundary-edge graph.
    template <class Faces>
    long long twiceHandleCount(size_t vertexCount, const Faces& faces)
    {
        std::vector<size_t> surface(vertexCount), boundary(vertexCount);
        for (size_t v = 0; v < vertexCount; ++v)
            surface[v] = boundary[v] = v;
        const auto find = [](std::vector<size_t>& parent, size_t v) {
            while (parent[v] != v)
                v = parent[v] = parent[parent[v]];
            return v;
        };
        std::map<std::pair<size_t, size_t>, size_t> edges;
        std::vector<char> used(vertexCount, 0);
        for (const auto& face : faces) {
            for (size_t i = 0; i < face.size(); ++i) {
                const size_t a = face[i], b = face[(i + 1) % face.size()];
                used[a] = 1;
                surface[find(surface, a)] = find(surface, b);
                ++edges[std::make_pair(std::min(a, b), std::max(a, b))];
            }
        }
        std::vector<char> onBoundary(vertexCount, 0);
        for (const auto& edge : edges) {
            if (1 != edge.second)
                continue;
            onBoundary[edge.first.first] = onBoundary[edge.first.second] = 1;
            boundary[find(boundary, edge.first.first)] = find(boundary, edge.first.second);
        }
        long long components = 0, loops = 0, vertices = 0;
        for (size_t v = 0; v < vertexCount; ++v) {
            if (!used[v])
                continue;
            ++vertices;
            components += find(surface, v) == v;
            loops += onBoundary[v] && find(boundary, v) == v;
        }
        const long long euler = vertices - (long long)edges.size() + (long long)faces.size();
        return 2 * components - euler - loops;
    }

}

bool extractWithQex(const std::vector<Vector3>& vertices,
    const std::vector<std::vector<size_t>>& triangles,
    const std::vector<std::vector<Vector2>>& triangleUvs,
    const QexLimits& limits,
    std::vector<Vector3>* outVertices,
    std::vector<std::vector<size_t>>* outPolygons,
    QexOutcome* outcome)
{
    *outcome = QexOutcome();
    outcome->attempted = true;
    outVertices->clear();
    outPolygons->clear();
    if (triangleUvs.size() != triangles.size()) {
        outcome->reason = "uv count differs from triangle count";
        return false;
    }
    QEx::TriMesh mesh;
    mesh.reserve(vertices.size(), vertices.size() + triangles.size(), triangles.size());
    for (const auto& v : vertices)
        mesh.add_vertex(QEx::TriMesh::Point(v.x(), v.y(), v.z()));
    std::vector<QEx::TriMesh::FaceHandle> faces;
    faces.reserve(triangles.size());
    for (size_t t = 0; t < triangles.size(); ++t) {
        const auto& tri = triangles[t];
        if (tri.size() != 3 || triangleUvs[t].size() != 3) {
            outcome->reason = "a face is not a triangle";
            return false;
        }
        const auto fh = mesh.add_face(mesh.vertex_handle((int)tri[0]),
            mesh.vertex_handle((int)tri[1]), mesh.vertex_handle((int)tri[2]));
        if (!fh.is_valid()) {
            outcome->reason = "OpenMesh rejected a triangle (non-manifold input)";
            return false;
        }
        faces.push_back(fh);
    }
    // QEx takes one uv per halfedge: the uv of its to-vertex in its face.
    std::vector<OpenMesh::Vec2d> uvs(mesh.n_halfedges(), OpenMesh::Vec2d(0, 0));
    for (size_t t = 0; t < faces.size(); ++t) {
        for (auto h = mesh.fh_iter(faces[t]); h.is_valid(); ++h) {
            const size_t to = (size_t)mesh.to_vertex_handle(*h).idx();
            for (size_t k = 0; k < 3; ++k) {
                if (triangles[t][k] == to)
                    uvs[h->idx()] = OpenMesh::Vec2d(triangleUvs[t][k].x(), triangleUvs[t][k].y());
            }
        }
    }
    QEx::QuadMesh quadMesh;
    try {
        outcome->steps = QEx::extractQuadMeshOMLimited(&mesh, &uvs, nullptr, &quadMesh,
            (unsigned long)limits.maxSteps, (unsigned long)limits.maxGridVertices);
    } catch (const std::exception& e) {
        outcome->reason = e.what();
        return false;
    }
    outVertices->reserve(quadMesh.n_vertices());
    for (auto v = quadMesh.vertices_begin(); v != quadMesh.vertices_end(); ++v) {
        const auto& p = quadMesh.point(*v);
        outVertices->emplace_back(p[0], p[1], p[2]);
    }
    outPolygons->reserve(quadMesh.n_faces());
    for (auto f = quadMesh.faces_begin(); f != quadMesh.faces_end(); ++f) {
        std::vector<size_t> polygon;
        for (auto v = quadMesh.cfv_iter(*f); v.is_valid(); ++v)
            polygon.push_back((size_t)v->idx());
        if (polygon.size() >= 3)
            outPolygons->push_back(std::move(polygon));
    }
    outcome->droppedFaces = dropUnrepairableFaces(outPolygons);
    if (outPolygons->empty()) {
        outcome->reason = "QEx returned no faces";
        return false;
    }
    // libQEx keeps the map's topology only where the map is valid; across a
    // fold it can join two sheets into a handle that our tracer, on the same
    // map, does not make (suzanne_sub2 Quality 5000: 6 of 6 replicates).
    const long long handlesIn = twiceHandleCount(vertices.size(), triangles);
    const long long handlesOut = twiceHandleCount(outVertices->size(), *outPolygons);
    if (handlesOut > handlesIn) {
        outcome->reason = "QEx added a handle (2g " + std::to_string(handlesIn) + " -> "
            + std::to_string(handlesOut) + ")";
        return false;
    }
    outcome->faces = outPolygons->size();
    for (const auto& face : *outPolygons)
        outcome->nonQuads += face.size() != 4;
    return true;
}

}
