# 2026-10-22 · Claude (cloud, thread "Release workflow for 0.1") · Release check on three platforms
- Repos/commits: quadami master 743192b
- Did: `release-check.yml` (manual): per platform, `ab.py` builds candidate and baseline, runs corpus and
  closed sets × 6, `tools/bench/release_gate.py` decides on `gates.py`'s gates (0.x: structural gates
  no worse than the baseline, §3.2 ratchet; `--hard` for 1.0). `ab.py` ported to Windows (no `nice`,
  `.exe` and Visual Studio's `Release/`, tarfile instead of tar, no wait4) and macOS (ru_maxrss in
  bytes). `gates.py` H6: exactly ±10 % passes (float edge).
- Found: master fails the strict structural gates on replicates and the closed set (corpus 21/432,
  closed 114/468; list in RELEASING.md "Gaps"), so a hard gate would block 0.1; TARGETS §6 decision 3
  (0.x under the ratchet) decides it.
- Measured: cloud dry run, Linux 4 cores, master ae27301 against 0e9bec8, corpus + closed × 6: 54 min
  for both sides, 900/900 outputs byte-identical; `release_gate.py` passes. Windows and macOS: not run
  yet (the workflow can only run once merged, it is `workflow_dispatch`).
- Next: first run of the workflow on master after the merge; fix the structural failures before 1.0.
