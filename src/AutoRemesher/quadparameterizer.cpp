/*
 *  Copyright (c) 2026 Jeremy HU <jeremy-at-dust3d dot org>. All rights reserved.
 *
 *  Permission is hereby granted, free of charge, to any person obtaining a copy
 *  of this software and associated documentation files (the "Software"), to deal
 *  in the Software without restriction, including without limitation the rights
 *  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 *  copies of the Software, and to permit persons to whom the Software is
 *  furnished to do so, subject to the following conditions:
 *
 *  The above copyright notice and this permission notice shall be included in all
 *  copies or substantial portions of the Software.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 *  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 *  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 *  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 *  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 *  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 *  SOFTWARE.
 */
#include <AutoRemesher/ConstrainedLeastSquares>
#include <AutoRemesher/MixedIntegerLeastSquares>
#include <AutoRemesher/QuadParameterizer>
#include <AutoRemesher/SurfaceMesh>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <queue>
#include <tbb/blocked_range.h>
#include <tbb/parallel_for.h>

namespace AutoRemesher {
namespace {
    Vector3 unit(const Vector3& v, const Vector3& fallback)
    {
        return v.length() < 1e-12 ? fallback.normalized() : v.normalized();
    }

    int edgeQuarterTurn(const SurfaceMesh& mesh, size_t corner,
        const std::vector<Vector3>& field, const std::vector<Vector3>& normals)
    {
        const size_t opposite = mesh.oppositeCorner(corner);
        if (opposite == SurfaceMesh::npos)
            return 0;
        const size_t f = mesh.cornerFace(corner), g = mesh.cornerFace(opposite);
        if (f > g) {
            const int r = edgeQuarterTurn(mesh, opposite, field, normals);
            return (4 - r) % 4;
        }
        size_t v0 = mesh.cornerVertex(corner), v1 = mesh.cornerVertex(mesh.nextCorner(corner));
        if (v1 < v0)
            std::swap(v0, v1);
        const Vector3 e = unit(mesh.position(v1) - mesh.position(v0), Vector3(1, 0, 0));
        const Vector3 y0 = unit(Vector3::crossProduct(normals[f], e), Vector3(0, 1, 0));
        const Vector3 yg = unit(Vector3::crossProduct(normals[g], e), Vector3(0, 1, 0));
        const double a0 = std::atan2(Vector3::dotProduct(field[f], y0), Vector3::dotProduct(field[f], e));
        int best = 0;
        double bestError = 1e100;
        Vector3 candidate = field[g];
        for (int r = 0; r < 4; ++r) {
            const double ag = std::atan2(Vector3::dotProduct(candidate, yg), Vector3::dotProduct(candidate, e));
            double d = std::fabs(a0 - ag);
            while (d > M_PI)
                d = std::fabs(d - 2.0 * M_PI);
            if (d < bestError) {
                bestError = d;
                best = r;
            }
            candidate = Vector3::crossProduct(normals[g], candidate);
        }
        return best;
    }

    enum EdgeConstraint { ConstraintNone = 0,
        ConstraintU = 1,
        ConstraintV = 2 };
    int edgeConstraint(const SurfaceMesh& mesh, size_t c, const std::vector<Vector3>& field,
        const std::vector<Vector3>& normals, double hardEdgeDegrees)
    {
        if (mesh.oppositeCorner(c) != SurfaceMesh::npos && std::fabs(mesh.normalAngle(c)) * 180.0 / M_PI < hardEdgeDegrees)
            return ConstraintNone;
        const size_t f = mesh.cornerFace(c);
        const Vector3 edge = unit(mesh.edgeVector(c), Vector3(1, 0, 0));
        const Vector3 b = unit(field[f], edge);
        const Vector3 br = unit(Vector3::crossProduct(normals[f], b), Vector3(0, 1, 0));
        const bool alongB = std::acos(std::max(-1.0, std::min(1.0, std::fabs(Vector3::dotProduct(edge, b))))) < 10.0 * M_PI / 180.0;
        const bool alongBr = std::acos(std::max(-1.0, std::min(1.0, std::fabs(Vector3::dotProduct(edge, br))))) < 10.0 * M_PI / 180.0;
        if (alongB == alongBr)
            return ConstraintNone;
        return alongB ? ConstraintV : ConstraintU;
    }

    struct CoverContext {
        const SurfaceMesh& mesh;
        const std::vector<Vector3>& field;
        const std::vector<Vector3>& normals;
        const std::vector<int>& rotation;
        const std::vector<char>& seam;
        const std::vector<signed char>& cornerConstraints;
        const std::vector<double>& scalingU;
        const std::vector<double>& scalingV;
        const std::vector<double>* faceScaling;
        double scale;
    };

    void initializeFieldAndNormals(const SurfaceMesh& mesh, const std::vector<Vector3>* guidance,
        std::vector<Vector3>* normals, std::vector<Vector3>* field)
    {
        const bool hasGuidance = guidance && guidance->size() == mesh.faceCount();
        normals->assign(mesh.faceCount(), Vector3());
        field->resize(mesh.faceCount());
        tbb::parallel_for(tbb::blocked_range<size_t>(0, mesh.faceCount()), [&](const tbb::blocked_range<size_t>& range) {
            for (size_t faceIndex = range.begin(); faceIndex != range.end(); ++faceIndex) {
                (*normals)[faceIndex] = unit(mesh.faceNormal(faceIndex), Vector3(0, 0, 1));
                Vector3 tangentAxis(1, 0, 0);
                if (std::fabs(Vector3::dotProduct(tangentAxis, (*normals)[faceIndex])) > .8)
                    tangentAxis = Vector3(0, 1, 0);
                Vector3 fieldDirection = hasGuidance ? (*guidance)[faceIndex] : tangentAxis;
                if (!hasGuidance)
                    fieldDirection = fieldDirection - (*normals)[faceIndex] * Vector3::dotProduct(fieldDirection, (*normals)[faceIndex]);
                (*field)[faceIndex] = unit(fieldDirection, mesh.edgeVector(3 * faceIndex));
            }
        });
    }

