// SPDX-License-Identifier: GPL-3.0-or-later
// Measurement probes for the AutoRemesher baseline (tools/bench).
//
// probes.patch inserts AR_PROBE_* calls into the upstream core. Without
// AR_BENCH_PROBE defined every macro compiles to nothing, so the patched tree
// still builds the pristine pipeline. The probes only record; they never change
// control flow or numerics.
#ifndef AR_BENCH_PROBE_H
#define AR_BENCH_PROBE_H

#ifdef AR_BENCH_PROBE
#include <chrono>
#include <initializer_list>
#include <string>
#include <utility>
#include <vector>

namespace ar_probe {

// One recorded event: a kind ("cls_factorize", "mils_iteration", ...), the
// pipeline step that was running on this thread, and named numeric values.
struct Event {
    std::string kind;
    std::string step;
    std::vector<std::pair<std::string, double>> values;
};

// Per-thread name of the pipeline step currently running, set from the core's
// stage progress handler so solver events can be attributed to a step.
void setStep(const char* step);

void record(const char* kind, std::initializer_list<std::pair<const char*, double>> values);

// Aggregated counter for loops that can run many thousands of rounds:
// rounds += 1, work += `work` (e.g. faces scanned in that round).
void round(const char* loop, double work);

std::vector<Event> events();
// (loop name, rounds, summed work)
std::vector<std::pair<std::string, std::pair<double, double>>> rounds();

inline double msSince(const std::chrono::steady_clock::time_point& start)
{
    return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
}

}

#define AR_PROBE_NOW() std::chrono::steady_clock::now()
#define AR_PROBE_MS_SINCE(t) ar_probe::msSince(t)
#define AR_PROBE_SET_STEP(name) ar_probe::setStep(name)
#define AR_PROBE_RECORD(kind, ...) ar_probe::record(kind, __VA_ARGS__)
#define AR_PROBE_ROUND(work) ar_probe::round(__func__, (double)(work))
#else
#define AR_PROBE_NOW() 0
#define AR_PROBE_MS_SINCE(t) 0.0
#define AR_PROBE_SET_STEP(name) ((void)0)
#define AR_PROBE_RECORD(kind, ...) ((void)0)
#define AR_PROBE_ROUND(work) ((void)0)
#endif

#endif
