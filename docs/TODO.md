# AutoRemesher upgrade: plan

One prioritized, dependency-ordered plan, merged on 2026-10-14 from the earlier TODO ([archive/TODO-2026-10-14-pre-merge.md](archive/TODO-2026-10-14-pre-merge.md)) and every research report in [research/](research/).
Update this file and add a session file in [sessions/](sessions/README.md) every session.

**Keys.** Status `[ ]` open, `[~]` in progress / partly done, `[x]` done, `[-]` deferred or dropped by a decision (reason given). Item IDs (e.g. **3.3**) are wave.number; "needs" lists hard dependencies. Issue IDs P*, M*, F* are in [REFERENCE.md](REFERENCE.md); SQ-* in [SPECIALIST-QUESTIONS.md](SPECIALIST-QUESTIONS.md). Effort: S days, M 1–3 weeks, L 1–3 months. **License flags** ([LICENSES.md](LICENSES.md) §2): `OK-MIT` own or permissive code, can also go upstream; `OK-GPL3` needs a GPL-compatible dependency; `GPL3-ONLY` pulls in GPL-3.0-only code (CoMISo), **excluded by 0.2**; `ASK` no license, needs author permission or a re-implementation; `NO` never ship.

**Rules.** Upgrade, don't rewrite, unless gate 7.1 says otherwise. Change one stage at a time behind its interface (FrameField, SingularitySimplifier, QuadParameterizer, MixedIntegerLeastSquares, QuadExtractor), and A/B every change on the corpus with the Wave 1 metrics. Keep `OK-MIT` fixes in separate commits free of GPL code, so they can still go upstream if 0.5 is ever picked up.

---

## Order at a glance

```
Wave 0  decisions ──────────────────────────────────────────────────────────────┐
Wave 1  build · corpus · metrics · baseline (measured: REFERENCE §4.1)          │
   ├── Quick wins, any time: 8.0 tbbmalloc · 8.7 local cancelPair · 2.11 count  │
   │             fix · 2.12 boundary capping                                    │
   ├── Wave 2  diagnostics (2.1–2.4) → cheap correctness fixes (2.5–2.14)      │  Track G: Blender layer,
   ├── Wave 3  solver interface (3.1–3.2) → greedy rounding, M1 Stage A (3.3)   │  in parallel throughout
   │             → lattice/elimination fixes → measure (3.7) ── gate 7.1        │
   ├── Wave 4  sizing field (4.1) → field energy/MBO (4.2–4.3) → size into      │
   │           param (4.5) → count controller (4.7)       [parallel to Wave 3]  │
   ├── Wave 5  features → symmetry → exact count → hard guides  [needs 2.5, 3.3]│
   ├── Wave 6  extraction: libQEx A/B → cleanup worklist         [needs 3.3]    │
   ├── Wave 7  gate → Stage B quantization; singularity research; finer field   │
   └── Wave 8  performance backends            [needs 3.1 and baseline numbers] ┘
```

Critical path: **1.4/1.6 → 2.1–2.2 → 3.1 → 3.2 → 3.3 → 3.7 → 7.1.** Most quality items (features, symmetry, hard guides, extraction swap) wait on 3.3 because they add integer constraints that one-shot rounding collapses (REFERENCE M1, §7).

The baseline (REFERENCE §4.1) confirms this order. UV flips occur in every run and predict both cleanup time and final irregularity. It also adds quick wins that need nothing else first: 8.0 (1.22–1.54× faster, identical output), 8.7 (up to 42 % of a run), 2.11 (the quad count is 2–3× under target by default) and 2.12 (open boundaries get capped).

---

## Wave 0: decisions and outreach (Kajetan)

