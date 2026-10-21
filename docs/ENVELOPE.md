# Supported-input envelope

Which inputs and settings the remesher is expected to handle. **Inside the envelope every gate of
[TARGETS.md](TARGETS.md) applies as written, and a failure is a bug. Outside it a failure is reported as
an *expected limit*:** it is still counted and ratcheted, but it does not fail a gate. Written
2026-10-21 (thread "Supported-input envelope for the remesher") for Kajetan's "strict, but not stupidly
strict". **Status: proposal.** The thresholds and user-facing behaviour are his call (§6).

Tags as in [README.md](README.md): **[M]** measured, **[C]** checked in code, **[I]** inferred. Every [I]
threshold names the experiment that would turn it into [M] (§4). Sources: the research notes named in each
row, master `124aeb8`.

**Unit.** h₀ = √(A / N): the input area divided by the target count, square-rooted. It is the core's base
quad edge (TODO 2.11) and the mean output edge length. Adaptive sizing makes the local edge smaller on
curved parts, so a feature measured in h₀ is an upper bound on its size in local quad edges.

---

## 1. Design critique first: how an envelope rots, and the guards

An envelope is a list of excuses. Each excuse is cheap to add and expensive to remove, and it hides bugs
by default. This project has already seen it happen once. V6's "handles shorter than 4 quad edges are
exempt" would have hidden an extractor bug: the tori lose handles of 2.1–2.7 h₀, and in torus_0.03 Fast 150
the map held a meridian of 4 grid units and the extractor still lost the handle
(research/genus-diagnosis-2026-10-21.md). The ways an envelope rots, and the guard against each:

| Rot | Guard |
|---|---|
| A threshold is set by a proxy (length) when the cause is a mechanism (the map holds the handle, the extractor drops it) | Where the mechanism is known, the condition names it. A length is allowed only where no mechanism is known yet, and it is marked [I] with the experiment that replaces it |
| A whole run is exempted because one part is out of range, and an unrelated bug elsewhere in the run hides behind it | **Exemptions are local:** only defects within 2 h₀ of the out-of-envelope region are expected. A defect anywhere else in the run still fails its gate (§5.3) |
| Exempt defects disappear from view | Exempt counts are still reported, per limit, and ratcheted like TARGETS §3.2: no release is worse than the previous one |
| A limit is added to make CI green | A row needs all of: an [M] measurement or an [I] with its experiment, a test mesh in `corpus.json` that sits outside the limit, a **canary mesh just inside it that must pass**, and an owning TODO item or the word *permanent* with a reason. A PR that adds or loosens a row needs Kajetan's yes |
| A fixed limit stays in the list | At each release (§5.4) every limit's test mesh is re-run. A limit whose mesh now passes is tightened or deleted in the same release |
| Things that can be fixed get documented instead | Rows tagged *temporary* (scale, degenerate edges, flipped patches) exist only until their TODO lands. The fix is better than the row |
| A real bug is filed as "weird input" | §2 lists defects that are **never** exempt, whatever the input |

**What Kajetan may have missed.** "Weird meshes may fail" splits into two different things, and the
envelope must keep them apart:
1. **Physically unrepresentable at the requested count.** A tunnel narrower than a quad cannot be
   represented by quads of that size, and no remesher can do it. This kind is *permanent*. The right
   answer is to tell the user the count they would need, not to hide the failure.
2. **Not handled yet.** Intersecting eyeballs, zero-area triangles and flipped patches are all ordinary
   sculpt inputs, and today they fail because of bugs. This kind is *temporary*: it is in the
   envelope's TODO column with an owner, not outside the envelope for good.

Most of today's sculpt failures are kind 2. If they were declared out of the envelope, the gates would go
green and the add-on would still break on eyes.

## 2. Never exempt (inside or outside)

Each of these is a bug wherever it happens, because no input makes it unavoidable [I, argument per row]:

- **Crash, hang, or no output** (H1). The worst outside-envelope result is a refusal with a reason, never
  a crash. The 2,000,000-quad ceiling already refuses instead of exhausting memory (TODO 2.17) [C].
