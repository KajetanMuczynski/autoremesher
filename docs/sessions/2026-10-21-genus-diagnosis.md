# 2026-10-21 · Claude (cloud thread "Why genus goes wrong") · genus diagnosis
- Repos/commits: core master 7aae3fe (classification) and 4d15d5f (re-baseline, intervention); probe patches
  and scripts in research/genus-diagnosis-2026-10-21/ (no core change in this PR)
- Did: ab.py corpus + closed set with 5 float32 replicates on both masters; a probe build that dumps every
  stage (decimated mesh, T with its map, raw extraction, fixHoles, repair, final) and can switch the extractor
  to the face-tracing prototype 0c98a87; classified and located every wrong replicate-run; base rate of the
  fold/cone proximity; map holonomy along handle loops; the extractor intervention on 250 runs.
- Found: with the same map, the face-tracing extractor makes 64 of the 75 wrong replicate-runs right, so
  `extractMesh` causes them. That is why 3.3 and 3.8 were genus neutral. The torus handles are held by the map
  (not sub-grid). demosthenes' 11 remaining failures have an undetermined cause. Decimation broke T on 7aae3fe
  (19 replicate-runs) and #44 fixed it.
- Measured: 4d15d5f corpus 365/432 and closed 460/468 replicate-runs right. Extra handles within 1 quad edge of
  a fold or cone in 53/53, against 23 % of random output faces. Tracer cost on the same runs: folded faces
  ×1.7–2.8, non-quads ×1.5–3.2, human_neutral Fast 10k broken (5/6 → 1/6).
- Next: 6.1 (libQEx or own tracer) judged on the same 250 runs; 1.14 homology-based V6 check in tools/bench.
