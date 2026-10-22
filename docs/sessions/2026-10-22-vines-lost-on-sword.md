# 2026-10-22 · cloud thread "Vines lost at 3k on sword" · non-manifold islands skipped libQEx
- Repos/commits: core master 0e9bec8 (libQEx default + fold repair), compared with 158b12e (before #72) and 4d15d5f.
- Did: reproduced Kajetan's Blender report (private joined sword, Quality 3000: 1979 quads, vines mostly gone,
  no warning) with `ab.py` on the private `realsword` set, 2k-6k, 6 replicates. Found the cause, fixed it in
  `extractWithQex` (cut each vertex into one copy per fan of manifold, oppositely oriented edges before OpenMesh),
  added a unit test (three sheets on one edge) and #75's `area_uncovered` as a `compare --per-run` column.
- Found:
  - The sword's vine island has 33 edges with three triangles (ribbons glued along an edge). OpenMesh refused
    every such island, so it always fell back to our tracing: master, `--extractor trace` and 158b12e give the
    same vine output, so the loss is old, not a libQEx regression. The tracer drops part of the vines in a
    replicate-dependent way (3k: 4 of 6 replicates lose 54-56 % of the vine surface; 4k: 3 of 6 lose ~17 %).
  - With the cut, libQEx runs on the vines. Two cleanup passes in `finishMesh` still delete thin-strip quads:
    `collapseThreeValenceEdgePairs` 8-10 % of the vine faces at 3k-6k, `repairTopology` 38 % at 2k (probe build,
    face count per step). The stress-test thread found the same pass on thin capsules.
  - Geometric limit: half of the vine area is thinner (ray-cast shape diameter) than 14 units; one quad edge is
    13 at 3k and 9.2 at 6k. Below about two quads across, some loss is unavoidable.
  - Fold repair on the private meshes (instrumented build, reason of the last failed attempt per cluster): head
    385 → 66 folded faces, cube 45 → 8, sword 0 of 33 spots; skips are non-disk patches, folds that keep growing
    past 8 rings, mostly steep patches and repairs that do not reduce the flags. On the sword the "folds" sit on
    ribbons thinner than the detector's radius (19 units), so many are likely false positives.
- Measured (`ab.py compare`, realsword sword 2k-6k × 6 replicates, master → fix): non-quads 179 → 1,
  SJ ≤ 0 ×0.70, folded faces ×0.61, Hausdorff ×0.85, count error ×0.51, area_uncovered 0.138 → 0.094
  (3k 0.247 → 0.098, 4k 0.132 → 0.044), islands dropped 1.17 → 0 per run, libQEx fallbacks 48 → 0. Corpus (72 runs), closed (78) and realsculpt (6): identical.
- Next: the thin-strip cleanup passes (separate PR); a panel warning when the output leaves part of the input
  uncovered (share of input area farther than one quad edge from the output, per island); thickness-aware
  fold detection (radius below the local thickness).
