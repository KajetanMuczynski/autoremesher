# 2026-10-21 · Claude (cloud thread "Check the map before extraction") · validity check of the map before extraction
- Repos/commits: core branch `claude/project-thread-ebvmti` on master 124aeb8; note research/map-check-2026-10-21.md
- Did: added `checkIntegerGridMap` (`src/AutoRemesher/mapcheck.{h,cpp}`), stage `map_check` per island, diagnostic
  only: flipped/degenerate triangles and their clusters, cones off the grid / in folds / closer than 0.5 q, handle loops
  by tree-cotree holonomy (lattice of unrotated translations; zero vector = collapsed), boundary loops that lose their
  width. Unit test `tests/map_check_test.cpp`; scorer `tools/bench/map_check_eval.py`.
- Found: a map that passes never gave wrong topology, but nearly every corpus map fails (flips), and within runs whose
  1-ulp replicates disagree the check cannot tell the failing replicate apart. Not a gate; no reject-and-re-round.
  Pinched boundary loops and 2 q handle rings predict where `extractMesh` fails (human_neutral mouth, tori), and the
  rings show the 2ℤ² seam lattice.
- Measured: ab.py, corpus + closed, 5 float32 replicates (900 replicate-runs) on 11a4fe4: map valid → right topology
  217/217; "invalid" fires in 98 % (corpus) / 55 % (closed), lift 1.0; within-run separation 0.46–0.62 for extra
  handles, non-quads, folded quads; pinched loop recall 1.00 for split loops (12/12 human_neutral 2k, 0/12 at 10k);
  ring of 0 or 2 q: 6 firings, 5 lost handles of 8 (closed). Outputs byte-identical to master on 150 plain runs;
  about 0.05 s per run.
- Next: re-score the check against the extractor from 6.1; use `map_handle_translation` in the ℤ² seam lattice A/B and
  the share of `map_valid` islands as the target for map work (7.2).
