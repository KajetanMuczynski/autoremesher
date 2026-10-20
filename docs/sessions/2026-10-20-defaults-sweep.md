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
- Next: Kajetan's call on 180°; if yes, one meaning for "off" across stages (with 2.6) and a test that
  the five default sites agree. Trace human_neutral's hole (2.13).
