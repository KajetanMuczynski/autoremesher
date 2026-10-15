# Open mathematical questions for specialists

Collected 2026-10-14 from every research report in [research/](research/) and the code-to-math spec. Each question is **self-contained**: copy one block and send it on its own. Each names what the project will do with the answer and where it came from. Duplicates across reports were merged; the "Sources" line lists every origin.

Project in one paragraph (paste above any question if the reader has no context): *AutoRemesher is an open-source quad remesher (C++, Eigen; being forked under GPL-3.0-or-later for a Blender add-on). Pipeline: isotropic triangle remesh T of the input at roughly quad resolution → 4-RoSy cross field per face as a complex power z = e^{4iθ} → field-aligned seamless parametrization by mixed-integer least squares (per-corner UVs, rotational transitions, integer translations) → integer rounding → quad extraction from integer isolines. The goal is ZBrush-ZRemesher-like output on organic sculpts: few, well-placed poles, clean loops, controllable density, features and symmetry.*

Status: **open** unless marked. IDs are referenced from [TODO.md](TODO.md) and [REFERENCE.md](REFERENCE.md). Short source names: spec = code-to-math-spec.md, cross = cross-fields.md, param = parametrization-rounding.md, extr = extraction-layout-metrics.md, size = sizing-guides-symmetry.md, perf = performance-robustness.md.

## Ask first

These sit on the critical path of TODO.md:
1. **SQ-P1** translation lattice, **SQ-P3** greedy rounding order, **SQ-P2** lattice under elimination (rounding fix, TODO 3.3–3.5).
2. **SQ-Z1** joint sizing/alignment and **SQ-Z2** cones from density (sizing into the parametrization, TODO 4.5).
3. **SQ-F2** feasibility of hard isolines (features and guides, TODO 5.3).
4. **SQ-L1** route to valid quantization (gate 7.1 / Stage B).
5. **SQ-X1** Ginzburg–Landau scale and **SQ-X4** alignment certainty (field, TODO 4.2–4.3).

Suggested experts by area are inferred from authorship of the cited work **[I]**; none has been contacted.

**Ready to send:** the nine "Ask first" questions are rewritten for an outside reader in [SPECIALIST-BRIEF.md](SPECIALIST-BRIEF.md): background and notation, four parts by recipient, full references, and no project-internal links. Not sent yet (TODO 0.8).

---

## X. Cross field and singularities

Suggested experts: Crane, Corman (fields, moving frames, RSP); Viertel, Osting, Remacle, Couplet, Chemin (Ginzburg–Landau, odeco); Vaxman (Directional).

### SQ-X1. Ginzburg–Landau scale versus quad size
**Context.** The cross field is stored per face as z_f = e^{4iθ_f}. The code solves a least-squares problem (connection-Laplacian smoothness plus alignment to a curvature target), normalizes z ← z/|z|, and repeats 5 times, but replaces the alignment target by the previous normalized iterate after the first solve. This is an MBO-type scheme for a Ginzburg–Landau energy whose effective ε is set implicitly by mesh resolution, so the number of surviving singularities depends on resolution. A greedy pass then cancels singularity pairs closer than 6 face hops. We want ε explicit and tied to the target quad edge length h.

**Question.** On a closed surface (M, g) with target edge length h, let z be a section of L^{⊗4} (L the tangent line bundle), ∇^{(4)} the induced connection, q a unit section (curvature-aligned target), w ≥ 0 a certainty weight, and
E_ε(z) = ½∫_M |∇^{(4)}z|² dA + (λ/2)∫_M w|z − q|² dA + (1/(4ε²))∫_M (1 − |z|²)² dA.
(a) What is the Γ-limit as ε → 0 with λ fixed, i.e. the renormalized energy W(x₁…x_m; k₁…k_m) of vortex positions and indices, including the Gaussian-curvature (connection) term and the alignment term?
(b) Is ε → 0 the right regime, or should ε ~ h stay finite? For ε ~ h, what is the minimal distance between surviving ±¼ vortices as a function of ε, λ and the local Gaussian curvature K?

**Use.** Choose c_ε in ε = c_ε·h, and replace the 6-hop cancellation heuristic by a principled rule (TODO 4.3; REFERENCE M5).
**Sources.** cross §5 Q1, §3.2, §4.2; spec §8.5, §9.

### SQ-X2. Cost of a ±¼ dipole, and a one-parameter pole budget
**Context.** For a cross field on a closed surface Poincaré–Hopf fixes Σ k_i/4 = χ(M); only singularity positions and the number of (+¼, −¼) pairs are free. The code cancels any pair whose charges sum to 0 mod 4 within 6 face hops, accepting a cancellation on topology alone (no energy test). Artists want few poles, placed where the geometry needs them.

