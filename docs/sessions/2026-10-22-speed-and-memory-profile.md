# 2026-10-22 · Claude (cloud, thread "Speed and memory profile") · Speed and memory profile of master
- Repos/commits: core ae27301 (master), compared with 0e9bec8 and 4d15d5f
- Did: corpus at 3k/10k/50k on all three refs, one run at a time; koala ladder 0.1–6.4M and the private
  sculpts (metrics only) on master; METIS ordering and allocator experiments (local only); thread caps
  1/2/4 cores; progress-bar and cancel-latency probes; perf on a 6.4M input. Added
  `tools/bench/speed_report.py` and `tools/bench/progress_probe.py`. Note: project files
  `research/speed-memory-2026-10-22.md`.
- Found: at 50k the rounding loop is 34 % (11 full numeric refactorizations), the curl solve 15 %; on
  inputs of 1.6M+ triangles at 3–10k quads input preprocessing is 30–52 % (fold check, island split, island
  contexts, surface projection rebuild topology/BVH of the whole input). libQEx made 10k/50k 19–20 % faster
  than 4d15d5f. Typical sculpts take 2.5–20 s. The progress bar reaches 50 % at 85–88 % of the time.
  Allocator swap now gains 0–10 % (TODO 8.0 not worth it). Single-island runs gain at most 20 % from 4 cores.
- Measured: peak RSS ≈ 0.54 KB per input triangle + 20 KB per target quad + 33 MB (× 1.58 upper bound,
  75 runs); wall ≈ 8.4 s/M triangles + 0.27 s × (target/1000)^1.47 + 0.9 s (p90 ×1.6). METIS ordering:
  −27 % at 50k, 0 % at 10k, outputs differ. Cancel latency up to 46 s inside the curl factorization (the
  add-on kills after 5 s).
- Next: rounding without full refactorization (integer variables last, update only the trailing block);
  one shared flat input structure per island; progress weights or a time-model bar, `--threads N`, pre-run
  estimate in the panel.