    void smoothCrossField(const SurfaceMesh& mesh, const std::vector<Vector3>& normals,
        double hardEdgeDegrees, std::vector<Vector3>* field)
    {
        std::vector<double> alpha(2 * mesh.faceCount(), 0.0);
        std::vector<char> locked(mesh.faceCount(), 0);
        tbb::parallel_for(tbb::blocked_range<size_t>(0, mesh.faceCount()), [&](const tbb::blocked_range<size_t>& range) {
            for (size_t faceIndex = range.begin(); faceIndex != range.end(); ++faceIndex) {
                alpha[2 * faceIndex] = 1.0;
                for (size_t localCorner = 0; localCorner < 3; ++localCorner) {
                    const size_t cornerIndex = 3 * faceIndex + localCorner, oppositeCornerIndex = mesh.oppositeCorner(cornerIndex);
                    if (oppositeCornerIndex != SurfaceMesh::npos && std::fabs(mesh.normalAngle(cornerIndex)) * 180.0 / M_PI < hardEdgeDegrees)
                        continue;
                    const Vector3 edge = unit(mesh.edgeVector(cornerIndex), Vector3(1, 0, 0));
                    const Vector3 fieldDirection = (*field)[faceIndex];
                    const Vector3 perpendicular = unit(Vector3::crossProduct(normals[faceIndex], fieldDirection), Vector3(0, 1, 0));
                    const double fieldAngle = std::atan2(Vector3::dotProduct(edge, perpendicular), Vector3::dotProduct(edge, fieldDirection));
                    alpha[2 * faceIndex] = std::cos(4.0 * fieldAngle);
                    alpha[2 * faceIndex + 1] = std::sin(4.0 * fieldAngle);
                    locked[faceIndex] = 1;
                }
            }
        });
        for (int iteration = 0; iteration < 40; ++iteration) {
            std::vector<double> next = alpha;
            tbb::parallel_for(tbb::blocked_range<size_t>(0, mesh.faceCount()), [&](const tbb::blocked_range<size_t>& range) {
                for (size_t f = range.begin(); f != range.end(); ++f)
                    if (!locked[f]) {
                        double x = alpha[2 * f], y = alpha[2 * f + 1];
                        const Vector3 bf = (*field)[f];
                        const Vector3 btf = unit(Vector3::crossProduct(normals[f], bf), Vector3(0, 1, 0));
                        for (size_t l = 0; l < 3; ++l) {
                            const size_t oc = mesh.oppositeCorner(3 * f + l);
                            if (oc == SurfaceMesh::npos)
                                continue;
                            const size_t g = mesh.cornerFace(oc);
                            Vector3 bg = (*field)[g];
                            bg = unit(bg - normals[f] * Vector3::dotProduct(bg, normals[f]), bf);
                            const double d = std::atan2(Vector3::dotProduct(bg, btf), Vector3::dotProduct(bg, bf));
                            const double cs = std::cos(4.0 * d), sn = std::sin(4.0 * d);
                            x += cs * alpha[2 * g] - sn * alpha[2 * g + 1];
                            y += sn * alpha[2 * g] + cs * alpha[2 * g + 1];
                        }
                        const double length = std::hypot(x, y);
                        if (length > 1e-12) {
                            next[2 * f] = x / length;
                            next[2 * f + 1] = y / length;
                        }
                    }
            });
            alpha.swap(next);
        }
        tbb::parallel_for(tbb::blocked_range<size_t>(0, mesh.faceCount()), [&](const tbb::blocked_range<size_t>& range) {
            for (size_t faceIndex = range.begin(); faceIndex != range.end(); ++faceIndex) {
                const double fieldAngle = .25 * std::atan2(alpha[2 * faceIndex + 1], alpha[2 * faceIndex]);
                const Vector3 fieldDirection = (*field)[faceIndex];
                const Vector3 perpendicular = unit(Vector3::crossProduct(normals[faceIndex], fieldDirection), Vector3(0, 1, 0));
                (*field)[faceIndex] = unit(fieldDirection * std::cos(fieldAngle) + perpendicular * std::sin(fieldAngle), fieldDirection);
            }
        });
    }

    void brushFieldAlongSpanningTree(const SurfaceMesh& mesh, const std::vector<Vector3>& normals,
        std::vector<Vector3>* field)
    {
        std::vector<char> seen(mesh.faceCount(), 0);
        if (mesh.faceCount() != 0) {
            std::queue<size_t> q;
            q.push(0);
            seen[0] = 1;
            while (!q.empty()) {
                size_t f = q.front();
                q.pop();
                for (size_t l = 0; l < 3; ++l) {
                    size_t c = 3 * f + l, oc = mesh.oppositeCorner(c);
                    if (oc == SurfaceMesh::npos)
                        continue;
                    size_t g = mesh.cornerFace(oc);
                    if (!seen[g]) {
                        int turns = edgeQuarterTurn(mesh, c, *field, normals);
                        Vector3 brushed = (*field)[g];
                        for (int k = 0; k < turns; ++k)
                            brushed = Vector3::crossProduct(normals[g], brushed);
                        (*field)[g] = unit(brushed, mesh.edgeVector(3 * g));
                        seen[g] = 1;
                        q.push(g);
                    }
                }
            }
        }
    }

