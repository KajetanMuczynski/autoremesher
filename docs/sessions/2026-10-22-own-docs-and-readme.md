# 2026-10-22 · Claude (cloud thread "Own Quadami docs and README") · Quadami's own README and docs
- Repos/commits: master 0e9bec8; docs only, no code or build change.
- Did: inventoried every upstream link and use of the name AutoRemesher outside `thirdparty/`, the
  core's code names and the session history (README, docs, add-on texts and manifest, CLAUDE.md,
  CHANGELOGS, notices, CMake, CI, package scripts). Rewrote README.md as Quadami's own (what it is, who
  it is for, status, install per system, limits, differences, docs, build, license, Origin and credits;
  upstream links only in Origin and credits); new docs/BUILDING.md (Linux, Windows, macOS, tests, the
  Qt app moved out of the README); USER-GUIDE §2 per system (where to get the zip today, install,
  where Blender keeps it, remove, scripts, macOS Gatekeeper); docs/README.md split into users,
  contributors, plan; addon/README.md intro and stale status; Quadami section on top of CHANGELOGS.md;
  THIRD_PARTY_NOTICES gained libQEx and OpenMesh, vendored in #72 but missing from the table.
- Found: kept on purpose: LICENSE-MIT-upstream, MIT file headers, AUTHORS, CONTRIBUTORS,
  ACKNOWLEDGEMENTS.html (upstream's About-box list), upstream's changelog, the `autoremesher-cli`,
  `AUTOREMESHER_*` and `AutoRemesher` code names (rename inventory of #59), the desktop app's own
  name and its qmake metadata (`autoremesher.pro` QMAKE_TARGET_*: not shipped), CLAUDE.md's fork
  notes, history in sessions/REFERENCE/TODO. The manifest's website already points to the fork.
- Measured: nothing measured.
- Next: screenshots of the panel; a release workflow so users get a zip without a GitHub account;
  `quadami-update.sh` into the repo; repository description and topics on GitHub.