- [x] **0.1** License: public GPL-3.0-or-later fork (LICENSES §1).
- [x] **0.1b** Blender layer: port jakeblakeley's packaging and subprocess-worker add-on onto current upstream; don't use its 1.0.0 core (REFERENCE §6.1).
- [x] **0.2** GPL-3.0-only code: **not allowed** (Kajetan, 2026-10-14). CoMISo is out, directly and through quadwild-bimdf; 6.4 is dropped. Nothing on the critical path needed it: greedy rounding (3.3) is our own code, and Stage B (7.2) uses Bi-MDF from MIT libSatsuma. This is a policy choice, not a legal block: linking GPL-3.0-only code into a GPL-3.0-or-later project is allowed but makes the distributed binary GPL-3.0-only (LICENSES §2). libQEx and QuadWild stay allowed: both are GPL-3.0-**or-later** (0.4).
- [ ] **0.3** Fork repo: `COPYING` (GPLv3), keep `LICENSE-MIT`, `THIRD_PARTY_NOTICES`, SPDX headers, distinct name, credits (LICENSES §6). S · `OK-MIT`.
- [~] **0.4** License checks before vendoring. Done by the research threads for most candidates (LICENSES §4). "Or later" confirmed 2026-10-14 from file headers [P]: libQEx (`src/MeshExtractorT.hh`, `interfaces/c/qex.h`, README) and QuadWild (`components/quad_from_patches/quad_from_patches.h`, one header sampled). Left: CoMISo COPYING on current master (moot after 0.2); RSP repository (conflicting reads, RECONCILIATION L2); `penner-optimization` LICENSE file (L3); Gravo MG.
- [-] **0.5** **Deferred** (Kajetan, 2026-10-14: not now). **Blocks nothing.** (a)–(d) only ask for intent: the code read already says what the code does, 3.3 and 4.5 replace both pieces, and SQ-P2 covers the correctness of the elimination. (e) is optional, since upstream is MIT and needs no permission for the fork. Cost of deferring: the fork diverges, so later upstream fixes must be cherry-picked by hand. Original items: write to Jeremy Hu (upstream): (a) intent of `max(d + 0.001, 1.0)` and the `break` in `solveIteration` (M1); (b) why `computeConformalScaling` was disabled in `dd87c6e`; (c) origin of the M0/M1/M2 elimination (not Geogram's public code, RECONCILIATION C1); (d) plans for `ModelType`; (e) offer the Wave 2 fixes as MIT patches.
- [ ] **0.6** Optional author requests, only if we want their code instead of re-implementing: Corman & Crane (RSP), Capouellez & Zorin (Penner seamless / feature-aligned), Livesu (topological IGM), Coudert-Osmont et al. 2024 and Ray 2025 (unreleased code), Du et al. (integer-constrained cones). `ASK`.
- [ ] **0.7** Define "closer to ZRemesher" as numbers before judging any fix: metric families of extr §5.2 (topology, element quality, fidelity, alignment, poles, symmetry, cost); pass gates T7 defects = 0 and G1 1st-percentile scaled Jacobian > 0; Pareto comparisons, no composite score until SQ-M1 is answered. Optional calibration: 3–5 artists rank blind pairs on ~20 meshes.
- [~] **0.8** Specialist questions: **prepared, not sent** (Kajetan, 2026-10-14: get them ready). The 9 "Ask first" questions are in [SPECIALIST-BRIEF.md](SPECIALIST-BRIEF.md), self-contained for a reader with no project context, split into four parts by recipient. Left: Kajetan decides when and to whom.
- [ ] **0.9** **Master branch ruleset** (Kajetan's setting, Settings > Rules > Rulesets; none active on `master` as of 2026-10-19, checked via the API). Target `master`; require a pull request (0 approvals, since Kajetan cannot approve his own PRs); require status check **CI passed**; block force pushes and deletion. Notes for the choice:
  - *Require branches to be up to date before merging*: GitHub then refuses to merge a PR until master is merged into it and CI has run again, so after every merge each other open PR needs an "Update branch" and a fresh CI run. It catches two PRs that are green alone but break master together; it removes no conflicts, it only makes you resolve them sooner. Recommended on (quality over speed), accepting the extra CI runs.
  - *Merge queue*: GitHub offers it only for organization-owned repositories (public, or private on Enterprise Cloud), so not for this personal-account fork (docs checked 2026-10-19). It would also need a `merge_group` trigger in `ci.yml`.
  - *Conflicts from shared files*: the session log used to be one `SESSIONS.md` every PR appended to, so each merge made every other open PR conflict there. Fixed 2026-10-19: one file per session in [sessions/](sessions/README.md). Rule for the future: no doc that every PR appends to (no shared changelog or index); TODO.md and REFERENCE.md are edited in place per item, so they conflict only when two PRs change the same item, which is a real conflict to resolve by hand. S.

## Wave 1: build, corpus, metrics, baseline

The baseline thread did most of this on a Linux VM: report [research/baseline-and-profiling.md](research/baseline-and-profiling.md), summary and verdicts in REFERENCE §4.1, scripts and raw tables in [research/baseline-scripts/](research/baseline-scripts/) (build, Qt-free `ar_bench`, probes patch, metrics, 18-mesh corpus, experiments). What it could not do needs Kajetan's machine (1.12).

- [~] **1.1** Build upstream `4a49f82`. Done on Linux (baseline §1: Ubuntu 24.04, GCC 13.3, Qt 5.15.13, oneTBB 2021.11; drop `libqt5multimedia5-dev`; headless needs `QT_QPA_PLATFORM=offscreen`). Left: Kajetan's machine(s), especially macOS; record OS, compiler, Qt, TBB in a session file. S.
- [~] **1.2** Qt-free headless bench driver. Done: `ar_bench` and `probes.patch` in research/baseline-scripts/bench/, checked equal to the CLI. Left: bring them into the fork. S.
- [ ] **1.3** CMake target for the core only (= G1): start from jakeblakeley's `CMakeLists.txt`/`pyproject.toml`/`src/python/binding.cpp`, swap its Geogram sources for current upstream files. S · `OK-MIT`.
- [~] **1.4** Metrics script covering extr §5.2: T1–T7 (incl. irregularity excess over the Euler bound, base-complex patch count), G1–G6, D1–D3 (two-sided Hausdorff vs. the **input**), A1–A5 (feature coverage, curvature alignment, loops), P1–P4 (pole spacing, pole–curvature sign, poles in flat areas), S1–S3, cost, plus UV flips after the cover solve (needs 2.1). Baseline `metrics.py` already covers valence, corner angles, scaled Jacobian, flipped and degenerate faces, non-manifold and boundary edges, Euler characteristic, two-sided Hausdorff vs. the input, mirror symmetry, UV flips. Missing: irregularity excess, patch count, alignment A1–A5, pole metrics P1–P4, loops. Open definitions: SQ-M2 (edge flow), SQ-M3 (pole placement proxy), SQ-M4 (Euler bound with features). M.
- [~] **1.5** Corpus. Baseline: 18 meshes (12 PD/CC from `odedstein/meshes@8352132`, 6 synthetic); Stanford, Smithsonian, Thingiverse etc. were blocked by the cloud network policy. Add Kajetan's own sculpts (most representative), one shape at 100k/1M/5M/10M triangles, scripted pathology meshes (slivers, duplicates, non-manifold, flipped shells, holes, 0.001 and 10⁴ scale), a QuadWild300/MAMBO subset for literature comparison. Each at 2k/10k/50k quads. Licenses: LICENSES §5.
- [~] **1.6** (Partly covered by the baseline `probes.patch`: per-step times, RSS, solver sizes and times, rounding and cleanup counters.) Extend `--report` to one JSON line per (mesh, target, stage): wall and CPU time, peak RSS, sizes, solver n / nnz / factorise / solve times / solves per factorisation / ridge / KKT fallback taken, MILS iterations and integers fixed, cleanup rounds and edits per pass, health counters (perf §9.1). S · `OK-MIT`.
- [~] **1.7** Determinism test: same input 10× and at 1/4/all threads ⇒ identical output hash (P8). Passed on Linux (baseline: 10 repeats, 1 vs 4 threads, two allocators, threaded CHOLMOD). Left: cross-platform, and keep it as a CI check (8.6). S.
- [ ] **1.8** External baselines at the same counts (±5 %): ZRemesher, Quad Remesher, Blender QuadriFlow, Instant Meshes, quadwild-bimdf free build (no Blossom-V, no Gurobi; local comparison only). Save outputs and screenshots. M.
- [x] **1.9** AutoRemesher 1.2 quality and time table frozen in REFERENCE §4.1 (2026-10-14).
- [~] **1.10** Confirm or reject P1–P8 by profiling. Done on Linux (REFERENCE §4 last column, §4.1): P1, P3, P5–P7 confirmed, P2 confirmed with larger systems, P4 corrected, P8 not observed; new P9, P10. Eigen bundled: 5.0.1. Unknowns: cover ≈10⁵, curl system 2.2–3.9·10⁵ at 50k. Input ladder to 6.4M done. Left: number of integer variables per run; macOS/Accelerate and core count on Kajetan's machine (1.12).
- [ ] **1.11** Code checks left by the spec (no code change): which charge (q = 1 or 3) is valence 3 vs. 5 (spec §9.1); charge-to-cone sign in the disabled conformal solve (spec §11); the passes not read in full (spec §22); which of jakeblakeley's 1.0.0 crash fixes are still needed on 1.2. S.
- [ ] **1.12** Kajetan's machine (baseline §5, in order of value): (1) 3–5 own ZBrush/Blender sculpts (1–10M triangles) through `run_corpus.py`; (2) macOS probe build, to see whether P2 matters with Accelerate; (3) `experiments.sh` E1 on 8–16 cores; (4) ZRemesher output at the same counts through `metrics.py`, as the quality target (overlaps 1.8). S.

## Wave 2: diagnostics and cheap correctness fixes

All `OK-MIT` and good upstream patches. A/B each on the corpus. Diagnostics first, because everything later is judged by them.

- [~] **2.1** UV flip/degenerate counter after the cover solve, with exact `orient2d` (Shewchuk) (M2; perf R6). The baseline probe already counts flips by signed area (flips in 54/54 runs, median 0.75 %); port it with exact predicates. needs 1.6. S.
- [ ] **2.2** Integrality residual max|x/p − round(x/p)| over the *original* integer variables after the final solve; report pass-3 residual rows instead of ignoring them (M13). needs 1.6. S.
- [ ] **2.3** Health counters: non-finite values per solve, field-normalisation fallbacks (1e-12 guards), KKT fallback taken, valence > 12, extreme corner angles (perf §8.6), plus non-manifold edges, holes on closed inputs and output components vs. input islands (M14–M16). S.
- [ ] **2.4** Cleanup-ops counter per pass (rounds, edits per round). It should fall toward 0 as M1/M2 improve. S.
- [ ] **2.5** Remesher crease preservation (M11): re-enable the flip feature check (`isotropicremesher.cpp:463`); relax feature vertices only along the feature and project them onto it (`:483`); closest-point fallback when the normal ray misses; keep the feature flags as one `FeatureEdges` set for stages 6, 7, 11. needs 2.1–2.4. M. **Prerequisite for Wave 5.**
- [ ] **2.6** One sharp test |β| ≥ θ_s in FrameField, SingularitySimplifier and `edgeConstraint`, so concave creases are protected in stage 7 (M11). S.
- [ ] **2.7** Input sanitizer + scale normalisation (perf R2): weld with relative ε, remove degenerate and duplicate faces, split non-manifold vertices, orient coherently, scale to a unit box and undo on output; report every fix. Makes the absolute tolerances (1e-12 guards, 1e-5 `PositionKey`) safe. M · `OK-MIT` (re-implement; VCGlib is GPL-3.0, Geogram BSD-3).
- [ ] **2.8** Output fidelity (M14): project the final mesh onto the input M (T only as fallback); tangential, feature-aware smoothing; report extra components instead of deleting them. S–M.
- [ ] **2.9** Deterministic extraction: ordered iteration in the face search and graph passes (P8). Still needed although Linux/GCC output was deterministic: iteration order of unordered containers differs between libstdc++ and libc++ (macOS) and MSVC. S.
- [ ] **2.10** Intra-island TBB on crossing extraction, curvature and projection loops (perf R5; P1). Independent; any time after 1.7. S.
- [x] **2.11** **Quad count fix, interim (M7):** done 2026-10-15 (PR #2). Corpus: 0.98 / 0.995 / 1.000 × target median at 2k / 10k / 50k with adaptivity 1, the same with adaptivity 0; 107 of 108 runs within ±10 % (master: 0.37–0.51 by default, 0.82 median at adaptivity 0). Two measured causes: m_f normalised by a per-vertex κ̄ (asks for 0.27–0.85 of the count) and the continuous cover solve losing 3–60 % of the area (M3). Fix: each island gets its input-area share of the count, base quad edge √(A/N), Σ_f A_f m_f⁻² = Σ_f A_f, and an exact rescale of the continuous cover before rounding; `tests/quad_count_test.cpp` in CI. Side effect: T now has ≈2.5 triangles per output quad instead of ≈5.8 (M4). Superseded by 4.1. S · `OK-MIT`.
- [ ] **2.12** **Stop capping real boundaries (M15):** `fixHoles` (`quadextractor.cpp:1295`) fills only output loops that don't match an input boundary loop. Test on hand, demosthenes, human_neutral at 2k/10k. S · `OK-MIT`.
- [~] **2.13** **Non-manifold edges and holes in the output (M16):** 20/54 runs non-manifold, 4 closed inputs with holes. Non-manifold part done 2026-10-15: `fixHoles` filled some holes twice (duplicate quad); 26/90 corpus runs → 0. Holes and pinches done 2026-10-15: the hole filler gave up on bent loops and the repair missed pinches between closed fans; on 72 runs holes in closed inputs 1 → 0, pinched vertices 10 → 0, wrong χ 19 → 14. Open: the 14 runs with extra or missing handles, which come from `extractMesh` taking short graph cycles as faces in UV folds (REFERENCE M16); needs an injective map (4.1/4.5, 3.3) or face tracing in the extractor (6.1). S–M · `OK-MIT`.
- [ ] **2.14** **Small islands vanish (M14):** human_neutral's eyes are decimated from 1088 to 84 triangles and lost. Trace which step drops them; likely fixes are a minimum triangle count per island before decimation and keeping (or reporting) every component. S · `OK-MIT`.
- [x] **2.15** **T resolution as a setting (M4):** done 2026-10-15. `RemeshParameters::resolution` (interface 1.2), `--resolution fast|quality`, add-on Advanced > Resolution; default Quality. Fast is the old T (2 triangles per quad before stage 3), output bit-identical to master on 36/36 corpus runs. Quality is 4.5, the knee of a sweep over 2, 3, 4.5 and 6 at 2k/10k (REFERENCE M4): against Fast it cuts Hausdorff by 22 / 14 %, mean distance by 33 / 28 % and UV flips by 30 / 19 %, with the same count, at 1.5× the time. Interim until 7.4 and 2.8. S · `OK-MIT`.

## Wave 3: solver interface and rounding Stage A (critical path)

- [ ] **3.1** `SparseSolverBackend` behind `ConstrainedLeastSquares::Cache`: analyse / factorise / solve(many rhs) / info; Eigen simplicial default, Accelerate on macOS; runtime selection, logged (perf R3). Removes the `#if`. needs 1.6. S · `OK-MIT`.
- [ ] **3.2** Assemble the MILS system once and update it in place when variables are fixed, instead of a new `ConstrainedLeastSquares` per iteration (P7). Without this, greedy rounding costs hundreds of full factorisations. needs 3.1. S–M · `OK-MIT`.
- [ ] **3.3** **Greedy/batched rounding (M1 Stage A):** fix all integers within δ_k of an integer, δ growing geometrically; never round two cones onto one grid point (IGM separation idea); tie-break by index for determinism; local Gauss–Seidel updates with a full re-solve every few batches. needs 3.2, 2.1, 2.2. M · `OK-MIT` (no CoMISo). SQ-P3.
- [ ] **3.4** Exact translation lattice (M12): t ∈ ℤ² plus explicit integer cone constraints (MIQ style) or per-cone sublattice constraints, as its own A/B. needs 3.3; SQ-P1(b). Cheap check first [I]: if the derivation is right, the layout induced by the map is bipartite with every valence-3/5 pole in one colour class (all ±90° cones at uv with even u + v); count this on the corpus with 2.1. M · `OK-MIT`.
- [ ] **3.5** Lattice-preserving elimination (M13): integer rows pivot only on continuous or unimodular columns, or a Hermite/Smith-form construction. needs 2.2; SQ-P2. S–M · `OK-MIT`.
- [ ] **3.6** Optional MIQ stiffening loop driven by the flip counter. needs 3.3. S · `OK-MIT`.
- [ ] **3.7** Measure Stage A vs 1.2: UV flips, integrality residual, cleanup ops, % quads, irregularity excess, Hausdorff, time, determinism. Run the A/B at adaptivity 0 **and** 1: the stage-5 sizing causes most of today's flips (4–20× more than at adaptivity 0), so a single setting confounds rounding gains with sizing. needs 3.3. Feeds gate 7.1.

## Wave 4: sizing and field (parallel to Wave 3)

Tier A order from research/sizing-guides-symmetry.md §0: sizing field first, then size into the parametrization.

- [~] **4.1** **One sizing field** (Tier A #1; M7, F3 wiring). **Law part done 2026-10-15:** default adaptivity 0.5, which makes stage 5 follow the chord-error law κ^{−1/2}; over 72 corpus runs final UV flips ×0.48, non-quads ×0.72, folds ×0.72, angle p95 ×0.76 at the same mean distance (Hausdorff ×1.11), REFERENCE M7. The rest below is open. **Raised by the baseline:** the default count misses by 2–2.7× (53/54 runs under target) and the sizing drives most UV flips; 2.11 is only the interim fix. Design: scale-aware tensor (Rusinkiewicz or quadric fit at r ≈ c·h), κ = max(|κ₁|, |κ₂|) excluding hard feature edges, P2–P98 clamp, one implicit smoothing step; h ∝ κ^{−a/2}; thin-part cap h ≤ SDF/k; paint h·2^p; log-domain gradation by Dijkstra (|∇log h| ≤ γ, γh ≈ 0.3); count normalisation. Replaces both stage 3 and stage 5; T's resolution and the quad size both come from h; keeps 2.11's count normalisation. Start on T (interim, RECONCILIATION D3). needs 1.4. S–M · `OK-MIT`. SQ-Z3, SQ-Z4.
- [ ] **4.2** Field energy explicit and resolution-independent (M6; cross §4.1): Knöppel discretisation with mass matrix, λ = strength·h⁻², local saturating certainty, curvature target kept in every solve. needs 1.4. S · `OK-MIT` (geometry-central, MIT, as reference). SQ-X4.
- [ ] **4.3** Controlled MBO / Ginzburg–Landau loop with ε = c_ε·h, iterated until the singularity set is stable; measure how often stage 7 still fires (M5; cross §4.2). needs 4.2. S · `OK-MIT`. SQ-X1.
- [ ] **4.4** Soft guide strokes (Tier A #6; F4 soft): stroke tangent as an extra alignment target in the power field (a right-hand-side change). needs 4.2, G2. S–M · `OK-MIT`.
- [ ] **4.5** **Size into the parametrization** (Tier A #2; M3): cones placed with K − Δφ*; then (L + λM)φ = div⋆ω + λMφ*; per-face scale e^{−φ} in the cover energy. After A/B, delete the curl correction and the disabled conformal solve. needs 4.1, 4.2. M · `OK-MIT`. SQ-Z1, SQ-Z2, SQ-Z5. **Projection step measured 2026-10-15 on today's field and stage-5 sizes, not adopted** ([research/sizing-projection-2026-10-15.md](research/sizing-projection-2026-10-15.md)): continuous flips ×0.18 and the continuous rescale factor → 1, but on the output no better than lower adaptivity and mean distance ×1.13; the circulation term adds little over plain smoothing. The curl correction is still needed (off: ×3 flips). The disabled conformal solve was deleted. Revisit with the 4.1 field and cone placement, after 3.3 (rounding then makes about two thirds of the flips).
- [ ] **4.6** Curvature tensor on the input at radius r ≈ c·h, transferred to T by closest point with frame transport (M4 part 1; RECONCILIATION D3). needs 4.1, 2.7. S–M · `OK-MIT`.
- [ ] **4.7** Count controller part 1 (Tier A #4a; F6): secant on log s with the field reused (±1–2 % in 2–4 cover solves); report parity limits. needs 4.1; better after 3.3. S · `OK-MIT`. SQ-S3.

## Wave 5: features, symmetry, exact count, hard guides

All add integer constraints. needs **2.5** and **3.3**.

- [ ] **5.1** `FeatureEdges` set (Tier A #3; F1, F2, M8): sources dihedral, crease, face set, material, normal split, seam, guide; hard/soft and weight; the remesh keeps them as edge chains and splits triangles touching two chains. needs 2.5. M · `OK-MIT`.
- [ ] **5.2** Always-hard field lock on every hard feature; sector rule q = max(1, round(2α/π)) with a tie-break near 135°; no "last edge wins". needs 5.1, 4.2. M · `OK-MIT`. SQ-F1.
- [ ] **5.3** Hard features as integer isolines without the 10° drop; drop only infeasible strips (narrower than ≈h/2) with a warning. needs 5.2, 3.3; may need Stage B (SQ-F2). M · `OK-MIT`.
- [ ] **5.4** Bridge inputs for F1/F2: sharp, crease, seams, face sets, materials → `FeatureEdges`. needs 5.1, G2. S.
- [ ] **5.5** Mirror symmetry (Tier A #5; F5): plane detection (PCA + bbox planes + reflective ICP), symmetric triangle remesh, field constraint z_σ(f) = conj(z_f), param constraint f∘σ = A f + t with joint rounding of σ-pairs, seam modes (edge loop / centred row / 45°), pair averaging. Not cut-mirror-weld of the output. needs 3.3; 5.1 helps. M · `OK-MIT`. SQ-S1, SQ-S2.
- [ ] **5.6** Count controller part 2 (Tier A #4b): chord enumeration + knapsack insert/collapse, ±1 local ops, paired steps under symmetry. needs 4.7, 3.3. M · `OK-MIT`. SQ-S3.
- [ ] **5.7** Hard guide curves (Tier A #7; F4 hard): embed, lock, integer isoline per segment, sector rule at corners and crossings, guide snap tolerance. needs 5.3. M–L · `OK-MIT`. SQ-F2, SQ-F3.
- [ ] **5.8** Density paint (F3): per-vertex log₂ multiplier from a vertex group or color attribute. needs 4.1, 4.5, G2. S.
- Deferred: intrinsic symmetry (Tier A #8): no licensed code (`ASK`), no commercial tool offers it.

## Wave 6: extraction and cleanup (needs 3.3)

- [ ] **6.1** libQEx A/B behind `QuadExtractor` (convert per-corner UV, cut graph and transitions). needs 3.3, 2.1. M · `OK-GPL3` (GPL-3.0-or-later, confirmed in 0.4). SQ-E1, SQ-E2.
- [ ] **6.2** Replace the 12 passes with a half-edge worklist of grid-preserving operators (doublet collapse → quad-vertex merge → diagonal collapse → chord collapse → cavity re-quadrangulation) under a validity guard (no flips, min scaled Jacobian, Hausdorff ≤ ε·h); flat arrays (P5) in the same rewrite (extr §4.2; perf R4; P3). needs 6.1 result, 2.4. M–L · `OK-MIT`. SQ-E5, SQ-E6, SQ-E7.
- [ ] **6.3** Optional: Ray 2025 dual-segmentation extractor, only if 3.7 still shows folds. needs 3.7. L · re-implement (no code released). SQ-E3, SQ-E4.
- [-] **6.4** **Dropped by 0.2** (no GPL-3.0-only code). Revisit only if 0.2 is reversed. Was: optional hard-surface backend, quadwild-bimdf free build. M · **`GPL3-ONLY`** (CoMISo); Gurobi and Blossom-V **`NO`**.

## Wave 7: gate and the larger steps

- [ ] **7.1** **Gate:** after 3.7 and 6.1, if Stage A gets within the agreed metric distance (0.7) of the targets → keep upgrading inside the current structure; otherwise start 7.2. Record numbers and decision in a session file.
- [ ] **7.2** **Stage B (M1(b), M2):** continuous seamless map with fixed cones → injectivity repair (foldover-free maps / SLIM) → motorcycle graph / T-mesh → Bi-MDF quantization with libSatsuma (build with Blossom-V off) → per-patch Tutte + SLIM → extraction (libQEx or own tracer). Metriko as reference and oracle; boundary support must be added (islands, F10). Penner-coordinate solve only with the authors' permission. needs 7.1. L · `OK-MIT` (libSatsuma MIT, Metriko MPL-2.0) + `OK-GPL3` (libQEx). SQ-L1–L5, SQ-P4, SQ-P5.
- [ ] **7.3** Research prototype, offline: singularity placement by distortion (M5, F9). A: cones first (integer-constrained cones from K − Δφ*) → trivial-connection field → 4.5. B: joint frames, port moving frames (MIT Python). Decide on corpus numbers. needs 4.5. L · `OK-MIT` (Du et al. code: `ASK`). SQ-X2, SQ-X5, SQ-X6; learned cone priors only later (SQ-P6).
- [ ] **7.4** Field on a finer mesh (M4 part 2; F11): k = 2–4×, with index-preserving restriction to the cover mesh. needs 3.1, 4.6; may need 8.3. M · `OK-MIT`. SQ-X3.

## Wave 8: performance (needs 3.1 and the baseline numbers)

Order from perf §10, now checked against the baseline profile (REFERENCE §4, §4.1). 8.0 and 8.7 need nothing first.

- [ ] **8.0** **Link TBB's scalable allocator** (`tbbmalloc_proxy`; TBB is already a dependency): 1.22–1.54× faster at 50k with byte-identical output (baseline §4.4; P5). Check Windows/macOS linking and the Blender worker process. Interim until flat containers (6.2). Caveat: the proxy replaces malloc through the shared library (Windows needs the DLL), while G3 plans static oneTBB; the fallback there is `tbb::scalable_allocator` on the hot node containers of the extractor. S · `OK-MIT` (oneTBB Apache-2.0).
- [ ] **8.1** CHOLMOD supernodal backend with a deterministic mode, only if the solve is > ≈20 % of time (perf R8). **Measured: not yet.** Solves are 14/20/27 % at 2k/10k/50k; CHOLMOD speeds factorisation 1.6–2.2× at 50k only, whole run −1 % to +13 %. Re-measure after 3.3 and 7.4. needs 3.1, 1.10. M · `OK-GPL3` (Supernodal GPL-2+, Cholesky LGPL-2.1+). Watch TBB/OpenMP oversubscription.
- [ ] **8.2** **Large inputs (P4, corrected by the baseline):** the cost at 6.4M triangles is serial pre-processing: island split 6.7 s (`meshseparator.cpp:94`), QEM decimation 9.9 s, island contexts 3.2 s, OBJ parse 4.3 s, i.e. 24 of 27.5 s. Parallel island split (union-find over edges) and contexts first, then parallel or partitioned decimation. The OBJ parse goes away with the G2 `.npz` protocol. The isotropic remesher itself is bounded by the target and comes last. M · `OK-MIT`.
- [ ] **8.3** AMGCL-preconditioned CG backend for finer field meshes (perf R10). needs 3.1, 7.4. S–M · `OK-MIT`.
- [ ] **8.4** Coloured hierarchical Gauss–Seidel field solver, Instant-Meshes style, re-implemented (perf R11; P1). needs 7.4. M · `OK-MIT`.
- [ ] **8.5** Ebke et al. 2016 proxy + transfer for 2M+ inputs at finer field resolution (perf R12). needs 3.7, 7.4. L · `OK-MIT`.
- [ ] **8.6** CI regression run: 5 meshes × 1 target per PR; fail on > 15 % time or any health-counter regression (threshold to tune). needs 1.6. S.
- [ ] **8.7** **Local `cancelPair` (P9):** `singularitysimplifier.cpp:263` allocates and scans face- and vertex-sized arrays per candidate pair (two full `vertexCharges()`), up to 42 % of a run on cone-heavy inputs. Keep region-local arrays and update charges incrementally; check identical output on the corpus. S · `OK-MIT`.
- Not planned: GPU solvers (≤ 2×, CUDA-only), MKL/Panua PARDISO, cuDSS, Gurobi (`NO`).

## Track G: Blender layer (parallel to everything)

- [ ] **G1** = 1.3: CMake + nanobind module of the Qt-free core (port jakeblakeley). S–M · `OK-MIT`.
- [ ] **G2** Subprocess worker of Blender's Python + modal operator (Esc cancels) + `.npz` protocol that carries per-vertex/edge/face attributes (port jakeblakeley's add-on). M · add-on GPL-3.0-or-later.
- [ ] **G3** cibuildwheel CI and per-OS extension packaging; static oneTBB, because Blender bundles oneTBB 2022.3.0. M · `OK-MIT`.
- [ ] **G4** Port from jakeblakeley: scale normalisation (= 2.7), result health check (= 2.3), island detail floor, weld-shells option, retries + triangle fallback. Thin features via the SDF cap in 4.1, not Geogram's LFS. S–M.
- [ ] **G5** Expose anisotropy; quality report panel (F15) from the 1.4 metrics. S.
- [ ] **G6** Wire the core inputs as they land: features (5.4), density paint (5.8), mirror (5.5), guides (4.4, 5.7).
- [ ] **G7** Later: half/double (F7), partial remesh (F10), cached field (F13), attribute transfer (F14).
- [ ] **G8** End-to-end Blender timing with headless Blender around the worker, to separate IO from core time (P6; perf §9.3). S.

---

## Open questions (project-level)

Math questions for specialists are in [SPECIALIST-QUESTIONS.md](SPECIALIST-QUESTIONS.md).

- [x] What does `setVariablePeriod(..., 2)` on translations mean? Translations are rounded to 2ℤ², which puts every cone on ℤ² without explicit constraints but over-restricts (REFERENCE M12). Exact encoding: SQ-P1.
- [~] Why was `computeConformalScaling` disabled? Commented out in `dd87c6e` "Add curl correction" (2026-08-12). Structural reason: with fixed cones it has no local size freedom (REFERENCE M3). Intent: only upstream knows; contact deferred (0.5), not needed for the fix.
- [~] Is the one-shot rounding intentional? Present since `8c9f01f` (2026-08-09); not a Geogram port (RECONCILIATION C1). Intent: only upstream knows; contact deferred (0.5), not needed for the fix.
- [x] Is `ModelType` used? No, stored and never read. Plans: unknown; contact deferred (0.5).
