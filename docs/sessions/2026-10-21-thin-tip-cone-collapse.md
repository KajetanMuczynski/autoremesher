# 2026-10-21 · cloud thread · Thin tip cone collapse
- Repos/commits: core on master a5e983a, branch claude/project-thread-agc02k
- Did: traced the joined sword's blade collapse (837 quads at 3k on master) reported by the real-sculpt benchmark.
  Not a regression of #51: 4d15d5f folds the same blade part at other targets (1000, 1150; master at 1000, 1217);
  #51 only closes a flipped 4-triangle patch, which moves the targets that hit it. Fixed the cause in the cross field
  and cover (TODO 2.19), with a procedural-blade test.
- Found: at a needle tip (the blade's remeshed tip: 4 edges, all sharp 160-176°) the rounded field asks for cone angle 0
  (valence 0). Valence 0 and 1 fold the whole continuous map (about 50 % of the area flipped, rescale 1e4-1e17);
  valence 2 and 3 do not. Releasing the sharp-edge locks around the tip is not enough: a free field also gives angle 0
  at tips with angle sums near 1 rad. The singularity simplifier summed quarter turns mod 4 and read a valence-1 tip
  (+3) as a valence-5 cone (-1), so it could cancel it into a valence-0 tip. A first version of the exact charges had
  the opposite sign to the simplifier's jumps and cancelled 2 pairs instead of 4238 on the corpus (flips x1.9): caught
  by the A/B. Procedural rhombus blades (no folded or non-manifold input) collapse at 18 of 44 targets on master,
  0 of 44 with the fix (CLI, not ab.py).
- Measured: ab.py corpus master vs fix (1 replicate): final flips x0.97, non-quads x1.01, p99 x0.99, topology 61 -> 62
  of 72. Minimum valence 3 instead of 2: flips x1.22. Closed set and replicates: see the PR.
- Next: the fold-repair thread removes the sword's folded-input trigger; valence-2 tips still give a doublet.
