# Nine open questions on field-aligned quad remeshing

> **Forwarding notes (delete this box before sending).**
> - Prepared 2026-10-14 for TODO 0.8. **Nothing has been sent.** Kajetan decides when and to whom.
> - Self-contained: the reader needs none of the project files. Send "About", "Background" and "References" with one Part, or the whole document.
> - Recipients are inferred from authorship of the cited work; none has been contacted. Part A: Bommes, Campen, Kobbelt groups. Part B: Zorin, Crane, Soliman, Campen. Part C: Bommes and Heistermann; Pietroni and Tarini; Ray and Sokolov. Part D: Viertel and Osting; Remacle, Chemin and Couplet; Crane.
> - The question IDs (SQ-P1 …) are the ones in SPECIALIST-QUESTIONS.md, which holds 30 further, lower-priority questions. File answers there.
> - Two points here go beyond SPECIALIST-QUESTIONS.md and are our own inferences, flagged in the text: the bipartite-layout consequence in SQ-P1 (a) and the gauge remark in SQ-P1 (a).

---

## About

AutoRemesher (github.com/huxingyi/autoremesher, MIT, C++/Eigen) is an open-source automatic quad remesher. We are forking it under GPL-3.0-or-later to bring its output closer to ZBrush's ZRemesher on organic sculpts: few, well-placed poles, clean edge loops, controllable density, sharp features and mirror symmetry, driven from a Blender add-on. We are upgrading the existing pipeline stage by stage rather than rewriting it.

Statements about the current code come from reading it at commit `4a49f82`. A first baseline measured it on 18 test meshes (organic sculpts, hard-surface parts, thin shells, scans) at 2k, 10k and 50k quads:
- The rounded map had flipped triangles in every run (median 0.75 %, max 10 %).
- The flip rate predicts both the cost of the extractor's repair passes and the final number of irregular vertices (Spearman ρ up to 0.85).
- Clean organic inputs come out well; hard-surface, thin-shell and scanned inputs do not.

**What helps.** Any of these is useful: "this is known, see X"; a check of a derivation; a sketch of the right formulation; "wrong question, the real issue is Y". Each question ends with what we will do with the answer. Statements marked *[inferred]* are our own derivations and may be wrong.

---

## Background

### Pipeline as implemented

Input: a triangle mesh M (up to about 10⁶ faces, often a noisy sculpt) and a target quad count Q.

1. **Isotropic remesh.** Builds a triangle mesh T with curvature-adapted edge length, about 2 triangles per requested quad. With default settings each output quad covers about 6 triangles, because step 4 enlarges quads. Every later stage uses T; M is not used again.
2. **Cross field.** One 4-RoSy direction per face of T, stored as z_f = e^{4iθ_f} in a local frame, with Levi-Civita transport by hinge unfolding. Each step solves a least-squares problem (connection Laplacian plus alignment to principal curvature directions) and then normalizes z ← z/|z|. This is repeated 5 times, and from the second solve on, the alignment target is the previous normalized iterate. Faces at boundaries and sharp edges are locked to the edge direction.
3. **Singularity cancellation.** Any pair of singularities whose charges k sum to 0 mod 4 (index k/4; for example +1 with −1, but also +2 with +2) within 6 face hops is cancelled. The test is topological only; no energy is compared.
4. **Size and anisotropy.** Each face gets a target quad edge length s_f from a curvature heuristic, and an aspect ratio of at most √2.3.
5. **Matchings and cut graph.** Matchings r ∈ ℤ/4 on dual edges, a cut graph, and one Gauss–Newton step that reduces the curl of the scaled frame.
6. **Seamless parametrization** by mixed-integer least squares, in the style of MIQ [BZK09]:
   - Unknowns are per-corner coordinates uv_c ∈ ℝ².
   - Across a cut, uv_c = R^{r} uv_{c′} + t_c, where R is the quarter turn and t_c is a translation.
   - Energy: Σ_f w_f Σ_{e∈f} |s_f Δ_e uv − F_f e|², with F_f the frame.
   - Every t_c is an integer variable **with period 2**, meaning it is rounded to 2ℤ².
   - The coordinate of a sharp-edge isoline is an integer variable with period 1.
   - Cone positions get **no** integer variables.
