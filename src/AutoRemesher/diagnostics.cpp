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
#include <AutoRemesher/Diagnostics>
#include <AutoRemesher/Predicates>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
// K32GetProcessMemoryInfo lives in kernel32, so no psapi import library.
#ifndef PSAPI_VERSION
#define PSAPI_VERSION 2
#endif
#include <psapi.h>
#else
#include <sys/resource.h>
#endif

namespace AutoRemesher {

namespace {

    void appendJsonString(std::string* out, const std::string& value)
    {
        out->push_back('"');
        for (const char character : value) {
            switch (character) {
            case '"':
                out->append("\\\"");
                break;
            case '\\':
                out->append("\\\\");
                break;
            case '\n':
                out->append("\\n");
                break;
            case '\r':
                out->append("\\r");
                break;
            case '\t':
                out->append("\\t");
                break;
            default:
                if ((unsigned char)character < 0x20) {
                    char escaped[8];
                    std::snprintf(escaped, sizeof(escaped), "\\u%04x", (unsigned)(unsigned char)character);
                    out->append(escaped);
                } else {
                    out->push_back(character);
                }
            }
        }
        out->push_back('"');
    }

    // The shortest of %.15g and %.17g that reads back to the same double, so
    // counts print as integers and measured values lose nothing.
    void appendJsonNumber(std::string* out, double value)
    {
        if (!std::isfinite(value)) {
            out->append("null");
            return;
        }
        char text[32];
        std::snprintf(text, sizeof(text), "%.15g", value);
        if (std::strtod(text, nullptr) != value)
            std::snprintf(text, sizeof(text), "%.17g", value);
        out->append(text);
    }

}

UvOrientation measureUvOrientation(const std::vector<double>& cornerUvs)
{
    UvOrientation orientation;
    const size_t triangleCount = cornerUvs.size() / 6;
    orientation.triangles = triangleCount;
    for (size_t f = 0; f < triangleCount; ++f) {
        const double* uv = &cornerUvs[6 * f];
        const Vector2 a(uv[0], uv[1]), b(uv[2], uv[3]), c(uv[4], uv[5]);
        const double area = std::fabs((b.x() - a.x()) * (c.y() - a.y()) - (b.y() - a.y()) * (c.x() - a.x()));
        orientation.totalArea += area;
        const int sign = Predicates::orient2d(a, b, c);
        if (sign > 0) {
            ++orientation.positive;
        } else if (sign < 0) {
            ++orientation.negative;
            orientation.negativeArea += area;
        } else {
            ++orientation.degenerate;
        }
    }
    return orientation;
}

void appendUvOrientation(DiagnosticRecord* record, const std::string& prefix,
    const UvOrientation& orientation)
{
    record->set(prefix + "_triangles", (double)orientation.triangles);
    record->set(prefix + "_flipped", (double)orientation.negative);
    record->set(prefix + "_degenerate", (double)orientation.degenerate);
    record->set(prefix + "_flipped_fraction",
        orientation.triangles > 0 ? (double)orientation.negative / orientation.triangles : 0.0);
    record->set(prefix + "_flipped_area_fraction",
        orientation.totalArea > 0.0 ? orientation.negativeArea / orientation.totalArea : 0.0);
}

std::string diagnosticsToJsonLines(const std::vector<DiagnosticRecord>& records,
    const std::vector<std::pair<std::string, std::string>>& context)
{
    std::string out;
    for (const DiagnosticRecord& record : records) {
        out.append("{\"schema\":\"autoremesher.stage-diagnostics\",\"version\":1");
        for (const auto& item : context) {
            out.push_back(',');
            appendJsonString(&out, item.first);
            out.push_back(':');
            appendJsonString(&out, item.second);
        }
        out.append(",\"stage\":");
        appendJsonString(&out, record.stage);
        if (record.island != DiagnosticRecord::noIsland) {
            out.append(",\"island\":");
            appendJsonNumber(&out, (double)record.island);
        }
        for (const auto& item : record.labels) {
            out.push_back(',');
            appendJsonString(&out, item.first);
            out.push_back(':');
            appendJsonString(&out, item.second);
        }
        for (const auto& item : record.values) {
            out.push_back(',');
            appendJsonString(&out, item.first);
            out.push_back(':');
            appendJsonNumber(&out, item.second);
        }
        out.append("}\n");
    }
    return out;
}

std::vector<std::pair<std::string, double>> summarizeDiagnostics(
    const std::vector<DiagnosticRecord>& records)
{
    const auto valueOf = [](const DiagnosticRecord& record, const char* key, double fallback) {
        for (const auto& item : record.values)
            if (item.first == key)
                return item.second;
        return fallback;
    };
    double flipped = 0, degenerate = 0, flippedContinuous = 0, flippedRounded = 0, mapped = 0;
    double integralityResidual = 0, constraintResidual = 0, droppedConstraints = 0;
    double roundingShift = 0, roundingPasses = 0;
    double solves = 0, factorizations = 0, fallbacks = 0, nonFinite = 0;
    double peakRss = 0, cpuSeconds = 0;
    // A solver object reports running totals, so only its last record counts
    // towards solves and factorisations: per island the frame field, the curl
    // correction and the last rounding pass.
    std::vector<const DiagnosticRecord*> lastRounding;
    for (const DiagnosticRecord& record : records) {
        if (record.stage == "run") {
            peakRss = valueOf(record, "peak_rss_bytes", 0);
            cpuSeconds = valueOf(record, "cpu_seconds", 0);
        } else if (record.stage == "cover_result") {
            flipped += valueOf(record, "snapped_flipped", 0);
            degenerate += valueOf(record, "snapped_degenerate", 0);
            flippedContinuous += valueOf(record, "continuous_flipped", 0);
            flippedRounded += valueOf(record, "rounded_flipped", 0);
            mapped += valueOf(record, "snapped_triangles", 0);
            integralityResidual = std::max(integralityResidual, valueOf(record, "integrality_residual", 0));
            constraintResidual = std::max(constraintResidual, valueOf(record, "constraint_residual", 0));
            roundingPasses = std::max(roundingPasses, valueOf(record, "iterations", 0));
        } else if (record.stage == "cover_system") {
            droppedConstraints += valueOf(record, "dropped_constraints", 0);
        } else if (record.stage == "rounding_iteration") {
            roundingShift = std::max(roundingShift, valueOf(record, "max_rounding_shift", 0));
            if (!lastRounding.empty() && lastRounding.back()->island == record.island)
                lastRounding.back() = &record;
            else
                lastRounding.push_back(&record);
        }
        const bool hasSolve = record.stage == "frame_field" || record.stage == "curl_correction"
            || record.stage == "rounding_iteration";
        if (hasSolve) {
            fallbacks += valueOf(record, "solve_kkt_fallback", 0);
            nonFinite += valueOf(record, "solve_non_finite", 0);
            if (record.stage != "rounding_iteration") {
                solves += valueOf(record, "solve_solves", 0);
                factorizations += valueOf(record, "solve_factorizations", 0);
            }
        }
    }
    for (const DiagnosticRecord* record : lastRounding) {
        solves += valueOf(*record, "solve_solves", 0);
        factorizations += valueOf(*record, "solve_factorizations", 0);
    }
    return {
        { "uv_flipped_triangles", flipped },
        { "uv_degenerate_triangles", degenerate },
        { "uv_flipped_triangles_continuous", flippedContinuous },
        { "uv_flipped_triangles_rounded", flippedRounded },
        { "uv_mapped_triangles", mapped },
        { "integrality_residual", integralityResidual },
        { "constraint_residual", constraintResidual },
        { "dropped_constraints", droppedConstraints },
        { "max_rounding_shift", roundingShift },
        { "rounding_passes", roundingPasses },
        { "solves", solves },
        { "factorizations", factorizations },
        { "kkt_fallbacks", fallbacks },
        { "non_finite_values", nonFinite },
        { "peak_rss_bytes", peakRss },
        { "cpu_seconds", cpuSeconds },
    };
}

size_t peakResidentSetBytes()
{
#if defined(_WIN32)
    PROCESS_MEMORY_COUNTERS counters;
    if (K32GetProcessMemoryInfo(GetCurrentProcess(), &counters, sizeof(counters)))
        return (size_t)counters.PeakWorkingSetSize;
    return 0;
#else
    struct rusage usage;
    if (0 != getrusage(RUSAGE_SELF, &usage))
        return 0;
#if defined(__APPLE__)
    return (size_t)usage.ru_maxrss;
#else
    return (size_t)usage.ru_maxrss * 1024;
#endif
#endif
}

double processCpuSeconds()
{
#if defined(_WIN32)
    FILETIME creation, exit, kernel, user;
    if (!GetProcessTimes(GetCurrentProcess(), &creation, &exit, &kernel, &user))
        return 0.0;
    const auto seconds = [](const FILETIME& time) {
        return (double)(((unsigned long long)time.dwHighDateTime << 32) | time.dwLowDateTime) * 1e-7;
    };
    return seconds(kernel) + seconds(user);
#else
    struct rusage usage;
    if (0 != getrusage(RUSAGE_SELF, &usage))
        return 0.0;
    return (double)usage.ru_utime.tv_sec + 1e-6 * usage.ru_utime.tv_usec
        + (double)usage.ru_stime.tv_sec + 1e-6 * usage.ru_stime.tv_usec;
#endif
}

}
