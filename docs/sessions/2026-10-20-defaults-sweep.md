# 2026-10-20 · cloud thread · Sharp-edge and anisotropy defaults
- Repos/commits: core master `0480366`.
- Did: gap-scan item 2. Swept the sharp-edge angle (30–180°) and anisotropy (0/0.5/1) with the
  `autoremesher-cli`, every run repeated on a 1-ulp float32 replicate, judged against TARGETS.md
  (gates, §2.4 margins). Scripts and per-run results: research/defaults-sweep-2026-10-20/ (not in the
  repo; tools/bench belongs to the A/B-harness work). Add-on tooltips for both settings now state the
  measured effect.
- Found: lowering θ_s is worse at every step; there is no cliff at 90°. 180° (sharp handling off)
  wins every validity metric, passes all structural gates, but loses crease coverage beyond the
  fidelity margin, so the default stays 90° until Kajetan decides. Anisotropy 1 stays: 0 costs p99
  distance ×1.34 for SJ p1 ×1.11. human_neutral 2k fails H5 (extra boundary loop) at the defaults.
- Measured (corpus, 108 runs per value, ratio to 90°): 180° non-quads 0.76, folds 0.84, irregular
  0.84, SJ p1 1.70, A1 0.88, distances 0.99–1.00. Anisotropy 0 vs 1: p99 1.34, Hausdorff 1.26,
  mean 1.26, A1 0.57, SJ p1 1.11, skew p95 0.85, aspect 0.73.
- Re-checked with `tools/bench/ab.py` (2026-10-21, corpus set, 72 runs × 2 replicates, on this branch
  after merging master): 60° non-quads ×2.09, flips ×2.37; 180° non-quads ×0.67, SJ ≤ 0 ×0.74, flips
  ×0.60, p99 / mean distance ×1.01 / ×1.00, topology kept 61 → 66 of 72; anisotropy 0 p99 ×1.35, mean
  ×1.26. Same direction as the first sweep. human_neutral quality 2k changes topology at the defaults
  in 6/6 replicates and keeps it at 180° in 6/6. Crease coverage A1 is not in ab.py; it comes from the
  first sweep's metrics_compare.py only.
- Decided: Kajetan (2026-10-21) keeps 90°; 180° and the field-lock-only variant are parked (TODO Parked).
- Next: trace human_neutral's hole (2.13); "off" needs one meaning across stages (with 2.6).
