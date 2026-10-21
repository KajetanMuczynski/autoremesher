# 2026-10-21 · Claude (cloud thread "Genus and validity in the literature") · how published quad meshers keep genus
- Repos/commits: core master 4d15d5f (code read only); note research/genus-validity-literature-2026-10-21.md
- Did: read QEx, IGM, QGP, Lyon et al. 2019/2021, Myles-Pietroni-Zorin 2014, Campen et al. 2019, Shen et al. 2022,
  QuadWild, Instant Meshes and QuadriFlow for how they keep output topology right, and mapped each technique to our
  measured failure classes (sub-grid handles, extra handles at folds, bridged boundary, decimation, flips, non-quads).
- Found: no paper gates genus at the output; IGM methods get it by construction from a valid map and put the guard
  before extraction (orientation constraints, positivity, separation test that rejects quantization updates). We have
  no such gate. A valid IGM cannot lose a handle (QGP keeps cells small instead), so sub-grid handle loss is a property
  of our quantization; our seam translations live in 2ℤ² (`quadparameterizer.cpp:1056`), so any loop under one quad
  rounds to zero holonomy (inferred, unmeasured). Instant Meshes and QuadriFlow do not avoid topology errors by
  construction (non-manifold "sometimes", "nearly always manifold", lose fingers at coarse counts).
- Measured: nothing measured.
- Next: pre-extraction validity gate (handle-loop holonomy/isoline crossings, boundary width, cone collisions); a
  closed-set A/B of a ℤ² seam lattice; libQEx with cone valences given, after the 6.1 A/B.
