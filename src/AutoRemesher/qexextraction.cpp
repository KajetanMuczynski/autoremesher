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
#include "qexextraction.h"
#include <algorithm>
#include <cmath>
#include <exception>
#include <map>
#include <qex.h>
#include <utility>

namespace AutoRemesher {

namespace {

    double distanceToSegment(const Vector3& p, const Vector3& a, const Vector3& b)
    {
        const Vector3 ab = b - a;
        const double length2 = Vector3::dotProduct(ab, ab);
        double t = length2 > 0 ? Vector3::dotProduct(p - a, ab) / length2 : 0.0;
        t = std::max(0.0, std::min(1.0, t));
        return (p - (a + ab * t)).length();
    }

    // Two kinds of QEx faces QuadExtractor's repair can't take, dropped so
    // that the hole filling sees an ordinary hole:
    // - faces on an edge more than two faces use, or on a directed edge
    //   another face uses too (sheets of a fold touching along an edge);
    //   the repair keys faces by directed edge and misses both;
    // - an n-gon all of whose vertices lie on the triangle mesh's boundary:
    //   QEx closes each boundary loop with such a face.
    void dropUnrepairableFaces(const QEx::TriMesh& mesh, const std::vector<Vector3>& vertices,
        std::vector<std::vector<size_t>>* polygons)
    {
        std::map<std::pair<size_t, size_t>, size_t> undirected, directed;
        for (const auto& face : *polygons) {
            for (size_t i = 0; i < face.size(); ++i) {
                const size_t a = face[i], b = face[(i + 1) % face.size()];
                ++undirected[std::make_pair(std::min(a, b), std::max(a, b))];
                ++directed[std::make_pair(a, b)];
            }
        }
        std::vector<std::pair<Vector3, Vector3>> boundary;
        double diagonal2 = 0.0;
        {
            Vector3 low = vertices.empty() ? Vector3() : vertices.front(), high = low;
            for (const auto& v : vertices) {
                low = Vector3(std::min(low.x(), v.x()), std::min(low.y(), v.y()), std::min(low.z(), v.z()));
                high = Vector3(std::max(high.x(), v.x()), std::max(high.y(), v.y()), std::max(high.z(), v.z()));
            }
            diagonal2 = (high - low).lengthSquared();
        }
        for (auto e = mesh.edges_begin(); e != mesh.edges_end(); ++e) {
            if (!mesh.is_boundary(*e))
                continue;
            const auto h = mesh.halfedge_handle(*e, 0);
            const auto& a = mesh.point(mesh.from_vertex_handle(h));
            const auto& b = mesh.point(mesh.to_vertex_handle(h));
            boundary.emplace_back(Vector3(a[0], a[1], a[2]), Vector3(b[0], b[1], b[2]));
        }
        const double tolerance = 1e-9 * std::sqrt(diagonal2);
        const auto onBoundary = [&](const Vector3& p) {
            for (const auto& segment : boundary) {
                if (distanceToSegment(p, segment.first, segment.second) <= tolerance)
                    return true;
            }
            return false;
        };
        std::vector<std::vector<size_t>> kept;
        kept.reserve(polygons->size());
        for (auto& face : *polygons) {
            bool drop = false;
            for (size_t i = 0; i < face.size() && !drop; ++i) {
                const size_t a = face[i], b = face[(i + 1) % face.size()];
                drop = undirected[std::make_pair(std::min(a, b), std::max(a, b))] > 2
                    || directed[std::make_pair(a, b)] > 1;
            }
            if (!drop && face.size() > 4 && !boundary.empty()) {
                drop = true;
                for (size_t v : face) {
                    if (!onBoundary(vertices[v])) {
                        drop = false;
                        break;
                    }
                }
            }
            if (!drop)
                kept.push_back(std::move(face));
        }
        *polygons = std::move(kept);
    }

}

bool extractWithQex(const std::vector<Vector3>& vertices,
    const std::vector<std::vector<size_t>>& triangles,
    const std::vector<std::vector<Vector2>>& triangleUvs,
    std::vector<Vector3>* outVertices,
    std::vector<std::vector<size_t>>* outPolygons,
    std::string* why)
{
    outVertices->clear();
    outPolygons->clear();
    if (triangleUvs.size() != triangles.size()) {
        *why = "uv count differs from triangle count";
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
            *why = "a face is not a triangle";
            return false;
        }
        const auto fh = mesh.add_face(mesh.vertex_handle((int)tri[0]),
            mesh.vertex_handle((int)tri[1]), mesh.vertex_handle((int)tri[2]));
        if (!fh.is_valid()) {
            *why = "OpenMesh rejected triangle " + std::to_string(t) + " (non-manifold)";
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
        QEx::extractQuadMeshOM(&mesh, &uvs, nullptr, &quadMesh);
    } catch (const std::exception& e) {
        *why = std::string("QEx threw: ") + e.what();
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
    dropUnrepairableFaces(mesh, *outVertices, outPolygons);
    if (outPolygons->empty()) {
        *why = "QEx returned no faces";
        return false;
    }
    return true;
}

}
