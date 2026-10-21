# 2026-10-21 · Claude (cloud thread) · Project output onto input surface (TODO 2.8)
- Repos/commits: core branch `claude/project-thread-m2z18q`, PR #48, on master 4d15d5f.
- Did: checked the premise first by projecting all 72 master corpus outputs onto the input after the fact
  (raw and with a fold guard), then built `SurfaceProjector` (new `src/AutoRemesher/surfaceprojector.*`,
  called per island after extraction in `autoremesher.cpp`; `closestPointOnTriangle` moved there from
  `quadextractor.cpp`), a unit test (`tests/surface_projection_test.cpp`) and `ab.py` rows for normal
  deviation, vertex-to-input distance and faces flipped against the input, plus `run --remeasure`.
- Found: the existing `smoothAndProject` projects onto T, not M, and cleanup moves vertices after it, so
  output vertices sat ~2.6·10⁻⁴ diag off M. Raw closest-point projection adds folds (SJ ≤ 0 237 → 322 in
  the post-hoc test); undoing the longest move of each face it makes worse removes the problem and even
  unfolds some faces. A strict "must face the landing face" guard gave most of that back; it is applied
  only to faces that faced the input before. The extra flipped-vs-input faces are rim faces of thin parts
  whose vertices land on opposite sheets: vertices whose closest input face faces away fell in every
  flagged run (thin_leaf Q2k 36 → 5, sword Q10k 74 → 28).
- Measured (`ab.py`, origin/master 4d15d5f vs PR head, 1 replicate; aggregates only, face lists identical
  in all 150 runs so no topology claim needs replicates): corpus mean distance ×0.691 (72/0), normal
  deviation ×0.864 (67/5), p99 ×0.914 (66/5), Hausdorff ×0.990, SJ ≤ 0 228 → 153 (16/0), flipped vs input
  636 → 530 (23/5), vertex distance → 0; closed set mean distance ×0.661, p99 ×0.783, SJ ≤ 0 229 → 168
  (30/0), flipped 535 → 402 (34/2). Projection 26.8 s of 463.5 s CLI time over the corpus. SJ 1st
  percentile corpus mean −0.002 (worst −0.06 at 2k), closed +0.023.
- Next: tangential, feature-aware relax after projection (rest of 2.8); re-baseline TARGETS "today" for
  D2/D3 and the vertex row; faces bridging thin rims belong to thin-part sizing (4.1).
