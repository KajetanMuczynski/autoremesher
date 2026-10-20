/*
 *  Copyright (c) 2020 Jeremy HU <jeremy-at-dust3d dot org>. All rights reserved. 
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
#ifndef AUTO_REMESHER_POSITION_KEY_H
#define AUTO_REMESHER_POSITION_KEY_H
#include <AutoRemesher/Vector3>

namespace AutoRemesher {

class PositionKey {
public:
    PositionKey(const Vector3& v);
    PositionKey(double x, double y, double z);
    const Vector3& position() const;
    bool operator<(const PositionKey& right) const;
    bool operator==(const PositionKey& right) const;

private:
    // Coordinates scaled by m_toIntFactor and truncated toward zero: points in
    // the same 1e-5 cell share a key.  Held as doubles, not integers, so no
    // coordinate overflows: a 32-bit long (MSVC) wrapped beyond about 21,475
    // units and merged every far point into one key.  Below 2^53 the values
    // are exactly the integers the old long cast gave.
    double m_cellX = 0.0;
    double m_cellY = 0.0;
    double m_cellZ = 0.0;
    Vector3 m_position;

    static const double m_toIntFactor;
};

}

#endif
