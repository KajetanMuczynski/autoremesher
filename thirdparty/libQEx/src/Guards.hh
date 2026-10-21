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
// Termination and memory guards added to libQEx by the Quadami fork
// (TODO 6.1b; thirdparty/libQEx/PATCHES.md). On a folded map libQEx can
// build halfedge connectivity on which OpenMesh's circulators never end,
// trace for minutes, or grow without bound. Every guard throws QEx::Abort,
// and the caller falls back to its own extractor.
#ifndef QEX_GUARDS_HH
#define QEX_GUARDS_HH

#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

// libQEx's diagnostics go nowhere in the fork: on folded maps they flooded
// stderr with millions of lines (minutes of I/O, logs of gigabytes). The
// arguments are not evaluated.
#define QEX_LOG while (false) std::cerr

namespace QEx {

struct Abort : std::runtime_error {
    explicit Abort(const std::string& what) : std::runtime_error("QEx: " + what) {}
};

// Deterministic limits, set by the caller; 0 means no limit.
struct Limits {
    size_t max_steps = 0;          // tracing steps (find_path, connection repair)
    size_t max_grid_vertices = 0;  // grid vertices, which bound QEx's memory
};

// Throws unless every vertex rotation h -> next(opposite(h)) of the polygon
// mesh returns to its start, which OpenMesh's vertex circulators assume.
// O(#halfedges).
template <class MeshT>
void checkCirculatorsTerminate(const MeshT& m, const char* where)
{
    std::vector<char> seen(m.n_halfedges(), 0);
    for (auto v = m.vertices_begin(); v != m.vertices_end(); ++v) {
        if (m.has_vertex_status() && m.status(*v).deleted())
            continue;
        const auto h0 = m.halfedge_handle(*v);
        if (!h0.is_valid())
            continue;
        if (m.from_vertex_handle(h0) != *v)
            throw Abort(std::string("outgoing halfedge of another vertex ") + where);
        auto h = h0;
        do {
            if (seen[h.idx()])
                throw Abort(std::string("vertex rotation does not close ") + where);
            seen[h.idx()] = 1;
            h = m.next_halfedge_handle(m.opposite_halfedge_handle(h));
            if (!h.is_valid())
                throw Abort(std::string("vertex rotation is open ") + where);
        } while (h != h0);
    }
}

}

#endif
