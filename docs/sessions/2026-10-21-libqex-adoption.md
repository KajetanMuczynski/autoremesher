# 2026-10-21 · cloud thread "libQEx adoption 6.1b" · libQEx as the default extractor
- Repos/commits: core master `223e987` (#60, #63 merged) → branch `claude/project-thread-u7tk6v` `7609364`.
- Did: vendored libQEx 517dcaa and the OpenMesh 9.1.0 core (BSD-3, notice in the add-on zip under
  `licenses/`), patched libQEx so every hang, crash and runaway found ends in `QEx::Abort`
  (`thirdparty/libQEx/PATCHES.md`), made it the default extractor with a per-island fallback to our tracer
  (`--extractor trace` keeps the old path), recorded per-island extractor stages, and taught `ab.py compare`
  to report fallbacks (per island and per retry attempt) with folds and topology on exactly those runs, and
  the worst run's time and memory ratio. CI fixtures: three recorded folded maps in `tests/data/`.
- Found: libQEx's loops are four, not two (vertex rotations broken by its own `add_face` and by OpenMesh's
  `delete_face`, the connection-repair do-loop, `find_path` on degenerate triangles). The first A/B found two
  more on `sculpt_parts`: a one-way local edge in `add_face` (segfault) and a face loop cut open during the
  n-gon merge (4–12 GB). The 8.3 GB head runs of #60 were a heap overflow through halfedge index −1.
- Measured: ab.py ×6 replicates, research note `qex-adoption-results-2026-10-21.md`. 0 failures or timeouts in
  1,338 replicate-runs; worst run time ×1.57 (sub-second), memory ×1.13; non-quads corpus 480.7 → 27,
  closed 126 → 1.3, sculpt 253.5 → 48.7, head/cube 78.8 → 7; topology right corpus 60.8 → 64.8; trace path
  byte-identical to master 900/900. Regression: collapsed blade maps (sword Q12000 Hausdorff ×3.9, 6/6).
- Next: pass the field's cone valences to libQEx (own A/B); blade maps are fixed by the blade-collapse work.
