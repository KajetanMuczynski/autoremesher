# 2026-10-21 · cloud thread · Rename to Quadami
- Repos/commits: master 4e9cdc7; script and inventory in project files `autoremesher/rename/`
- Did: renamed user-visible AutoRemesher strings to Quadami with a reviewed, per-file script (not a blanket sed):
  copyright holder of our own files, doc titles, temp-folder prefixes, add-on package folder
  `addon/autoremesher_blender` -> `addon/quadami`, fork URLs (repo renamed to KajetanMuczynski/quadami).
  Kept: C++ namespace, `autoremesher-cli`/`autoremesher_core` targets (`ab.py` builds old refs by target name),
  `AUTOREMESHER_*` options and env var, report schema ids, the Qt app, upstream attribution, history.
- Found: `src/AutoRemesher/surfaceprojector.cpp` carries upstream's `closestPointOnTriangle()` (quadextractor.cpp,
  50 lines verbatim) without Jeremy HU's credit; added it. 23 upstream files we changed now carry a
  "Modifications Copyright ... Quadami contributors" line under his MIT notice; 66 unchanged ones are untouched.
- Measured: nothing measured (add-on unit tests pass; zip name unchanged, `quadami-0.1.0.zip`).
- Next: rebase #57/#58 if they conflict (headers, folder move).
