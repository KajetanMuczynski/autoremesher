# 2026-10-21 · Claude (cloud) · Net effect of today's merges
- Repos/commits: Kajetan's last tested build 4d15d5f; master 9e84f93 (after #65) and 9648bb6 (after #67);
  bisect points 7998e98 (#48), 97d61e9 (#51), 4e9cdc7 (#56), e7a0ea2 (#61), fc1e812 (#62).
- Did: `ab.py run <ref> --replicates 5 --jobs 4 --timeout 1200` on corpus, closed, sculpt, brush and the
  private realsculpt/realsword sets (`AR_CORPUS`), 1,428 runs per ref; `compare` A→C and B→C per set;
  bisected by PR every metric that got worse. Non-manifold vertices counted from out.obj for every ref
  (the CLI report has them only since #65, so older refs read 0 there). Note, tables and scripts:
  research/net-effect-2026-10-21.md and research/net-effect-2026-10-21/ (project files).
- Found: net improvement; no gate worse, no run broken in all replicates on any set. Overall
  4d15d5f → 9648bb6: all-quad runs 548 → 612, non-quads 9232 → 6299, folds 4896 → 2955, holes 214 → 45,
  runs with a non-manifold edge or vertex 11 → 2, p99 geo-mean ×0.78, Hausdorff ×0.84. Got worse:
  sword blade faces flipped vs input 241 → 1861 (#51, + #67 at 12k), most likely an artifact: the raw blade
  is inconsistently oriented, #51 reorients 4 triangles, and every flipped face sits over that patch;
  closed non-quads 756 → 824 and valence 2/≥7 137 → 182 (#61, then #67); corpus topology right 365 → 355
  of 432 (csg_bracket and human_neutral, #61 and #67; trend, not unanimous); brush flip-free runs 95 → 87
  (#61, #62, #67). Head: little change (non-quads 253 → 224, folds 132 → 134, holes 6 → 4 runs).
- Measured:

  | family (runs) | all-quad | non-quads | folds | flipped vs input | holes | topology right | p99 geo | Hausdorff geo |
  |---|---|---|---|---|---|---|---|---|
  | corpus (432) | 135 → 167 | 2888 → 2786 | 1439 → 974 | 3890 → 3069 | 13 → 1 | 365 → 355 | ×0.87 | ×0.94 |
  | closed (468) | 277 → 275 | 756 → 824 | 1209 → 716 | 2599 → 1628 | 0 → 0 | 460 → 459 | ×0.80 | ×0.82 |
  | sculpt (252) | 63 → 96 | 3377 → 576 | 655 → 249 | 1940 → 1718 | 39 → 0 | 205 → 212 | ×0.56 | ×0.64 |
  | brush (144) | 67 → 68 | 623 → 598 | 286 → 229 | 750 → 821 | 1 → 0 | 136 → 136 | ×0.90 | ×0.96 |
  | private head + cube (36) | 0 → 0 | 473 → 404 | 176 → 156 | 573 → 532 | 6 → 4 | 27 → 31 | ×0.92 | ×1.02 |
  | private sword set (96) | 6 → 6 | 1115 → 1111 | 1131 → 631 | 4952 → 6568 | 155 → 40 | 24 → 24 | ×0.79 | ×0.82 |

  Time (CLI sum under `--jobs 4`): corpus +12 %, brush +16 %, within this container's ±30 % load noise.
- Next: measure flips against the cleaned input in metrics.py (TODO 1.4) to settle the blade; 10-replicate
  re-run of csg_bracket and human_neutral if V6 is ratcheted on the corpus.
