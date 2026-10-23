# 2026-10-22 · cloud thread · Public showcase gallery
- Repos/commits: core 0e9bec8 (master)
- Did: read the license of every downloaded corpus mesh at the source (odedstein/meshes READMEs);
  wrote `tools/gallery/gallery.py` (ab.py runs with 4 replicates + metrics, Blender Workbench renders
  via bpy 5.2.2, table from the add-on's report.py) and the `gallery` set in corpus.json; produced
  `docs/gallery/` (10 runs, 9 meshes, 340 KB of WebP) with limits seeds and sources; design note
  `docs/WEBSITE.md`; test that keeps the gallery to public or procedural meshes.
- Found: public sword at 1,000 quads loses part of the guard or blade tip in all 5 runs (shape error
  2.0-29.7 % of the diagonal) with no panel warning and the input's topology; the folded-input
  warning fires on 8 of 10 runs incl. CAD and scans with clean output and blames "a sculpt brush";
  panel row "Folds repaired: -29 of 3 spots" on brush_layers 5000 with repair (clusters 3 -> 32).
  SMPL hand/human and Nefertiti flagged unclear, not used.
- Measured: see docs/gallery/README.md table (ab.py, origin/master 0e9bec8, 4-core cloud box).
- Next: Kajetan decides the WEBSITE.md questions after the first release; core shape-distance
  check for the thin-part warning; fold warning threshold and wording; the negative "Folds repaired".
