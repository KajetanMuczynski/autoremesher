# 2026-10-21 · Claude (cloud thread "Seam lattice and lost handles") · seam lattice and rounding batch size
- Repos/commits: core master 4d15d5f; branch claude/project-thread-lb6w2x
- Did: probed the seam holonomy of every handle loop of T at the continuous, rounded and untangled
  stage (probe and scripts in research/seam-lattice-2026-10-21/); built ℤ² translations + integer cone
  uv (TODO 3.4); traced its corpus regression to the rounding batch size; fixed the batch size (3.3).
- Found: tori lose the meridian by rounding it to 2, not 0 (2ℤ²); demosthenes' tunnels have holonomy
  ≈ 1 quad, which no lattice keeps. The batch size counted nearly integral integers, so some islands
  rounded in ~5 coarse passes; that made most of ℤ²'s extra flips.
- Measured (ab.py, corpus + closed, plain + 5 float32 replicates): batch fix vs master corpus flips
  ×0.92, non-quads ×0.93, time ×1.09, closed neutral, genus unchanged. ℤ² vs 2ℤ² with the fix on both
  sides: corpus flips ×1.16, closed ×1.05, genus unchanged. 40 batches instead of the fix: same gain
  at time ×1.23.
- Next: V6 stays, narrowed to handles under 3 quads of holonomy (Kajetan's call; TARGETS not edited).
  ℤ² only with 7.2 or a cone-aware rounding order, and only together with the torus thread's extractor fix.
