# 2026-10-22 · Claude (cloud thread "Thin feature strips in the map") · TODO 5.3 narrow feature strips, not adopted
- Repos/commits: code was PR #58 (branch claude/project-thread-9egfhk, closed unmerged); A/B bases master 9648bb6
  (2026-10-21) and 0e9bec8 (libQEx default, 2026-10-22). This record is docs only.
- Did: classified the pinned faces left after untangling (instrumented build); intervention test (two-pass
  release of the strips' constraints); built the release as a continuous probe solve before the cover
  (boundary edges kept); A/B against master before and after libQEx became the default.
- Found: strips cause the defects near them (release removes 37 % of the non-quads and 38 % of the folds
  within h of a strip). Under libQEx default that no longer matters: libQEx already leaves ~0 non-quads, and
  released strips make libQEx fall back more often, which brings our extractor's non-quads back.
- Measured (ab.py vs 0e9bec8): corpus libQEx fallbacks 1 → 3, non-quads 0 → 40, SJ ≤ 0 85 → 98, p99 ×0.98;
  6 strip meshes × 6 replicates fallbacks 1 → 7 of 144, non-quads 3.7 → 22 per replicate, p99 ×0.94,
  human_neutral Fast 2k topology 6/6 → 2/6; closed set better (SJ ≤ 0 134 → 101, p99 ×0.96, topology 78/78
  both); sculpt set neutral; Kajetan's private sculpts neutral to slightly worse (metrics only).
- Next: revisit with 5.2 (crease alignment): strips as hard alignment that libQEx accepts.
  Notes and tables: research/thin-strips-2026-10-21.md, research/thin-strips-2026-10-22-libqex.md,
  research/thin-strips-scripts/.
