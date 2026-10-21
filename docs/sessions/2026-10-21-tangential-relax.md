# 2026-10-21 · Claude (cloud thread) · Tangential relax after projection (TODO 2.8)
- Repos/commits: core branch `claude/project-thread-84xa4a`, on master 7998e98 (after PR #48).
- Did: checked the headroom first without a build: `tools/bench/relax_probe.py` smooths the 72 master
  corpus outputs in Python and measures both sides (uniform tangential Laplace, parallelogram rule,
  crease snap at 40/60/90°, a bend lock). Then `SurfaceProjector::relax()` (crease snap + 5 rounds of
  tangential Laplace, same fold guard as the projection; the guard moved into a shared helper), called
  after `project()` in `autoremesher.cpp`; unit tests in `tests/surface_projection_test.cpp`;
  `metrics.py` and `ab.py` gained SJ 1st percentile (G1), skew 95th percentile (G2) and crease
  coverage (A1) rows, so TARGETS shape and crease rows come from `ab.py`.
- Found: the extractor's `smoothAndProject` already does 5 uniform Laplace rounds on T, so organic
  meshes have no headroom (G1 0.81 either way); hard surface, thin shells and scans do. The
  parallelogram rule (keeps graded and anisotropic grids) gains nothing. Snapping vertices next to a
  crease onto it is what lifts A1; at 40° it snaps to scan noise (scan G1 −0.08), so it uses the
  sharp-edge setting (90°). The first C++ version cut thin rims on the closed set (mean distance up to
  ×1.5 on ellipsoid 0.003/0.01): vertices whose faces bend > 45° from their normal now stay.
- Measured (`ab.py`, master 7998e98 vs d03b139 (same code as the PR head; later commits change
  comments and tools only, outputs checked byte-identical on 3 runs), 1 replicate, aggregates only;
  face lists identical in all 150 runs, so no topology claim): corpus SJ ≤ 0 153 → 132 (13 better,
  0 worse), mean distance ×0.966, p99 ×0.972, normal deviation ×0.927, skew p95 ×0.927, SJ p1
  0.663 → 0.674, crease coverage 0.062 → 0.105; closed set mean distance ×1.012, p99 ×1.012,
  SJ ≤ 0 168 → 160, normal deviation ×0.902. Relax 2.7 s of 371 s CLI time over the corpus.
- Next: a feature-aware `smoothAndProject` in the extractor (owner: extractor threads); crease-following
  layout (5.2–5.3) for A1 ≥ 0.6; a sizing-aware smoothing instead of uniform Laplace.
