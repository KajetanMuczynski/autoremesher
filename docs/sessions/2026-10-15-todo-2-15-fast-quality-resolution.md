# 2026-10-15 · Claude (cloud thread "Fix quad count undershoot") · TODO 2.15 Fast/Quality resolution
- Repos/commits: fork master `d95bdd7` → PR (feat(sizing), TODO 2.15).
- Did: made T's resolution a setting (engine triangles per quad; `remesh()` `resolution` fast|quality, interface 1.2; CLI, `ar_bench`, add-on Advanced > Resolution); small-island floor keeps the mode; count test covers both modes. Swept 2, 3, 4.5, 6 triangles per quad at 2k/10k.
- Found: 4.5 is the knee; Fast's output is bit-identical to master (36/36).
- Measured: Quality vs master (= Fast) at 2k / 10k: Hausdorff −22 / −14 %, mean distance −33 / −28 %, UV flips −30 / −19 %, scaled Jacobian < 0.5 share −43 / −6 %, angle p95 −4 / −6 %, same count, 1.5× the time.
- Next: 7.4 (field on a finer mesh) and 2.8 (project onto the input) should make most of Quality's cost unnecessary.
