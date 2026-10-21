# 2026-10-21 · cloud thread "libQEx extraction A/B" · TODO 6.1
- Repos/commits: core master 0729fa5; branch claude/project-thread-22ovl0 (QEx at 2a9083e, variant 3 at 7c1959c)
- Did:
  - Added an opt-in CMake switch `-DAUTOREMESHER_QEX=1|2|3` (default 0, not built by CI) that extracts with
    libQEx `517dcaa` and OpenMesh 9.1.0 core (both fetched pinned) instead of our graph tracing.
    The hook is one `#if` block in `QuadExtractor::extract()`; the bridge is `src/AutoRemesher/qexextraction.{h,cpp}`
    and drops QEx's boundary caps and its faces on edges used more than twice.
  - Extended `tools/bench/ab.py` with `--cmake-arg` (its own build and run key), `--timeout` (a hang counts as a
    failed run) and an 8 MB log cap.
  - Ran corpus and closed sets for master and 3 QEx variants with 5 float32 replicates.
  - Re-checked the licences (`docs/LICENSES.md`).
- Found:
  - Our extractor makes almost all non-quads; libQEx on the same map makes almost none.
  - Folds and flips against the input are mostly the map's.
  - libQEx hangs on folded maps: OpenMesh circulators loop on connectivity it builds inconsistently.
  - Out of the box it also caps boundary loops and leaves 4-face edges.
  - Upstream used libQEx until 2020-09 (`b2c46fc9`).
- Measured (research/qex-ab-2026-10-21.md, ab.py):
  - corpus 432 runs, QEx + cleanup vs master: all-quad 147 → 424, non-quads 2,884 → 5, folded quads
    1,638 → 1,055, topology right 366 → 388, p99 ×0.97, median time 3.1 → 2.3 s; 4 runs hang (sword).
  - closed 468 runs: non-quads 798 → 0, topology right 460 → 463, 1 hang, 4 runs at 40–255 s.
- Next: 6.1b (vendor libQEx with termination fixes and fallback, cone valences, then default); 6.2 on QEx output;
  try untangling the output quads in 3D for V2.
