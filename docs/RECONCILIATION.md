# Conflicts between sources and how they were resolved

Written 2026-10-14 while folding the research threads into [REFERENCE.md](REFERENCE.md), [TODO.md](TODO.md) and [LICENSES.md](LICENSES.md).
Every place where two project files disagree is listed here, with the source that wins and why. REFERENCE.md, TODO.md and LICENSES.md already follow the "winner" column.

Rules used to pick a winner, in order:
1. A line-level code read at `4a49f82` beats a description of the code taken second-hand (e.g. from REFERENCE.md).
2. A primary source read in the session (paper PDF, LICENSE/COPYING file, official doc) beats memory, abstracts or third-party pages.
3. A derivation beats an unsupported statement, but both stay marked **[I]** until a specialist or a measurement confirms them.
4. If neither side clears these bars, the conflict is left **open** with the conservative reading and a TODO check.

Tags (research files used their own [V] for external reads too; here those are written [P]): **[V]** checked in the AutoRemesher code at `4a49f82`; **[P]** checked against a primary external source (paper, LICENSE file, official doc); **[E]** external claim not checked at the source; **[S]** abstract or secondary page; **[I]** inferred.

Short names: **spec** = [research/code-to-math-spec.md](research/code-to-math-spec.md), **cross** = [research/cross-fields.md](research/cross-fields.md), **param** = [research/parametrization-rounding.md](research/parametrization-rounding.md), **extr** = [research/extraction-layout-metrics.md](research/extraction-layout-metrics.md), **size** = [research/sizing-guides-symmetry.md](research/sizing-guides-symmetry.md) (raw notes in `research/sizing-guides-symmetry-notes/`), **perf** = [research/performance-robustness.md](research/performance-robustness.md), **REF-old** = REFERENCE.md as it was before this merge.

§1–4 were written before any measurement. §5 lists where the baseline measurements ([research/baseline-and-profiling.md](research/baseline-and-profiling.md), "baseline") overturned or sharpened a code-read claim. Rule 0, above all others: **a measurement beats a code read or a derivation about behaviour**, within the measured setting (Linux, 18 meshes, default parameters).

---

## 1. What the code does

