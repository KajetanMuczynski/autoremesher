# 2026-10-14 · Claude (thread "Research: speed and numerical robustness", 19:10–19:23 UTC) · Performance research
- Repos/commits: core `4a49f82` (solver and threading code).
- Did: wrote [research/performance-robustness.md](../research/performance-robustness.md): sparse solvers and licenses, MIQ speed, multiresolution (Instant Meshes, multigrid, Ebke 2016), GPU, parallel remeshing, preprocessing, exact predicates, profiling method, corpus design, ranked actions R1–R13.
- Found: systems are ≈10⁵ unknowns, so the solver is probably not today's bottleneck; MILS rebuilds the whole system each iteration, which greedy rounding would turn into a ~100× regression; coarse-to-fine beats GPU; determinism must be a requirement; MKL/Panua PARDISO, cuDSS, Gurobi excluded.
- Measured: nothing.
- Next: TODO 1.6, 1.7, 2.3, 2.7, 2.10, 3.1–3.2, Wave 8.