    std::vector<int> computeCornerRotations(const SurfaceMesh& mesh,
        const std::vector<Vector3>& field, const std::vector<Vector3>& normals)
    {
        const size_t corners = mesh.cornerCount();
        std::vector<int> rotation(corners, 0);
        for (size_t c = 0; c < corners; ++c) {
            const size_t oc = mesh.oppositeCorner(c);
            if (oc == SurfaceMesh::npos)
                continue;
            rotation[c] = edgeQuarterTurn(mesh, c, field, normals);
        }
        return rotation;
    }

    std::vector<signed char> computeCornerConstraints(const SurfaceMesh& mesh,
        const std::vector<Vector3>& field, const std::vector<Vector3>& normals, double hardEdgeDegrees)
    {
        const size_t corners = mesh.cornerCount();
        std::vector<signed char> cornerConstraints(corners, ConstraintNone);
        tbb::parallel_for(tbb::blocked_range<size_t>(0, corners), [&](const tbb::blocked_range<size_t>& range) {
            for (size_t c = range.begin(); c != range.end(); ++c)
                cornerConstraints[c] = static_cast<signed char>(edgeConstraint(mesh, c, field, normals, hardEdgeDegrees));
        });
        return cornerConstraints;
    }

    void applyDirectionalSwaps(const SurfaceMesh& mesh, const std::vector<Vector3>& fieldBeforeBrush,
        const std::vector<Vector3>& field, const std::vector<Vector3>& normals,
        std::vector<double>* scalingU, std::vector<double>* scalingV)
    {
        size_t directionalSwaps = 0;
        for (size_t f = 0; f < mesh.faceCount(); ++f) {
            const Vector3 before = unit(fieldBeforeBrush[f], field[f]);
            const Vector3 after = unit(field[f], before);
            const Vector3 perpendicular = unit(Vector3::crossProduct(normals[f], after), before);
            if (std::fabs(Vector3::dotProduct(before, after)) < std::fabs(Vector3::dotProduct(before, perpendicular)))
                std::swap((*scalingU)[f], (*scalingV)[f]), ++directionalSwaps;
        }
    }

    const double quarterTurn[4][2][2] = {
        { { 1, 0 }, { 0, 1 } },
        { { 0, 1 }, { -1, 0 } },
        { { -1, 0 }, { 0, -1 } },
        { { 0, -1 }, { 1, 0 } }
    };

