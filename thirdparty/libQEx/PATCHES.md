# Changes to libQEx in this fork

Upstream: libQEx `517dcaa` (see `VENDORED.md`). The first vendoring commit is unmodified, so
`git diff <that commit> -- thirdparty/libQEx` shows exactly these changes. Why: research note
`qex-adoption-design-2026-10-21.md` (TODO 6.1b); every hang and crash below was reproduced with ab.py
replicates on #60's build and confirmed with gdb or ASan.

| # | Change | Files | Why |
|---|---|---|---|
| 1 | `Guards.hh` (new): `QEX_LOG`, `QEx::Abort`, `QEx::Limits`, `checkCirculatorsTerminate` | `src/Guards.hh`, `src/Globals.hh` | Shared by the patches below |
| 2 | Vertex-rotation check (O(#halfedges)) after face generation, before merging, after deleting obsolete faces, before deleting merged vertices; throws `QEx::Abort` | `MeshExtractorT.cc`, `QuadExtractorPostprocT.cc`, `qex.cc` | On folded maps QEx's own `add_face` (and later OpenMesh's `delete_face` at pinched vertices) leaves a vertex whose rotation never returns to its start; `PolyConnectivity::valence` and `delete_vertex` then loop forever (sword corpus runs) |
| 3 | Step budget: one counter per extraction, charged in `find_path` and in `try_connect_incomplete_gvertices`; over `Limits::max_steps` throws | `MeshExtractorT.hh/.cc` | `try_connect_incomplete_gvertices` loops forever on inconsistent connections (thin ellipsoid); `find_path` walks up to 10⁵ steps per path on degenerate triangles (thin torus: 26–235 s per run) |
| 4 | Grid-vertex cap: over `Limits::max_grid_vertices` throws | `MeshExtractorT.hh/.cc` | Bounds memory by the target quad count rather than by how much the map folds |
| 5 | `getNextConnectedLeiWithHE` returns null after a full turn without a candidate | `MeshExtractorT.cc` | It returned its start edge, whose halfedge index is −1; `add_face` wrote through it (heap overflow; crash and 8.3 GB runs on a real sculpt) |
| 6 | No face of more than 4 grid vertices that all lie on the input boundary | `MeshExtractorT.cc` | QEx closes each open boundary with one n-gon |
| 7 | `std::cout`/`std::cerr` → `QEX_LOG` (compiled out) | all sources | Millions of diagnostic lines on folded maps: minutes of I/O, logs filling the disk |
| 8 | `extractQuadMeshOMLimited` (C++ linkage) | `interfaces/c/qex.h/.cc` | Entry point with the limits; returns the steps used |
