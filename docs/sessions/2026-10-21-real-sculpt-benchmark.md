# 2026-10-21 · Claude (cloud) · Real sculpt models benchmark
- Repos/commits: master 4e9cdc7, Kajetan's add-on build 4d15d5f, libQEx variant 1 from PR #60 (3a84e77).
- Did: ran Kajetan's first real sculpts (head, crumpled cube, a sword of three joined parts; private,
  kept out of the repo) through `ab.py` at 1.5k-24k with 5 float32 replicates on all three builds.
  `ab.py` and `sculpt_report.py` read a private mesh set from `AR_CORPUS` (this PR).
  Measured where folds, non-quads and holes sit, and how many folds a vertex-only untangling removes.
  Note with metrics: research/real-sculpts-2026-10-21.md (project files).
- Found: 4d15d5f reproduces his Blender panel exactly. On the head, 96-100 % of folds, non-quads and hole
  edges sit within 2 h of the input's own self-intersections (5-10 % of the area); from 6k up 5-6 of 6
  runs open holes in the closed head. On the sword all folds sit on the vine ribbons, 83 % where they are
  thinner than a quad; joining the parts is not the cause. Quads follow area, not detail. Master
  regression: the input pre-pass glues a fin onto the sword's blade and the blade collapses
  (6-13 quads instead of ~1,050). libQEx: all-quad on head and cube, but one abort and two 8.3 GB runs; it
  falls back on the sword's vines.
- Measured: see the note; vertex-only untangling removes 0-48 % of folds (sword 6 %).
- Next: fix the blade collapse (own thread); add these runs to the 6.1b and 5.3 gates; show opened
  holes in the panel (ENVELOPE §3.2).