    void applyCurlCorrection(const SurfaceMesh& mesh, const std::vector<Vector3>& normals,
        const std::vector<int>& rotation, const std::vector<signed char>& cornerConstraints,
        const std::vector<double>* faceScaling, double scale, double regularization,
        std::vector<double>* scalingU, std::vector<double>* scalingV,
        std::vector<Vector3>* field, DiagnosticRecord* diagnostics)
    {
        const size_t faceCount = mesh.faceCount();
        const bool hasFaceScaling = faceScaling && faceScaling->size() == faceCount;
        std::vector<double> su(faceCount), sv(faceCount);
        std::vector<Vector3> perpendicular(faceCount);
        for (size_t f = 0; f < faceCount; ++f) {
            const double faceScale = hasFaceScaling ? std::max(1e-12, (*faceScaling)[f]) : 1.0;
            su[f] = scale * faceScale * std::max(1e-12, (*scalingU)[f]);
            sv[f] = scale * faceScale * std::max(1e-12, (*scalingV)[f]);
            perpendicular[f] = unit(Vector3::crossProduct(normals[f], (*field)[f]),
                mesh.edgeVector(3 * f));
        }

        std::vector<char> anchored(faceCount, 0);
        for (size_t c = 0; c < mesh.cornerCount(); ++c)
            if (cornerConstraints[c] != ConstraintNone)
                anchored[mesh.cornerFace(c)] = 1;

        const auto request = [&](size_t corner, size_t face, double* constant,
                                 double* turnGradient, double* alongGradient, double* acrossGradient) {
            const Vector3 e = mesh.edgeVector(corner);
            const double along = Vector3::dotProduct((*field)[face], e);
            const double across = Vector3::dotProduct(perpendicular[face], e);
            constant[0] = along / su[face];
            constant[1] = across / sv[face];
            turnGradient[0] = across / su[face];
            turnGradient[1] = -along / sv[face];
            alongGradient[0] = -along / su[face];
            alongGradient[1] = 0.0;
            acrossGradient[0] = 0.0;
            acrossGradient[1] = -across / sv[face];
        };

        ConstrainedLeastSquares system(3 * faceCount);
        size_t edgeCount = 0;
        for (size_t c = 0; c < mesh.cornerCount(); ++c) {
            const size_t oc = mesh.oppositeCorner(c);
            if (oc == SurfaceMesh::npos || oc < c)
                continue;
            const size_t f = mesh.cornerFace(c), g = mesh.cornerFace(oc);
            const int r = (rotation[c] % 4 + 4) % 4;
            double here[2], hereTurn[2], hereAlong[2], hereAcross[2];
            double across[2], acrossTurn[2], acrossAlong[2], acrossAcross[2];
            request(c, f, here, hereTurn, hereAlong, hereAcross);
            request(oc, g, across, acrossTurn, acrossAlong, acrossAcross);
            const auto turned = [&](const double* value, size_t k) {
                return quarterTurn[r][k][0] * value[0] + quarterTurn[r][k][1] * value[1];
            };
            for (size_t k = 0; k < 2; ++k) {
                const double residual = here[k] + turned(across, k);
                system.addEnergy({ { 3 * f, hereTurn[k] },
                                     { 3 * f + 1, hereAlong[k] },
                                     { 3 * f + 2, hereAcross[k] },
                                     { 3 * g, turned(acrossTurn, k) },
                                     { 3 * g + 1, turned(acrossAlong, k) },
                                     { 3 * g + 2, turned(acrossAcross, k) } },
                    -residual, 1.0);
            }
            ++edgeCount;
        }
        if (0 == edgeCount)
            return;
        for (size_t f = 0; f < faceCount; ++f) {
            if (anchored[f])
                system.addConstraint({ { 3 * f, 1.0 } }, 0.0);
            else
                system.addEnergy({ { 3 * f, 1.0 } }, 0.0, regularization);
            system.addEnergy({ { 3 * f + 1, 1.0 } }, 0.0, regularization);
            system.addEnergy({ { 3 * f + 2, 1.0 } }, 0.0, regularization);
        }

        std::vector<double> correction;
        const bool solved = system.solve(&correction);
        appendSolveStats(diagnostics, "solve", system.lastSolveStats());
        if (!solved || correction.size() != 3 * faceCount)
            return;

        const double limit = .3, scaleLimit = std::log(1.5);
        size_t clampedAngles = 0, clampedScales = 0;
        for (size_t f = 0; f < faceCount; ++f) {
            if (std::fabs(correction[3 * f]) > limit)
                ++clampedAngles;
            if (std::fabs(correction[3 * f + 1]) > scaleLimit || std::fabs(correction[3 * f + 2]) > scaleLimit)
                ++clampedScales;
        }
        diagnostics->set("clamped_angles", (double)clampedAngles);
        diagnostics->set("clamped_scales", (double)clampedScales);
        for (size_t f = 0; f < faceCount; ++f) {
            const double angle = std::max(-limit, std::min(limit, correction[3 * f]));
            (*field)[f] = unit(std::cos(angle) * (*field)[f] + std::sin(angle) * perpendicular[f],
                (*field)[f]);
            (*scalingU)[f] *= std::exp(std::max(-scaleLimit, std::min(scaleLimit, correction[3 * f + 1])));
            (*scalingV)[f] *= std::exp(std::max(-scaleLimit, std::min(scaleLimit, correction[3 * f + 2])));
        }
        double areaBefore = 0.0, areaAfter = 0.0;
        for (size_t f = 0; f < faceCount; ++f) {
            const double faceScale = hasFaceScaling ? std::max(1e-12, (*faceScaling)[f]) : 1.0;
            const double area = Vector3::crossProduct(mesh.edgeVector(3 * f),
                -mesh.edgeVector(3 * f + 2))
                                    .length();
            areaBefore += area / (su[f] * sv[f]);
            su[f] = scale * faceScale * std::max(1e-12, (*scalingU)[f]);
            sv[f] = scale * faceScale * std::max(1e-12, (*scalingV)[f]);
            areaAfter += area / (su[f] * sv[f]);
        }
        if (areaBefore > 0.0 && areaAfter > 0.0) {
            const double factor = std::sqrt(areaAfter / areaBefore);
            for (size_t f = 0; f < faceCount; ++f) {
                (*scalingU)[f] *= factor;
                (*scalingV)[f] *= factor;
            }
        }
    }

    std::vector<char> computeSeam(const SurfaceMesh& mesh, const std::vector<int>& rotation)
    {
        const size_t corners = mesh.cornerCount();
        std::vector<char> insideBall(corners, 0), ballSeen(mesh.faceCount(), 0);
        if (mesh.faceCount() != 0) {
            std::queue<size_t> q;
            q.push(0);
            ballSeen[0] = 1;
            while (!q.empty()) {
                const size_t f = q.front();
                q.pop();
                for (size_t l = 0; l < 3; ++l) {
                    const size_t c = 3 * f + l, oc = mesh.oppositeCorner(c);
                    if (oc == SurfaceMesh::npos || rotation[c] != 0)
                        continue;
                    const size_t g = mesh.cornerFace(oc);
                    if (!ballSeen[g]) {
                        ballSeen[g] = 1;
                        q.push(g);
                        insideBall[c] = insideBall[oc] = 1;
                    }
                }
            }
        }
        std::vector<char> seam(corners, 0);
        for (size_t c = 0; c < corners; ++c)
            seam[c] = (mesh.oppositeCorner(c) == SurfaceMesh::npos || !insideBall[c]);
        std::vector<size_t> borderDegree(mesh.vertexCount(), 0);
        for (size_t c = 0; c < corners; ++c)
            if (seam[c])
                ++borderDegree[mesh.cornerVertex(c)];
        bool changed = true;
        while (changed) {
            changed = false;
            for (size_t c = 0; c < corners; ++c) {
                const size_t oc = mesh.oppositeCorner(c);
                if (oc == SurfaceMesh::npos || !seam[c] || rotation[c] != 0)
                    continue;
                const size_t v0 = mesh.cornerVertex(c);
                if (borderDegree[v0] != 1)
                    continue;
                const size_t v1 = mesh.cornerVertex(mesh.nextCorner(c));
                seam[c] = seam[oc] = 0;
                insideBall[c] = insideBall[oc] = 1;
                if (borderDegree[v0] > 0)
                    --borderDegree[v0];
                if (borderDegree[v1] > 0)
                    --borderDegree[v1];
                changed = true;
            }
        }
        return seam;
    }

