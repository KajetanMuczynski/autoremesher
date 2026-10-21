# 2026-10-21 · Claude (cloud thread) · Holes warning in the panel
- Repos/commits: core based on master a5e983a
- Did: the quality report counts boundary loops and non-manifold vertices (`measureMesh`), and,
  per input island that was closed, whether its output came out open and how many holes and open
  edges it has (`measureClosedIslands`, which runs `measureMesh` on each island's slice; the engine
  now says which slice belongs to which island). Interface 1.4, JSON `output.boundary_loops`,
  `output.non_manifold_vertices`, `islands.closed_in_input|opened|holes|hole_edges`, plus a warning
  "Output has N holes where the input was closed (E open edges)". The add-on panel shows Holes and
  Non-manifold vertices rows, and draws warnings full width, wrapped, with a hint how to find the
  holes in Blender. CI's output gate lists holes (not gated). ENVELOPE §3.2, TODO 2.3.
- Found: Kajetan's closed head (Sphere.obj) at 10k: 2 holes, 240 open edges, 2 non-manifold
  vertices; at 6k: 1 hole, 74 edges, 1 vertex. Non-manifold vertex counts equal `sculpt_report.py`'s
  on those outputs. The panel showed none of it before ("Non-manifold edges 0").
- Measured: output OBJ byte-identical to master on the 6 output-gate meshes, head 6k and 10k, cube
  3k and the joined sword 3k (10 islands, 5 closed: 0 holes).
- Next: gate H5 (holes in closed inputs) and H2 vertices in `output_gate.py` once 2.18 is fixed;
  the panel's "Select All by Trait > Non Manifold" click path is from memory, check it in Blender.
