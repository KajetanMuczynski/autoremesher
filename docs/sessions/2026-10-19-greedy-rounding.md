# 2026-10-19 · cloud thread "Fix the map: rounding and solver" · greedy rounding on one factorisation (TODO 3.2, 3.3)
- Repos/commits: core master `04e83ba` → PR #37 (branch `claude/project-thread-f7uemq`)
- Did: design critique of 3.1–3.3 before building. Then:
  - `ConstrainedLeastSquares::fixVariables`: held rows and columns are reduced to the diagonal, so the pattern and the analysis are kept (3.2).
  - Batched greedy rounding: the closest tenth per pass plus everything within 1e-3, ties by index (3.3).
  - Energy diagnostics and `tests/rounding_test.cpp`.
  - Corpus A/B against master with 1-ulp replicates, at adaptivity 0 and 1, on a closed set of thin ellipsoids and tori, plus timing.
  - Throwaway prototypes: geometric δ_k thresholds and the exact lattice (3.4).
- Found:
  - At default adaptivity 0.5 rounding made half of the final flips, not two thirds. The other half is in the continuous map, so no rounding order makes the map injective.
  - The exact lattice is far worse in our elimination basis (one mesh), so it needs 3.5 first.
  - 3.1's runtime backend selection would make macOS output differ from the other platforms, and the shipped CMake build never uses Accelerate.
  - Cone separation can't be checked per variable, because cones are not variables in our basis.
  - The face-tracing thread's closed-set generator was not kept, so the closed set is a reconstruction (`make_closed.py` in the research scripts).
- Measured: 72 corpus runs against master:
  - final UV flips 11480 → 8634 (made by rounding 5692 → 2846);
  - non-quads ×0.73, SJ ≤ 0 324 → 250, topology right 61 → 63/72;
  - integrality residual 0;
  - rounded / continuous energy 1.37 → 1.20.

  The gains hold over 1-ulp replicates (flips ×0.80, 28 of 36 runs fully separated) and at adaptivity 0 and 1.

  Genus is about neutral:
  - boat Q2k and sword Q10k fixed, thin_leaf Q10k broken, each in 6 of 6 replicates;
  - closed thin-shell set 75 → 74/78.

  Time: ×1.06 geo-mean; the rounding step is 1.4–3.5× master's, +16–26 % of the run at 50k quads. Details: [research/rounding-greedy-2026-10-19.md](../research/rounding-greedy-2026-10-19.md).
- Next: untangling with the integers fixed (new 3.8), or MIQ stiffening (3.6), now cheap. Then 3.5 → 3.4, and the 2.1 cone-collision count before any separation rule. 3.1: decision open, deferral recommended.