    void addRotationConstraints(MixedIntegerLeastSquares& s, size_t ax, size_t bx, int r, double sign)
    {
        r = (r % 4 + 4) % 4;
        if (r == 0) {
            s.addConstraint(ax, 1, bx, sign);
            s.addConstraint(ax + 1, 1, bx + 1, sign);
        } else if (r == 1) {
            s.addConstraint(ax, 1, bx + 1, sign);
            s.addConstraint(ax + 1, 1, bx, -sign);
        } else if (r == 2) {
            s.addConstraint(ax, 1, bx, -sign);
            s.addConstraint(ax + 1, 1, bx + 1, -sign);
        } else {
            s.addConstraint(ax, 1, bx + 1, -sign);
            s.addConstraint(ax + 1, 1, bx, sign);
        }
    }

    // Net uv area of the cover in grid cells (one cell is one quad); faces
    // mapped with the opposite orientation count negative.
    double coverCellArea(const SurfaceMesh& mesh, const MixedIntegerLeastSquares& s)
    {
        double area = 0.0;
        for (size_t f = 0; f < mesh.faceCount(); ++f) {
            const size_t a = 3 * f, b = 3 * f + 1, c = 3 * f + 2;
            const double ax = s.value(2 * a), ay = s.value(2 * a + 1);
            area += .5 * ((s.value(2 * b) - ax) * (s.value(2 * c + 1) - ay) - (s.value(2 * c) - ax) * (s.value(2 * b + 1) - ay));
        }
        return std::fabs(area);
    }

    // Rescales the continuous cover so it spans as many cells as the face
    // sizes ask for. Least squares projects the sized frame onto integrable
    // maps and loses the part of it that has curl, so the map came out with
    // 40-97 % of the requested cells on the baseline corpus, the least on
    // hard-surface parts. The continuous solution is linear in 1 / size, so
    // the rescale is exact there; rounding afterwards moves the count by a
    // few percent.
    // Returns expected / actual cells, the factor the cover's area was (or,
    // beyond the limit, would have been) scaled by; 0 if either is empty.
    // How far it is from 1 measures how much of the requested sizing was not
    // integrable (REFERENCE M3).
    double matchCellCount(const SurfaceMesh& mesh, double expectedCells, MixedIntegerLeastSquares* s)
    {
        const double cells = coverCellArea(mesh, *s);
        if (!(expectedCells > 0.0) || !(cells > 0.0))
            return 0.0;
        const double ratio = expectedCells / cells;
        // Beyond this the map is broken rather than shrunk, and growing it
        // would only multiply the extraction work on a bad map.
        const double maximumRatio = 4.0;
        if (ratio > maximumRatio || ratio < 1.0 / maximumRatio)
            return ratio;
        s->scaleSolution(std::sqrt(ratio));
        return ratio;
    }

    // How closely the map follows the requested quad sizes. Per face,
    // a = log of the edge the map gives it (sqrt of 3D area over uv area) and
    // r = log of the requested edge, both area weighted and centred. Records
    // the RMS of a - r and the slope of a against r: 1 when every requested
    // size change is realised, 0 for uniform quads. Flipped faces count with
    // their absolute uv area; degenerate ones are skipped.
    void appendSizeFidelity(DiagnosticRecord* record, const std::string& prefix, const SurfaceMesh& mesh,
        const MixedIntegerLeastSquares& s, const std::vector<double>* faceScaling, double scale)
    {
        const bool hasFaceScaling = faceScaling && faceScaling->size() == mesh.faceCount();
        std::vector<double> realised(mesh.faceCount(), 0.0), requested(mesh.faceCount(), 0.0), weight(mesh.faceCount(), 0.0);
        double totalWeight = 0.0, meanRealised = 0.0, meanRequested = 0.0;
        for (size_t f = 0; f < mesh.faceCount(); ++f) {
            const size_t a = 3 * f, b = 3 * f + 1, c = 3 * f + 2;
            const double ax = s.value(2 * a), ay = s.value(2 * a + 1);
            const double uvArea = .5 * std::fabs((s.value(2 * b) - ax) * (s.value(2 * c + 1) - ay) - (s.value(2 * c) - ax) * (s.value(2 * b + 1) - ay));
            const double area = .5 * Vector3::crossProduct(mesh.edgeVector(a), -mesh.edgeVector(c)).length();
            if (!(uvArea > 0.0) || !(area > 0.0))
                continue;
            weight[f] = area;
            realised[f] = .5 * std::log(area / uvArea);
            requested[f] = std::log(scale * (hasFaceScaling ? std::max(1e-12, (*faceScaling)[f]) : 1.0));
            totalWeight += area;
            meanRealised += area * realised[f];
            meanRequested += area * requested[f];
        }
        if (!(totalWeight > 0.0))
            return;
        meanRealised /= totalWeight;
        meanRequested /= totalWeight;
        double error = 0.0, covariance = 0.0, variance = 0.0;
        for (size_t f = 0; f < mesh.faceCount(); ++f) {
            const double da = realised[f] - meanRealised, dr = requested[f] - meanRequested;
            error += weight[f] * (da - dr) * (da - dr);
            covariance += weight[f] * da * dr;
            variance += weight[f] * dr * dr;
        }
        record->set(prefix + "_size_error_rms", std::sqrt(error / totalWeight));
        record->set(prefix + "_size_slope", variance > 0.0 ? covariance / variance : 0.0);
        record->set("requested_size_spread", std::sqrt(variance / totalWeight));
        record->set("size_measured_area", totalWeight);
    }

    // The corner uvs of the current solution, laid out as measureUvOrientation
    // expects.
    std::vector<double> cornerUvs(const MixedIntegerLeastSquares& s, size_t uvVariables)
    {
        std::vector<double> uvs(uvVariables);
        for (size_t i = 0; i < uvVariables; ++i)
            uvs[i] = s.value(i);
        return uvs;
    }

