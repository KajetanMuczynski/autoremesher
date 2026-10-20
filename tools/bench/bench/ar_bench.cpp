// SPDX-License-Identifier: GPL-3.0-or-later
// Qt-free benchmark driver for the AutoRemesher core (src/AutoRemesher).
//
// Runs the same AutoRemesher::remesh() call the Qt app's headless mode makes
// (QuadMeshGenerator::generate) with the same OBJ loader, and writes a JSON
// record with wall/CPU time, peak RSS (overall and per pipeline step), the
// core's own phase report, the result counts and parametrization-level checks
// (flipped / degenerate UV triangles of the integer-grid map).
//
// Usage: ar_bench --input in.obj --output out.obj --json run.json
//          [--target-quads 50000] [--edge-scaling 1] [--sharp-edge 90]
//          [--smooth-normal 0] [--adaptivity 0.5] [--anisotropy 1]
//          [--resolution fast|quality|<triangles per quad>]
//          [--threads N] [--dump-param param.obj]
//          [--stage-diagnostics stages.jsonl]   (the core's per-stage records,
//                                                as autoremesher-cli writes them)
#define TINYOBJLOADER_IMPLEMENTATION
#include "tiny_obj_loader.h"

#include <AutoRemesher/AutoRemesher>
#include <AutoRemesher/Diagnostics>
#include <oneapi/tbb/global_control.h>

#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <sys/resource.h>
#include <thread>
#include <unistd.h>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

double secondsSince(const Clock::time_point& start)
{
    return std::chrono::duration<double>(Clock::now() - start).count();
}

size_t currentRssBytes()
{
    long pages = 0, resident = 0;
    FILE* fp = fopen("/proc/self/statm", "r");
    if (nullptr == fp)
        return 0;
    if (2 != fscanf(fp, "%ld %ld", &pages, &resident))
        resident = 0;
    fclose(fp);
    return (size_t)resident * (size_t)sysconf(_SC_PAGESIZE);
}

// Kernel high-water mark of the resident set (exact, unlike sampling).
size_t peakRssBytes()
{
    std::ifstream status("/proc/self/status");
    std::string line;
    while (std::getline(status, line)) {
        if (0 == line.compare(0, 6, "VmHWM:"))
            return (size_t)std::strtoull(line.c_str() + 6, nullptr, 10) * 1024;
    }
    return 0;
}

double cpuSeconds()
{
    rusage usage {};
    getrusage(RUSAGE_SELF, &usage);
    return usage.ru_utime.tv_sec + usage.ru_utime.tv_usec * 1e-6
        + usage.ru_stime.tv_sec + usage.ru_stime.tv_usec * 1e-6;
}

// Samples the resident set every few milliseconds and attributes each sample
// to the pipeline step last named by the progress handler. With several
// islands in flight the core names the slowest island's step, so per-step
// figures are exact for single-island meshes and approximate otherwise.
class RssSampler {
public:
    void start()
    {
        m_thread = std::thread([this] {
            while (!m_stop.load()) {
                sample();
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
            }
        });
    }
    void stop()
    {
        m_stop = true;
        if (m_thread.joinable())
            m_thread.join();
        sample();
    }
    void setStep(const char* name)
    {
        if (nullptr == name || '\0' == name[0])
            return;
        // Sample on entry too, so steps shorter than the sampling period
        // still get a value.
        const size_t rss = currentRssBytes();
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_step == name)
            return;
        m_step = name;
        if (m_stepPeak.find(m_step) == m_stepPeak.end())
            m_order.push_back(m_step);
        auto& peak = m_stepPeak[m_step];
        peak = std::max(peak, rss);
    }
    std::vector<std::pair<std::string, size_t>> stepPeaks()
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        std::vector<std::pair<std::string, size_t>> result;
        for (const auto& name : m_order)
            result.emplace_back(name, m_stepPeak[name]);
        return result;
    }

private:
    void sample()
    {
        const size_t rss = currentRssBytes();
        std::lock_guard<std::mutex> lock(m_mutex);
        auto& peak = m_stepPeak[m_step];
        peak = std::max(peak, rss);
    }
    std::atomic<bool> m_stop { false };
    std::thread m_thread;
    std::mutex m_mutex;
    std::string m_step = "(setup)";
    std::vector<std::string> m_order { "(setup)" };
    std::map<std::string, size_t> m_stepPeak { { "(setup)", 0 } };
};

void onProgress(void* tag, float, const char* status)
{
    static_cast<RssSampler*>(tag)->setStep(status);
}