**Question.** (a) For a conformal seamless parametrization with cones, compare the distortion energy (e.g. ∫|∇φ|² dA, φ the log conformal factor) of a configuration with and without a cone pair (+π/2, −π/2) at geodesic distance d, in a region of Gaussian curvature K, with target edge length h. What is the leading-order term in d, K, h?
(b) Is there an energy combining smoothness, alignment and a cost per cone (or per dipole) in which **one** user parameter trades pole count against alignment and distortion, with minimizers that behave monotonically in that parameter?

**Use.** A principled pair-cancellation rule (stage 7) and a "pole budget" slider (REFERENCE M5, F9; TODO 7.3).
**Sources.** cross §5 Q2; pre-merge REFERENCE M5 ("one user parameter"); spec §9.

### SQ-X3. Index-preserving restriction of a fine field to a coarse mesh
**Context.** Creases and small forms are lost when the field is computed on a mesh at output-quad resolution. Plan: compute the field on a mesh T_f that is 2–4× finer, then transfer it to the coarser mesh T_c on which the parametrization is solved.

**Question.** Given a cross field with simple zeros (indices ±¼) on T_f and a closest-point correspondence T_c → T_f, find the field on T_c whose singular set is the "snapped" image of the fine one (same indices, positions moved to coarse vertices or faces) and whose energy is closest to the fine field's. Once the snapping is fixed, is this a linear problem (trivial connections on T_c, Crane–Desbrun–Schröder 2010)? How should the snapping be done when two singularities land in the same or adjacent coarse faces (merge, keep apart, refine locally)?

**Use.** TODO 7.4 (REFERENCE M4).
**Sources.** cross §5 Q3, §4.3.

### SQ-X4. Alignment certainty for curvature-aligned fields
**Context.** The field is aligned to principal curvature directions with a per-face weight. Today the weight is (|λ₁ − λ₂| / global max)², from an edge-based Cohen-Steiner–Morvan tensor summed over a face's three vertices without area normalization. It vanishes at umbilics, but it scales like |κ₁ − κ₂|ℓ² (ℓ local edge length) and is dominated by the most curved region of the mesh. Plan: a scale-aware tensor at radius r ≈ h and a local weight such as ((κ₁ − κ₂)h)² / (1 + ((κ₁ − κ₂)h)²), in an energy E = smoothness + λ∫w|z − q|² dA with a mass matrix.

**Question.** For a discrete shape operator estimated at scale r ≈ h, which weight w(κ₁, κ₂, h) makes the aligned field (i) stable under normal noise of amplitude σ and (ii) consistent under refinement? Is there a variance-based choice (e.g. inverse variance of the estimated principal angle under a noise model) that should replace a gap heuristic? Is λ ∝ h⁻² the right scaling for λ to mean the same thing at every resolution?

**Use.** TODO 4.2 (REFERENCE M6).
**Sources.** cross §5 Q4, §4.1; spec §8.3; size §1.1.

### SQ-X5. Convergence of joint frame/parametrization methods
**Context.** Recent methods choose singularities by minimizing parametrization distortion jointly with the frame instead of by field smoothness: Coiffier–Corman 2023 (moving frames, MIT code), Corman–Crane 2025 (Rectangular Surface Parameterization), Couplet–Chemin–Bommes–Chien 2026 (integrable odeco fields). We consider prototyping one offline.

**Question.** What guarantees exist on cone count and location under refinement for the moving-frames formulation (or RSP)? Do the emergent cones converge as h → 0, or do they depend on the discretization and the initialization? If on the initialization, which one (smoothest field, curvature-aligned field, Ginzburg–Landau with ε ~ h) gives the lowest final distortion in expectation?

**Use.** Go/no-go for the joint-frames prototype (TODO 7.3, architecture B).
**Sources.** cross §5 Q7, §3.3, §4.5.

### SQ-X6. Conformal versus rectangular target, and the anisotropy bound
**Context.** The code can elongate quads along the low-curvature direction with aspect ratio (κ_max/κ_min)^{α/2} (α = user anisotropy; at α = 1 this is the classical optimal anisotropy for piecewise-linear approximation), clamped to 2.3 and smoothed over 12 graph hops. ZRemesher output on organic sculpts looks mostly near-isotropic. Conformal parametrizations force squares; RSP lets the aspect ratio vary.

