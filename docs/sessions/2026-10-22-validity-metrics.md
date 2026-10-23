# 2026-10-22 · cloud thread "Validity metrics and re-baseline" · validity metrics in metrics.py
- Repos/commits: master 0e9bec8 (libQEx default); tools only, no core change.
- Did: `metrics.py` measures flips (V3) and normal deviation (D3) against the input oriented the way
  the core's `orientInput` (#51) orients it; the old count stays as `faces_vs_raw_input`. New
  `validity` block per input island (matched to output islands by nearest input triangle): dropped,
  split, merged, Euler characteristic / boundary loops changed, holes added or closed, handles lost or
  added, non-manifold vertices from the OBJ, folded faces of any size, input area not covered within one
  output edge and area under an output face facing the other way (thin parts collapsed into one sheet).
  Input islands that are not manifold themselves are counted and left out of the topology counts.
  `ab.py compare` gains these rows and a per-island topology line (additive; no row renamed);
  it warns when a side was measured by an older metrics.py. `nonmanifold_vertices` moved from
  `sculpt_report.py` into `metrics.py`. Unit tests: `tools/bench/tests/test_validity_metrics.py`.
- Found: the raw-vs-oriented difference touches only inputs with a turned patch: of all corpus, closed,
  sculpt, brush and private inputs only the sword parts (blade 4, vines 10, joined 14 triangles, same
  counts as the core's `input_flipped_triangles`) and sculpt_dirty (240) are reoriented, so every other
  run keeps its flip count exactly. The blade's input has 6 edges shared by three triangles (the glued
  fin); every blade run splits the fin off as a disc, which the global `same_as_input` read as a new hole.
- Measured (master 0e9bec8, realsword, 6 replicates per run, `ab.py`): sword blade faces flipped vs
  input 1801 (raw) → 495 (oriented) over 24 replicate-runs; at 24k u0 and 12k u0 none of the remaining
  flips lies over the 4 reoriented triangles: they sit over 6 input triangles near the blade tip
  (0.8 diagonal from the fin), so they are real flips, not the artifact.
- Next: re-baseline TARGETS on master with these metrics (all sets, 5 replicates, private sets as
  metrics only); TODO 1.14 homology check stays open (a handle lost and another added in the same island
  still passes).
