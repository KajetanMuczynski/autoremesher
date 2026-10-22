# 2026-10-22 · Claude (cloud thread "Release workflow for 0.1") · Draft releases from tags
- Repos/commits: master a01823c; CI, packaging scripts and docs only, no core or add-on code change.
- Did: Linux add-on zip built the way it ships on every PR (AlmaLinux 8 container,
  `ci/build_linux_portable.sh`, static oneTBB) and uploaded as `addon-linux-x64`; `ci/check_linux_libs.py`
  fails a build needing more than glibc 2.28 / GCC 8 libstdc++. Job `release (draft)` in `ci.yml` on
  `v*` tags, `ci/release.py` (tag vs manifest version, zip checks, notes, `SHA256SUMS.txt`), notes
  template and 0.1.0 skeleton in `docs/releases/`, procedure and checklist in `docs/RELEASING.md`,
  tests in `ci/tests/test_release.py`.
- Found: a native Ubuntu 24.04 build needs GLIBC_2.38 and GLIBCXX_3.4.32 (measured with the new check),
  so the old cloud-built Linux zips ran only on 24.04+. Decided: manifest version = release version,
  bumped only in a release PR; no `+sha` (build line carries the commit); extension id stays `quadami`.
- Measured: nothing on remeshing output.
- Next: release PR for 0.1.0 after the vines fix and its warnings; attestations PR; manual corpus
  release check workflow for Windows/macOS; tag ruleset before anyone else gets write access.
