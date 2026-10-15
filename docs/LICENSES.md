# Licenses: decision, dependencies and candidate code

Split out of REFERENCE.md §1 on 2026-10-14 and extended with every license the research threads checked. Not legal advice; review once more before the first public release.

Tags: **[P]** a project thread read the LICENSE/COPYING file, file headers or README (source in the last column). **[E]** stated by a thread with a link to the project, but the license text itself was not quoted. **[U]** unverified. **[I]** inferred. Conflicts between threads are resolved in [RECONCILIATION.md](RECONCILIATION.md) §3.

---

## 1. Decision (Kajetan, 2026-10-14): public GPL fork

The project is published as a **GPL-3.0-or-later** fork. GPL solvers are allowed if they are GPL-3.0-or-later compatible (libQEx and QuadWild are, see §4). Core changes won't be merged back into the MIT upstream as a whole.

**GPL-3.0-only code is not allowed** (Kajetan, 2026-10-14, TODO 0.2). That excludes CoMISo, directly or through quadwild-bimdf. This is a policy choice, not a legal block: linking it would be allowed but would make the distributed binary GPL-3.0-only. Nothing planned needs it: greedy rounding is our own code, and Bi-MDF comes from MIT libSatsuma.

**Upstream contact is deferred** (TODO 0.5). The MIT license needs no permission for the fork; only the attribution in §6 is required.

Why GPL-3.0-or-later and not GPL-2.0 **[I, check before release]**:
- oneTBB is Apache-2.0, which is compatible with GPLv3 but **not** with GPLv2-only.
- Blender accepts GPL-3.0-or-later add-ons; both existing AutoRemesher add-ons use it **[P]** (their manifests).

## 2. Flags used in TODO.md

| Flag | Meaning | What to do |
|---|---|---|
| `OK-MIT` | Own code, or permissive dependencies only (MIT/BSD/Apache/MPL/public domain) | Can also be offered upstream as an MIT patch. |
| `OK-GPL3` | Needs a GPL-compatible dependency (GPL-3.0, GPL-2.0-or-later, LGPL, AGPL) | Fine in the fork; cannot go upstream. |
| `GPL3-ONLY` | Pulls in **GPL-3.0-only** code (CoMISo, directly or through quadwild-bimdf) | **Not allowed** (TODO 0.2, 2026-10-14). Linking it would make distributed binaries effectively GPL-3.0-only. |
| `ASK` | Repository has **no LICENSE file** (all rights reserved by default), or no code was released | Don't copy code. Re-implement from the paper, or get written permission from the authors (TODO 0.6). |
| `NO` | Non-free, commercial or license-keyed | Never in a distributed build. |

Re-implementing a method from its paper does not copy code, so the source repository's license doesn't apply **[I]**. Algorithm patents are a separate question that no thread checked.

## 3. What the fork already contains or will contain

| Component | License | Status | Notes |
|---|---|---|---|
| Upstream AutoRemesher core (Jeremy Hu) | MIT ("Copyright (c) 2026 Dust3D Project") | [P] size notes B | Allowed inside GPL. **Keep the MIT copyright and permission notice.** |
| isotropicremesher, meshoptimizer (vendored) | MIT | [E] | Same as above. |
| Eigen | MPL-2.0 | [E] | GPL-compatible; keep the notice. `EIGEN_MPL2_ONLY` avoids its LGPL parts. Which Eigen version upstream bundles is unchecked (TODO 1.10). |
| oneTBB | Apache-2.0 | [E] | GPLv3 only; keep the NOTICE. Blender bundles oneTBB 2022.3.0 as a shared library, so link ours statically and run in a subprocess worker (perf §2.4). |
| Qt (desktop app only) | LGPL-3.0 | [E] | Dynamic linking; not part of the Blender build. |
| adriflex bridge, jakeblakeley add-on | GPL-3.0-or-later | [P] manifests | Copy with attribution. |
| jakeblakeley core and packaging changes | MIT (inherits upstream LICENSE) | [I] | Credit Jake Blakeley. |

