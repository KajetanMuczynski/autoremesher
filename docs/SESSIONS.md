# AutoRemesher upgrade: session log

Append one entry per working session (newest at the bottom). Keep it short: what was done, what was found, what's next, which commit/versions.

Template:
```
## YYYY-MM-DD · <who / device> · <short title>
- Repos/commits: core <sha>, bridge <sha>
- Did:
- Found:
- Measured: (numbers or "nothing measured")
- Next:
```

---

## 2026-10-14 · Claude (cloud session) · Initial audit and plan
- Repos/commits: core `huxingyi/autoremesher@4a49f82` (v1.2.0, MIT); bridge `adriflex/autoremesher-blender-bridge@75f0c22` (v0.1.3, GPLv3).
- Did: cloned both, read the full core pipeline (autoremesher, parameterizer, framefield, singularitysimplifier, quadparameterizer, mixedintegerleastsquares, constrainedleastsquares, quadextractor structure) and the bridge. Wrote REFERENCE.md and TODO.md.
- Found (code read, see REFERENCE §4–5):
  - Integer rounding is effectively one-shot (all integers rounded at once): `mixedintegerleastsquares.cpp:461`.
  - Conformal sizing solve exists but is commented out: `parameterizer.cpp:388`.
  - Field and parametrization are solved on a mesh at roughly target quad resolution.
  - Islands are the only parallelism; single-island sculpts run parameterize/extract on one core.
  - QuadExtractor has ~12 repair passes that rebuild a global edge map every round.
  - Two different curvature/density estimators; `ModelType` unused.
  - Core has no Qt dependency, so it can become a library / Python module.
  - Bridge: blocking `subprocess.run`, OBJ files, no anisotropy option.
- Measured: nothing. Not built or run.
- Next: Phase 0 decisions (upstream vs private fork, licensing), Phase 1 build, Phase 2 corpus + metrics.

## 2026-10-14 · Claude (cloud session) · Review of jakeblakeley/autoremesher-blender
- Repos/commits: fork `jakeblakeley/autoremesher-blender@5368a8c`, forked from upstream `061f740a` (v1.0.0).
- Did: cloned, diffed against its fork point, read the add-on, worker, binding, CMake/packaging and core changes. Added REFERENCE §6.1 and TODO items.
- Found: a one-day fork (2026-07-07), unmaintained since, macOS-only tested, core still on the Geogram pipeline that upstream replaced in 1.1. Strong parts: nanobind module + cibuildwheel + Blender extension packaging, crash-isolated subprocess worker with modal progress. Core additions: LFS thin-feature sizing (Geogram), island detail floor, health check, scale normalisation. No changes to the field/param/rounding/extraction math.
- Decision proposed: borrow the infrastructure and ideas, port them onto current upstream; don't build on its core.
- Measured: nothing.
- Next: same as before, plus port the packaging during Phase 1.

## 2026-10-14 · Claude (cloud session) · License decision recorded
- Decision (Kajetan): public GPL-3.0-or-later fork for the community. GPL solvers (QEx, CoMISo, QuadWild) allowed.
- Did: added the "License decision" section to REFERENCE §1 (why GPLv3 not v2: oneTBB Apache-2.0; dependency compatibility table; attribution checklist) and the matching Phase 0 TODO items.
- Next: Phase 1 on Kajetan's machine: create the fork repo with license files, build, then port the jakeblakeley packaging.

## 2026-10-14 · Claude (thread "Research: cross-fields and singularities", 19:10–19:21 UTC) · Cross-field research
- Repos/commits: literature and code survey; AutoRemesher field code not re-read (described from REFERENCE.md).
- Did: wrote [research/cross-fields.md](research/cross-fields.md): formulations (power field, Ginzburg–Landau/MBO, trivial connections, PolyVector, joint frame + metric), methods, learned fields, upgrade plan for stages 6–7, questions Q1–Q8.
- Found: the power-field representation is already right; the gap is what the field sees (resolution, M4) and how singularities are chosen (M5). The relax–normalise loop is a truncated MBO scheme with an implicit ε. Joint methods: moving frames (MIT), RSP (license unclear), odeco fields (no code). Learned fields are AGPL or unreleased and GPU-bound.
- Measured: nothing.
- Next: TODO 4.2, 4.3, 7.3, 7.4; SQ-X1–X6.

