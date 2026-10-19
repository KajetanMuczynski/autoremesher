# AutoRemesher upgrade: project files

Goal: upgrade AutoRemesher (huxingyi/autoremesher, MIT) into a GPL-3.0-or-later fork with ZBrush-ZRemesher-like quality, usable from Blender. Stage-by-stage upgrade, not a rewrite. Index last updated 2026-10-14.

**New here?** Read TODO.md "Order at a glance", then the latest entry in SESSIONS.md, then REFERENCE.md §3 (pipeline) and §5 (issues).

## Working files

| File | What it is |
|---|---|
| [README.md](README.md) | This index. |
| [TODO.md](TODO.md) | The plan: one dependency-ordered list (Waves 0–8 + Blender track G) with status, effort and a license flag per item. Start here. |
| [REFERENCE.md](REFERENCE.md) | Technical reference: repos and commits, build, pipeline map with line numbers, performance issues P1–P10, math issues M1–M16, Blender integration, ZRemesher-like features F1–F15, papers, and the log of the 21 code-to-math corrections (§9). §4.1 holds the measured baseline. |
| [SPECIALIST-BRIEF.md](SPECIALIST-BRIEF.md) | The 9 "Ask first" questions, ready to forward: self-contained for a reader who has seen none of these files, in four parts by recipient, with full references. Not sent yet (TODO 0.8). |
| [SPECIALIST-QUESTIONS.md](SPECIALIST-QUESTIONS.md) | 39 open math questions (SQ-X, Z, P, L, F, S, E, M), each self-contained so it can be forwarded alone, with an "Ask first" list and suggested experts. |
| [LICENSES.md](LICENSES.md) | License decision, dependency table, every candidate library's license as checked by the research, the flags used in TODO.md, test-data licensing, attribution checklist. |
| [RECONCILIATION.md](RECONCILIATION.md) | 27 places where project files disagreed and 8 where measurement overturned a code read (B1–B8), which source wins and why. |
| [SESSIONS.md](SESSIONS.md) | Session log, one entry per working session or thread (append at the bottom). |

## Research reports (`research/`)

All written 2026-10-14. Only the baseline report measured anything; the others are code reads and literature. Their conclusions are folded into the working files above; read a report for the detail and the sources.

| File | Scope |
|---|---|
| [research/code-to-math-spec.md](research/code-to-math-spec.md) | What the code at `4a49f82` computes, stage by stage: formulas, constants table, deviations from the papers, 21 corrections to REFERENCE.md (§23). The most precise description of the current code. |
| [research/cross-fields.md](research/cross-fields.md) | Cross fields and singularities (stages 6–7; M4–M6, M8): formulations, Ginzburg–Landau/MBO, joint frame + parametrization methods, learned fields, upgrade plan. |
| [research/parametrization-rounding.md](research/parametrization-rounding.md) | Seamless / integer-grid parametrization and rounding (stages 13–16; M1, M2): MIQ, IGM, QGP, Bi-MDF, valid seamless maps, the period-2 lattice, why not neural rounding, Stage A / Stage B path. |
| [research/extraction-layout-metrics.md](research/extraction-layout-metrics.md) | Quad extraction (QEx, Ray 2025), layout-first pipelines (QuadWild, Bi-MDF, FSCQ), cleanup operators, and the metric set and benchmark protocol. |
| [research/sizing-guides-symmetry.md](research/sizing-guides-symmetry.md) | Tier A features: unified sizing field, density paint, how size enters the parametrization, features and guide curves, mirror symmetry, exact quad count. |
| [research/sizing-guides-symmetry-notes/](research/sizing-guides-symmetry-notes/) | Raw worker notes behind the sizing report: `A-sizing.md`, `B-guides-features.md`, `C-symmetry-count.md`. Superseded by the report where they differ. |
| [research/performance-robustness.md](research/performance-robustness.md) | Solvers and their licenses, MIQ speed, multiresolution, GPU, parallel remeshing, input sanitizing, exact predicates, profiling method, ranked actions R1–R13. |
| [research/baseline-and-profiling.md](research/baseline-and-profiling.md) | Measured baseline of AutoRemesher 1.2 on Linux: build, 18-mesh corpus × 2k/10k/50k, time, memory, quality, UV flips, experiments (threads, input size, CHOLMOD, allocator, adaptivity, CPU profile), verdicts on every REFERENCE claim, 6 new findings, what to run on Kajetan's machine. Summary in REFERENCE §4.1. |
| [research/baseline-scripts/](research/baseline-scripts/) | Scripts behind it: build script, Qt-free `ar_bench` driver, counters-only probes patch, CHOLMOD experiment, corpus definition and fetch script, metrics, experiments, per-run tables in `results/`. See its README. |

## Archive (`archive/`)

| File | What it is |
|---|---|
| [archive/REFERENCE-2026-10-14-pre-merge.md](archive/REFERENCE-2026-10-14-pre-merge.md) | REFERENCE.md before the research merge ("REF-old" in RECONCILIATION.md). |
| [archive/TODO-2026-10-14-pre-merge.md](archive/TODO-2026-10-14-pre-merge.md) | TODO.md before it was rebuilt as the ordered plan. |
| [archive/REFERENCE-2026-10-14-pre-baseline.md](archive/REFERENCE-2026-10-14-pre-baseline.md) | REFERENCE.md just before the baseline was folded in (saved by the "Fold baseline results" thread). No pre-baseline copy of TODO.md exists; the SESSIONS.md entry "Baseline folded in" lists what changed. |

## Conventions

- Evidence tags: **[V]** checked in the AutoRemesher code at `4a49f82`; **[M]** measured by the baseline; **[P]** checked against a primary external source (paper, LICENSE file, official doc); **[E]** external claim not checked at the source; **[I]** inferred. The research reports use their own variants ([K], [S], [U], [ours]); each defines them at the top.
- IDs: P* performance and M* math issues and F* features are in REFERENCE.md; TODO items are numbered wave.item (e.g. 3.3); SQ-* questions are in SPECIALIST-QUESTIONS.md; C*/D*/L* conflicts are in RECONCILIATION.md.
- Several threads edit these files: re-read before editing, keep edits small, read back after writing.

