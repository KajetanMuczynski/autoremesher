# 2026-10-21 · Claude (cloud, thread "Torus handle loss in extraction") · Thin torus handle loss
- Repos/commits: core master 4d15d5f (measured), docs on 97d61e9. Experiment and fix commits not merged:
  16f209e, 3e40146 (patches in research/torus-extraction-2026-10-21/).
- Did: tested refining T before extraction (1-to-4, map interpolated) on the tori; traced the lost
  handle on the seam-lattice thread's Z² map into `extractMesh`; built a fix (interpolated T normals in
  the face test, `collapseTriangles` keeps 3-cycles that ring a thin part); ab.py A/B on the closed set
  and the corpus with 5 float32 replicates; compared with the libQEx thread's torus runs.
- Found: refining T changes nothing. Two extractor defects lose a valid 3-quad ring: the triangle
  collapse and the flat-normal face test on a coarse T. With both fixed and the Z² map, torus_0.03
  Fast 150 is right in 6/6. On master's map the fix is neutral (meridian rounds to 2), and on the
  corpus the normals change only moves which folds close a handle. libQEx keeps the Fast tori on
  master's map; torus_0.03 Quality 150 stays 3/6 with every extractor (map flips).
- Measured: closed topology master 76.7, fix 76.7, Z² 75.5, Z² + fix 77.7 of 78; corpus master 60.8,
  fix 60.7, Z² + fix 58.8 of 72 (Z² still in progress); corpus metrics of the fix flat (×0.996–1.003).
  Details: research/torus-extraction-2026-10-21.md.
- Next: don't merge the fix; decide `extractMesh` vs libQEx (6.1) first. A handle needs ≥ 3 quads
  around in the map (V6 wording). Re-test the patch only if `extractMesh` stays and Z² is settled.
