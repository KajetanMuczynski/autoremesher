# meshoptimizer (vendored subset)

Upstream: https://github.com/zeux/meshoptimizer
Version: 1.2 (`MESHOPTIMIZER_VERSION 1020`)
License: MIT (see LICENSE.md)

Only the files needed for mesh simplification are vendored:

- `src/meshoptimizer.h`    - public API
- `src/simplifier.cpp`     - `meshopt_simplify`, `meshopt_simplifyScale`
- `src/indexgenerator.cpp` - `meshopt_generateVertexRemap`, `meshopt_remapVertexBuffer`,
                             `meshopt_remapIndexBuffer`

These two translation units link on their own; the rest of the library
(vertex cache optimisation, compression, meshlets) is not used here.

Used by `AutoRemesher::resample` as a decimation pre-pass for inputs that are
too dense for the isotropic remesher to coarsen directly.

## Local changes

One addition, marked "AutoRemesher local addition" in the source, not in
upstream: the option `meshopt_SimplifyKeepTopology` (bit 24, clear of
upstream's bits). With it the simplifier keeps the topology the indices
define: vertices with identical positions are not merged, and a collapse
that breaks the link condition (its two ends share a neighbour that is not
the apex of a triangle on the edge) is skipped. Without it, thin closed
shells and noisy scans came out of decimation with non-manifold edges
(gap scan 2026-10-19 item 6). Re-apply it when bumping the vendored version,
or drop it if upstream gains an equivalent option.