7. **Constraint elimination and rounding.** Linear constraints are removed by substitution, x = Ky. After one continuous solve, *all* integer variables are rounded at once to the nearest multiple of their period ("direct rounding"), and one constrained re-solve follows.
8. **Extraction.** Integer isolines are traced per triangle, quads are assembled from the resulting graph, and 12 greedy cleanup passes follow.

Compared with the literature, the pipeline has no greedy or branch-and-bound rounding [BZK09, BCE+13], no orientation or injectivity constraints [BCE+13, MPZ14], and no validity check before extraction.

### Notation

- (M, g) is a compact oriented surface, with Gaussian curvature K, geodesic boundary curvature κ_g, area form dA and Hodge star ⋆. Δ = div ∇ is the non-positive Laplace–Beltrami operator.
- h is the target quad edge length, a function on M. ρ = 1/h, and φ = log ρ.
- X is a unit cross field. R = [[0, −1], [1, 0]] is the quarter turn.
- A cone c_j of a quad layout has index k_j/4 with k_j ∈ ℤ: its angle deficit is k_j π/2, and its valence is 4 − k_j (k = 1 is valence 3, k = −1 is valence 5). On a closed surface, Σ_j k_j π/2 = 2πχ(M).
- Throughout, ℓ denotes local triangle edge length on T.

---

## Part A. Integer lattice and rounding

### SQ-P1. Translation lattice of the seamless map

**Context.** As described in step 6, every seam translation t_c is rounded to 2ℤ² and cones have no integer variables. Let v be an interior cone with holonomy R^{r}, r ≢ 0 mod 4, and let τ_v be the composed translation of the transitions around v, in the chart of one incident corner. Composing the transitions forces uv(v) = (I − R^{r})^{−1} τ_v. We derive the following *[inferred]*:

- uv(v) ∈ ℤ² if and only if τ_v ∈ (I − R^{r})ℤ². For r = ±1 that lattice is D₂ = {(x, y) : x + y even}, of index 2 in ℤ². For r = 2 it is 2ℤ², of index 4.
- R preserves 2ℤ², so t_c ∈ 2ℤ² for all c gives τ_v ∈ 2ℤ², and therefore uv(v) ∈ ℤ² for every cone with no explicit constraint. This is presumably why period 2 was chosen.
- The exact conditions would be t_c ∈ ℤ² on every seam, plus τ_v ∈ (I − R^{r_v})ℤ² at every cone.

**Question.**

(a) Is the derivation right, and what does the period-2 restriction cost? Each seam translation goes from ℤ² to 2ℤ² (index 4). At ±90° cones, τ_v ∈ 2ℤ² is an index-2 sublattice of the required D₂. Along non-contractible loops with trivial holonomy (handles, tubes), the period lies in 2ℤ², which forces an even number of quads around them. Rounding to 2ℤ can move a translation by up to one quad instead of half a quad. Two further points need checking:
- *[inferred, not checked]* Every closed loop then has a period in 2ℤ² and every face loop has even length. If so, the quad layout induced by the map has a bipartite vertex graph, and every valence-3 and valence-5 vertex lies in the same colour class (uv(v) ∈ (I − R^{±1})^{−1} 2ℤ² = D₂). For example, a cube-like layout would need an even number of quads along every edge between two corners. Is that right?
- *[inferred]* The gauge, which fixes uv = 0 at one corner. Once the translations are integers and at least one cone exists, the global translation is already determined, so the gauge seems to pin a regular vertex to a grid point as well. Is that a spurious constraint? Is the interplay with boundaries and with period-1 feature coordinates sound?

(b) What is the cleanest exact encoding: explicit integer cone coordinates, as in MIQ, or a per-cone sublattice constraint on τ_v?

(c) How much optimal energy does the 2ℤ² restriction cost, at roughly 2–6 triangles per quad (the range we observe)?

**Use.** If the derivation holds, we replace the period-2 trick by the exact constraints before building better rounding on top of it.

### SQ-P2. Lattice preservation under constraint elimination

**Context.** Each variable has a period p ∈ {0 (continuous), 1, 2}. All constraints are homogeneous, with coefficients ±1 at the start. They are eliminated in three passes:

- **M0** removes single-term rows (x_i = 0).
- **M1** merges two-term rows x_i = ±x_j by union-find. The merged group takes the **maximum** period of its members.
- **M2** eliminates each remaining row by substitution, using the pivot with the smallest p·|a|. A continuous pivot is therefore preferred whenever the row has one.

