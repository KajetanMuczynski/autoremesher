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
#ifndef AUTO_REMESHER_DIAGNOSTICS_H
#define AUTO_REMESHER_DIAGNOSTICS_H

#include <cstddef>
#include <limits>
#include <string>
#include <utility>
#include <vector>

// Measurements the pipeline takes about itself while it runs: per-stage sizes
// and times, solver statistics, rounding behaviour and health counters.  They
// only record; nothing here feeds back into the result.  The records are
// written as JSON lines (schema "autoremesher.stage-diagnostics", one object
// per line) so that runs over a corpus can be concatenated and filtered with
// line tools.  Readers must accept keys they don't know.  Only standard
// library types, so hosts can take the records through the remesh interface.

namespace AutoRemesher {

struct DiagnosticRecord {
    static const size_t noIsland = std::numeric_limits<size_t>::max();

    explicit DiagnosticRecord(std::string stage = std::string(), size_t island = noIsland)
        : stage(std::move(stage))
        , island(island)
    {
    }

    // Adds the key, or overwrites it: a JSON object has each key once.
    DiagnosticRecord& set(const std::string& key, double value)
    {
        for (auto& item : values)
            if (item.first == key) {
                item.second = value;
                return *this;
            }
        values.emplace_back(key, value);
        return *this;
    }

    DiagnosticRecord& label(const std::string& key, const std::string& value)
    {
        for (auto& item : labels)
            if (item.first == key) {
                item.second = value;
                return *this;
            }
        labels.emplace_back(key, value);
        return *this;
    }

    // The pipeline stage this record measures, e.g. "cover_result".
    std::string stage;
    // The island the record belongs to, or noIsland for the whole run.
    size_t island = noIsland;
    std::vector<std::pair<std::string, std::string>> labels;
    std::vector<std::pair<std::string, double>> values;
};

// Orientation of the triangles of a 2D map, decided with the exact orient2d.
// The cover maps each triangle with a rotation-only transition to its
// neighbours, so a valid map has every triangle positive.
struct UvOrientation {
    size_t triangles = 0;
    size_t positive = 0;
    size_t negative = 0;
    // Exactly collinear corners: zero area in the map.
    size_t degenerate = 0;
    // Sums of |doubled area| in map units, for the flipped share by area.
    double negativeArea = 0.0;
    double totalArea = 0.0;
};

// `cornerUvs` holds u, v for corner 3f + l of triangle f.
UvOrientation measureUvOrientation(const std::vector<double>& cornerUvs);

// Appends the orientation as `<prefix>_triangles`, `<prefix>_flipped`, ...
void appendUvOrientation(DiagnosticRecord* record, const std::string& prefix,
    const UvOrientation& orientation);

// One JSON object per record and line.  `context` pairs are written first in
// every line (the mesh and target of a corpus run, say), as strings.
std::string diagnosticsToJsonLines(const std::vector<DiagnosticRecord>& records,
    const std::vector<std::pair<std::string, std::string>>& context
    = std::vector<std::pair<std::string, std::string>>());

// Whole-run totals and maxima of the records of one remesh(), as the flat
// numeric counters of the interface's QualityReport::diagnostics.
std::vector<std::pair<std::string, double>> summarizeDiagnostics(
    const std::vector<DiagnosticRecord>& records);

// Process-wide figures: 0 where the platform does not provide them.
size_t peakResidentSetBytes();
double processCpuSeconds();

}

#endif