## 4. Candidate code from the research, by area

### 4.1 Linear solvers and numerics

| Code | License | Status | Flag | Source |
|---|---|---|---|---|
| Eigen SimplicialLDLT (current) | MPL-2.0 | [E] | OK-MIT | perf §2.1 |
| SuiteSparse CHOLMOD, Cholesky/Core modules | LGPL-2.1+ | [P] License.txt | OK-GPL3 | perf §2.1 |
| SuiteSparse CHOLMOD, Supernodal module | GPL-2.0-or-later | [P] | OK-GPL3 | perf §2.1 |
| SuiteSparse METIS (modified) / AMD, COLAMD | Apache-2.0 / BSD-3 | [P] | OK-MIT | perf §2.1 |
| SPQR | GPL-2.0-or-later | [P] | OK-GPL3 | perf §2.1 |
| Apple Accelerate | system library | – | OK-MIT | perf §2.1 (non-deterministic unless `VECLIB_MAXIMUM_THREADS=1`) |
| Catamari | MPL-2.0 | [E] | OK-MIT | perf §2.1 (maintenance [U]) |
| BaSpaCho | MIT | [E] | OK-MIT | perf §2.1 |
| QDLDL | Apache-2.0 | [E] | OK-MIT | perf §2.1 |
| AMGCL | MIT | [E] | OK-MIT | perf §4.2 |
| hypre | Apache-2.0 / MIT | [E] | OK-MIT | perf §4.2 |
| surface_multigrid_code (Liu et al. 2021) | GPL-3.0 | [E] | OK-GPL3 | perf §4.2 |
| Gravo MG | "Apache (MIT)" on PyPI, ambiguous | [U] | check first | perf §4.2 |
| geometry-central / robust-laplacians | MIT | [P] / [E] | OK-MIT | cross §3.1, perf §8.4 |
| MUMPS | CeCILL-C | [E] | too heavy | perf §2.1 |
| MKL PARDISO | Intel Simplified Software License | [P] | **NO** | perf §2.1 |
| Panua PARDISO | commercial, machine-keyed | [P] | **NO** | perf §2.1 |
| NVIDIA cuDSS | proprietary, CUDA only | [P] | **NO** | perf §5 |
| NVIDIA AMGX | BSD-3 believed, CUDA only | [U] | not planned | perf §5 |

### 4.2 Rounding, quantization, layout

| Code | License | Status | Flag | Source |
|---|---|---|---|---|
| CoMISo (MIQ solver) | **GPL-3.0-only** (COPYING, 2018-era commit; re-check master) | [P] | **GPL3-ONLY** | param §0.7 |
| libigl core / `igl/copyleft/comiso` (MIQ) | MPL-2.0 / GPL-3 (wraps CoMISo) | [P] | OK-MIT / **GPL3-ONLY** | cross, size §6 |
| libSatsuma (Bi-MDF solver) | MIT | [P] | OK-MIT | param §3.2, extr §3.2 |
| Blossom-V (optional libSatsuma dependency) | research/evaluation only, no redistribution | [P] | **NO**: build with `-DSATSUMA_ENABLE_BLOSSOM5=0` | extr §3.2 |
| quadwild-bimdf | GPL-3.0; depends on vcglib (GPL-3.0), **CoMISo**, OpenMesh, libigl, lemon, xfield_tracer (GPL-3.0), lpsolve | [P] | **GPL3-ONLY** (through CoMISo); keep Gurobi and Blossom-V off | extr §3.2 |
| QuadWild (original) | GPL-3.0-or-later (LICENSE is GPLv3; header of `components/quad_from_patches/quad_from_patches.h` says "or any later version", one header sampled 2026-10-14); quantization needs Gurobi | [P] | OK-GPL3 without Gurobi; Gurobi **NO** | extr §3.1; consolidation thread |
| Metriko (QGP pipeline) | MPL-2.0 | [P] LICENSE | OK-MIT (check per-file "Incompatible With Secondary Licenses") | param §3.2 |
| FSCQ (Liang, Du, Fu 2025) | GPL-3.0, needs Gurobi, ships precompiled `.so` | [P] | **NO** as shipped; ideas only | extr §3.3 |
| Generalized Motorcycle Graph | BSD-3 | [P] | OK-MIT | extr §3.4 |
| Gurobi, CPLEX | commercial | [P] | **NO** | param §3.1, perf §0 |
| Coudert-Osmont et al. 2024 (quantization without T-mesh) | no code found | – | ASK | param §3.2 |
| Lyon et al. 2021 (T-mesh quantization) | no code; needs Gurobi | [P] | ASK / NO | size §3.3, perf §3.3 |

