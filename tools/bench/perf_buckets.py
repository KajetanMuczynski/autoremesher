#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Group a `perf report` symbol listing into cost buckets.

    perf record -e cpu-clock -F 999 -g -o perf.data -- ar_bench ...
    perf report -i perf.data --no-children --sort symbol --stdio -g none > perf.txt
    python perf_buckets.py perf.txt

Buckets are matched in order on the demangled symbol (self time only).
"""
import re
import sys
from collections import defaultdict

BUCKETS = [
    ("allocator (malloc/free/new)", r"(^|[^a-z])(_int_malloc|_int_free|malloc|cfree|free|malloc_consolidate|unlink_chunk|"
                                    r"operator new|operator delete|_int_realloc|realloc|calloc|tcache)"),
    ("std::map / std::set (red-black tree)", r"_Rb_tree|std::map<|std::set<|_Rb_tree_increment|_Rb_tree_insert"),
    ("std::unordered_* (hash tables)", r"_Hashtable|unordered_map|unordered_set|_Map_base|_Prime_rehash"),
    ("Eigen sparse Cholesky (analyze+factor+solve)", r"SimplicialCholesky|SimplicialLDLT|factorize_preordered|"
                                                     r"ordering_helper|amd_|AMDOrdering|minimum_degree|cholmod|"
                                                     r"TriangularView|sparse_solve_triangular"),
    ("Eigen sparse products / assembly", r"Eigen::.*(Product|SparseView|setFromTriplets|conservative_sparse|"
                                         r"SparseMatrix.*operator=|transpose|Triplet|prune)"),
    ("isotropic remesher", r"IsotropicRemesher|IsotropicHalfedgeMesh|AxisAlignedBoudingBoxTree|"
                           r"AxisAlignedBoundingBox"),
    ("quad extractor", r"QuadExtractor"),
    ("parameterizer / field / MILS", r"QuadParameterizer|Parameterizer|FrameField|SingularitySimplifier|"
                                     r"MixedIntegerLeastSquares|ConstrainedLeastSquares|SurfaceMesh"),
    ("meshoptimizer decimation", r"meshopt"),
    ("OBJ load/write", r"tinyobj|LoadObj|strtod|fprintf|vfprintf|__printf|_IO_|parseReal|tryParseDouble"),
    ("memcpy/memmove/memset", r"__memmove|__memcpy|__memset|memcpy|memmove|memset"),
    ("TBB scheduler", r"tbb::|r1::"),
]


def main():
    path = sys.argv[1]
    totals = defaultdict(float)
    top = []
    for line in open(path, errors="replace"):
        m = re.match(r"\s*([0-9.]+)%\s+\[[.k]\]\s+(.*)$", line)
        if not m:
            continue
        pct, sym = float(m.group(1)), m.group(2).strip()
        top.append((pct, sym))
        for name, pattern in BUCKETS:
            if re.search(pattern, sym):
                totals[name] += pct
                break
        else:
            totals["other"] += pct
    print("| bucket | self time % |\n|---|---|")
    for name, pct in sorted(totals.items(), key=lambda kv: -kv[1]):
        print("| %s | %.1f |" % (name, pct))
    print("\nTop symbols:")
    for pct, sym in sorted(top, reverse=True)[:15]:
        print("%6.2f%%  %s" % (pct, sym[:160]))


if __name__ == "__main__":
    main()
