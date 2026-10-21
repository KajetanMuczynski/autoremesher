# 2026-10-21 · cloud thread · Beginner user guide
- Repos/commits: quadami master 9648bb6
- Did: wrote docs/USER-GUIDE.md for non-technical Blender 4.5 users (glossary, install/update, build line,
  every panel setting with defaults from addon/quadami/__init__.py, result rows from report.py incl. the
  Holes and Non-manifold vertices rows of #65, warnings from remesh.cpp and the Target Quads guard,
  sculpt strengths and limits from ENVELOPE.md and the real-sculpt / sculpt-defect research, troubleshooting).
  Pointer from docs/README.md. Blender menu paths not checked in a real Blender are marked "from memory, check".
- Found: three overlapping how-tos existed (addon/BEGINNERS.md, addon/README.md "First test", the
  project-files command sheet). Made USER-GUIDE the only user-facing guide: BEGINNERS.md cut to
  build-from-source steps, README's "First test" replaced by a pointer (headless smoke check kept),
  navigation and the practice model moved into the guide; the command sheet (project files) got a pointer
  and a note that builds from #65 on show Holes. Panel/manifest link: follow-up in TODO G5.
- Measured: nothing measured.
- Next: fill §8 (folded input, Repair Folds and Re-run) when the fold-repair PR merges.
