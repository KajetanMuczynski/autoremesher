# 2026-10-20 · Claude (cloud thread) · Thin closed inputs and Target Quads guard
- Repos/commits: core on master 47529e1, branch claude/project-thread-4jw1b5
- Did: gap scan items 6 and 5. Per-island topology of T after decimation and after isotropic
  remeshing in the stage diagnostics (`ab.py` rows `t_non_manifold`, `t_opened`). Root fix in the
  decimator: `meshopt_SimplifyKeepTopology` in the vendored meshopt (no merge of coincident
  vertices, link-condition check per collapse), zero-length edges collapsed first, fallback to no
  decimation if the topology still changes (never fired). Target ceiling 2M quads in the core
  (interface 1.3), CLI warning and add-on confirm above 200k. Topology counting made dense
  (vector union-find, parallel sort): 708 → 229 ms on the cat.
- Found: meshopt made T non-manifold in 15/52 decimated closed runs and 8/26 corpus runs [M].
  Two causes: no link condition (thin ellipsoids, demosthenes, sword) and welding every coincident
  pair (cat: 50 pairs where the surface touches itself → 100 non-manifold edges) [M]. Not welding
  at all hurt blob_sym (marching cubes: 115 zero-length edges, 134 zero-area triangles; flips 8 → 33
  over 6 replicates), because meshopt refuses every collapse next to a zero-area triangle as a flip;
  hence the zero-length edge collapse. Halving-step decimation does not help: one halving already
  breaks demosthenes, so it fell back to no decimation (resample 10× slower); dropped.
  T's defects did not change any output genus on the closed set at u0 (75/78 both sides): the
  extractor and PR #16 already hid them; the remaining 3 failures are the map's.
- Measured: T defects after the fix 0 in all 270 runs (corpus, closed, replicates); corpus 72 runs
  aggregates flat (flips 8634 → 8665, Hausdorff ×1.000), closed 78 runs flips 5096 → 4806, Hausdorff
  −3 %; replicates (12 decimated meshes at 2k, 6 each): no run separated either way. Peak memory
  21 KB per quad at Quality, 9 KB at Fast (spot 25k–100k, linear); 100k quads took 142 s,
  time grows about as count^1.6 (rounding and curl correction lead).
- Next: blob_sym still 8 → 15 flips (not separated); TODO 2.7's sanitizer would own degenerate
  input. Upstream the meshopt option to zeux/meshoptimizer.
