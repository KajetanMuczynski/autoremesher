/*
 *  Copyright (c) 2020 Jeremy HU <jeremy-at-dust3d dot org>. All rights reserved. 
 *  Modifications Copyright (C) 2026 Quadami contributors, GPL-3.0-or-later (see LICENSE).
 *
 *  Permission is hereby granted, free of charge, to any person obtaining a copy
 *  of this software and associated documentation files (the "Software"), to deal
 *  in the Software without restriction, including without limitation the rights
 *  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 *  copies of the Software, and to permit persons to whom the Software is
 *  furnished to do so, subject to the following conditions:

 *  The above copyright notice and this permission notice shall be included in all
 *  copies or substantial portions of the Software.

 *  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 *  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 *  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 *  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 *  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 *  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 *  SOFTWARE.
 */
#include <AutoRemesher/PositionKey>
#include <cmath>

namespace AutoRemesher {

const double PositionKey::m_toIntFactor = 100000.0;

PositionKey::PositionKey(const Vector3& v)
    : PositionKey(v.x(), v.y(), v.z())
{
}

PositionKey::PositionKey(double x, double y, double z)
{
    m_position.setX(x);
    m_position.setY(y);
    m_position.setZ(z);

    m_cellX = std::trunc(x * m_toIntFactor);
    m_cellY = std::trunc(y * m_toIntFactor);
    m_cellZ = std::trunc(z * m_toIntFactor);
}

const Vector3& PositionKey::position() const
{
    return m_position;
}

bool PositionKey::operator<(const PositionKey& right) const
{
    if (m_cellX < right.m_cellX)
        return true;
    if (m_cellX > right.m_cellX)
        return false;
    if (m_cellY < right.m_cellY)
        return true;
    if (m_cellY > right.m_cellY)
        return false;
    if (m_cellZ < right.m_cellZ)
        return true;
    if (m_cellZ > right.m_cellZ)
        return false;
    return false;
}

bool PositionKey::operator==(const PositionKey& right) const
{
    return m_cellX == right.m_cellX && m_cellY == right.m_cellY && m_cellZ == right.m_cellZ;
}

}
