# 2026-10-21 · Claude (cloud thread "Sculpt defects: eyeball caps and swirls") · real-sculpt defects and the brush set
- Repos/commits: core master `a5e983a`; this branch `claude/project-thread-4z5inw` (tools/bench only).
- Did: traced every defect class from Kajetan's Blender tests (private head and cube; meshes stay out of the repo)
  per location through the stages, with a research-only probe that dumps T, cones, corner locks and the continuous,
  rounded, untangled and snapped maps (`research/sculpt-defects-2026-10-21/probe-stages.patch`, not merged). Added
  the brush set (`make_sculpt.py --set brush`, twelve brush situations, corpus set `brush`), a geodesic folded-input
  detector (`sculpt_report.input_folds`, with the on-fold defect counts in its report) and its unit tests. Made
  `sculpt_parts`' eyeballs smooth.
- Found: on the head, the defects sit on folded triangles that are already in the input (twist pleats in both
  eye sockets, an over-pinched crease line). T keeps those folds, the sharp-edge test locks their edges, and the
  continuous map is already flipped there before any rounding. Master also opens holes there at 10k (5 of 6
  replicates), which the add-on panel does not show. Most cube defects sit in pinched grooves narrower than half a
  quad. The cube 10k handle (5 of 6) comes from the extractor at an overhanging lip, where the maps are clean.
  TODO 2.18's open eyeball caps were a test-set artefact: the generator gave the eyeballs the crumbs' 15 % radial
  noise, which made them crumpled balls.
- Measured (ab.py, 5 float32 replicates): see research/sculpt-defects-2026-10-21.md. Head 10k: 94 % of non-quads and
  99 % of SJ ≤ 0 quads within 1.5 h of folded input. Offline input unfolding: head 10k non-quads 26.7 → 2.7,
  SJ ≤ 0 21.8 → 0, topology 1/6 → 6/6, but p99 ×2.5 against the original input. sculpt_parts 5k with smooth
  eyeballs: topology right 2/6 → 6/6, non-quads 16 → 2.
- Next: Kajetan decides whether the core repairs folded input (proposed TODO 2.19); add-on warning for holes in
  closed islands and for folded input; after #58, keep fold edges out of the sharp-edge locks; after 6.1b, re-measure
  the holes and the handle.
