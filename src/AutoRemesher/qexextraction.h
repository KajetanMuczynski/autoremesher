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
#ifndef AUTO_REMESHER_QEX_EXTRACTION_H
#define AUTO_REMESHER_QEX_EXTRACTION_H
#include <AutoRemesher/Vector2>
#include <AutoRemesher/Vector3>
#include <string>
#include <vector>

namespace AutoRemesher {

// Experiment for TODO 6.1 (built only with -DAUTOREMESHER_QEX=1 or 2): the
// polygons libQEx (Ebke et al. 2013) extracts from the integer-grid map,
// given per triangle corner as QuadExtractor takes it.  Faces QEx leaves as
// n-gons are kept.  Returns false, with the reason in *why, when OpenMesh
// rejects the triangle mesh (a non-manifold edge or vertex) or QEx fails, so
// the caller can fall back to its own extraction.
bool extractWithQex(const std::vector<Vector3>& vertices,
    const std::vector<std::vector<size_t>>& triangles,
    const std::vector<std::vector<Vector2>>& triangleUvs,
    std::vector<Vector3>* outVertices,
    std::vector<std::vector<size_t>>* outPolygons,
    std::string* why);

}

#endif
