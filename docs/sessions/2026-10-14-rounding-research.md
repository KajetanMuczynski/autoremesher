# 2026-10-14 · Claude (thread "Research: parametrization and integer rounding", 19:10–19:21 UTC) · Rounding research
- Repos/commits: core `4a49f82`; Geogram `ef0e4e3` (parameterization dir).
- Did: wrote [research/parametrization-rounding.md](../research/parametrization-rounding.md): taxonomy (MIQ rounding, QGP/T-mesh quantization, valid seamless maps, robust extraction, learned), recommended Stage A / Stage B path, questions Q1–Q10.
- Found: one-shot rounding confirmed; not a Geogram port (Geogram's quad param is PGP, no integers); period-2 translations put cones on ℤ² implicitly but over-restrict; Bi-MDF via libSatsuma (MIT) is the integer engine for Stage B, Metriko (MPL-2.0) the reference; CoMISo is GPL-3.0-only; Penner/RSP/topological-IGM repos have no LICENSE file; neural rounding not recommended.
- Measured: nothing.
- Next: TODO 3.1–3.7, 7.2; SQ-P1–P6, SQ-L4–L5, SQ-Z5.
