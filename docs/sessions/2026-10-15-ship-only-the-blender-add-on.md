# 2026-10-15 · Claude (cloud thread "Supply-chain audit") · Ship only the Blender add-on
- Repos/commits: fork master after PR #24 → PR (ci(ci): ship only the Blender add-on in releases, draft).
- Did: on Kajetan's decision, removed upstream's `release.yml` (AppImage, Windows Qt zip, DMG) and its AppImage metadata in `ci/`; tags now run `ci.yml`. Added a macOS (Apple silicon) add-on build: static oneTBB, macOS 11.2 target, `otool` check, installed into Blender 5.2.2 from its DMG. The Windows and macOS zips are uploaded as `addon-<platform>`.
- Found: removes the audit's AppImage-tool, Qt 5.15.2 and Homebrew `qt@5` findings. Static oneTBB also builds on Linux (checked locally).
- Next: portable Linux add-on zip (static oneTBB and libstdc++, glibc 2.28 floor); try the macOS zip on a real Mac (Gatekeeper).
