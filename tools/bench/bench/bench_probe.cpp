// SPDX-License-Identifier: GPL-3.0-or-later
#include "bench_probe.h"
#include <map>
#include <mutex>

namespace ar_probe {
namespace {
    std::mutex g_mutex;
    std::vector<Event> g_events;
    std::map<std::string, std::pair<double, double>> g_rounds;
    thread_local std::string t_step;
}

void setStep(const char* step)
{
    if (nullptr != step && '\0' != step[0])
        t_step = step;
}

void record(const char* kind, std::initializer_list<std::pair<const char*, double>> values)
{
    Event event;
    event.kind = kind;
    event.step = t_step;
    for (const auto& value : values)
        event.values.emplace_back(value.first, value.second);
    std::lock_guard<std::mutex> lock(g_mutex);
    g_events.push_back(std::move(event));
}

void round(const char* loop, double work)
{
    std::lock_guard<std::mutex> lock(g_mutex);
    auto& entry = g_rounds[loop];
    entry.first += 1.0;
    entry.second += work;
}

std::vector<Event> events()
{
    std::lock_guard<std::mutex> lock(g_mutex);
    return g_events;
}

std::vector<std::pair<std::string, std::pair<double, double>>> rounds()
{
    std::lock_guard<std::mutex> lock(g_mutex);
    return { g_rounds.begin(), g_rounds.end() };
}

}
