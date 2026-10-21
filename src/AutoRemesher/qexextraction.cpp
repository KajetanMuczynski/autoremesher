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
#include <exception>
#include <qex.h>

namespace AutoRemesher {

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
    if (outPolygons->empty()) {
        *why = "QEx returned no faces";
        return false;
    }
    return true;
}

}