| # | Topic | Claim A | Claim B | Winner | Why |
|---|---|---|---|---|---|
| C1 | Where the rounding logic comes from | REF-old M1 and §3 row 14: possibly a mis-port of Geogram's threshold logic; spec §14.1: "M0/M1/M2 naming looks like a port of Geogram's mixed-integer solver [I], not checked" | param §0.2: Geogram's public tree (`ef0e4e3`) has no iterative rounding loop and no integer variables in its quad parametrization (PGP, `mesh_PGP_2d.cpp`); `mesh_global_param.cpp:555` only snaps coordinates **[P]** | **param** | Read the Geogram source; the others are guesses. **Residual:** the Geogram copy vendored by upstream 1.0 was not checked, and where the kernel construction (M0/M1/M2) comes from is still unknown. Only upstream knows (TODO 0.5, deferred; not needed for any fix). |
| C2 | How much the period-2 translations over-restrict | spec §13: "index 2 for ±¼ cones" | param §0.3: "over-constrains by index 2 (±90° cones) to 4 (regular seams)" | **Both, reconciled** | Different objects. Each seam translation t ∈ ℤ² is restricted to 2ℤ², which has index 4 in ℤ². The reachable composed translations around a cone are 2ℤ² versus the exact set (I − R)ℤ², which has index 2 for ±90° cones and index 1 for 180° cones. Same derivation in two independent reads; still **[I]** until SQ-P1 is answered. |
| C3 | Mesh on which stage 3 (target-length field) runs | perf §8.1: "runs on the raw input" | spec §5: on M_I′, the island **after** decimation | **spec** | Line-level read (`autoremesher.cpp:330-451` after `:177-302`). The two agree only when the decimation trigger (|F_I| ≥ 8 n_I) does not fire. |
| C4 | What the final smoothing projects onto | perf §4.3: "only the final smoothing projects to the input" | spec §17.7, correction 14: closest-point projection onto **T** (the isotropic remesh); the input is never used after stage 4 | **spec** | Line-level read (`quadextractor.cpp:1541-1668`, `autoremesher.cpp:806-855`). Consequence: output error is bounded only by d(out, T) + d(T, M) **[I]**. |
| C5 | Triangles per target quad in the param mesh | extr Q-E3: "≈1 triangle per quad" | REF-old M4, spec §2, perf §0.1: N = 2Q triangles, so ≈2 per target quad | **spec** | `src/mainwindow.cpp:1078, 1122`. Locally the ratio varies because quad size and T's resolution come from different fields (spec §16). Q-E3 was rewritten in SPECIALIST-QUESTIONS.md accordingly. |
| C6 | How the extractor decides crossings | perf §1: "no epsilon literals in `quadextractor.cpp`; needs a read" | spec §17.2: sign test plus `Double::isZero` (machine epsilon); 3D points merged on an absolute 10⁻⁵ grid (`positionkey.cpp:26`) | **spec** | It answers perf's open question. The 10⁻⁵ grid is absolute, so robustness depends on model units **[I]**. |
| C7 | What the 5 field iterations are | cross §1.1, §3.2: a truncated Ginzburg–Landau / MBO scheme (cross did not re-read the code) | spec §8.5: only the **first** solve sees the curvature target; solves 2–5 replace the target by the previous normalised iterate (proximal steps toward the smoothest field) | **spec** for what the code does; **cross** for what to build | Both describe a heat-step + normalise loop, but the code drops the data term after step 1. So cross §4.2's MBO, which keeps q fixed in every step, is a behaviour change, not just tuning. |
| C8 | Umbilic weight (REF-old M6) | REF-old: "principal directions meaningless in umbilic regions but still get weight" | spec correction 15: weight (|λ₁−λ₂|/max)² → 0 at umbilics | **spec** | Line-level read (`framefield.cpp:151-158`). The real issues are the global-max normalisation, the missing area normalisation and the target being used only once. |
| C9 | Anisotropy exponent (REF-old M9) | REF-old: heuristic exponent 1/4 | spec §10, correction 5: ρ = (κ_v/κ_u)^{1/4} gives aspect √(κ_max/κ_min), the classical optimal law | **spec** | Derivation from the CSM tensor property **[I]**, consistent with the cited literature **[E]**. The heuristic parts are the 12-hop smoothing and the signed tensor. |
| C10 | Rounding as described in the raw notes | size notes B, R4: "replace greedy rounding" | spec §14.2: the current rounding is one-shot (direct), not greedy | **spec** | Line-level read. The raw note is wrong; the synthesised size report does not repeat it. |

## 2. Mathematics and design