A final consistency pass reports rows that are still unsatisfied, but its result is ignored. The reduced unknowns y satisfy x = Ky, and integer y are rounded to multiples of their period.

**Question.**
- Under what conditions is the map from integer kernel variables to the original integer variables unimodular, so that rounding y to pℤ puts every original x in its lattice?
- Is the "maximum period" rule correct when a period-1 and a period-2 variable merge? We suspect it over-restricts.
- If integrality is not guaranteed in general, what is the right construction: a Hermite or Smith normal form of the integer part of the constraint matrix, or elimination on continuous pivots only? What does it cost at about 10⁵ variables?

**Use.** A correct elimination layer before any new constraint types are added (exact cone lattice, features, symmetry).

### SQ-P3. Order of greedy rounding

**Context.** We are replacing direct rounding by greedy rounding in the spirit of [BZK09]. Most integer variables are seam translations, which act globally. Local Gauss–Seidel updates therefore help little, and full re-solves are expensive. Measured today: all integers are fixed in one pass, moving them by up to ≈0.5. Our plan:
- In batches, round every variable within δ_k of an integer, with δ_k growing geometrically.
- Never let two cones round onto the same grid point (the separation idea of [BCE+13]).
- Break ties deterministically.
- Re-solve fully every few batches.

**Question.**
- Is there a provably better order than "smallest fractional part first"? One candidate is the energy increase of rounding x_i with all other variables free, which is a Schur-complement diagonal (equivalently, a conditional variance). Can that be computed cheaply from one sparse Cholesky factorization, for example by selected inversion?
- Which batch size or δ schedule keeps the final energy close to sequential greedy rounding?
- Is there any bound on the gap?

**Use.** This is the first rounding fix we will implement. It sits on the critical path of the project.

---

## Part B. Sizing, integrability and cone placement

### SQ-Z1. Solving sizing and alignment jointly

**Context.** The target per face is ∇u ≈ ρX and ∇v ≈ ρX^⊥.

- **Integrability.** Away from cones the map is then a local isometry from (M, e^{2φ}g) to the plane, so the metric e^{2φ}g must be flat there. Since its curvature is e^{−2φ}(K − Δφ), this gives Δφ = K − K̂ with K̂ = Σ_j k_j (π/2) δ_{c_j}. On a free boundary the condition is ∂_n φ = κ_g − κ̂_g, with n the inward normal and κ̂_g the prescribed turning, concentrated at corners.
- **Coupling to the field.** Let ω be the rotation 1-form of X relative to Levi-Civita transport. The field and the density are tied by ⋆ω = dφ, up to orientation convention ([MZ13] write ω = −⋆dφ). So a given field admits an exact φ only if ω is co-closed.
- **Current plan, which is sequential.**
  1. Compute a curvature-aligned field.
  2. Solve φ = argmin ∫|dφ − ⋆ω_X|² dA + λ ∫(φ − φ*)² dA, one SPD system, where φ* is the target log density.
  3. Let the parametrization absorb the remaining curl as distortion.

  This replaces both the current one-step curl correction and the old conformal solve, which upstream has disabled.
- **Joint alternative.** Write the field as an angle θ per face, with A the discrete Levi-Civita connection and p ∈ ℤ the period jumps on dual edges, so that ω_X = dθ − A + (π/2)p. For fixed p,

  min_{θ, φ} ∫|dφ − ⋆(dθ − A + (π/2)p)|² dA + α ∫ w |θ − θ_curv|² dA + λ ∫(φ − φ*)² dA

  is linear least squares in (θ, φ). Here θ_curv is the principal direction, lifted to the branch fixed by p.
- **Measured.** Switching the curvature-driven sizing off reduces flipped triangles in the rounded map 4–20× at the same target. That is consistent with the non-integrable size target being a main cause of flips, though it does not separate it from plain distortion caused by size gradients.

**Question.**
- (a) Is the joint solve preferable to the sequential one, and is the formulation above correct, including the boundary terms?
- (b) Which weighting makes α and λ scale-invariant? φ is dimensionless, while ∇φ has units of 1/length.
- (c) The field code uses the power representation z = e^{4iθ}, which hides p. Can the joint solve take p from the power field's matchings, or does it need an angle formulation throughout?

**Use.** It decides how density enters the parametrization: one principled solve instead of today's clamped heuristics.

