# 2026-10-21 · Claude (cloud thread) · Faster A/B runs and cached builds
- Repos/commits: core 7998e98 (master, key d1517f791507)
- Did: measured where an `ab.py` A/B spends its time; added metrics.py's input cache
  (`--input-cache`, filled once per mesh before the runs start), recorded `jobs` and `input_sha` per
  run, `compare` flags a time row whose sides ran with different `--jobs`, fixed a race in the 1-ulp
  replicate inputs, Python tests for the cache in CI (`qt-app`).
- Found:
  - The build is not the bottleneck: ~50 s per key (configure 0.7 s, core 36 s, LTO link 13 s at
    `-j2`), once per key. ccache, Ninja or a prebuilt thirdparty would save under a minute per variant.
  - The CLI is parallel only across islands (TBB per island): csg_bracket 22 s wall = 22 s CPU,
    spot_x8 1.8 s wall = 5.7 s CPU. So `--jobs 2` kept ~2.2 of 4 cores busy.
  - metrics.py was 47 % of the work (334 s of 705 s per corpus pass): on nefertiti and cat ~25 s of
    ~27 s is reading the input OBJ and its topology, the same for every run of that mesh.
  - Outputs don't depend on `--jobs` or thread count: 72/72 `out.obj` identical at `--jobs 2` vs 4,
    and 1 core vs all; 143/143 runs identical in `out.obj` and metrics, old vs new harness.
  - `--jobs 4` inflates the CLI's own time by ×1.2 (geo-mean), so time rows need equal `--jobs`.
  - Bug (old harness): two parallel runs of the same mesh and replicate wrote the same
    `<hash>-u<k>.obj.tmp`. Seen as `FileNotFoundError ... -u1.obj.tmp` when adding `--replicates` to
    finished u0 runs (spot, `--jobs 2`); one run was lost. Worse case possible: a run reading a
    replicate input while the other writer still writes it. Runs made that way should be checked.
- Measured (4 vCPUs, master 7998e98): corpus set, 1 replicate 5:53 → 3:12; with `--replicates 5`
  ~35:24 (u0 5:53 and u1 5:55 measured, ×6) → 19:46 measured; closed set 0:59 → 0:41 per replicate.
- Not done, on purpose: a shared cache of master runs across threads (saves one variant per thread
  at most; master's key changes with every core merge; needs a toolchain + metrics.py + ab.py
  fingerprint to be safe from poisoning, and /mnt/project-files is a slow last-write-wins mount).
- Next: if threads keep re-running the same master, revisit the shared cache with a fingerprint.
