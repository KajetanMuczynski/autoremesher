# 2026-10-20 · Claude (cloud) · Untangling the rounded cover (TODO 3.8)
- Repos/commits: core master 47529e1 (#40), branch claude/project-thread-f7uemq
- Did: TODO 3.8 with the three gap-scan items. Cone-winding count per vertex (`<prefix>_miswound_cones`
  and neighbours, continuous/rounded/untangled) first; `Untangler` (`src/AutoRemesher/untangler.{h,cpp}`,
  Garanzha et al. 2021 re-implemented from the paper, its own Hessian pattern analysed once per
  component, PSD projection, kept best map, patience 10) with an alignment term; `untangleCover` in
  `quadparameterizer.cpp` (2 rings around bad faces, integers held, one solve per connected component
  in parallel, accept only if fewer bad faces); MILS kernel accessors; the snap keeps a vertex
  unsnapped only where that rights triangles; `untangle_*` diagnostics as the infeasibility exit;
  `tests/untangle_test.cpp`; TODO 3.8 done, new 3.9.
- Found: the paper's energy depends on J only through tr JᵀJ and det J, so it lets the map rotate off
  the frames: it cut flips ×0.08–0.24 on 20 runs but did not lower folded quads or SJ ≤ 0 until
  α|J − I|² (α = 10) was added. Every degenerate face of the rounded map is degenerate by its integers
  alone; untangling never changes their count. 2310 corpus faces are degenerate by the constraints
  alone (two edges on one constrained isoline): TODO 3.9. The rest of what stays bad needs other
  integers: with the region's integers free 90 % of it untangles, but greedy re-rounding (a tenth
  per pass, untangling between) gives three quarters of that back at 12× the untangling time, so no
  re-rounding exit (experiment commit 1c588fa, not on any branch; patch in the research note's folder).
- Measured [M] (`ab.py`, origin/master 47529e1 vs 35eaab9, the PR code but for one unused include; 72-run corpus and 78-run closed set, one
  replicate; candidates over 5 float32 replicates): corpus flips 8634 → 2709, non-quads 661 → 507,
  SJ ≤ 0 250 → 237, irregular/1k ×0.95, Hausdorff ×0.98; closed flips 5096 → 562, non-quads 170 → 140.
  Topology 63 → 61/72 and 75 → 76/78; replicates: thin_leaf Q10k 4/6 → 6/6, human_neutral F2k 5/6 → 0/6
  (mouth hole bridged: one 13-edge loop becomes 5 + 4 edges and a handle), sword Q10k 3/6 → 1/6,
  csg_bracket F2k 4/6 → 2/6, torus_0.03 F150 1/6 → 2/6. Time: 5 large Quality 10k meshes × 2
  replicates, one job, 276 → 271 s; untangling's own timer 3.3 % of the corpus.
- Next: 3.9 (ears), then re-check human_neutral F2k; the integer remainder goes to 7.2 or cone
  separation (3.3).
