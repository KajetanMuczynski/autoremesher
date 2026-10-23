# Changelog

## Quadami (unreleased, add-on 0.1.0 test builds)

Changes since the fork from AutoRemesher 1.2.0 (`4a49f82`), up to master `0e9bec8` (2026-10-22).
Builds are told apart by the build line in the panel, not by the version number.

Blender add-on
- New Blender 4.2+ extension "Quadami": panel in the 3D Viewport sidebar, remesher in its own
  process, Esc to cancel, result next to the hidden original, modifiers used as shown
- Quality report after every run: quads against target, non-quads, holes, non-manifold edges and
  vertices, winding flips, folded faces, empty islands, input cleanup, time, with warnings
- Repair Folds and Re-run: detects folded sculpt input and, on request, repairs it before remeshing
- Build line in the panel and preferences; red when add-on and remesher come from different builds
- Confirmation above 200,000 target quads, with the memory estimate; Target Quads capped at 2,000,000
- Zips with the remesher inside for Linux x64, Windows x64 and macOS Apple silicon (no release yet)

Remeshing
- libQEx is the default quad extractor, with a per-island fallback to the previous one
- Closed inputs stay closed and small islands stay present; holes left in closed islands are reported
- Input cleanup: zero-length edges and inconsistently wound patches are fixed before remeshing
- Quad cover rounded greedily on one factorisation, then untangled with its integers held
- Validity check of the map before extraction
- Output projected onto the input surface and relaxed along it
- Default adaptivity 0.5 with a chord-error size law; Fast/Quality resolution setting
- Cones kept off needle tips; exact crossing keys far from the origin

Project
- License GPL-3.0-or-later (upstream MIT notices kept); renamed to Quadami
- CI on every pull request for Linux, Windows and macOS, with an output quality gate
- A/B benchmark harness (`tools/bench/ab.py`) that every quality claim must come from

## AutoRemesher (upstream history, by Jeremy Hu and contributors)

1.2.0
- Reduce triangles and irregular vertices in quad extraction
- Support touch pad pinch and scroll zooming
- Fix parameterization for tiny size model
- Fix repeated file name in the Windows release zip

1.1.0
- Replace Geogram with a native quad parameterizer
- Add anisotropic quad sizing and the `--anisotropy` CLI option
- Improve UV parameterization and quad extraction
- Smooth and project extracted quads onto the input mesh
- Split six-edge faces during quad extraction
- Add source, isotropic, parameterization, and remeshed-model previews
- Show singular vertices and extracted connections in previews
- Fix remeshing of non-manifold meshes
- Fix a resampling data race
- Print headless progress as a percentage
- Add headless remeshing reports
- Enable high-DPI support with Qt 5
- Use Accelerate/BLAS on macOS
- Support Linux CPUs without AVX2
- Update Windows CI and build instructions
- Add a Contributors dialog
- Improve quad extraction and remeshing robustness
- Fix a crash when previewing very large input meshes
- Add mesh simplification and decimated mesh preview
- Allow direct numerical input for remeshing parameters
- Improve progress reporting

1.0.0
- Relicense from GPLv3 to MIT (reimplemented MIT-incompatible dependencies)
- Improve parameterizer, isotropic remesher, and quad extraction algorithms
- Add adaptivity parameter
- Add sharp edge parameter
- Add smooth normal parameter for low-poly mesh
- Replace density with target quads parameter
- Add command-line interface
- Refine main window, theme, and graphics widgets
- Replace app icon

1.0.0-beta.3
- Remesh isolated meshes separately   
- Improve quad extractor  
- Add edge scaling setting for generating low poly  
- Add rough progress reporting (Windows only)  
- Generate quad dominated mesh    
- Improve parameterization for thin surfaces  

1.0.0-beta.2
- Fix holes  
- Replace Poly budget with density setting  
- Remove laplacian smooth in preprocess  

1.0.0-beta.1
- Replace MIQ with QuadCover  
- Implement simple quad extractor  
- Remove libQEx  
- Add OpenVDB for uniform remeshing  

1.0.0-alpha.4
- Add constrained option: Better Edge Flow/Less Distortion  
- Fix libQEx access violation  
- Fix OpenMesh crash  
- Limit singularities to 320  
- Improve wireframe render  

1.0.0-alpha.3
- Support mesh with holes  
- Generate better edge flow by increase the default constraint ratio from 0.4 to 0.5  
- Alleviate spiral pattern by up-sampling  
- Speed up on complex mesh by reducing singularities   
- Add debug dialog  
