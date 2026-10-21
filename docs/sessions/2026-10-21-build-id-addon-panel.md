# 2026-10-21 · Claude (cloud thread) · Build id in the add-on panel
- Repos/commits: core 7998e98 (master)
- Did: one build id, worked out only in `cmake/BuildId.cmake` (short commit, `-dirty`, commit date;
  `-DAUTOREMESHER_BUILD_ID=` overrides; `dev` without git), regenerated on every build so it follows
  commits without reconfiguring and only `src/cli/main.cpp` recompiles. `autoremesher-cli --version`
  prints it; `cmake --install` puts `build-id.txt` in the prefix; `addon/package.py` copies it into the
  zip. The panel and the preferences show it; a different id from the remesher shows both in red.
  CI PR runs label the merge-commit build `pr<N> <head>+master`.
- Found: Blender 4.5 accepts semver build metadata in the manifest version (`RE_MANIFEST_SEMVER`), so
  the id could also go into the extension list later; not done (ids with spaces would need a second form).
- Measured: nothing measured (no quality code touched).
- Next: none.
