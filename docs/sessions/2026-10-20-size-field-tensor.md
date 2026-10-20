# 2026-10-20 · Claude (cloud VM) · Scale-aware tensor size field (TODO 4.1)
- Repos/commits: core 47529e1 (master); experiment patch in ../research/size-field-tensor-scripts/ (project files, not merged)
- Did: replaced stage 5's one-ring estimator with a Cohen-Steiner–Morvan tensor over a 0.5 h ball (feature edges out),
  P2–P98 clamp and Persson gradation (g = 0.3); A/B with tools/bench/ab.py on the corpus and closed sets, plus
  ablations (no gradation, no clamp, 0.25 h ball, feature edges kept, adaptivity 0.75 and 1) and master at 0.25.
- Found: no variant leaves the fidelity/validity front that master's adaptivity already draws; master at 0.25
  dominates the graded field at 0.5. Gradation is what cuts flips, and it is only less size variation.
- Measured: graded a 0.5 vs master: flips ×0.83, non-quads ×0.92, p99 distance ×1.14, mean ×1.06 (72 runs);
  master a 0.25: flips ×0.66, non-quads ×0.82, p99 ×1.17, mean ×1.03. Full table in the research note.
- Next: not adopted. Validity work stays on the map (3.3, 3.8); 4.1's open part is the thin-part cap and paint.