### SQ-Z2. Cones quantized to multiples of π/2 from a target density

**Context.** Given a target log density φ*, the measure μ = (K − Δφ*) dA is the curvature that cones must absorb for φ = φ* to hold exactly. A quad layout needs every cone deficit to be a multiple of π/2.

**Question.**
- How should cones c_j with k_j ∈ ℤ and Σ k_j π/2 = 2πχ(M) (plus boundary terms) be chosen to minimize ‖φ − φ*‖ after solving Δφ = K − K̂?
- Can the sparse-cone methods ([SSC18], an optimal-control/measure formulation; [Fang21] and [Fang23], sparse cones with bounded distortion; [Du25], integer-constrained cones) be restricted to multiples of π/2?
- Or is greedy rounding of a smoothed μ, with a minimum separation between cones, good enough? Is there an error bound?

**Use.** Pole placement driven by curvature and painted density. Artists judge a result mostly on this.

---

## Part C. Hard features and quantization

### SQ-F2. Feasibility of hard isoline constraints

**Context.** Hard features (sharp edges, face-set borders, user guide curves) should become grid lines. Today a feature's isoline constraint is dropped whenever the field is more than 10° off the feature. We want every hard feature to be an integer isoline, and to drop only constraints that are infeasible. Two parallel isolines of the same family that are closer than about half a quad collapse to one grid line under rounding, or fold the map.

**Question.**
- (a) What is the precise condition under which a set of curves with integer-isoline constraints admits a fold-free integer-grid map at scale s? One candidate is a parametric distance ≥ 1 between same-family isolines along every transversal path.
- (b) Is feasibility-checked rounding, in the style of IGM [BCE+13], enough? Or is T-mesh quantization [HWB23] required before hard features are switched on?
- (c) In the T-mesh setting, what are the feasibility conditions for forcing a feature network with corners of arbitrary angle onto grid lines, and where must extra cones go? Feature-aligned Penner parametrization [FAP25] gives sufficient conditions for the continuous map; we need the discrete counterpart.

**Use.** It decides whether sharp features and guide curves can ship on top of improved greedy rounding, or must wait for a full quantization stage.

### SQ-L1. Route to a valid integer quantization

**Context.** The setting:
- A field-aligned global parametrization on a triangle mesh, not on a T-mesh.
- 10⁴–10⁵ output quads.
- Mostly organic sculpts with many cones, boundaries and several components.

Today all integers are rounded at once. The result has flipped triangles in every test run: a median of 2.2 % of triangles at 2k quads, 0.6 % at 10k and 0.25 % at 50k, and up to 10 % on hard-surface and thin-shell inputs. Our plan is to implement greedy rounding first (SQ-P3), measure again, and only then decide on a heavier stage.

**Question.** What is the cleanest route to a valid quantization, and what are the expected quality, time and robustness of each at these sizes on organic shapes?
- (a) Greedy MIQ rounding with safeguards [BZK09, BCE+13].
- (b) Quantization on a decimated surface, without a T-mesh [CDH+24].
- (c) A T-mesh or motorcycle graph traced from separatrices, quantized by Bi-MDF [HWB23], in the style of QGP [CBK15].

**Use.** Choosing the quantization stage, if greedy rounding is not good enough.

---

## Part D. Cross-field design

### SQ-X1. Ginzburg–Landau scale versus quad size

**Context.** The field loop described in step 2 behaves like an MBO-type scheme (diffusion followed by projection onto |z| = 1) for a Ginzburg–Landau energy. Its effective ε is set implicitly by the mesh resolution and the step, so the number of surviving singularities depends on resolution. A greedy pass then cancels close pairs (step 3). We want ε explicit and tied to the target quad edge length h.

**Question.** On a closed surface with target edge length h, let:
- z be a section of L^{⊗4}, with L the tangent line bundle and ∇ the induced connection;
- q be a unit section (the curvature-aligned target) and w ≥ 0 a certainty weight;
- E_ε(z) = ½ ∫|∇z|² dA + (λ/2) ∫ w|z − q|² dA + (1/(4ε²)) ∫(1 − |z|²)² dA.

(a) What is the Γ-limit as ε → 0 with λ fixed, that is, the renormalized energy W(x₁, …, x_m; k₁, …, k_m) of vortex positions and indices, including the curvature (connection) term and the alignment term? We understand the case without alignment on closed surfaces is treated in [IJ21] (not yet read by us).

