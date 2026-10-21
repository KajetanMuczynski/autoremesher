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
#ifndef AUTO_REMESHER_MEASURE_MESH_H
#define AUTO_REMESHER_MEASURE_MESH_H
#include <AutoRemesher/Remesh>

namespace AutoRemesher {

// Adds the counts that depend only on the mesh to report: vertices, faces,
// quads, non-quads, boundary, non-manifold and flipped edges, folded and
// degenerate faces, components.  Definitions in INTERFACE.md §3.1.  Used by
// remesh(); not part of the stable interface.
void measureMesh(const RemeshMesh& mesh, QualityReport* report);

}

#endif
