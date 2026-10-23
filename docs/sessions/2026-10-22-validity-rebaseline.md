# 2026-10-22 · cloud thread "Validity metrics and re-baseline" · TARGETS re-baseline on libQEx master
- Repos/commits: master c2ffd24 (libQEx default); tools and docs only.
- Did: `tools/bench/gates.py` computes every TARGETS §3 gate per family from an `ab.py` run folder
  (mean over replicates, unanimous count, defects per 1k, fidelity medians). `metrics.py`: an island counts
  as merged only when it has no output island of its own but is covered (the centroid vote also flagged
  small islands that touch a bigger one: human_neutral's eyes), and a split of a non-manifold input island
  is not counted. TARGETS §3 and §4 "today" columns re-measured.
- Measured: 1,482 replicate-runs (corpus, closed, sculpt, brush, Suzanne, private), all complete, 0
  non-manifold edges or vertices. V1–V5 together corpus 28.3/72 over replicates (33/72 plain, 19 in every
  replicate), closed 43.3/78; V3 is the binding gate; V6 corpus 66.5/72, closed 77.7/78. Thin ellipsoids and
  torus_0.03 at 150 quads collapse to blobs (up to 86 % of the input area uncovered) with "same" topology.
  Full note and critique: research/rebaseline-2026-10-22.md (project files).
- Next: coverage into ci/output_gate.py; input-fold mask for V3 and wrong-side area; TODO 1.14 (V6
  homology and loop-length exemption); decide whether to restore the all-quad V1.
