# 2026-10-22 · Claude (cloud, thread "Release workflow for 0.1") · Linux install docs
- Repos/commits: quadami master c2ffd24
- Did: install docs (README, USER-GUIDE §2, BUILDING.md) now point Linux users to the CI artifact
  `addon-linux-x64` (built in AlmaLinux 8 since #77) and state glibc 2.28+ instead of Ubuntu 24.04 /
  glibc 2.38; snap Blender notes (`/snap/bin/blender`); BUILDING.md gained the portable build
  (`ci/build_linux_portable.sh`).
- Found: the old text was written before #77, when the only Linux zip was a native Ubuntu 24.04 build.
- Measured: nothing measured (numbers from #77: the AlmaLinux-built CLI needs at most GLIBC 2.14).
- Next: none.