### 4.3 Parametrization (continuous stage, injectivity)

| Code | License | Status | Flag | Source |
|---|---|---|---|---|
| ConformalIdealDelaunay (Campen et al. 2021) | MIT | [P] | OK-MIT | param §3.3 |
| CEPS (Gillespie, Springborn, Crane 2021), BFF | MIT | [P] | OK-MIT | size §2.2 |
| `geometryprocessing/penner-optimization` | GPL-3.0 / MPL-2.0 per README | [P] README; LICENSE file to confirm | OK-GPL3 after confirmation | size §2.5, RECONCILIATION L3 |
| `rjc8237/seamless-parametrization-penner` | no LICENSE file | [P] | **ASK** | param §3.3 |
| `rjc8237/feature-aligned-penner` | no LICENSE file | [P] | **ASK** | param §3.3, extr §6 |
| RSP, `etcorman/RectangularSurfaceParameterization` (Matlab) | **conflicting reads**: no LICENSE file (cross, param) vs AGPL-3.0 (extr) | open | **ASK** until checked | RECONCILIATION L2 |
| `mlivesu/topological_IGM` | no LICENSE file | [P] | **ASK** | param §3.3, extr §2.4 |
| moving_frames_parametrization (Coiffier–Corman 2023, Python) | MIT | [P] | OK-MIT | cross §3.3 |
| Integrable odeco fields (Couplet et al. 2026) | no code yet | – | ASK | cross §3.3 |
| Integer-constrained cones (Du et al., arXiv 2512.20904) | placeholder URL only | – | ASK | cross §3.3 |

### 4.4 Extraction and robustness

| Code | License | Status | Flag | Source |
|---|---|---|---|---|
| libQEx | GPL-3.0-**or-later** (file headers `src/MeshExtractorT.hh`, `interfaces/c/qex.h` and README checked 2026-10-14; commercial on request) | [P] | OK-GPL3 | extr §2.1; consolidation thread |
| OpenMesh (libQEx dependency) | BSD-3 | [E] | OK-MIT | extr §2.1 |
| Ray 2025 messy-map extraction | no code released | – | re-implement | extr §2.2 |
| Shewchuk adaptive predicates | public domain | [E] | OK-MIT | perf §8.3 |
| Geogram (PCK predicates, mesh_repair) | BSD-3 | [P] | OK-MIT | perf §8.1, §8.3 |
| Attene indirect predicates | LGPL | [E] | OK-GPL3 | perf §8.3 |
| VCGlib (`tri::Clean`) | GPL-3.0 | [E] | OK-GPL3 (or re-implement: OK-MIT) | perf §8.1 |
| MeshFix | GPL-3.0; keeps only the largest component | [E] | not recommended | perf §8.1 |
| CGAL PMP, CGAL Jet_fitting_3 | GPL-3.0-or-later or commercial | [P] Jet_fitting | OK-GPL3, heavy | perf §8.1, size §1.1 |
| Gmsh | GPL-2.0-or-later | [E] | OK-GPL3 | extr §4.1 |

