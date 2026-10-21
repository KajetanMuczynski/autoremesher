# 2026-10-21 · Claude (cloud thread "Split ears in the untangled map") · TODO 3.9 feature ears
- Repos/commits: core master 7aae3fe; ear-split experiment kept as a patch only (research/feature-ears-scripts/ear-split.patch)
- Did: classified the pinned faces that untangling leaves (instrumented build), implemented the ear split (midpoint
  of the free edge of every triangle with two near-parallel feature edges, plus a unit test) and A/B'd it against master
  with `ab.py`: corpus × 6 float32 replicates and the closed set.
- Found: only 324 of 2314 pinned faces are ears; 86 % lie in feature strips narrower than half a quad in the
  continuous map (5.3). The ear split makes the output worse, so 3.9 is closed as not adopted. human_neutral Fast 2k's
  mouth is not an ear problem.
- Measured: corpus final flips ×1.09 (30 worse / 5 better), degenerate ×0.93, non-quads ×1.00, plane Fast 2k topology wrong
  in 6/6; closed flips ×1.24, p99 ×1.07 (research/feature-ears-2026-10-21.md).
- Next: 5.3 (infeasible strips: drop the constraint or keep one quad, by A/B); human_neutral mouth with 2.13.
