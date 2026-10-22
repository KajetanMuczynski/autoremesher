# 2026-10-22 · cloud thread · Unrepaired fold spots classified
- Repos/commits: core 0e9bec8 (master) → claude/project-thread-t2bgxn
- Did: traced every fold repair patch attempt on the private head, cube and sword (per ring: which guard
  rejected it; patch kept out of the repo in the research folder), classified every spot left; fold repair
  passes 3 → up to 10 (stops when a pass moves nothing); panel and warning count folded faces instead of
  spots, and the folded-input warning no longer says a sculpt brush caused it.
- Found: no fold wider than r; the 0.25 r offset guard is never what stops a spot. Joined sword: 22 of 33
  spots are not folds (no dihedral above 90°, parts thinner than r, and r is 1 % of the whole object's
  diagonal), 5 more sit at non-manifold edges. Head 31 left: pass limit 6, leftovers of partly repaired
  spots 10, untangler stalls 5, post-check 5, steep 3, chart 2. Single-vertex spikes sit at cube 2/4 and the
  head's lower crease: repairing them means lowering the tip 0.5–1.4 r, a shape change. The panel's
  "M of K spots" undercounted (head: 41 of 67 spots fully gone, panel said 36) and could go negative.
  Kajetan's "blade 3 of 5" was a second remesh of a quad output (OSTZRE_remesh_remesh).
- Measured: see the PR and research/fold-repair-left-2026-10-22.md (project files).
- Next: detector needs a turned-over edge and a local radius (next PR); non-manifold edges as fixed
  boundary; spike handling waits for Kajetan's choice.