## 2026-10-14 · Claude (thread "Research: parametrization and integer rounding", 19:10–19:21 UTC) · Rounding research
- Repos/commits: core `4a49f82`; Geogram `ef0e4e3` (parameterization dir).
- Did: wrote [research/parametrization-rounding.md](research/parametrization-rounding.md): taxonomy (MIQ rounding, QGP/T-mesh quantization, valid seamless maps, robust extraction, learned), recommended Stage A / Stage B path, questions Q1–Q10.
- Found: one-shot rounding confirmed; not a Geogram port (Geogram's quad param is PGP, no integers); period-2 translations put cones on ℤ² implicitly but over-restrict; Bi-MDF via libSatsuma (MIT) is the integer engine for Stage B, Metriko (MPL-2.0) the reference; CoMISo is GPL-3.0-only; Penner/RSP/topological-IGM repos have no LICENSE file; neural rounding not recommended.
- Measured: nothing.
- Next: TODO 3.1–3.7, 7.2; SQ-P1–P6, SQ-L4–L5, SQ-Z5.

## 2026-10-14 · Claude (thread "Research: quad extraction and layout methods", 19:10–19:19 UTC) · Extraction and metrics research
- Did: wrote [research/extraction-layout-metrics.md](research/extraction-layout-metrics.md): QEx, Ray 2025, graph extraction, layout-first pipelines (QuadWild, Bi-MDF, FSCQ), cleanup operators, a metric set (topology, element quality, fidelity, alignment, poles, symmetry, cost) and a benchmark protocol; questions Q-E, Q-L, Q-C, Q-M.
- Found: the extractor is not the root problem (M1/M2 are); libQEx (GPL-3.0) is the drop-in candidate once the map is valid; replace the 12 repair passes with a grid-preserving operator queue; Blossom-V and Gurobi must stay off in quadwild-bimdf.
- Measured: nothing.
- Next: TODO 0.7, 1.4, 6.1–6.4; SQ-E1–E7, SQ-L1–L3, SQ-M1–M4.

## 2026-10-14 · Claude (thread "Research: sizing fields, guides and symmetry", 19:10–19:24 UTC) · Tier A feature research
- Did: wrote [research/sizing-guides-symmetry.md](research/sizing-guides-symmetry.md) and raw worker notes in `research/sizing-guides-symmetry-notes/` (A sizing, B guides/features, C symmetry/count); Tier A order and questions Q1–Q10.
- Found: one unified sizing field (h ∝ κ^{−a/2}, SDF cap, log gradation, count normalisation); density and an isotropic field are coupled by Δφ = K − K̂, so paint forces poles unless graded and projected by (L + λM)φ = div⋆ω + λMφ*; sector rule q = max(1, round(2α/π)) for feature corners; symmetry via a symmetric triangle remesh plus linear constraints, not output cut-mirror-weld; exact count via secant on log s plus strip knapsack. Disagreed with REFERENCE §7 on F3 risk and F5 method.
- Measured: nothing.
- Next: TODO Wave 4 and 5; SQ-Z1–Z4, SQ-F1–F3, SQ-S1–S3.

## 2026-10-14 · Claude (thread "Research: speed and numerical robustness", 19:10–19:23 UTC) · Performance research
- Repos/commits: core `4a49f82` (solver and threading code).
- Did: wrote [research/performance-robustness.md](research/performance-robustness.md): sparse solvers and licenses, MIQ speed, multiresolution (Instant Meshes, multigrid, Ebke 2016), GPU, parallel remeshing, preprocessing, exact predicates, profiling method, corpus design, ranked actions R1–R13.
- Found: systems are ≈10⁵ unknowns, so the solver is probably not today's bottleneck; MILS rebuilds the whole system each iteration, which greedy rounding would turn into a ~100× regression; coarse-to-fine beats GPU; determinism must be a requirement; MKL/Panua PARDISO, cuDSS, Gurobi excluded.
- Measured: nothing.
- Next: TODO 1.6, 1.7, 2.3, 2.7, 2.10, 3.1–3.2, Wave 8.

## 2026-10-14 · Claude (thread "Code-to-math spec of AutoRemesher", 19:15–19:42 UTC) · Stage-by-stage specification
- Repos/commits: core `4a49f82` (code read only).
- Did: wrote [research/code-to-math-spec.md](research/code-to-math-spec.md): formulas, constants and deviations from the source papers for every stage, and §23 with 21 corrections to REFERENCE.md.
- Found: curvature target used only in the first of 5 field solves; quad size = λ·ℓ̄_T·m_f·ρ_f^{±1}, ≈0.87 Q in the uniform case; remesher erodes creases; final projection onto T, not the input; period 2 ⇒ translations in 2ℤ²; elimination ignores its consistency check.
- Measured: nothing.
- Next: corrections merged into REFERENCE.md by the consolidation thread (below).

## 2026-10-14 · Claude (thread "Reproducible baseline and profiling", 19:15–20:25 UTC) · Baseline measured
- (Entry written by the consolidation thread from the finished report; the baseline thread did not edit shared files.)
- Did: built upstream `4a49f82` on Ubuntu 24.04 (GCC 13.3, Qt 5.15.13, oneTBB 2021.11, bundled Eigen 5.0.1). Wrote the Qt-free `ar_bench` driver and a counters-only probe patch. Ran 18 meshes × 2k/10k/50k quads (54 runs, 0 failures) plus experiments: threads, input ladder to 6.4M triangles, CHOLMOD, tbbmalloc, adaptivity, `perf`. Report: [research/baseline-and-profiling.md](research/baseline-and-profiling.md); scripts and per-run tables: [research/baseline-scripts/](research/baseline-scripts/).
- Measured: median run 0.7/3.1/20.4 s; quads 0.37–0.51 × target by default; UV flips in 54/54 runs (median 0.75 %); non-manifold output in 20/54; open boundaries capped by `fixHoles`; no symmetric layout; tbbmalloc 1.22–1.54× with identical output; `cancelPair` up to 42 % of a run; CHOLMOD −1 % to +13 % end to end; deterministic on Linux.
- Next: the same scripts on Kajetan's machine (TODO 1.12).
## 2026-10-14 · Claude (thread "Consolidate research into project files", 19:52– UTC) · Research merged into the project files
- Did: applied all 21 code-to-math corrections and the research conclusions to REFERENCE.md (pipeline table, P1–P8, M1–M14 with new M11–M14, §7 features, papers, corrections log in §9); split licenses into LICENSES.md (flags OK-MIT / OK-GPL3 / GPL3-ONLY / ASK / NO); wrote RECONCILIATION.md (27 conflicts between sources and which one wins); rebuilt TODO.md as one dependency-ordered plan (Waves 0–8 + Blender track) with license flags; collected 39 self-contained questions (merged from the 42 numbered questions in the reports plus the open asks in the old REFERENCE) in SPECIALIST-QUESTIONS.md; added README.md; archived the pre-merge REFERENCE.md and TODO.md in `archive/`. Left a marked placeholder for the baseline report (REFERENCE §4.1).
- Found: conflicts worth knowing: CoMISo is GPL-3.0-only (also via quadwild-bimdf); the RSP repository's license is reported both as "none" and as AGPL-3.0 (unresolved, treated as none); final projection is onto T, not the input; curvature should be computed on the input, not on T, once M4 work starts.
- Measured: nothing.
- Next: Kajetan: TODO 0.2 (GPL-3.0-only policy), 0.5 (write to upstream), 0.8 (send SPECIALIST-QUESTIONS.md "Ask first"). Code: TODO 1.6 → 2.1–2.2 → 3.1–3.3.

## 2026-10-14 · Claude (thread "Consolidate research into project files", ≈20:16 UTC) · Wave 0 decisions recorded
- Decided by Kajetan: **0.2** no GPL-3.0-only code (CoMISo and quadwild-bimdf out; TODO 6.4 dropped). **0.5** upstream contact deferred; it blocks nothing. **0.8** specialist questions prepared, not sent.
- Did: recorded the decisions in TODO.md (new status `[-]` deferred/dropped), LICENSES.md §1–2, REFERENCE.md and RECONCILIATION.md. Wrote [SPECIALIST-BRIEF.md](SPECIALIST-BRIEF.md): the 9 "Ask first" questions rewritten for an outside reader, in four parts by recipient, with full references.
- Found: libQEx is GPL-3.0-**or-later** (file headers and README); QuadWild is too (one header sampled). Both stay allowed under 0.2, so TODO 6.1 is unaffected. A new consequence of the 2ℤ² lattice **[I, unchecked]**: the induced layout is bipartite with every valence-3/5 pole in one colour class, and the gauge pins a regular vertex to a grid point. Added to REFERENCE M12, SQ-P1 and the brief, with a cheap check in TODO 3.4.
- Measured: nothing.
- Next: Kajetan decides when and to whom the brief goes (TODO 0.8). Code: TODO 1.6 → 2.1–2.2 → 3.1–3.3.

## 2026-10-14 · Claude (thread "Consolidate research into project files", ≈20:26 UTC) · Baseline folded in
- Did: replaced the REFERENCE §4.1 placeholder with the measured baseline. Added a measured verdict to P1–P8, M1–M4, M7 and M14, and new items P9, P10, M15 and M16. Corrected §2 (apt package, headless env var, `--report`). Added RECONCILIATION §5 (B1–B8, measurement beats code read). Updated TODO Wave 1 statuses (1.9 done, 1.12 new) and added quick wins 2.11–2.14, 8.0 and 8.7; retargeted 8.1 and 8.2. Added the measured flip rates to SPECIALIST-BRIEF.md and SQ-E1.
- Found: the biggest user-visible bug is the quad count (2–3× under target by default), not speed. The cheapest win is tbbmalloc (one link flag).
- Archive: the exact pre-baseline REFERENCE.md was saved by a parallel thread as `archive/REFERENCE-2026-10-14-pre-baseline.md`. **No pre-baseline copy of TODO.md was made**; the changes are the ones listed in "Did". That parallel thread ("Fold baseline results into plan files") stood down without editing; its checklist added: A/B at adaptivity 0 and 1 in 3.7, 4.1 raised, the tbbmalloc static-TBB caveat, the 2.9 libc++ note, and measured lines in SQ-P1/P3/Z1/E2/E3.
- Measured: nothing new (folding only).
- Next: code: 8.0, 2.11, 2.12 (quick wins), then the critical path 1.6 → 2.1–2.2 → 3.1–3.3. Kajetan: 1.12 on his machine; 0.8 when he wants.

## 2026-10-15 · Claude (cloud thread "Fix quad count undershoot") · TODO 2.11 fixed
- Repos/commits: fork master `ea03fc1` → PR #2 (merged as `246a315`).
- Did: traced the low count with a local probe (per-island sizing count, continuous and integer uv area), fixed it, added `tests/quad_count_test.cpp` and the CI job `core-tests`, ran the 18-mesh corpus at 2k/10k/50k (adaptivity 1 and 0, master and fix) and an equal-output-count comparison against master; tested a 2.25× finer T.
- Found: two causes multiply. m_f is normalised by a per-vertex κ̄ on the adaptive T (asks for 0.27–0.85 of the count), and the continuous cover solve loses 3–60 % of the area with the curvature scale field (a direct M3 measurement). Fixing the count drops T to ≈2.5 triangles per quad, which costs per-quad quality (M4).
- Measured: count 0.98–1.00 × target median, 107/108 runs within ±10 % (master 0.37–0.51 default, 0.82 at adaptivity 0). At equal output count 1.4–1.6× faster than master but worse angles and Hausdorff; T 2.25× finer recovers flips and Hausdorff at 1.5–1.65× the time (REFERENCE M4).
- Next: 2.15 (T resolution setting and its default) needs Kajetan's call on quality vs time; 4.5 should shrink the continuous rescale factor.

## 2026-10-15 · Claude (cloud thread "Fix quad count undershoot") · TODO 2.15 Fast/Quality resolution
- Repos/commits: fork master `d95bdd7` → PR (feat(sizing), TODO 2.15).
- Did: made T's resolution a setting (engine triangles per quad; `remesh()` `resolution` fast|quality, interface 1.2; CLI, `ar_bench`, add-on Advanced > Resolution); small-island floor keeps the mode; count test covers both modes. Swept 2, 3, 4.5, 6 triangles per quad at 2k/10k.
- Found: 4.5 is the knee; Fast's output is bit-identical to master (36/36).
- Measured: Quality vs master (= Fast) at 2k / 10k: Hausdorff −22 / −14 %, mean distance −33 / −28 %, UV flips −30 / −19 %, scaled Jacobian < 0.5 share −43 / −6 %, angle p95 −4 / −6 %, same count, 1.5× the time.
- Next: 7.4 (field on a finer mesh) and 2.8 (project onto the input) should make most of Quality's cost unnecessary.

## 2026-10-15 · Claude (cloud thread "Suzanne check on master") · Suzanne re-check, TODO 2.13 non-manifold part fixed
- Repos/commits: fork master `12be408` → PR (fix(extraction), TODO 2.13).
- Did: re-ran Kajetan's first Blender case (Suzanne + Subdivision 2, 5000 quads) through the add-on zip installed into `bpy` 4.5; the pre-fix CLI (`bd84f73`) reproduces his 1730 / 6 / 5. Traced Quality's 4 non-manifold edges to `fixHoles`, fixed it, added `tests/hole_filling_test.cpp`, ran a master/fix A/B on 90 corpus runs.
- Found: `fixHoles` ran its unscored pass on holes the scored pass had already closed at 4 vertices and added the closing quad again. This was the source of M16's non-manifold edges; it also made small islands look unhealthy and get retried at a raised count (spot_x8 2k).
- Measured: Suzanne 5k on master: Fast 5091 quads / 4 non-quads / 5 folded, Quality 4769 / 3 / 2 (4763 / 3 / 2 with the fix), eye loops open, head UV flips 141 / 9624 (Fast) and 127 / 19 990 (Quality). A/B: 63/90 byte-identical; 26 runs with non-manifold edges (316 in all) → 0; quads −0.1 to −1.7 %, boundary edges unchanged.
- Next: holes in closed inputs (rest of 2.13); remaining non-quads/folds are 4.1/4.5 + 3.3.

## 2026-10-15 · Claude (cloud thread "Supply-chain audit") · CI and dependency supply-chain audit
- Repos/commits: fork master `6f68495` → PR #24 (ci(ci), draft).
- Did: audited both workflows, every fetched or bundled library and tool, and the add-on zip; checked recent advisories (actions-cool tag hijack May/Sep 2026, Megalodon, PyPI Shai-Hulud copycat, Qt 5.15 CVEs, Homebrew qt@5 deprecation). PR #24 pins all actions to commit SHAs, sets a read-only token, drops persisted checkout credentials, pins the test-model repo, checks the Blender archive's SHA-256 and adds Dependabot for actions. Report: project files `research/supply-chain-audit-2026-10-15.md`.
- Found: no compromise; no secrets or `pull_request_target`. Open risks: AppImage built with unverified "continuous" linuxdeployqt/appimagetool; AppImage and Windows zip ship Qt 5.15.2; install-qt-action v3 still runs a mutable inner ref (v4.4.1 fixes it); Homebrew qt@5 disabled 2027-05-19.
- Measured: zizmor 1.31 offline 31 high + 19 medium → 0; vendored Eigen byte-identical to 5.0.1, meshoptimizer `.cpp` identical to v1.2.
- Next: pin and checksum the AppImage tools; install-qt-action v4.4.1; hashed CI requirements; Kajetan's repo settings list in the report.

## 2026-10-15 · Claude (cloud thread "Holes in closed inputs") · TODO 2.13 holes and pinches fixed
- Repos/commits: fork master `6f68495` → PR #25 (fix(extraction), TODO 2.13).
- Did: per-step probe of the extractor (topology after each step, the isoline graph, cycles the side test rejects) on csg_bracket, sword, boat and plane; fixed the two repair defects below; added the corner-hole and pinch cases to `tests/hole_filling_test.cpp` (both fail without the fix); A/B on 72 corpus runs (18 meshes, 2k/10k, Fast and Quality) and 78 closed procedural runs (thin ellipsoids, tori; 150/500/2000 quads).
- Found: the map folds on these inputs (5–8 % of T flipped), so `extractMesh` leaves 40–80 holes and pinched pieces per island. `fixHoleWithQuads` gave up on loops bent around a fold or corner (sword 2k Fast kept an 8-, later 6-edge hole), and `removeNonManifoldFaces` missed pinches between closed fans. The cleanup passes never change χ. The remaining genus errors are extra handles already in the extracted faces, one per fold (csg_bracket: bolt-hole rims), from `extractMesh` taking short cycles as faces.
- Measured: master: 1 closed run with a hole, 10 with pinched vertices, 19 with wrong χ. Fix: 61/72 corpus and 75/78 closed runs byte-identical; holes 1 → 0, pinches 10 → 0, wrong χ 19 → 14; thin torus 150 keeps its handle (Hausdorff 61 → 3.9 % diag). Changed runs: quads within ±1 %, SJ ≤ 0 quads lower in 9 of 11, equal in 1, higher on sword 2k Fast (63 → 68).
- Next: face tracing in the extractor or an injective map (4.1/4.5, 3.3) for the handles; Kajetan to choose whether to prototype tracing.

## 2026-10-15 · Claude (cloud thread "Supply-chain audit") · Ship only the Blender add-on
- Repos/commits: fork master after PR #24 → PR (ci(ci): ship only the Blender add-on in releases, draft).
- Did: on Kajetan's decision, removed upstream's `release.yml` (AppImage, Windows Qt zip, DMG) and its AppImage metadata in `ci/`; tags now run `ci.yml`. Added a macOS (Apple silicon) add-on build: static oneTBB, macOS 11.2 target, `otool` check, installed into Blender 5.2.2 from its DMG. The Windows and macOS zips are uploaded as `addon-<platform>`.
- Found: removes the audit's AppImage-tool, Qt 5.15.2 and Homebrew `qt@5` findings. Static oneTBB also builds on Linux (checked locally).
- Next: portable Linux add-on zip (static oneTBB and libstdc++, glibc 2.28 floor); try the macOS zip on a real Mac (Gatekeeper).
