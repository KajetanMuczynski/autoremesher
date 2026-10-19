# 2026-10-14 · Claude (thread "Code-to-math spec of AutoRemesher", 19:15–19:42 UTC) · Stage-by-stage specification
- Repos/commits: core `4a49f82` (code read only).
- Did: wrote [research/code-to-math-spec.md](../research/code-to-math-spec.md): formulas, constants and deviations from the source papers for every stage, and §23 with 21 corrections to REFERENCE.md.
- Found: curvature target used only in the first of 5 field solves; quad size = λ·ℓ̄_T·m_f·ρ_f^{±1}, ≈0.87 Q in the uniform case; remesher erodes creases; final projection onto T, not the input; period 2 ⇒ translations in 2ℤ²; elimination ignores its consistency check.
- Measured: nothing.
- Next: corrections merged into REFERENCE.md by the consolidation thread (below).
