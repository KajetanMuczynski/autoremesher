# 2026-10-22 · cloud thread · Scout external test models
- Repos/commits: core origin/master ae27301 (ab.py key 74b97d2139c2)
- Did: checked which model sources the cloud reaches (GitHub, GitLab, PyPI, npm only; Sketchfab,
  Smithsonian, NIH 3D, Poly Haven, Thingiverse, Objaverse/HuggingFace, Stanford, Blender Studio, Zenodo
  are blocked); picked 20 public meshes from GitHub mirrors that state their license (odedstein/meshes,
  Khronos glTF-Sample-Assets, pyvista/vtk-data Smithsonian CC0 scans, three.js head scan, MakeHuman base
  mesh) plus 4 Stanford meshes kept test-only outside the repo; added `tools/bench/fetch_external.py`,
  `external.json`, set `external`, docs/EXTERNAL-MESHES.md, tests. Ran origin/master on all 24 at 3k,
  10k and one mesh-specific target, 5 replicates on 9 surprising cases.
- Found: no crash or timeout in 90 runs; clean organic meshes all-quad with the input's topology.
  Genus loss on thin handles (Happy Buddha 92-99 of 104 handles at 3k, flight helmet 26-32, sci-fi
  helmet 10, boot 2-4 at 3k; all 5/5 replicates). Many-island inputs: plant leaf cards give 4.5x the
  target count (5/5), mosquito drops ~870 of 1,208 islands (5/5), corset +45 % count. XYZ dragon
  (7.2M tris) peaks at 4.4 GB RSS. pyvista documents its Nefertiti as CC BY-NC-SA 4.0, unlike
  `meshes.tsv`. `ab.py run master` builds the local `master` branch, which was stale in this clone.
- Measured: tables in the project-files note research/external-models-2026-10-22.md.
- Next: Kajetan's hand downloads (knight sculpt, tentacle monster, Rain, Sprite, Phenebub, Cosmic
  Buddha) into the set; genus thread to take the handle losses, ledger the many-island cases.
