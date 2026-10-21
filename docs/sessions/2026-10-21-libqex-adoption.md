# 2026-10-21 · cloud thread "libQEx adoption 6.1b" · libQEx as the default extractor
- Repos/commits: core master `223e987` (#60, #63 merged), then `b4995a6` merged in → branch
  `claude/project-thread-u7tk6v`, PR #72, head `dc30f24` plus docs.
- Did:
  - Vendored libQEx 517dcaa and the OpenMesh 9.1.0 core (BSD-3). The OpenMesh notice goes into the add-on zip
    under `licenses/`.
  - Patched libQEx so that every hang, crash and runaway found ends in `QEx::Abort`
    (`thirdparty/libQEx/PATCHES.md`).
  - Made libQEx the default extractor, with a per-island fallback to our tracer; `--extractor trace` keeps
    the old path. An island that libQEx extracted and that has more handles than T after the repair is traced
    again.
  - Recorded per-island extractor stages, keeping superseded retry attempts.
  - Taught `ab.py compare` to report fallbacks, with folds and topology on exactly those runs, and the worst
    run's time and memory ratio.
  - Added CI fixtures: three recorded folded maps in `tests/data/`.
- Found:
  - libQEx has four loop sites, not two: vertex rotations broken by its own `add_face` and by OpenMesh's
    `delete_face`, the connection-repair do-loop, and `find_path` on degenerate triangles.
  - The A/B found three more problems:
    - on `sculpt_parts`, a one-way local edge in `add_face` (segfault);
    - on `sculpt_parts`, a face loop cut open during the n-gon merge (4–12 GB);
    - on suzanne_sub2 Q5000 and hammer F10000, extra handles across folds.
  - A handle check on the raw libQEx output misfires (110 of 432 corpus runs): it is torn by dropped faces and
    pinches. The check after the repair, with fans counted apart, falls back only on real cases.
  - The 8.3 GB head runs of #60 were a heap overflow through halfedge index −1.
- Measured: ab.py ×6 against `b4995a6`, research note `qex-adoption-results-2026-10-21.md`.
  - 0 failures or timeouts in 1,482 replicate-runs.
  - Worst run: time ×1.50 (sub-second), memory ×1.03.
  - Non-quads: corpus 464 → 4.7, closed 137 → 1, brush 100 → 2.3, head and cube 67 → 0.
  - Topology right: corpus 59.2 → 66.5; nothing broken unanimously on any set.
  - Trace path byte-identical to master in 900 of 900 runs.
  - The collapsed-blade fidelity loss of the first round is gone since the needle-tip fix.
- Next: pass the field's cone valences to libQEx (own A/B).