std::string jsonEscape(const std::string& text)
{
    std::string out;
    for (char c : text) {
        if ('"' == c || '\\' == c) {
            out += '\\';
            out += c;
        } else if ('\n' == c) {
            out += "\\n";
        } else if ((unsigned char)c < 0x20) {
            char buffer[8];
            snprintf(buffer, sizeof(buffer), "\\u%04x", c);
            out += buffer;
        } else {
            out += c;
        }
    }
    return out;
}

std::string number(double value)
{
    if (!std::isfinite(value))
        return "null";
    char buffer[64];
    snprintf(buffer, sizeof(buffer), "%.9g", value);
    return buffer;
}

double mb(size_t bytes) { return bytes / (1024.0 * 1024.0); }

struct UvCheck {
    bool available = false;
    size_t triangles = 0;
    size_t components = 0;
    size_t flipped = 0; // sign opposite to the majority of its connected component
    size_t degenerate = 0; // |signed area| below 1e-8 grid cells
};

// Flip test on the integer-grid map. UVs are per triangle corner, in grid
// units (one target quad ~ one unit cell). Orientation is only meaningful
// relative to a connected component, so the majority sign is taken per
// component of the isotropic mesh.
UvCheck checkUvs(const std::vector<std::vector<size_t>>& triangles,
    const std::vector<std::vector<AutoRemesher::Vector2>>& uvs, size_t vertexCount)
{
    UvCheck check;
    if (triangles.empty() || triangles.size() != uvs.size())
        return check;
    check.available = true;
    check.triangles = triangles.size();

    std::vector<size_t> parent(vertexCount);
    for (size_t i = 0; i < vertexCount; ++i)
        parent[i] = i;
    const auto find = [&](size_t x) {
        while (parent[x] != x) {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        return x;
    };
    for (const auto& t : triangles) {
        parent[find(t[1])] = find(t[0]);
        parent[find(t[2])] = find(t[0]);
    }
    std::map<size_t, std::pair<size_t, size_t>> signs; // root -> (positive, negative)
    std::vector<int> sign(triangles.size(), 0);
    for (size_t f = 0; f < triangles.size(); ++f) {
        const auto& a = uvs[f][0];
        const auto& b = uvs[f][1];
        const auto& c = uvs[f][2];
        const double area = 0.5 * ((b.x() - a.x()) * (c.y() - a.y()) - (c.x() - a.x()) * (b.y() - a.y()));
        if (!std::isfinite(area) || std::fabs(area) < 1e-8) {
            ++check.degenerate;
            continue;
        }
        sign[f] = area > 0 ? 1 : -1;
        auto& count = signs[find(triangles[f][0])];
        if (area > 0)
            ++count.first;
        else
            ++count.second;
    }
    check.components = signs.size();
    for (size_t f = 0; f < triangles.size(); ++f) {
        if (0 == sign[f])
            continue;
        const auto& count = signs[find(triangles[f][0])];
        const int majority = count.first >= count.second ? 1 : -1;
        if (sign[f] != majority)
            ++check.flipped;
    }
    return check;
}

void writeObj(const std::string& path, const std::vector<AutoRemesher::Vector3>& vertices,
    const std::vector<std::vector<size_t>>& faces)
{
    FILE* fp = fopen(path.c_str(), "wb");
    if (nullptr == fp)
        return;
    for (const auto& v : vertices)
        fprintf(fp, "v %.9g %.9g %.9g\n", v.x(), v.y(), v.z());
    for (const auto& face : faces) {
        fputc('f', fp);
        for (size_t index : face)
            fprintf(fp, " %zu", index + 1);
        fputc('\n', fp);
    }
    fclose(fp);
}

void writeParamObj(const std::string& path, const std::vector<AutoRemesher::Vector3>& vertices,
    const std::vector<std::vector<size_t>>& triangles,
    const std::vector<std::vector<AutoRemesher::Vector2>>& uvs)
{
    FILE* fp = fopen(path.c_str(), "wb");
    if (nullptr == fp)
        return;
    for (const auto& v : vertices)
        fprintf(fp, "v %.9g %.9g %.9g\n", v.x(), v.y(), v.z());
    const bool withUv = uvs.size() == triangles.size();
    if (withUv) {
        for (const auto& t : uvs)
            for (const auto& uv : t)
                fprintf(fp, "vt %.9g %.9g\n", uv.x(), uv.y());
    }
    for (size_t f = 0; f < triangles.size(); ++f) {
        const auto& t = triangles[f];
        if (withUv)
            fprintf(fp, "f %zu/%zu %zu/%zu %zu/%zu\n", t[0] + 1, 3 * f + 1, t[1] + 1, 3 * f + 2, t[2] + 1, 3 * f + 3);
        else
            fprintf(fp, "f %zu %zu %zu\n", t[0] + 1, t[1] + 1, t[2] + 1);
    }
    fclose(fp);
}

}