### 4.5 Fields, remeshing, symmetry, learned methods

| Code | License | Status | Flag | Source |
|---|---|---|---|---|
| geometry-central (Knöppel fields, trivial connections) | MIT | [P] | OK-MIT | cross §3.1 |
| Directional (Vaxman) | MPL-2.0 (file headers) | [P] | OK-MIT | extr §9, RECONCILIATION L4 |
| Instant Meshes | BSD-3 plus an "enhancements" grant-back clause | [P] | OK-MIT; prefer re-implementing | perf §4.1, RECONCILIATION L5 |
| QuadriFlow | BSD-3 plus "enhancements" clause | [P] | OK-MIT; prefer re-implementing | size §6 |
| wildmeshing-toolkit | MIT | [E] | OK-MIT | perf §6 |
| pmp-library | MIT | [E] | OK-MIT | perf §6 |
| libigl `shape_diameter_function` (thin-part sizing) | MPL-2.0 (function name unverified) | [U] | OK-MIT | size §1.3 |
| trimesh2 (Rusinkiewicz curvature) | GPL-2.0+ believed | [U] | re-implement (~100 LOC) | size §6 |
| NeurCross, CrossGen | AGPL-3.0 | [P] | OK-GPL3 (keep the AGPL notice); deferred | cross §3.5 |
| SQuadGen | MIT | [P] | metrics/dataset only | extr §6 |
| SATO | GPL-3.0 | [P] | out of scope | extr §6 |
| TopGen, CrossLift, NeurFrame, Dielen et al. 2021 | no code found | – | n/a | cross §3.5 |
| Symmetry detection: Nagar & Raman 2018, SignNet | no license | [P] | ASK; deferred | size §4.3 |

### 4.6 Tools that are not shipped

Tracy (BSD-3), perf + hotspot (GPL), VTune (free), Instruments, heaptrack (LGPL-2.1+), Google Benchmark (Apache-2.0), Superluminal (commercial). Licensing only matters if one is vendored into the repository (perf §9.2).

## 5. Test data

Vendor only what is clearly redistributable (perf §9.4): Thingi10K filtered to CC0/CC-BY, Objaverse CC0/CC-BY objects, Smithsonian CC0, synthetic pathology meshes generated by script. Download Stanford models at test time (research use, no products). Don't redistribute MPI-FAUST or ABC. Kajetan's own sculpts stay private unless licensed explicitly. The baseline thread collected 12 PD/CC0/CC-BY meshes and 6 procedural ones (reported in its status; its report is pending).

## 6. Attribution checklist

- Keep upstream `LICENSE` as `LICENSE-MIT` (or under `licenses/`) and add `COPYING` (GPL-3.0 text). Explain in the README that the combined work is GPL-3.0-or-later and the original files are MIT, © Jeremy Hu / Dust3D Project.
- Never remove existing copyright headers. Add `SPDX-License-Identifier: GPL-3.0-or-later` to new files, and a "Modifications © 2026 Kajetan …" line to modified MIT files.
- Keep a `THIRD_PARTY_NOTICES` listing every vendored library with its license text (AGPL parts too, if any are ever used).
- Credit Jake Blakeley and Adrien Rouquié (adriflex) for ported code. Cite the papers behind each method in the README.
- Use a distinct project name so users don't confuse it with upstream releases **[I]**.
- Keep generic bug fixes in separate commits free of GPL code, so they can still be sent upstream as MIT patches if TODO 0.5 (deferred) is picked up **[I]**. Every `OK-MIT` item in TODO.md qualifies.

## 7. Still to check

- QuadWild: only one source header was sampled for "or later"; check the rest before vendoring. CoMISo: moot after TODO 0.2.
- RSP repository license (RECONCILIATION L2); `penner-optimization` LICENSE file (L3).
- Gravo MG license; Eigen version bundled upstream.