    // Appends "cover_system" and one "rounding_iteration" per pass to
    // `diagnostics`, and fills `result` with the residuals and map validity.
    bool solveQuadCover(const CoverContext& ctx, std::vector<double>* values,
        const ProgressHandler* progressHandler,
        std::vector<DiagnosticRecord>* diagnostics, DiagnosticRecord* result)
    {
        const SurfaceMesh& mesh = ctx.mesh;
        const std::vector<Vector3>& field = ctx.field;
        const std::vector<Vector3>& normals = ctx.normals;
        const std::vector<int>& rotation = ctx.rotation;
        const std::vector<char>& seam = ctx.seam;
        const std::vector<signed char>& cornerConstraints = ctx.cornerConstraints;
        const std::vector<double>& activeScalingU = ctx.scalingU;
        const std::vector<double>& activeScalingV = ctx.scalingV;
        const std::vector<double>* faceScaling = ctx.faceScaling;
        const double scale = ctx.scale;
        const size_t corners = mesh.cornerCount();
        const size_t uvVariables = 2 * corners;
        const size_t variables = 2 * uvVariables;
        const auto report = [progressHandler](float fraction, const char* name) {
            if (nullptr != progressHandler && *progressHandler)
                (*progressHandler)(fraction, name);
        };
        report(0.0f, "Building cover system");
        MixedIntegerLeastSquares s(variables);
        for (size_t t = 0; t < 2 * corners; ++t)
            s.setVariablePeriod(uvVariables + t, 2);
        double expectedCells = 0.0;
        for (size_t f = 0; f < mesh.faceCount(); ++f) {
            const Vector3 u = field[f], v = unit(Vector3::crossProduct(normals[f], u), mesh.edgeVector(3 * f));
            const double faceScale = faceScaling && faceScaling->size() == mesh.faceCount()
                ? std::max(1e-12, (*faceScaling)[f])
                : 1.0;
            const double directionalU = std::max(1e-12, activeScalingU[f]);
            const double directionalV = std::max(1e-12, activeScalingV[f]);
            const double su = scale * faceScale * directionalU;
            const double sv = scale * faceScale * directionalV;
            const double faceArea = .5 * Vector3::crossProduct(mesh.edgeVector(3 * f), -mesh.edgeVector(3 * f + 2)).length();
            expectedCells += faceArea / (su * sv);
            for (size_t l = 0; l < 3; ++l) {
                size_t c = 3 * f + l, n = mesh.nextCorner(c);
                Vector3 e = mesh.edgeVector(c);
                const double weight = su * sv;
                s.addEnergy(2 * n, 1, 2 * c, -1, Vector3::dotProduct(u, e) / su, weight);
                s.addEnergy(2 * n + 1, 1, 2 * c + 1, -1, Vector3::dotProduct(v, e) / sv, weight);
            }
        }
        s.addConstraint(0, 1);
        s.addConstraint(1, 1);
        size_t hardCoordinateCount = 0;
        for (size_t c = 0; c < corners; ++c) {
            size_t oc = mesh.oppositeCorner(c);
            if (oc == SurfaceMesh::npos)
                continue;
            const size_t tc = uvVariables + 2 * c;
            const size_t toc = uvVariables + 2 * oc;
            int r = rotation[c];
            if (seam[c]) {
                addRotationConstraints(s, tc, toc, r, 1.0);
            } else {
                s.addConstraint(tc, 1);
                s.addConstraint(tc + 1, 1);
            }
        }
        for (size_t c = 0; c < corners; ++c) {
            const size_t oc = mesh.oppositeCorner(c);
            if (oc == SurfaceMesh::npos)
                continue;
            const size_t other = mesh.nextCorner(oc);
            const size_t tc = uvVariables + 2 * c;
            const int r = (rotation[c] % 4 + 4) % 4;
            if (r == 0) {
                s.addConstraint(2 * c, 1, 2 * other, -1, tc, -1);
                s.addConstraint(2 * c + 1, 1, 2 * other + 1, -1, tc + 1, -1);
            } else if (r == 1) {
                s.addConstraint(2 * c, 1, 2 * other + 1, -1, tc, -1);
                s.addConstraint(2 * c + 1, 1, 2 * other, 1, tc + 1, -1);
            } else if (r == 2) {
                s.addConstraint(2 * c, 1, 2 * other, 1, tc, -1);
                s.addConstraint(2 * c + 1, 1, 2 * other + 1, 1, tc + 1, -1);
            } else {
                s.addConstraint(2 * c, 1, 2 * other + 1, 1, tc, -1);
                s.addConstraint(2 * c + 1, 1, 2 * other, -1, tc + 1, -1);
            }
        }
        for (size_t vertex = 0; vertex < mesh.vertexCount(); ++vertex) {
            const auto& incident = mesh.cornersAroundVertex(vertex);
            if (incident.empty())
                continue;
            size_t start = incident.front(), c = start;
            int accumulated = 0;
            bool closed = true;
            std::vector<std::pair<size_t, int>> wheel;
            do {
                if (mesh.oppositeCorner(c) == SurfaceMesh::npos) {
                    closed = false;
                    break;
                }
                wheel.push_back({ c, accumulated });
                accumulated = (accumulated + rotation[c]) % 4;
                c = mesh.nextCorner(mesh.oppositeCorner(c));
            } while (c != start && wheel.size() <= incident.size() + 1);
            if (!closed || c != start || accumulated != 0)
                continue;
            for (int coord = 0; coord < 2; ++coord) {
                std::vector<std::pair<size_t, double>> row;
                for (const auto& item : wheel) {
                    const size_t t = uvVariables + 2 * item.first;
                    const int r = item.second;
                    if (coord == 0) {
                        if (r == 0)
                            row.push_back({ t, 1 });
                        else if (r == 1)
                            row.push_back({ t + 1, 1 });
                        else if (r == 2)
                            row.push_back({ t, -1 });
                        else
                            row.push_back({ t + 1, -1 });
                    } else {
                        if (r == 0)
                            row.push_back({ t + 1, 1 });
                        else if (r == 1)
                            row.push_back({ t, -1 });
                        else if (r == 2)
                            row.push_back({ t + 1, -1 });
                        else
                            row.push_back({ t, 1 });
                    }
                }
                s.addConstraint(row);
            }
        }
        for (size_t c = 0; c < corners; ++c) {
            const size_t n = mesh.nextCorner(c);
            const int constraint = cornerConstraints[c];
            if (constraint == ConstraintV) {
                s.setVariablePeriod(2 * c + 1, 1);
                s.setVariablePeriod(2 * n + 1, 1);
                hardCoordinateCount += 2;
                s.addConstraint(2 * c + 1, 1, 2 * n + 1, -1);
            } else if (constraint == ConstraintU) {
                s.setVariablePeriod(2 * c, 1);
                s.setVariablePeriod(2 * n, 1);
                hardCoordinateCount += 2;
                s.addConstraint(2 * c, 1, 2 * n, -1);
            }
        }
        report(0.2f, "Eliminating cover constraints");
        s.finalizeConstraints();
        {
            DiagnosticRecord record("cover_system");
            record.set("faces", (double)mesh.faceCount());
            record.set("variables", (double)variables);
            record.set("kernel_size", (double)s.kernelSize());
            record.set("original_integers", (double)s.originalIntegerVariableCount());
            record.set("kernel_integers", (double)s.integerKernelVariableCount());
            record.set("hard_coordinates", (double)hardCoordinateCount);
            record.set("dropped_constraints", (double)s.droppedConstraintCount());
            diagnostics->push_back(std::move(record));
        }
        // Rounding converges well short of the cap, so spread the fraction over
        // the passes it is expected to take and clamp instead of pacing it
        // against the cap and barely moving.
        const size_t maximumIterations = 100;
        const size_t expectedIterations = 1 + MixedIntegerLeastSquares::expectedRoundingPasses();
        size_t iterations = 0;
        for (size_t iteration = 0; iteration < maximumIterations; ++iteration) {
            report(0.3f + 0.65f * std::min(1.0f, (float)iteration / expectedIterations),
                "Rounding cover to integers");
            const bool solved = s.solveIteration();
            ++iterations;
            const MixedIntegerLeastSquares::IterationStats& stats = s.lastIterationStats();
            DiagnosticRecord record("rounding_iteration");
            record.set("iteration", (double)stats.iteration);
            record.set("kernel_integers", (double)stats.integerVariables);
            record.set("fixed_before", (double)stats.fixedBefore);
            record.set("newly_fixed", (double)stats.newlyFixed);
            record.set("max_rounding_shift", stats.maximumRoundingShift);
            record.set("mean_rounding_shift", stats.meanRoundingShift);
            appendSolveStats(&record, "solve", stats.solve);
            diagnostics->push_back(std::move(record));
            result->set("iterations", (double)iterations);
            if (!solved)
                return false;
            if (0 == iteration) {
                result->set("continuous_rescale", matchCellCount(mesh, expectedCells, &s));
                result->set("continuous_energy", s.energy());
                appendSizeFidelity(result, "continuous", mesh, s, faceScaling, scale);
                // Nothing is fixed in the first pass, so its solution is the
                // continuous relaxation: flips there are not caused by
                // rounding.
                appendUvOrientation(result, "continuous", measureUvOrientation(cornerUvs(s, uvVariables)));
            }
            if (s.converged())
                break;
        }
        report(0.98f, "Rounding cover to integers");
        size_t violatedConstraints = 0;
        const double constraintResidual = s.constraintResidual(1e-6, &violatedConstraints);
        result->set("converged", s.converged() ? 1.0 : 0.0);
        result->set("integrality_residual", s.integralityResidual());
        result->set("rounded_energy", s.energy());
        result->set("constraint_residual", constraintResidual);
        result->set("violated_constraints", (double)violatedConstraints);
        appendUvOrientation(result, "rounded", measureUvOrientation(cornerUvs(s, uvVariables)));
        values->resize(variables);
        for (size_t i = 0; i < variables; ++i)
            (*values)[i] = s.value(i);
        return s.converged();
    }