**Question.** For near-isotropic, "artist-like" quads on organic surfaces, is there a principled argument (second fundamental form, Chebyshev nets, principal-curvature-line theory, approximation error) for targeting conformal or rectangular parametrizations? If rectangular, how should an aspect bound enter as a constraint (e.g. in RSP's formulation) rather than as a post-hoc clamp, and should the smoothing of the anisotropy tensor be defined in world units rather than hops?

**Use.** Choose the target family for TODO 7.3; decide what to do with anisotropy (REFERENCE M9).
**Sources.** cross §5 Q6; spec §10; pre-merge REFERENCE M9.

---

## Z. Sizing and integrability

Suggested experts: Zorin, Myles (controlled-distortion parametrization); Crane, Soliman (cone placement); Campen (conformal equivalence); Remacle, Couplet (size-controlled odeco fields).

### SQ-Z1. Solving sizing and alignment jointly
**Context.** Target per face: ∇u ≈ ρX, ∇v ≈ ρX^⊥, with X a unit cross field, ρ = 1/h the target density and φ = log ρ. Seamlessness away from cones requires ⋆ω = dφ (up to sign convention), where ω is the connection 1-form of X relative to Levi-Civita transport (Myles & Zorin 2013, Prop. 3). Hence Δφ = K − K̂, K̂ = Σ k_j(π/2)δ_{c_j}, and on a free boundary ∂_nφ = κ_g − κ̂_g. A given field admits an exact φ only if its rotation form is co-closed. Current plan (sequential): compute a curvature-aligned field, then (L + λM)φ = div(⋆ω_X) + λMφ* (least-squares projection toward the target φ*), and let the cover solve absorb the residual curl. In the angle representation ω_X = dθ − A + (π/2)p (A the Levi-Civita form, p integer period jumps); for fixed p,
min_{θ,φ} ∫|dφ − ⋆(dθ − A + (π/2)p)|² + α∫w|θ − θ_curv|² + λ∫(φ − φ*)²
is linear least squares in (θ, φ).

**Question.** (a) Is the joint solve preferable to the sequential one, and is the formulation above correct, including boundary terms? (b) Which weighting makes α and λ scale-invariant (φ is dimensionless, ∇φ has units 1/length)? (c) The code's field uses the complex power z = e^{4iθ}, which hides p. Can the joint solve be done with p fixed from the power field's matchings, or does it need an angle formulation throughout?

**Measured.** Turning the curvature sizing off cuts flipped UV triangles 4–20× at the same target (REFERENCE M3), consistent with a non-integrable size target but not separating it from plain scale-gradient distortion.

**Use.** TODO 4.5 (REFERENCE M3): replaces the current one-step "curl correction" and the disabled conformal solve.
**Sources.** size §7 Q1, §2.1–2.3; spec §11, §12.6; pre-merge REFERENCE M3 ("which energy to minimise jointly").

### SQ-Z2. Quarter-quantized cone placement from a target density
**Context.** With φ = log ρ the target log density of quads, Δφ = K − K̂ must hold away from cones, where K̂ is a sum of point masses k_j·π/2. Given a target φ*, the measure μ = (K − Δφ*) dA is the curvature cones must absorb for φ = φ* to hold exactly. A quad mesh needs every cone angle to be a multiple of π/2.

**Question.** How should cones c_j with k_j ∈ ℤ, Σ k_j π/2 = 2πχ(M) (plus boundary terms) be chosen to minimize ‖φ − φ*‖ after solving Δφ = K − K̂? Can Soliman–Slepčev–Crane 2018 (sparse cones as a measure/optimal-control problem), Fang et al. 2021/2023 (sparse cones with bounded distortion) or Du–Fang–Liu–Fu (integer-constrained cones, arXiv 2512.20904) be restricted to multiples of π/2, or is greedy rounding of a smoothed μ with a minimum separation good enough? Any error bound?

**Use.** Cone placement in TODO 4.5 and 7.3.
**Sources.** size §7 Q2, §2.2(a); cross §3.3.

### SQ-Z3. Density gradation versus pole count
**Context.** Target edge length is graded in the log domain: log h(x) = min_y (log h₀(y) + γ·d(x, y)), which enforces |∇log h| ≤ γ (adjacent quad rows differ by at most a factor e^{γh}). Because Δ(log ρ) = K − K̂ for a square-quad field, abrupt density changes (e.g. painted density) force pole pairs.

**Question.** Is there a usable bound on the number of forced cones in terms of ∫|K − Δφ*| dA (or similar), so that γ can be chosen from a user "pole budget"? Is a Lipschitz bound on log h the right control, or should one bound Δφ* directly (in L¹, or a negative Sobolev norm)?

**Use.** Gradation constant in TODO 4.1; density paint (F3) and pole budget (F9).
**Sources.** size §7 Q3, §1.4.

### SQ-Z4. Thin-structure cap in the sizing field
**Context.** The sizing field is h = min(h_κ, SDF/k, …), where SDF is the shape diameter function and k ≈ 3–4 quad rows across a thin part. The minimum of two smooth fields has a gradient jump on the switching curve, so Δ log h concentrates there.

**Question.** Since Δφ* concentrated on a curve would attract cones there (via Δφ = K − K̂), must this cap be smoothed before it enters the parametrization? Which smooth minimum (e.g. log-sum-exp in log h, with width relative to h) avoids that without losing the thin-part guarantee?

**Use.** TODO 4.1.
**Sources.** size §7 Q10, §1.3.

### SQ-Z5. Cone-consistent metric at production scale
**Context.** For a guaranteed-valid pipeline we need a metric e^{2φ}g with prescribed cone angles and loop holonomies that is close to a target density, at 10⁵–10⁶ faces, as input to quantization.

**Question.** State the joint problem: given cones {(v_i, k_iπ/2)}, a target quad density ρ per unit area and a frame field, find e^{2φ}g with those cone angles and loop holonomies minimizing ‖φ − ½ log ρ‖ (or a distortion energy). Is a Penner-coordinate solve (Capouellez–Zorin 2023–2024) or a conformal ideal-Delaunay solve (Campen et al. 2021; Gillespie–Springborn–Crane 2021) the right tool at that size, and what does each guarantee for downstream quantization (local injectivity, exact seamlessness)?

**Use.** Stage B (TODO 7.2).
**Sources.** param §5 Q5, §3.3.

---

## P. Parametrization lattice and rounding

Suggested experts: Bommes, Campen, Kobbelt (MIQ, IGM, QGP); Zorin (seamless maps).

### SQ-P1. Translation lattice of the seamless map
**Context.** Per-corner UVs u_c ∈ ℝ²; across a seam u_c = R^{r}u_{c′} + t_c with R the quarter turn, r ∈ ℤ/4; every t_c is declared integer with **period 2**, i.e. rounded to 2ℤ². There are **no** integer variables for cone (singular vertex) positions. Feature-edge coordinates have period 1; gauge u = 0 at one corner. Two independent code reads derive: around a cone with holonomy R the transitions force (I − R)p = τ, τ the composed translation; so t ∈ 2ℤ² ⇒ τ ∈ 2ℤ² ⇒ p ∈ ℤ² for every cone type, with no explicit constraints. The exact conditions would be t_e ∈ ℤ² per seam plus τ_v ∈ (I − R_v)ℤ² per cone, where (I − R)ℤ² is the checkerboard lattice D₂ (index 2) for R = ±90° and 2ℤ² for R = 180°.

**Question.** (a) Is the derivation right, including the gauge (once integer t and one cone fix the translation, uv = 0 at corner 0 seems to pin a regular vertex to a grid point [I]), boundaries and period-1 feature coordinates? Claimed consequences: each seam translation is restricted from ℤ² to 2ℤ² (index 4); at ±90° cones τ is restricted to 2ℤ², index 2 in the required D₂, so such cones can only sit at uv ∈ D₂ and the induced layout is bipartite with all valence-3/5 poles in one colour class [I, unchecked]; along non-contractible loops with trivial holonomy (handles, tubes) the period lies in 2ℤ², forcing an even number of quads around them; rounding can shift a translation by up to one quad instead of half. (b) What is the cleanest exact encoding: explicit integer cone coordinates (as in MIQ) or a per-cone sublattice constraint on τ_v? (c) How much optimal energy does the 2ℤ² restriction cost at 2–6 triangles per quad (the measured range)?

**Use.** TODO 3.4 (REFERENCE M12).
**Sources.** param §5 Q1, §0.3; spec §13.

### SQ-P2. Lattice preservation under constraint elimination
**Context.** Linear constraints are eliminated by substitution before the least-squares solve: M0 removes single-term rows (x_i = 0); M1 merges two-term rows with coefficients ±1 by union-find, giving the group the **maximum** period of its members; M2 eliminates each remaining row with the pivot of smallest period·|a| (continuous variables preferred); a final consistency pass reports residual rows, but its result is ignored. The reduced unknowns are kernel variables y with x = Ky, and integer kernel variables are rounded to multiples of their period.

**Question.** Under what conditions is the map from integer kernel variables to the original integer variables unimodular, so that rounding y to pℤ puts every original x in its lattice? Is the "maximum period" rule correct when a period-1 and a period-2 variable merge? If integrality is not guaranteed, what is the right construction (Hermite/Smith normal form of the integer part of the constraint matrix, or eliminating only on continuous pivots), and what does it cost at 10⁵ variables?

**Use.** TODO 3.5 (REFERENCE M13).
**Sources.** param §5 Q2, §1; spec §14.1.

### SQ-P3. Order of greedy rounding
**Context.** One-shot rounding (all integers fixed after one continuous solve) is being replaced by greedy rounding in the spirit of Bommes et al. 2009. The integers are mostly seam translations, which act globally, so local Gauss–Seidel updates help little and full re-solves are expensive. Plan: batched rounding of all variables within δ_k of an integer with δ growing geometrically, plus a rule that two cones never round to the same grid point. Measured today: all integers are fixed in one pass, moving them by up to ≈0.5.

**Question.** Is there a provably better order than "smallest fractional part first", for example by the energy increase of rounding x_i with the rest free (a Schur-complement diagonal / conditional variance), and can it be computed cheaply from one sparse Cholesky factorization (selected inversion)? What batch size or δ schedule keeps the final energy close to sequential greedy? Is there a bound on the gap?

**Use.** TODO 3.3 (REFERENCE M1, Stage A).
**Sources.** param §5 Q3, §3.1; perf §3.

### SQ-P4. Validity certificate before extraction
**Context.** After rounding, the map has known cones, transition rotations and integer translations. Extraction needs a valid integer-grid map (locally injective, every arc of the induced layout of positive length). Campen et al. 2015 (QGP) note that no polynomial test is known for whether a **partial** quantization can be completed.

**Question.** For a **complete** quantization, what is the cheapest sufficient test that an integer-grid map with this combinatorics exists (all T-mesh arcs of positive length, no cone collapse), beyond QGP's O(n²) singularity-contact search? How does it relate to the holonomy-signature feasibility results of Shen et al. 2022 ("Which cross fields can be quadrangulated?")?

**Use.** A guard between rounding and extraction (TODO 3.3, 7.2).
**Sources.** param §5 Q4.

### SQ-P5. Injectivity chain and exact arithmetic
**Context.** Candidate guaranteed pipeline: seamless map → injectivity repair (foldover-free maps, SLIM) → motorcycle graph → Bi-MDF quantization → per-patch Tutte embedding → SLIM → extraction.

**Question.** Which steps can break discrete injectivity in floating point? Is exact or rational arithmetic needed anywhere (Mandad–Campen 2019 suggests exact seam constraints), or are exact predicates for topological decisions plus inexact geometry (QEx's approach) enough? Shen et al. 2019 note that exact results rounded back to doubles can flip again; what is the right final rounding policy?

**Use.** TODO 7.2.
**Sources.** param §5 Q9; perf §8.3.

### SQ-P6. Learned priors with a correctness check (low priority)
**Context.** No published method predicts integer assignments for integer-grid maps; recent neural work predicts cross fields or singularities (NeurCross, CrossGen, TopGen). Validity of an integer-grid map is a global, topological property.

**Question.** Is there a formulation in which a learned proposal (cones, or a partial integer assignment) comes with a cheap correctness check and a bounded repair cost, so that the classical solver only verifies? If only cone placement qualifies, what energy (alignment, pole count, symmetry) should score proposals so that learned and classical fields can be compared on one objective?

**Use.** Long-term option only.
**Sources.** param §5 Q10, §3.6; cross §3.5.

---

## L. Quantization and layout

Suggested experts: Bommes, Heistermann (Bi-MDF); Ray, Sokolov, Coudert-Osmont (quantization without a T-mesh); Campen, Lyon (T-mesh quantization).

### SQ-L1. Route to a valid integer quantization
**Context.** The parametrization is a field-aligned global parametrization on a triangle mesh (not a T-mesh), for 10k–100k output quads on mostly organic sculpts with boundaries and several islands. Today all integers are rounded at once.

**Question.** What is the cleanest route to a valid quantization: (a) greedy MIQ rounding with safeguards; (b) quantization on a decimated surface (Coudert-Osmont et al. 2024, no T-mesh); (c) a T-mesh/motorcycle graph traced from separatrices, quantized by Bi-MDF (Heistermann–Warnett–Bommes 2023)? Expected quality/time trade-off at these sizes, and robustness on organic shapes with many singularities?

**Use.** Gate 7.1 and the Stage B design (TODO 7.2).
**Sources.** extr §8 Q-L1; param §2, §4.

### SQ-L2. Extra objective terms in Bi-MDF
**Context.** Bi-MDF quantizes a T-mesh by minimizing the deviation of integer arc lengths from continuous ones as a min-deviation flow on a bi-directed graph, solved exactly in seconds.

**Question.** Can the objective be extended with terms that penalize pole proximity, enforce mirror symmetry (paired arcs equal), or price the total quad count (a Lagrangian price per strip length), while keeping the flow structure and hence speed and exactness? Which of these break the network structure?

**Use.** Stage B, mirror symmetry (F5), exact count (F6).
**Sources.** extr §8 Q-L2; size §5.3.

### SQ-L3. QuadriFlow's flow versus Bi-MDF
**Context.** QuadriFlow (Huang et al. 2018) fixes the integer edge vectors of an Instant-Meshes-style position field with a min-cost network flow so that every face closes as a quad. Its code is BSD-3 with an "enhancements" grant-back clause; libSatsuma (Bi-MDF) is MIT.

**Question.** On a position field, is QuadriFlow's formulation equivalent or reducible to Bi-MDF / T-mesh quantization? If yes, is either the better basis for a permissive implementation in this pipeline?

**Use.** Choice of quantizer (TODO 7.2).
**Sources.** extr §8 Q-L3.

### SQ-L4. Cancelling singularities during quantization
**Context.** Close ± cone pairs produce zero-length T-mesh arcs. Bi-MDF's half-arc formulation admits some layouts that were previously infeasible, but quantizers generally cannot change the cone set.

**Question.** Should quantization be allowed to cancel a ± pair, and how can that be put into the flow model with a single cost parameter (a pole budget)?

**Use.** Stage B and the pole budget (F9).
**Sources.** param §5 Q6.

### SQ-L5. Boundaries and islands in quantization
**Context.** Metriko (an open QGP implementation) has no boundary support; topological integer-grid-map initializations cover limited genus. We need free and feature-aligned boundaries (open meshes, partial remesh with a frozen border, many islands).

**Question.** What is the minimal extension of motorcycle-graph quantization to free and aligned boundaries? Coudert-Osmont et al. 2024 claim easier free-boundary handling; is that the better base?

**Use.** TODO 7.2, F10.
**Sources.** param §5 Q8.

---

## F. Features, corners and guides

Suggested experts: Pietroni, Tarini (QuadWild); Bommes, Campen (feature-aligned quantization); Zorin, Capouellez (feature-aligned Penner).

### SQ-F1. Corner indices at feature junctions
**Context.** Hard features (sharp edges, face-set borders, guide curves) lock the field to the feature tangent and should become grid lines. At a vertex of the feature graph, each sector between consecutive feature edges with developed angle α gets q = max(1, round(2α/π)) quads and corner index (2 − q)/4. With M′ the surface cut along features, combinatorial Gauss–Bonnet reads Σ_interior (4 − val)/4 + Σ_sectors (2 − q)/4 = χ(M′). Rounding is ambiguous near α = (k + ½)π/2 (e.g. 135°). The field uses the complex power z = e^{4iθ}, in which corner indices are not explicit.

**Question.** (a) Formulate the choice of corner indices together with interior singularities as one small integer problem whose objective is the distortion of the resulting conformal map, with Gauss–Bonnet as the only coupling. Is it solvable exactly for a few hundred corners? Is it the same reduced problem as the cone-angle step of Du et al. (integer-constrained cones)? (b) Can an angle + period-jump formulation near features (q an integer unknown with a distortion penalty) be coupled to the power-field formulation elsewhere?

**Use.** TODO 5.2 (REFERENCE M8).
**Sources.** cross §5 Q5, §4.4; size §7 Q4, §3.2.

### SQ-F2. Feasibility of hard isoline constraints
**Context.** Today a feature's isoline constraint is dropped whenever the field is more than 10° off the feature. We want every hard feature and guide to be an integer isoline and to drop only infeasible ones. Two parallel same-family isolines closer than about half a quad collapse to one grid line under rounding, or fold.

**Question.** (a) What is the precise condition under which a set of curves with integer-isoline constraints admits a fold-free integer-grid map at scale s (e.g. parametric distance ≥ 1 between same-family isolines along every transversal path)? (b) Is feasibility-checked rounding (IGM-style) enough, or is T-mesh quantization (Bi-MDF) required before hard features are switched on? (c) In the T-mesh setting, what are the feasibility conditions for forcing a feature network with corners of arbitrary angle onto grid lines, and where must extra cones go? Feature-aligned Penner (2025) gives sufficient conditions for the continuous map; we need the discrete counterpart.

**Use.** TODO 5.3, 5.7.
**Sources.** size §7 Q5, §3.4; param §5 Q7.

### SQ-F3. Closed guide loops
**Context.** A user draws a closed guide around a limb, which must become a closed edge loop (an integer isoline). Separately, the current solver puts translations in 2ℤ², which forces even quad counts around loops with trivial holonomy (see SQ-P1).

**Question.** Necessary conditions appear to be: field holonomy along the loop ≡ 0 mod π/2, and zero translational period in the transversal coordinate. How can these be imposed as linear constraints (cf. the cycle constraints of Ebke et al. 2016) without fixing the singularity configuration elsewhere? How do they interact with the parity restriction?

**Use.** TODO 5.7; edge loops around tubes (F12).
**Sources.** size §7 Q6.

---

## S. Symmetry and quad count

Suggested experts: Panozzo, Lipman, Zorin (fields on symmetric surfaces); Bommes, Heistermann (count in quantization).

### SQ-S1. Mirror-symmetric cross fields
**Context.** Mirror symmetry σ (a reflection) acts on an exactly symmetric triangulation as a vertex/face permutation. With mirrored local frames it acts on the 4-fold power representation by conjugation, z_{σ(f)} = conj(z_f): an ℝ-linear, not ℂ-linear, constraint. On the fixed curve (the plane), z·e^{−4iφ_plane} ∈ ℝ, so the field is aligned with the plane or at 45° unless singular (Panozzo et al. 2012, Prop. 6).

**Question.** (a) Confirm symmetric criticality here: is the minimizer of the energy restricted to the σ-invariant subspace a critical point of the unrestricted energy, and for Knöppel's eigenproblem is the smallest eigenvector of the restricted real operator the right object? (b) Which singularity configurations are forced on the fixed curve (index parity constraints), and does Gauss–Bonnet on the half-surface, with the fixed curve as boundary, give all constraints? (c) Should the branch on the plane (aligned vs 45°) be imposed as a sign constraint or as Dirichlet values?

**Use.** TODO 5.5 (F5).
**Sources.** size §7 Q7, §4.2; cross §5 Q8, §4.6.

### SQ-S2. Mirror-symmetric parametrization
**Context.** Symmetry is imposed on the map as f(σ(x)) = A·f(x) + t with det A = −1 and t ∈ ℤ²: A = diag(1, −1) with t_v even (an edge loop on the plane) or odd (a row of self-symmetric quads centred on it), or A = coordinate swap (45° mode). σ-paired integer variables are rounded jointly.

**Question.** How to construct a σ-invariant cut graph that crosses the plane, so that f∘σ = Af + t is linear in the chart unknowns? What is the correct integer bookkeeping for t (one variable per connected component of the plane?) when the plane meets cones? Is there any obstruction to rounding σ-paired integers jointly?

**Use.** TODO 5.5.
**Sources.** size §7 Q8, §4.2.

### SQ-S3. Controller for an exact quad count
**Context.** N(s) ≈ s⁻²∫ρ² dA for global scale s. Plan: secant iteration on log s with the field reused, then a knapsack over quad strips (chords) — minimize Σ|x_c|·cost_c subject to Σ x_c L_c = N* − N₀, x_c ∈ {−1, 0, 1}, where L_c is the strip length in quads — then ±1 local operations. After rounding, N(s) is piecewise constant with jumps; for independent per-strip rounding errors σ_N ≈ √(Σ L_c²/12). Parity facts so far: a closed quad mesh imposes no parity on F; with boundary the total number of boundary edges is even; a mirror mesh with an edge loop on the plane has F even.

**Question.** Is secant + strip knapsack sound, or is there a monotone formulation (e.g. a Lagrangian price per strip inside Bi-MDF) that guarantees the count crosses N* without topology changes? Is the parity list complete?

**Use.** TODO 4.7, 5.6 (F6).
**Sources.** size §7 Q9, §5.

---

## E. Extraction and cleanup

Suggested experts: Ebke, Bommes, Campen (QEx); Ray (messy-map extraction); Remacle, Reberol (Gmsh cleanup operators).

### SQ-E1. Which property of the map fails first (partly answered)
**Context.** Extraction assumes an integer-grid map: transitions g(z) = iʳz + t with t ∈ ℤ², cones at integer points, det ∇f > 0 everywhere. AutoRemesher rounds all integers in one shot, keeps translations in 2ℤ² (so transitions are integral and cones land on ℤ² by construction, see SQ-P1), snaps coordinates within 0.01 of an integer, has no injectivity term, and ignores a failed consistency check in constraint elimination.

**Answered by the code read [I]:** transitions and cone positions are integral by construction, so the expected first failures are fold-overs (det ∇f ≤ 0) and degenerate triangles, plus any silently violated constraints. **Measured (baseline, REFERENCE §4.1):** flipped triangles in the integer-grid map in 54 of 54 runs, median 0.75 %, max 10.1 %. Their rate predicts cleanup rounds (Spearman ρ 0.65–0.85) and final irregularity (ρ 0.48–0.81). The output also has non-manifold edges in 20 of 54 runs (REFERENCE M16).
**Remaining question.** Can anything else fail with this construction (e.g. the 0.01 snap producing inconsistent transitions)? For a map that is grid-preserving but not injective, which extractor class fits better: parameter-space tracing (QEx) or dual segmentation (Ray 2025)?

**Use.** TODO 6.1, 6.3.
**Sources.** extr §8 Q-E1; spec §13, §14.

### SQ-E2. Fold-over tolerance of QEx
**Context.** QEx (Ebke et al. 2013) traces integer isolines in parameter space with exact predicates and handles small fold-overs and degeneracies locally. Our maps currently have 0.25–2.2 % flipped triangles (median by target size), up to 10 % on hard-surface and thin-shell inputs.

**Question.** Is there a characterization of the fraction or spatial pattern of flipped triangles below which QEx still yields a closed, manifold quad mesh? What fraction p is tolerable before holes appear?

**Use.** TODO 6.1.
**Sources.** extr §8 Q-E2.

### SQ-E3. Singularity-merging threshold versus mesh resolution
**Context.** Ray 2025 ("On quad mesh extraction from messy grid preserving maps") merges low-valence singularities along short paths, with a threshold of 10 edges. Our parametrization mesh has 2.0–2.6 triangles per *requested* quad. Measured per *output* quad: 2.4–2.6 with curvature sizing off, but a median 5.8 (3.3–13.4) with default settings, because the sizing step enlarges quads. So on average it is finer than the quads; whether it is locally coarser was not measured.

**Question.** Is a 10-edge threshold meaningful at that resolution, or must the parametrization mesh be refined first? How should the threshold scale with triangles per quad?

**Use.** TODO 6.3.
**Sources.** extr §8 Q-E3 (corrected from "≈1 triangle per quad", RECONCILIATION C5).

### SQ-E4. Restoring validity locally before extraction
**Context.** Between rounding and extraction a map may have small flipped regions.

**Question.** Can validity be restored by a local re-solve with an injectivity barrier on the flipped regions only, keeping the integer data fixed, at acceptable cost? When does such a local repair provably exist for the given integers, and when must the integers change?

**Use.** TODO 3.6, 6.3.
**Sources.** extr §8 Q-E4; param §3.3.

### SQ-E5. A complete set of local cleanup operators
**Context.** AutoRemesher repairs its extracted mesh with 12 greedy passes (polygon splits, pentagon merges, valence fixes). We want a small set of grid-preserving local operators under a validity guard.

**Question.** Which minimal set of local quad-mesh operators (doublet collapse, quad-vertex merge, diagonal collapse, edge rotation, chord collapse, cavity re-quadrangulation) is complete for removing all non-quad faces and all vertices of valence ∉ {3, 4, 5} while preserving a valid embedding? A proof or a counterexample.

**Use.** TODO 6.2.
**Sources.** extr §8 Q-C1.

### SQ-E6. Pattern table for cavity re-quadrangulation
**Question.** For re-quadrangulating a cavity with a fixed boundary, which table of patterns (n-sided boundaries with given side subdivisions) covers 3-, 5- and 6-sided cavities with at most one irregular vertex, and when does Bunin's linear solve apply? (Related: Takayama et al. 2014; Tarini 2022.)

**Use.** TODO 6.2.
**Sources.** extr §8 Q-C2.

### SQ-E7. Telling spurious chords from geometric ones
**Context.** Chord (poly-chord) collapse removes a whole ring of quads and changes the global structure.

**Question.** What criterion decides that a chord is spurious (an artefact of rounding noise) rather than geometric (forced by field singularities or features)? Candidates: chord width in parameter space, correlation with cones, energy change on collapse.

**Use.** TODO 6.2.
**Sources.** extr §8 Q-C3.

---

## M. Quality metrics

Suggested experts: authors of quad-layout user studies, if any exist (none found); SQuadGen authors (loop simplicity metric).

### SQ-M1. Which metrics predict artist preference
**Context.** Planned metrics for quad meshes: quad fraction, irregularity excess over the Euler bound, base-complex patch count, scaled Jacobian, size fidelity, curvature alignment, loop statistics and simplicity, pole spacing, pole–curvature correlation, symmetry.

**Question.** Which of these correlate with artist preference? Is there published work linking objective quad metrics to perceived topology quality? If not, how should a small blind ranking study (3–5 artists, ~20 meshes, pairwise comparisons) be designed to have enough power to fit weights?

**Use.** TODO 0.7 (composite score and pass criteria).
**Sources.** extr §8 Q-M1, §5.3.

### SQ-M2. A principled definition of edge flow
**Question.** Is anisotropy-weighted alignment of output edges with principal curvature directions, plus the fraction of simple (non-self-intersecting) edge and face loops, sufficient to measure "edge flow"? Or is a cross-field energy better, e.g. the Dirichlet energy of the cross field implied by the output mesh?

**Use.** TODO 1.4, 0.7.
**Sources.** extr §8 Q-M2.

### SQ-M3. A proxy for good pole placement
**Question.** Is "the sign of integrated Gaussian curvature within 2h of a pole matches its index (valence 3 ↔ K > 0, valence 5 ↔ K < 0)" a sound proxy for good pole placement on organic shapes? Or should poles be compared with the singularities of an optimal field (Knöppel et al. 2013) or of an optimal cone metric?

**Use.** TODO 1.4 (metric P2).
**Sources.** extr §8 Q-M3.

### SQ-M4. Euler lower bound with boundaries and features
**Context.** For a closed all-quad mesh Σ_v (4 − deg v) = 4χ, so the "irregularity excess" Σ_v |4 − deg v| − |4χ| counts unnecessary poles.

**Question.** How should boundary and feature-corner terms enter this lower bound for meshes with boundaries and feature curves (corners count like boundary corners of a quad layout)? Is the sector-rule corner index (2 − q)/4 of SQ-F1 the right term?

**Use.** TODO 1.4 (metric T4).
**Sources.** extr §8 Q-M4; size §3.2.

---

## Not for a math specialist

Code checks and measurements that came up in the same reports are in TODO.md (1.10, 1.11): charge-to-valence convention, sign convention of the disabled conformal solve, unread cleanup passes, Eigen version, solver sizes, CoMISo's escalation strategy, how `quadextractor.cpp` handles degeneracies.
