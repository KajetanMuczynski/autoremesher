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
#include <AutoRemesher/Predicates>
#include <cmath>
#include <limits>

namespace AutoRemesher {
namespace Predicates {

    namespace {
        // Error bound of the plain determinant (Shewchuk's ccwerrboundA):
        // if |det| exceeds it, the rounded result already has the right sign.
        const double epsilon = std::numeric_limits<double>::epsilon() / 2.0;
        const double orientBound = (3.0 + 16.0 * epsilon) * epsilon;

        inline void twoSum(double a, double b, double* sum, double* error)
        {
            const double s = a + b;
            const double bVirtual = s - a;
            const double aVirtual = s - bVirtual;
            *error = (a - aVirtual) + (b - bVirtual);
            *sum = s;
        }

        // a * b = product + error exactly; fma rounds once, so its residual is
        // the exact rounding error of the product.
        inline void twoProduct(double a, double b, double* product, double* error)
        {
            *product = a * b;
            *error = std::fma(a, b, -*product);
        }

        // Adds `value` to the expansion h[0..length), which stays
        // non-overlapping and ordered by increasing magnitude.
        inline void growExpansion(double* h, int* length, double value)
        {
            double q = value;
            for (int i = 0; i < *length; ++i)
                twoSum(q, h[i], &q, &h[i]);
            h[(*length)++] = q;
        }

        int exactOrient2d(const Vector2& a, const Vector2& b, const Vector2& c)
        {
            // (ax - cx)(by - cy) - (ay - cy)(bx - cx) expanded into six
            // products, so no subtraction rounds before the exact sum.
            const double terms[6][2] = {
                { a.x(), b.y() },
                { -a.x(), c.y() },
                { -c.x(), b.y() },
                { -a.y(), b.x() },
                { a.y(), c.x() },
                { c.y(), b.x() },
            };
            double h[12];
            int length = 0;
            for (const auto& term : terms) {
                double product, error;
                twoProduct(term[0], term[1], &product, &error);
                growExpansion(h, &length, error);
                growExpansion(h, &length, product);
            }
            // The most significant non-zero component carries the sign.
            for (int i = length - 1; i >= 0; --i) {
                if (h[i] > 0.0)
                    return 1;
                if (h[i] < 0.0)
                    return -1;
            }
            return 0;
        }
    }

    int orient2d(const Vector2& a, const Vector2& b, const Vector2& c)
    {
        const double left = (a.x() - c.x()) * (b.y() - c.y());
        const double right = (a.y() - c.y()) * (b.x() - c.x());
        const double determinant = left - right;
        const double bound = orientBound * (std::fabs(left) + std::fabs(right));
        if (determinant > bound)
            return 1;
        if (-determinant > bound)
            return -1;
        return exactOrient2d(a, b, c);
    }

}
}