    void buildResultUv(const SurfaceMesh& mesh, const std::vector<int>& rotation,
        const std::vector<double>& allValues,
        size_t uvVariables, QuadParameterizer::Result* result, DiagnosticRecord* diagnostics)
    {
        std::vector<double> uv(allValues.begin(), allValues.begin() + uvVariables);
        for (double& coordinate : uv) {
            const double integer = std::round(coordinate);
            if (std::fabs(coordinate - integer) < 0.01)
                coordinate = integer;
        }
        // The map quad extraction actually sees, after the snap above.
        appendUvOrientation(diagnostics, "snapped", measureUvOrientation(uv));
        result->singularVertices.clear();
        for (size_t vertex = 0; vertex < mesh.vertexCount(); ++vertex) {
            const auto& fan = mesh.cornersAroundVertex(vertex);
            int sum = 0;
            bool boundary = false;
            for (size_t c : fan) {
                sum = (sum + rotation[c]) % 4;
                if (mesh.oppositeCorner(c) == SurfaceMesh::npos)
                    boundary = true;
            }
            if (!boundary && sum != 0)
                result->singularVertices.push_back(vertex);
        }
        result->triangleUvs.assign(mesh.faceCount(), std::vector<Vector2>(3));
        for (size_t f = 0; f < mesh.faceCount(); ++f)
            for (size_t l = 0; l < 3; ++l) {
                size_t c = 3 * f + l;
                result->triangleUvs[f][l] = Vector2(uv[2 * c], uv[2 * c + 1]);
            }
    }

}

bool QuadParameterizer::parameterize(const std::vector<Vector3>& vertices,
    const std::vector<std::vector<size_t>>& triangles,
    const std::vector<Vector3>* guidance, double quadEdgeLength,
    double hardEdgeDegrees, Result* result,
    const std::vector<double>* faceScaling,
    const std::vector<double>* faceScalingU,
    const std::vector<double>* faceScalingV,
    const ProgressHandler* progressHandler)
{
    const auto report = [progressHandler](float fraction, const char* name) {
        if (nullptr != progressHandler && *progressHandler)
            (*progressHandler)(fraction, name);
    };

    if (vertices.empty() || triangles.empty() || !(quadEdgeLength > 0.0))
        return false;
    report(0.0f, "Initializing cover field");
    SurfaceMesh mesh(vertices, triangles);
    if (mesh.faceCount() != triangles.size())
        return false;
    const size_t corners = mesh.cornerCount();
    const size_t uvVariables = 2 * corners;
    const double scale = std::max(1e-12, quadEdgeLength);

    std::vector<Vector3> normals;
    initializeFieldAndNormals(mesh, guidance, &normals, &result->field);
    {
        // Faces where unit() had to fall back because a normal or a projected
        // guidance direction had (near) zero length.
        const bool hasGuidance = guidance && guidance->size() == mesh.faceCount();
        size_t zeroNormals = 0, zeroGuidance = 0;
        for (size_t f = 0; f < mesh.faceCount(); ++f) {
            const Vector3 normal = mesh.faceNormal(f);
            if (normal.length() < 1e-12)
                ++zeroNormals;
            if (hasGuidance) {
                const Vector3 projected = (*guidance)[f] - normals[f] * Vector3::dotProduct((*guidance)[f], normals[f]);
                if (projected.length() < 1e-12)
                    ++zeroGuidance;
            }
        }
        {
            DiagnosticRecord record("cover_input");
            record.set("faces", (double)mesh.faceCount());
            record.set("vertices", (double)mesh.vertexCount());
            record.set("scale", scale);
            record.set("zero_normal_faces", (double)zeroNormals);
            record.set("zero_guidance_faces", (double)zeroGuidance);
            result->diagnostics.push_back(std::move(record));
        }
    }
    const std::vector<Vector3> fieldBeforeBrush = result->field;

    std::vector<double> activeScalingU(mesh.faceCount(), 1.0), activeScalingV(mesh.faceCount(), 1.0);
    const bool trackDirectionalScale = faceScalingU && faceScalingV
        && faceScalingU->size() == mesh.faceCount() && faceScalingV->size() == mesh.faceCount();
    if (trackDirectionalScale) {
        activeScalingU = *faceScalingU;
        activeScalingV = *faceScalingV;
    }

    report(0.04f, "Smoothing cross field");
    if (!(guidance && guidance->size() == mesh.faceCount()))
        smoothCrossField(mesh, normals, hardEdgeDegrees, &result->field);
    brushFieldAlongSpanningTree(mesh, normals, &result->field);

    report(0.14f, "Computing corner rotations");
    const std::vector<int> rotation = computeCornerRotations(mesh, result->field, normals);
    result->cornerRotations = rotation;
    const std::vector<signed char> cornerConstraints = computeCornerConstraints(mesh, result->field,
        normals, hardEdgeDegrees);
    if (trackDirectionalScale)
        applyDirectionalSwaps(mesh, fieldBeforeBrush, result->field, normals,
            &activeScalingU, &activeScalingV);
    report(0.20f, "Correcting field curl");
    DiagnosticRecord curlDiagnostics("curl_correction");
    applyCurlCorrection(mesh, normals, rotation, cornerConstraints,
        faceScaling, scale, 1e-4, &activeScalingU, &activeScalingV, &result->field,
        &curlDiagnostics);
    result->diagnostics.push_back(std::move(curlDiagnostics));
    const std::vector<char> seam = computeSeam(mesh, rotation);

    const CoverContext ctx { mesh, result->field, normals, rotation, seam, cornerConstraints,
        activeScalingU, activeScalingV, faceScaling, scale };

    // The cover solve reports on its own 0..1, so remap it into the tail of this
    // function's range and keep the fractions monotonic end to end.
    ProgressHandler coverProgress;
    if (nullptr != progressHandler && *progressHandler) {
        coverProgress = [progressHandler](float fraction, const char* name) {
            (*progressHandler)(0.35f + 0.63f * fraction, name);
        };
    }
    std::vector<double> allValues;
    DiagnosticRecord coverResult("cover_result");
    if (!solveQuadCover(ctx, &allValues, coverProgress ? &coverProgress : nullptr,
            &result->diagnostics, &coverResult)) {
        coverResult.set("ok", 0.0);
        result->diagnostics.push_back(std::move(coverResult));
        return false;
    }

    report(0.99f, "Building cover uvs");
    buildResultUv(mesh, rotation, allValues, uvVariables, result, &coverResult);
    coverResult.set("ok", 1.0);
    result->diagnostics.push_back(std::move(coverResult));
    return true;
}
}
