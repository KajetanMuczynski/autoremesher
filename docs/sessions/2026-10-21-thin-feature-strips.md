# 2026-10-21 · Claude (cloud thread "Thin feature strips in the map") · TODO 5.3 narrow feature strips
- Repos/commits: core branch claude/project-thread-9egfhk (PR #58), base master 9648bb6.
- Did: classified the pinned faces left after untangling (instrumented build, not merged); tested whether
  they cause defects by releasing their constraints (two-pass hack); built the release as a continuous
  probe solve before the cover (`narrowStripVertices`, `narrowStripQuads = 0.5`), boundary edges excluded;
  diagnostics `feature_corners`, `feature_corners_released`; `ab.py compare` prints the released share and
  takes `--only`; test `narrow_strip_test` (Z fold); TARGETS watch row A1w; TODO 5.3.
- Found: pinned strips are tiny (median 2 triangles); about half sit at acute feature corners (< 60°),
  30 % between parallel lines. Output faces within h of a strip have 4.5× the non-quad and 4× the fold
  rate of faces near strip-free feature lines; releasing the strip's constraints removes 37 % of the
  non-quads and 38 % of the folds there, so the strips cause them. A geometric (frame-width) detector
  before the cover catches only a quarter of the strips; the continuous probe catches them like the
  two-pass oracle at one continuous solve. Releasing boundary constraints moves the output boundary
  (cloth_sheet p99 ×6), so boundaries are kept. An instrumented build (stderr prints only) changed 15 of
  72 outputs against master (codegen), so final numbers compare against master itself.
- Measured (ab.py vs master 9648bb6): corpus non-quads 483 → 380, SJ ≤ 0 160 → 118, degenerate ×0.56,
  p99 ×0.975, crease_cov 0.108 → 0.108, time ×1.03; 6 strip meshes × 6 replicates non-quads ×0.76,
  SJ ≤ 0 ×0.74, topology 16.2 → 19.2/24, nothing broken in every replicate; closed set non-quads
  156 → 102, topology 76 → 78/78; Kajetan's real sword neutral (non-quads ×1.02, SJ ≤ 0 ×1.04, time ×1.13).
  Released share 19.7 % of constrained corners on the corpus (csg_bracket 64 %).
- Next: add-on warning for released strips (Kajetan: warning, repair only as a clickable option);
  boundary-adjacent strips (release only the crease side); revisit A1w once 5.2 lifts A1.
  Note and scripts: research/thin-strips-2026-10-21.md, research/thin-strips-scripts/.