- **Extra handles; boundary loops split or merged** (V6, H5). Every measured extra handle came from the
  extractor (53/53 near a fold or a cone; 64 of 75 wrong replicate-runs fixed by tracing alone) [M]. Losing
  a handle can be physical (§3 row 1). Adding one never is.
- **6+-gons, and non-quad clusters of more than 2 faces** in organic or sculpt runs (sculpt note §5: the
  largest cluster on common inputs is 2) [M].
- **Non-manifold output edges or vertices** (H2).
- **Lost input islands** (H4). A too-small island is enlarged or reported, never dropped silently (TODO 2.14).
- **A closed input island coming out open** (H5). Measured on sculpt_parts eyeballs, where it is a bug,
  not a limit (§3 row 6).

## 3. The limits

h₀ as above. The "user sees" column is a proposal. *pre* means a pre-run check on the input, cheap enough
for the add-on panel to show before Remesh. *report* means the core's quality report after the run.

| # | Quantity (how measured) | Inside the envelope | Evidence | Test mesh (outside) / canary (inside) | Outside: what is exempt | User sees | Kind / owner |
|---|---|---|---|---|---|---|---|
| 1 | **Handle size**: per input handle, the continuous map's meridian holonomy H (grid units = quads, along the shortest homology loop of T; `seam-lattice-2026-10-21/holonomy.py`). Pre-run proxy: shortest input loop L ÷ h₀ (`handles.py`) | H ≥ 3 | Three bands, §3.1 | demosthenes 2k (H ≈ 1) / torus_0.1 at 150 (bug band) and torus_0.05 at 150 (owner band) | H < 2: the handle may close. 2 ≤ H < 3: may close until the owner's fix lands. Never: an extra handle | *pre:* "N handles narrower than 3 quads: raise Target Quads to ≈ N·(3/H)² to keep them, or they may close". *report:* handles closed | §3.1 |
| 2 | **Thin sheet**: local thickness t (inward ray from each input face centroid to the opposite side, area-weighted) ÷ h₀; the fraction of area with t < h₀ | t ≥ 1 h₀ everywhere for V2/V3 (folds, flips); **any t** for topology | Every tool folds on parts thinner than a quad (13/54 pairs have no fold-free tool) [M]. Yet topology holds: ellipsoid_0.4_0.003 (t ≈ 0.17 h₀ at 2k) keeps genus on 4d15d5f; on the closed set only the tori fail [M]. thin_leaf (t ≈ 0.32 h₀ at 2k, 0.71 at 10k): folds 2–12 in every replicate [M] | thin_leaf 2k / ellipsoid_0.4_0.1 (t ≈ 5 h₀ at 2k) | Folds and flips within 2 h₀ of the thin region. Topology, islands and the count are **not** exempt | *pre:* "thin parts below quad size: expect folds there" | permanent below 1 h₀ until 5.3/4.1 add a thin-part cap |
| 3 | **Sub-quad tips and crests**: input faces in the sharp/thin band (normal spread within one h₀ < 0.7, `sculpt_report.py`) | Not a run condition, a location. Non-quads there are tolerated (V1 rewording); folds are expected limits | Non-quads up to 5× concentrated in the band, folds often 100 % in it [M]. Kajetan's crater tip: 1 fold at a valence 10–12 pole [M, reported] | sculpt_voxel horn tips / spot (smooth: no exemption) | Folds and valence ≥ 7 within 2 h₀ of a band face. Counted and ratcheted | *report:* "N folds at sharp tips" | temporary: 5.3, 4.1 |
| 4 | **Input size**: triangles; **target**: quads | ≤ 6.4M triangles [M]; target ≤ 100k quads [M], 100k–200k [I] | 6.4M triangles in 27.5 s on the ladder (TODO 8.2) [M]. Memory 21 KB per quad at Quality, linear over 25k–100k [M] | koala ladder / spot 100k | Time and memory only. Quality gates still apply | Exists: the CLI warns above 200,000 with an estimate; the add-on asks; the core refuses above 2,000,000 [C] | permanent (hardware) |
| 5 | **Target vs input detail**: input triangles ÷ target quads | ≥ 2 [I] | Kajetan's coarse 3.7k-triangle blob at 1500 quads (ratio 2.5): 0 non-quads, 1 fold [M, one run]. Nothing measured below 2 | needs a mesh (E3) | Nothing exempt until E3 measures it | *pre:* "input coarser than the requested quads: the result follows the facets; consider Subdivision first" | open (E3) |
| 6 | **Joined / intersecting parts** (separate closed islands that intersect each other: eyes in sockets, teeth) | **Inside.** Ordinary sculpt layout | sculpt_parts: eyeballs come out as open caps in 19/36 runs, with non-manifold output vertices in 15/36 [M]. Cause not traced | sculpt_parts / sculpt_steps | **Nothing.** These are bugs (§2) | – | bug: eyeball-caps item (not yet in TODO) |
| 7 | **Self-intersection of one island** (a surface pushed through itself; triangle–triangle intersections within an island, BVH) | No self-intersection | Not in any test set. The map assumes an embedded surface [I] | needs a mesh (E4) | Folds and flips within 2 h₀ of the intersection | *pre:* "N self-intersections; result may fold there" | permanent [I] until E4 |
| 8 | **Degenerate input**: zero-length edges, zero-area triangles | Inside **after #51** (cleanup pre-pass) | sculpt_degenerate (21 % zero-area triangles) at 15k: 500–777 non-quads, wrong genus, 89–202 s. Cleaned: 0–8 non-quads, 4–16 s [M] | sculpt_degenerate / sculpt_steps | Until #51 merges: everything on that island | *report:* "Input cleanup: N degenerate triangles removed" (#51) | temporary: #51 (2.7) |
| 9 | **Inconsistent orientation** (manifold edges used twice in the same direction) | Inside after orientation repair (2.7, not in #51) | sculpt_dirty: a flipped patch tears off as its own island in 36/36 runs [M] | sculpt_dirty | Until 2.7: the torn patch and its hole | *pre:* "N faces with flipped normals" | temporary: 2.7 |
| 10 | **Non-manifold input** (fins, pinch vertices, duplicate faces) | Inside | sculpt_dirty: absorbed, 0 non-manifold output edges in 36/36 runs, a non-manifold vertex in 2/36 [M] | sculpt_dirty | Nothing | *report* only | covered; the 2/36 vertices are a bug |
| 11 | **Open boundaries and holes** | Inside | hand, demosthenes, cloth_sheet, human_neutral and Suzanne keep their loops (TODO 2.12) [M]. sculpt_dirty: 3 input loops come out as 1–6 [M] | sculpt_dirty / hand | Nothing. The sculpt_dirty loops are a bug (or row 9's tear) | – | bug, after 2.7 re-check |
| 12 | **Islands**: count, and the smallest island's area ÷ h₀² | ≤ 14 islands [M]; smallest island ≥ 0.1 h₀² [I] | spot_x8 (8) and sculpt_parts (14, crumbs of radius 0.008–0.02) keep every island in 35/36 runs [M]. 64-triangle floor and retries (TODO 2.14) [C]. Thousands of islands never run | needs a mesh (E5) | Above the measured count: time only. Below the area floor: the island may come out coarser than asked, never dropped | *pre:* "N islands; small ones get the minimum detail" | open (E5) |
| 13 | **Triangle size ratio**: edge length p99 ÷ p1 | ≤ 30 [M] | sculpt_dyntopo (p99/p1 = 30, 5:1 density jumps): 2 folds, topology 6/6 [M]; Kajetan's Dyntopo sculpt fine [M] | needs a mesh beyond 30 (E6) | Nothing measured to exempt | – | open (E6) |
| 14 | **Scale and position**: bounding-box diagonal d; centre offset | d ∈ [10⁻², 10⁴] [I]; centre at 10⁵ [M] | CI's output gate passes a sphere centred at 10⁵ [C]. `PositionKey` no longer overflows (now doubles) [C]. It still merges positions in absolute 10⁻⁵ cells, which is 1 % of a 10⁻³ model [C, I]. 1e-12 guards are absolute (TODO 2.7) [C] | needs a mesh (E7) | Below or above: everything, until 2.7 normalises scale | *pre:* "model is N m across; scale is normalised internally" after 2.7 | temporary: 2.7 (scale to a unit box) |
| 15 | **Settings**: adaptivity, anisotropy, sharp edge | Defaults (adaptivity 0.5, sharp 90°) [M]; adaptivity 1 [M] | Gates are measured at the defaults; csg_bracket opens a hole at adaptivity 1 (H5, 2.13) [M] | – | Non-default settings: the ratchet only, not the 1.0 bar | *panel:* "outside tested settings" next to a non-default value | permanent policy |

### 3.1 Handles: three bands

Measured on the continuous map, before rounding, because that is where the representability is decided.
A quad ring around a tube needs integer meridian holonomy of at least 3. Today's lattice is 2ℤ²: a
meridian rounds to 0, 2 (a collapsed ring) or 4 (research/seam-lattice-2026-10-21/, probe on tori and
demosthenes) [M].

| Band | Status | Evidence | What changes it |
|---|---|---|---|
| H < 2 | **Permanent limit** at this count. No lattice gives a ring of ≥ 3 without stretching the map by more than half (needs ×1.5 or more); the user is told the count that keeps it | demosthenes' three scan tunnels sit at H ≈ 1: 2ℤ² rounds them to 0 and ℤ² to 1, still no ring [M] | Nothing at this count: raise the count |
| 2 ≤ H < 3 | **Known limit with an owner.** Expected and ratcheted, and the canary below must not get worse | torus_0.03 / 0.05 at 150 (2.1–2.7 h₀). On master: 2ℤ² rounds to 2 (collapsed) or 4. ℤ² plus the torus thread's two extractor fixes keeps them (torus_0.05 Quality 0 → 5/6, Fast 1 → 5/6), but ℤ² alone regresses the corpus (flips ×1.35, plane 2k broken in 6/6) [M, seam-lattice and torus threads] | The ℤ² lattice landing together with the extractor fix. From then on this band is a **bug** |
| H ≥ 3 | **Bug.** Every loss here is the extractor's (2.13, 6.1) | 64 of 75 wrong replicate-runs on master are extractor losses or additions with the map right [M] | – |

Two open edges:
- The 2.0 boundary is [I]. It is the halfway point between holonomies that round to 1 and to 3 under
  ℤ²; no handle has been measured between 1.4 and 2.1. E1 settles it.
- H is a stage diagnostic, not an input property. The pre-run check can only use L/h₀. Adaptive sizing
  makes the local quads smaller, so H ≥ L/h₀ as a rule [I], and the proxy errs on the side of warning.

Two corrections to the brief: the add-on's Target Quads guard is 200,000 (warn) and 2,000,000 (refuse),
not 300,000 (TODO 2.17) [C]; and #51 collapses zero-length edges only, without orientation repair (PR
body, checked 2026-10-21), so row 9 stays open after #51.

## 4. Experiments that settle each [I]

| ID | Row | Experiment (all through `ab.py` with `--replicates 5`, per CLAUDE.md) | Settles |
|---|---|---|---|
| E1 | 1 | Tori at r ∈ {0.03, 0.05} over targets that sweep H from 1 to 4 (≈ 8 targets), demosthenes 2k/5k/10k, on master and on ℤ² + extractor fix. Log H per handle (holonomy probe) next to kept/lost | The 2.0 band edge, and how well L/h₀ predicts H |
| E2 | 2 | Thickness column (ray cast) added to the metrics; ellipsoid set at 2k–10k | Whether folds are confined to within 2 h₀ of thin parts, as row 2 assumes |
| E3 | 5 | spot and sculpt_steps decimated to 1k / 3k / 10k triangles, run at 1k–15k quads (ratio 0.1–10) | The lower bound of input ÷ target |
| E4 | 7 | Generator: one island folded through itself (a sphere with a dent pushed out through the opposite wall) | Whether self-intersection breaks only locally |
| E5 | 12 | spot_x8 pattern scaled to 100 and 1,000 islands; crumbs of area 0.01–1 h₀² | Island-count time and the small-island floor |
| E6 | 13 | sculpt_dyntopo variants with p99/p1 = 100 and 300 | The size-ratio ceiling |
| E7 | 14 | spot scaled ×10⁻³, ×10⁻², ×10³, ×10⁴ (a scaled copy in `corpus.json`, no new generator) | The scale range; needed before 2.7 to prove its effect |

Cost: E1, E5 and E7 are about 1 CPU hour each, the rest less [I]. They fit a single thread after the
speed thread's `ab.py` change lands.

## 5. How the harness decides inside or outside (design only)

`ab.py` is not edited here: other threads are changing it, and 1.14 (homology check) has to land first.

### 5.1 Per input: an envelope descriptor
Computed once per (mesh, target) from the input, and cached next to the mesh hash:
`h0`, `diag`, `centre_offset`, `triangles`, `islands`, `min_island_area_h2`, `edge_ratio_p99_p1`,
`zero_length_edges`, `zero_area_triangles`, `orientation_conflicts`, `non_manifold_edges`,
`self_intersections`, `handles[{L_h0, loop_vertices}]`, `thin_area_fraction`, `thin_faces`,
`sharp_band_faces`. Sources: `handles.py` (1.14), `sculpt_report.py`'s band, plus a ray-cast thickness
and a BVH intersection test (libigl is already in the bench venv).

### 5.2 Per run: inside / outside
`envelope = {"inside": bool, "violations": [{"row": 2, "value": 0.32, "limit": 1.0}, ...]}`.
A run is *inside* when no row is violated. Rows 4, 5 and 12–15 are run-wide. Rows 1, 2, 3 and 7 are
**regions**: the faces of the thin part, the handle's loop vertices, the band, and the intersection.

### 5.3 Per defect: bug or expected limit
For each gate defect (fold, flip, non-quad, valence ≥ 7, lost handle), find its nearest input point. It is
**expected** if that point is within 2 h₀ of a violated region whose row exempts that defect type.
Otherwise it is a **bug**, even in an outside run. Lost handles are matched by loop: a lost handle is
expected only if its H puts it in an expected band of §3.1, read from the stage diagnostics (so the core must export H per handle; until then the L/h₀ proxy decides and is reported as such). §2's defects are always bugs.

`compare` then prints per gate: `bugs` (fails the gate, A/B and release), `expected` (ratcheted, shown
per row) and `runs inside`. A PR that moves defects from `bugs` to `expected` without changing the code
that produces them, for example by editing a threshold, is flagged.

### 5.4 Release review
Before each tag: re-run every row's test mesh and canary. A canary that fails is a bug that blocks the
release. An outside mesh that now passes tightens its row. The envelope is re-signed with the release
version at the top of this file.

## 6. Open questions for Kajetan

1. **User-facing behaviour outside the envelope:** warn and run (my proposal: the panel shows *pre*
   warnings and runs anyway), or refuse? I'd refuse only above the memory ceiling, which already
   happens. Refusing a thin leaf would be "stupidly strict".
2. **Row 1, band 2 ≤ H < 3:** accept "known limit with an owner" until ℤ² and the extractor fix land
   together, then make it a bug? Below 2 is permanent, because no lattice can make a ring there.
3. **Row 6, eyeball caps:** keep it inside the envelope (my proposal), which makes 19/36 sculpt_parts
   runs count as gate failures today?
4. **Locality radius 2 h₀** (§5.3): no data says 1 or 3 is better. E2 measures it for folds. Accept 2 as
   provisional?
5. **Non-default settings** (row 15): does the 1.0 bar apply only at the defaults?
