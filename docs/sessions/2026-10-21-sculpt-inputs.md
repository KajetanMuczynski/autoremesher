# 2026-10-21 · Claude (cloud) · Remesher on messy sculpts
- Repos/commits: core master 7aae3fe (ab.py key d1517f791507), branch claude/project-thread-7kez1w
- Did: Kajetan's question whether the add-on works on messy sculpts. `tools/bench/make_sculpt.py`
  (set `sculpt` in `corpus.json`: voxel, terraces, zero-area variant, dyntopo, decimated, joined parts,
  export damage; 60k-573k triangles), `tools/bench/sculpt_report.py` (non-quads by side count, cluster
  and location band, one Catmull-Clark step, non-manifold vertices), `ab.py --timeout` and per-run peak
  RSS. Ran Fast/Quality at 2k/5k/15k, koala and cat at the same counts, 5 replicates for the discrete
  claims, and QuadriFlow, Instant Meshes and Blender 5.2.2's QuadriFlow for reference. Report:
  research/sculpt-inputs-2026-10-21.md (project files).
- Found: typical sculpt tessellations work (36 runs: 0.91-1.03× count, 0-8 isolated non-quads, 0-5
  folds, topology 34/36, ≤ 19 s and 0.66 GB). Isolated triangles and pentagons don't hurt subdivision
  (2 folded children over 23 fold-free runs); folds do. All-quad tools fold as often or more often, and
  Blender's QuadriFlow refuses 5 of 9 meshes. Breaks: (1) eyeballs sunk into the head come out as open
  caps (topology right in 9/36 replicate runs, non-manifold output vertices in 17/36); (2) a flipped
  patch tears off as its own island (36/36), and exact zero-area triangles break high-resolution runs
  (500-777 non-quads, holes, wrong genus, 90-200 s; 0 non-quads in 4 s once cleaned); (3) non-quads
  and folds collect on sub-quad tips and crests.
- Measured: as above [M], tables in research/sculpt-inputs-2026-10-21/.
- Next: Kajetan decides on the TARGETS V1 rewording (tolerated isolated 3/5-gons, count stays a
  ratchet metric) and H2 on vertices; then trace the eyeball opening, an input cleanup pre-pass (drop
  zero-area triangles, orient per island), and his own sculpts (1.12).