| # | Topic | Claim A | Claim B | Winner | Why |
|---|---|---|---|---|---|
| D1 | Fix for M3 (sizing vs singularities) | REF-old M3: "turn on and validate the conformal solve" | spec §11, size §2.2, cross §2: with fixed cones on a closed surface, Δφ = K − K̂ fixes φ up to a constant, so an exact conformal solve leaves no local size freedom; the field must also be co-closed | **spec + size** | Standard theorem (Myles & Zorin 2013 Prop. 3, read by size **[P]**). The conformal solve becomes one ingredient (cone placement from K − Δφ*), not the fix. |
| D2 | Wording of the field–density coupling | size §2.1: "field, density and cones are one object: fix any two and the third is determined" | spec §11: dφ = ±⋆(dθ − ω) needs d⋆(dθ − ω) = 0 away from cones, so a given field admits an exact φ only if it is the smoothest (co-closed, trivial-connection) field for its cones | **spec** | spec's statement is the precise one; size's "fix the field and the cones" is too strong, because a curvature-aligned field with those cones is generally not co-closed. Both agree on the remedy: least-squares projection (L + λM)φ = div⋆ω + λMφ*, and the residual curl is absorbed as distortion (size §2.2(c)). |
| D3 | Where to compute curvature (sizing and field alignment) | size §1.1: tensor on the isotropic remesh T | cross §4.3 and perf §4.3: on the input (or a mildly decimated input) at radius r ≈ c·h, then transferred | **cross + perf**, with size's choice as the interim step | T is produced after a decimation with no error bound (spec §4) and a remesh that erodes creases (spec §6), so estimates on T inherit both losses **[I]**. On T the estimate is cheaper and good enough at scales ≥ h, so the sizing field (TODO 4.1) may start on T; moving the estimator to the input is TODO 4.6. |
| D4 | Risk of density paint (F3) | REF-old §7: S effort, low risk | size §0: not low risk; painted density with sharp borders forces pole pairs unless graded and projected (Δφ = K − K̂) | **size** | Theorem-backed (D1). REFERENCE §7 now says Medium risk and depends on the sizing field. |
| D5 | Mirror symmetry method (F5) | REF-old §7: cut at plane, remesh one half, mirror, weld the **output** | size §4.2: symmetric **triangle** remesh, then linear symmetry constraints in field and param, then pair averaging | **size** | Output cut-mirror-weld forces an edge loop on the plane and lines poles up along it (what Blender's QuadriFlow does **[P]**). The alternative is barely more work **[I]**. |
| D6 | Effort of the "cheapest high-value set" F1, F2, F5, F6 | REF-old §7: all S | size §0 + spec §6, §12.5: hard features need the remesher fix, the sector rule and robust rounding; F5 is M; exact F6 is M | **size + spec** | The code read shows creases are eroded before the field (M11) and dropped at 10° (M8). Wiring is S; quality is not. |
| D7 | Conditioning of the normal equations (REF-old P2) | REF-old P2: normal equations square the condition number | perf §1: for a gradient-fitting energy AᵀA is the cotan-like Laplacian every method factors; the real risk is rank deficiency hidden by the ridge | **perf**, still **[I]** | More specific argument. Both are inferences; neither was measured. |
| D8 | Priority of a faster solver (P2) | REF-old P2: supernodal Cholesky typically 3–10× faster | perf §0.1–0.2: at ≈10⁵ unknowns the solve is probably not the bottleneck today; it becomes one after greedy rounding (one re-solve per batch) and M4 (4–16× larger systems) | **perf**, still **[I]** | Better reasoned. So the solver **interface** comes before greedy rounding, and the backend swap waits for measurements (TODO 3.1, 8.2). |

## 3. Licenses and code availability

| # | Topic | Claim A | Claim B | Winner | Why |
|---|---|---|---|---|---|
| L1 | CoMISo license | REF-old §1: GPL-3.0 **[E]**; perf, cross: GPL-3.0 / GPL | param §0.7: COPYING says **GPL-3.0-only** (read at a 2018-era commit) | **param** | Read the COPYING file. Linking CoMISo makes the distributed binary GPL-3.0-only. Moot since TODO 0.2 excludes GPL-3.0-only code. |
| L2 | Rectangular Surface Parameterization (Corman–Crane 2025) repository | cross §3.3 and param §3.2: **no LICENSE file** at main/master **[P]** | extr §6: **AGPL-3.0** **[P]** | **Open**; treat as no license (ask the authors) | Two independent reads found no LICENSE file; extr may have mixed it up with NeurCross/CrossGen (both AGPL). It changes no decision: all three threads recommend RSP as a formulation to re-implement, not code to vendor. TODO 0.4 re-checks. |
| L3 | Penner-coordinate code | param §3.3: `rjc8237/seamless-parametrization-penner` has no LICENSE file; "penner-optimization same" | size §2.5 and notes B: `geometryprocessing/penner-optimization` is dual GPL-3.0 / MPL-2.0 per its README **[P]** | **Both, per repository** | Different repositories. `seamless-parametrization-penner` and `feature-aligned-penner` (2024/2025 seamless and feature work): no LICENSE file, so ask. `geometryprocessing/penner-optimization` (2023 metric optimisation): README declares GPL-3.0/MPL-2.0; confirm a LICENSE file exists before vendoring. |
| L4 | Directional (Vaxman) | cross, size: license not verified | extr §9: MPL-2.0 per file headers **[P]** | **extr** | Headers were read. |
| L5 | Instant Meshes | cross, extr: BSD-3 | perf §4.1: BSD-3 plus a clause that licenses enhancements you share back to the authors (LICENSE read) | **perf** (adds detail, no conflict) | Prefer re-implementing ideas over copying code. Same clause in QuadriFlow (size §6). |
| L6 | ConformalIdealDelaunay (Campen et al. 2021) | size §2.2: code license unverified | param §3.3: MIT **[P]** | **param** | LICENSE read. |
| L7 | Metriko (QGP implementation) | size §6: MPL-2.0, LICENSE not read | param §3.2: MPL-2.0 **[P]** | **param** | LICENSE read. Check per-file "Incompatible With Secondary Licenses" notices before vendoring. |
| L8 | CrossGen code and speed | cross §3.5: repo exists, AGPL-3.0 (LICENSE read), ≈1 s per shape | perf §5: "≈0.07 s per shape on GPU, code not released" | **cross** on code existence; speed **open** | cross read the LICENSE in the repository. The speeds may refer to different stages; irrelevant to decisions, since every thread defers learned fields. |
| L9 | Integrable odeco fields (Couplet et al. 2026) venue and code | param: "submitted SGP 2026"; extr: "SGP 2026 per alphaXiv [S]" | cross §3.3: CGF, SGP 2026, DOI 10.1111/cgf.70492 **[P]** | **cross** | DOI seen. All agree no code has been released. |

## 4. Not conflicts, but corrections to how things were described

- REF-old §4 reads the progress-bar split 17/33/50 % as "upstream measured extraction as the largest share". The constants are verified, but that they come from a measurement is **[I]**; spec §20 lists them as UI-only.
- REF-old §3 row 0 says L is chosen so the isotropic mesh has 2 × target triangles. Correct, but the resulting quad count is ≈0.87 Q in the uniform case, not Q (spec §2, §16).
- REF-old §8 calls Geogram "origin of the QuadCover-style solver AutoRemesher replaced in 1.1". Per C1, Geogram's public quad parametrization is PGP; which Geogram routine 1.0 used was not checked.

## 5. Code read vs. measurement (added 2026-10-14 after the baseline report)

| # | Topic | Code-read claim | Measured (baseline) | Winner | Consequence |
|---|---|---|---|---|---|
| B1 | Quad count | spec §16: ≈0.87 Q uniform; with adaptivity the count moves in a mesh-dependent direction | Default: 0.37–0.51 × target (medians), under target in 53/54 runs; adaptivity 0: 0.80–1.16 × | **baseline** | Systematic 2–3× undershoot from the stage-5 factor m_f. REFERENCE M7 corrected; interim fix TODO 2.11. |
| B2 | T vs. quad resolution | REF M4: quad edge ≈ mean triangle edge on average | True only with adaptivity 0. Default: 5.8 triangles per quad, quad edge ≈ 1.6× triangle edge | **baseline** | On average T is finer than the quads; the local "coarser" case is unmeasured. |
| B3 | Where big inputs cost | REF P4: serial isotropic remesher matters on 5M+ inputs | The remesher sees only the decimated mesh; 24 of 27.5 s at 6.4M are island split, contexts, decimation and OBJ parse | **baseline** | TODO 8.2 retargeted. |
| B4 | Largest linear system | REF P2: cover system ≈ 10⁵ unknowns at 50k | Curl correction (n = 3F) is the largest: 2.2–3.9·10⁵, nnz(L) ≤ 21.6M | **baseline** | Solver work should target the curl system too. |
| B5 | Determinism | REF P8 **[I]**: threaded solvers and unordered containers break it | Byte-identical across repeats, threads, allocators, threaded CHOLMOD (one platform) | **baseline**, for Linux | P8 stays a cross-platform risk; TODO 1.7 left for other platforms. |
| B6 | `--report` | REF §2: per-stage timings in the report file | Totals only; per-step times go to stderr | **baseline** | REFERENCE §2 corrected. |
| B7 | Build packages | README: `libqt5multimedia5-dev` | Does not exist on Ubuntu 24.04, not needed | **baseline** | REFERENCE §2 corrected. |
| B8 | Progress-bar split | 17/33/50 (UI constants, provenance **[I]**) | 36/35/29 at 2k, 25/37/38 at 10k, 15/40/46 at 50k | **baseline** | Matches only at 50k; confirms they are not a measurement of small targets. |

Not conflicts but new facts, added as REFERENCE P9 (O(S·F) `cancelPair`), P10 (peak memory in rounding), M15 (real boundaries capped), M16 (non-manifold output and holes), the M14 measurement (small islands vanish) and the F5 baseline (no symmetric layout).