int main(int argc, char** argv)
{
    std::map<std::string, std::string> args;
    for (int i = 1; i + 1 < argc; i += 2) {
        if (0 != strncmp(argv[i], "--", 2)) {
            std::cerr << "Unexpected argument " << argv[i] << std::endl;
            return 2;
        }
        args[argv[i] + 2] = argv[i + 1];
    }
    const auto arg = [&](const char* name, const std::string& fallback) {
        auto it = args.find(name);
        return it == args.end() ? fallback : it->second;
    };
    const std::string inputPath = arg("input", "");
    const std::string outputPath = arg("output", "");
    const std::string jsonPath = arg("json", "");
    if (inputPath.empty() || outputPath.empty() || jsonPath.empty()) {
        std::cerr << "Usage: ar_bench --input in.obj --output out.obj --json run.json [options]" << std::endl;
        return 2;
    }
    const long targetQuads = std::stol(arg("target-quads", "50000"));
    const double edgeScaling = std::stod(arg("edge-scaling", "1.0"));
    const double sharpEdge = std::stod(arg("sharp-edge", "90.0"));
    const double smoothNormal = std::stod(arg("smooth-normal", "0.0"));
    const double adaptivity = std::stod(arg("adaptivity", "0.5"));
    const double anisotropy = std::stod(arg("anisotropy", "1.0"));
    // The remesh() resolutions by name, or any triangles-per-quad value for sweeps.
    const std::string resolution = arg("resolution", "quality");
    const double trianglesPerQuad = "fast" == resolution ? AutoRemesher::FastTrianglesPerQuad
        : "quality" == resolution                        ? AutoRemesher::QualityTrianglesPerQuad
                                                         : std::stod(resolution);
    const int threads = std::stoi(arg("threads", "0"));
    const std::string paramPath = arg("dump-param", "");
    const std::string stagesPath = arg("stage-diagnostics", "");

    std::unique_ptr<tbb::global_control> threadLimit;
    if (threads > 0)
        threadLimit.reset(new tbb::global_control(tbb::global_control::max_allowed_parallelism, (size_t)threads));
    const size_t effectiveThreads = tbb::global_control::active_value(tbb::global_control::max_allowed_parallelism);

    // Load exactly like MainWindow::loadObj: tinyobj with its default
    // triangulation, positions taken as stored, no welding.
    const auto loadStart = Clock::now();
    tinyobj::attrib_t attributes;
    std::vector<tinyobj::shape_t> shapes;
    std::vector<tinyobj::material_t> materials;
    std::string warn, err;
    if (!tinyobj::LoadObj(&attributes, &shapes, &materials, &warn, &err, inputPath.c_str())) {
        std::cerr << "Failed to load " << inputPath << ": " << err << std::endl;
        return 1;
    }
    std::vector<AutoRemesher::Vector3> vertices(attributes.vertices.size() / 3);
    for (size_t i = 0, j = 0; i < vertices.size(); ++i, j += 3)
        vertices[i] = AutoRemesher::Vector3(attributes.vertices[j], attributes.vertices[j + 1], attributes.vertices[j + 2]);
    std::vector<std::vector<size_t>> triangles;
    for (const auto& shape : shapes) {
        for (size_t i = 0; i + 2 < shape.mesh.indices.size(); i += 3) {
            triangles.push_back({ (size_t)shape.mesh.indices[i].vertex_index,
                (size_t)shape.mesh.indices[i + 1].vertex_index,
                (size_t)shape.mesh.indices[i + 2].vertex_index });
        }
    }
    attributes = tinyobj::attrib_t();
    shapes.clear();
    const double loadSeconds = secondsSince(loadStart);

    RssSampler sampler;
    const size_t rssBefore = currentRssBytes();
    sampler.start();

    // Same parameter mapping as QuadMeshGenerator::generate().
    const auto remeshStart = Clock::now();
    const double cpuBefore = cpuSeconds();
    auto remesher = std::make_unique<AutoRemesher::AutoRemesher>(vertices, triangles);
    if (edgeScaling > 0)
        remesher->setScaling(edgeScaling);
    remesher->setTargetTriangleCount((size_t)targetQuads * 2);
    remesher->setModelType(AutoRemesher::ModelType::Organic);
    remesher->setGradientAdaptivity(adaptivity);
    remesher->setAnisotropy(anisotropy);
    remesher->setSharpEdgeDegrees(sharpEdge);
    remesher->setSmoothNormalDegrees(smoothNormal);
    remesher->setTrianglesPerQuad(trianglesPerQuad);
    remesher->setTag(&sampler);
    remesher->setProgressHandler(onProgress);
    const bool ok = remesher->remesh();
    const double remeshSeconds = secondsSince(remeshStart);
    const double cpuUsed = cpuSeconds() - cpuBefore;
    sampler.stop();

    const auto& outVertices = remesher->remeshedVertices();
    const auto& outFaces = remesher->remeshedQuads();
    const auto writeStart = Clock::now();
    if (ok)
        writeObj(outputPath, outVertices, outFaces);
    const double writeSeconds = secondsSince(writeStart);

    size_t quads = 0, nonQuads = 0;
    for (const auto& face : outFaces) {
        if (4 == face.size())
            ++quads;
        else
            ++nonQuads;
    }

    const auto& isoVertices = remesher->isotropicVertices();
    const auto& isoTriangles = remesher->isotropicTriangles();
    const auto& uvs = remesher->isotropicTriangleUvs();
    const UvCheck uvCheck = checkUvs(isoTriangles, uvs, isoVertices.size());
    if (!paramPath.empty())
        writeParamObj(paramPath, isoVertices, isoTriangles, uvs);
    if (!stagesPath.empty())
        std::ofstream(stagesPath) << AutoRemesher::diagnosticsToJsonLines(remesher->diagnostics());

    std::ostringstream json;
    json << "{\n";
    json << "  \"input\": \"" << jsonEscape(inputPath) << "\",\n";
    json << "  \"output\": \"" << jsonEscape(outputPath) << "\",\n";
    json << "  \"ok\": " << (ok ? "true" : "false") << ",\n";
    json << "  \"params\": {\"target_quads\": " << targetQuads << ", \"edge_scaling\": " << number(edgeScaling)
         << ", \"sharp_edge\": " << number(sharpEdge) << ", \"smooth_normal\": " << number(smoothNormal)
         << ", \"adaptivity\": " << number(adaptivity) << ", \"anisotropy\": " << number(anisotropy)
         << ", \"triangles_per_quad\": " << number(trianglesPerQuad)
         << ", \"threads\": " << effectiveThreads << "},\n";
    json << "  \"input_vertices\": " << vertices.size() << ",\n";
    json << "  \"input_triangles\": " << triangles.size() << ",\n";
    json << "  \"time_s\": {\"load_obj\": " << number(loadSeconds) << ", \"remesh\": " << number(remeshSeconds)
         << ", \"write_obj\": " << number(writeSeconds) << ", \"remesh_cpu\": " << number(cpuUsed) << "},\n";
    json << "  \"cpu_utilisation\": " << number(remeshSeconds > 0 ? cpuUsed / remeshSeconds : 0) << ",\n";
    json << "  \"rss_mb\": {\"before_remesh\": " << number(mb(rssBefore)) << ", \"peak\": " << number(mb(peakRssBytes())) << "},\n";
    json << "  \"step_peak_rss_mb\": [";
    {
        bool first = true;
        for (const auto& it : sampler.stepPeaks()) {
            json << (first ? "" : ", ") << "[\"" << jsonEscape(it.first) << "\", " << number(mb(it.second)) << "]";
            first = false;
        }
    }
    json << "],\n";
    json << "  \"phase_report\": [";
    for (size_t i = 0; i < remesher->phaseReport().size(); ++i)
        json << (i ? ", " : "") << "\"" << jsonEscape(remesher->phaseReport()[i]) << "\"";
    json << "],\n";
    json << "  \"result\": {\"vertices\": " << outVertices.size() << ", \"faces\": " << outFaces.size()
         << ", \"quads\": " << quads << ", \"non_quads\": " << nonQuads << "},\n";
    json << "  \"param\": {\"decimated\": " << (remesher->decimated() ? "true" : "false")
         << ", \"decimated_triangles\": " << remesher->decimatedTriangles().size()
         << ", \"iso_vertices\": " << isoVertices.size() << ", \"iso_triangles\": " << isoTriangles.size()
         << ", \"singularities\": " << remesher->isotropicSingularVertices().size()
         << ", \"uv_available\": " << (uvCheck.available ? "true" : "false")
         << ", \"uv_components\": " << uvCheck.components
         << ", \"uv_flipped\": " << uvCheck.flipped << ", \"uv_degenerate\": " << uvCheck.degenerate << "}";
    json << "\n}\n";

    std::ofstream out(jsonPath);
    out << json.str();
    return ok ? 0 : 1;
}
