# 2026-10-14 · Claude (thread "Research: quad extraction and layout methods", 19:10–19:19 UTC) · Extraction and metrics research
- Did: wrote [research/extraction-layout-metrics.md](../research/extraction-layout-metrics.md): QEx, Ray 2025, graph extraction, layout-first pipelines (QuadWild, Bi-MDF, FSCQ), cleanup operators, a metric set (topology, element quality, fidelity, alignment, poles, symmetry, cost) and a benchmark protocol; questions Q-E, Q-L, Q-C, Q-M.
- Found: the extractor is not the root problem (M1/M2 are); libQEx (GPL-3.0) is the drop-in candidate once the map is valid; replace the 12 repair passes with a grid-preserving operator queue; Blossom-V and Gurobi must stay off in quadwild-bimdf.
- Measured: nothing.
- Next: TODO 0.7, 1.4, 6.1–6.4; SQ-E1–E7, SQ-L1–L3, SQ-M1–M4.
