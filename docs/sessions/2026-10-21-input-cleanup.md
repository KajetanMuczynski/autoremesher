# 2026-10-21 · Claude (cloud thread "Input cleanup before remeshing") · Input cleanup pre-pass
- Repos/commits: core 7998e98 (base) → PR #51 (5b562f6 measured, master merged after: only the `--version` build id)
- Did: `AutoRemesher::cleanInput` (collapse edges up to 4 float32 ulps of the bbox diagonal, drop triangles with a
  repeated corner, per-part topology check) and `orientInput` (each manifold-connected piece takes the orientation
  of most of its area), run before island splitting; removed the duplicate collapse inside decimation; counts in the
  run diagnostics and the add-on panel ("Input cleanup"); `tests/input_cleanup_test.cpp`.
- Found: all 36,334 zero-area triangles of sculpt_degenerate sit on a zero-length edge (no collinear caps). A flipped
  patch is an island of its own because island splitting follows opposite half-edges.
- Measured (`ab.py`, master 7998e98 vs 5b562f6): closed identical; corpus 64/72 outputs byte-identical (blob_sym,
  cat change); sculpt ×6 replicates: sculpt_degenerate non-quads 2543 → 22, folds 379 → 7, time 1102 → 204 s;
  sculpt_dirty folds 176 → 86; whole sculpt set non-quads ×0.62. Watch item: sculpt_voxel Fast 5k topology 17/20 vs
  master 19/20 (noise level). Note: research/input-cleanup-2026-10-21.md (project files).
- Next: rest of TODO 2.7 (soups, duplicate faces, non-manifold vertices, scale normalisation).