(b) Is ε → 0 the right regime, or should ε ~ h stay finite? For ε ~ h, what is the minimal distance between surviving ±¼ vortices, as a function of ε, λ and the local Gaussian curvature K?

**Use.** It sets c in ε = c·h, and replaces the 6-hop cancellation rule by a principled one. Background: [VO19], [BLH+17].

### SQ-X4. Alignment certainty for curvature-aligned fields

**Context.** The field is aligned to principal directions with a per-face weight. Today the weight is (|λ₁ − λ₂| / global max)², where the λ's come from an edge-based Cohen-Steiner–Morvan tensor summed over the face's vertices without area normalization. The weight vanishes at umbilics, as it should, but it scales like |κ₁ − κ₂|ℓ² and is dominated by the most curved region of the mesh. Our plan:
- A shape operator estimated at scale r ≈ h.
- A local weight such as ((κ₁ − κ₂)h)² / (1 + ((κ₁ − κ₂)h)²).
- An energy E = smoothness + λ ∫ w|z − q|² dA with a proper mass matrix.

**Question.**
- For a discrete shape operator estimated at scale r ≈ h, which weight w(κ₁, κ₂, h) makes the aligned field (i) stable under normal noise of amplitude σ and (ii) consistent under refinement?
- Is there a variance-based choice that should replace a gap heuristic, for example the inverse variance of the estimated principal angle under a noise model?
- Is λ ∝ h⁻² the right scaling for λ to mean the same thing at every resolution?

**Use.** Edge flow that follows the form on noisy sculpts without locking onto noise.

---

## References

- [BZK09] D. Bommes, H. Zimmer, L. Kobbelt. Mixed-integer quadrangulation. ACM TOG 28(3), 2009.
- [BCE+13] D. Bommes, M. Campen, H.-C. Ebke, P. Alliez, L. Kobbelt. Integer-grid maps for reliable quad meshing. ACM TOG 32(4), 2013.
- [CBK15] M. Campen, D. Bommes, L. Kobbelt. Quantized global parametrization. ACM TOG 34(6), 2015.
- [HWB23] M. Heistermann, J. Warnett, D. Bommes. Min-deviation-flow in bi-directed graphs for T-mesh quantization. ACM TOG 42(4), 2023.
- [CDH+24] Y. Coudert-Osmont, D. Desobry, M. Heistermann, D. Bommes, N. Ray, D. Sokolov. Quad mesh quantization without a T-mesh. Computer Graphics Forum 43(1), 2024.
- [MZ13] A. Myles, D. Zorin. Controlled-distortion constrained global parametrization. ACM TOG 32(4), 2013.
- [MPZ14] A. Myles, N. Pietroni, D. Zorin. Robust field-aligned global parametrization. ACM TOG 33(4), 2014.
- [SSC18] Y. Soliman, D. Slepčev, K. Crane. Optimal cone singularities for conformal flattening. ACM TOG 37(4), 2018.
- [Fang21] Q. Fang et al. Computing sparse cones with bounded distortion for conformal parameterizations. ACM TOG 40(6), 2021.
- [Fang23] Efficient cone singularity construction for conformal parameterizations. SIGGRAPH Asia 2023.
- [Du25] Du, Fang, Liu, Fu. Integer-constrained cone construction. arXiv:2512.20904, 2025.
- [FAP25] Feature-aligned seamless parametrization in Penner coordinates. Capouellez, Zorin and coauthors (NYU and Bern), 2025. Builds on R. Capouellez, D. Zorin, Seamless parametrization in Penner coordinates, ACM TOG 43(4), 2024.
- [VO19] R. Viertel, B. Osting. An approach to quad meshing based on harmonic cross-valued maps and the Ginzburg–Landau theory. SIAM J. Sci. Comput. 41(1), 2019.
- [BLH+17] P.-E. Beaufort, J. Lambrechts, F. Henrotte, C. Geuzaine, J.-F. Remacle. Computing cross fields: a PDE approach based on the Ginzburg–Landau theory. Procedia Engineering 203 (26th IMR), 2017.
- [IJ21] R. Ignat, R. L. Jerrard. Renormalized energy between vortices in some Ginzburg–Landau models on 2-dimensional Riemannian manifolds. Arch. Ration. Mech. Anal. 239, 2021.
