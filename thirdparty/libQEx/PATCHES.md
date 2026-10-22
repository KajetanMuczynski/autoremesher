# Changes to libQEx in this fork

Upstream: libQEx `517dcaa` (see `VENDORED.md`). The first vendoring commit is unmodified, so
`git diff <that commit> -- thirdparty/libQEx` shows exactly these changes. Why: research note
`qex-adoption-design-2026-10-21.md` (TODO 6.1b); every hang and crash below was reproduced with ab.py
replicates on #60's build and confirmed with gdb or ASan.

| # | Change | Files | Why |
|---|---|---|---|
| 1 | `Guards.hh` (new): `QEX_LOG`, `QEx::Abort`, `QEx::Limits`, `checkCirculatorsTerminate` | `src/Guards.hh`, `src/Globals.hh` | Shared by the patches below |
| 2 | Vertex-rotation and face-loop check (O(#halfedges)) after face generation, before merging, after deleting obsolete faces, before deleting merged vertices; face-loop check of each face before the n-gon merge rebuilds it; throws `QEx::Abort` | `Guards.hh`, `MeshExtractorT.cc`, `QuadExtractorPostprocT.cc`, `qex.cc` | On folded maps QEx's own `add_face` (and later OpenMesh's `delete_face` at pinched vertices) leaves a vertex whose rotation never returns to its start; `PolyConnectivity::valence` and `delete_vertex` then loop forever (sword corpus runs). `delete_face` can also cut another face's loop open in the middle of the merge pass; the next face circulation then grew a vector until memory ran out (`sculpt_parts` Quality 15000, 4–12 GB) |
| 9 | `add_face` throws when a local edge, or its opposite, is not connected to a grid vertex | `MeshExtractorT.cc` | The opposite of a traced local edge can be connected one way only on folded maps; `add_face` indexed the grid vertices with its signal value (heap overflow, segfault: `sculpt_parts` Quality 5000) |
| 10 | `add_face` throws when the opposite of the previous connected local edge around a vertex has no halfedge yet | `MeshExtractorT.cc` | It set `next` through halfedge index −1 (heap overflow, `free(): invalid size`, rc 134: a test-only scan model at Quality 10000 in 1 of 6 replicates; ASan pointed at the write) |
| 3 | Step budget: one counter per extraction, charged in `find_path` and in `try_connect_incomplete_gvertices`; over `Limits::max_steps` throws | `MeshExtractorT.hh/.cc` | `try_connect_incomplete_gvertices` loops forever on inconsistent connections (thin ellipsoid); `find_path` walks up to 10⁵ steps per path on degenerate triangles (thin torus: 26–235 s per run) |
| 4 | Grid-vertex cap: over `Limits::max_grid_vertices` throws | `MeshExtractorT.hh/.cc` | Bounds memory by the target quad count rather than by how much the map folds |
| 5 | `getNextConnectedLeiWithHE` returns null after a full turn without a candidate | `MeshExtractorT.cc` | It returned its start edge, whose halfedge index is −1; `add_face` wrote through it (heap overflow; crash and 8.3 GB runs on a real sculpt) |
| 6 | No face of more than 4 grid vertices that all lie on the input boundary | `MeshExtractorT.cc` | QEx closes each open boundary with one n-gon |
| 7 | `std::cout`/`std::cerr` → `QEX_LOG` (compiled out) | all sources | Millions of diagnostic lines on folded maps: minutes of I/O, logs filling the disk |
| 8 | `extractQuadMeshOMLimited` (C++ linkage) | `interfaces/c/qex.h/.cc` | Entry point with the limits; returns the steps used |
