<!--
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (C) 2026 Quadami contributors
-->

# Releasing the add-on

What ships is the Blender extension zip, one per platform: `linux-x64`, `windows-x64`,
`macos-arm64`. A release is a GitHub release with those three zips, `SHA256SUMS.txt` and notes. It
is made by CI from a tag and always starts as a **draft**: nothing is public until Kajetan presses
**Publish release** on GitHub.

## How it works

- Pushing a tag `v<version>` or `v<version>-<suffix>` runs the normal `ci` workflow on the tagged
  commit (`.github/workflows/ci.yml`): every check a PR gets, with all three add-on jobs, which
  build, test and upload `addon-<platform>`.
- Its last job, **release (draft)**, runs only when **CI passed** is green. `ci/release.py` checks
  that the tag matches the manifest version (`addon/quadami/blender_manifest.toml`), that the three
  zips carry that version, their own platform, the program, every license file and the same build
  id naming the tag (`v0.1.0 abc1234 2026-11-02`, shown in the panel's build line), and writes the
  notes from [releases/TEMPLATE.md](releases/TEMPLATE.md) and `releases/<version>.md`. Then it
  creates the draft release, or updates the draft of a re-run. A published release is never touched.
- A suffix (`v0.1.0-rc.1`, `v0.1.0-test.1`) makes a **pre-release**; its notes file may be missing
  or unfinished. A plain `v0.1.0` needs `releases/0.1.0.md` with the sections *What changed*,
  *Warnings in the panel* and *Known limits* and no "TBD".
- A macOS job that GitHub drops for want of a runner turns **CI passed** red and skips the release;
  `rerun-dropped.yml` re-runs it (and the release job) up to attempt 3. After that: Actions > the
  tag's run > **Re-run failed jobs**. Any real failure leaves no release.
- The Linux zip is built in an AlmaLinux 8 container (`ci/build_linux_portable.sh`) and
  `ci/check_linux_libs.py` fails it if it needs anything newer than glibc 2.28 and GCC 8's libstdc++
  (the floor of Blender 4.2 itself), so it runs on Ubuntu 20.04+, Debian 10+, RHEL 8+ and the rest.
  Every PR builds it the same way, so what ships is what was tested.

## Versions

- The manifest version is the release version, `MAJOR.MINOR.PATCH`, and changes only in a release
  PR. While the major number is 0, the minor goes up for a release with new features or changed
  output, the patch for fixes only.
- Test builds between releases keep the last version; the build line in the panel tells them apart
  (`pr77 abc1234+master`, `abc1234 2026-11-03`, or `v0.1.0 ...` for the release itself).
- Not `0.1.0+<commit>` in the manifest: Blender would show it but every build would need its own
  manifest edit, and Blender 4.2's version check was not shown to accept build metadata. The build
  line already carries the commit.
- The extension id stays `quadami` (`bl_ext.user_default.quadami`): a new zip replaces the old one in
  place, and a renamed id would leave two add-ons installed side by side.

## Release checklist

Copy into the release PR's description and tick each line there.

1. **Gates.**
   - [ ] master CI green on the commit to tag (Actions > ci, branch master).
   - [ ] TARGETS release check ([TARGETS.md](TARGETS.md) §2.5, §5 "Releases"): the structural gates
         H1–H8 hold on every corpus run and replicate (`tools/bench/ab.py run <ref> --replicates 5`,
         plus `--set closed`), and the §3.2 validity numbers are no worse than the previous release's
         (the 0.x ratchet; for the first release, no worse than master of 2026-10-22, `0e9bec8`).
         Linux in the cloud; Windows and macOS have no corpus runner yet (gap, see below).
   - [ ] The changes this release promises are merged. For 0.1.0 (Kajetan, 2026-10-22): the
         thin-parts (vines) fix and its panel warnings.
2. **Real-machine checks** (CI runs Blender without a window): install the master zip from CI on
   Kajetan's Linux laptop and remesh a sculpt; Windows and a Mac when one is at hand (unsigned
   program: SmartScreen and Gatekeeper behaviour are untested, write down what happened).
3. **Release PR** (`docs(docs): release <version>`): bump `version` in
   `addon/quadami/blender_manifest.toml`, write `docs/releases/<version>.md` (no TBD left), add the
   version's section to `CHANGELOGS.md`, point the install docs (README, USER-GUIDE §2) to the
   Releases page. Merge after CI is green.
4. **Optional dress rehearsal**: tag the merge commit `v<version>-rc.1` and check the draft
   pre-release (zips, notes, build line after installing one zip). Delete that draft and tag after.
5. **Tag**: `git tag -a v<version> -m "Quadami <version>" <merge commit>` and
   `git push origin v<version>`. Wait for the run's **release (draft)** job.
6. **Review the draft** on GitHub > Releases: three zips plus `SHA256SUMS.txt`, notes read well, the
   build line names the tag. Install one zip from the draft.
7. **Publish** (Kajetan only). A mistake found later: publish a new patch version; never replace
   the assets of a published release.

## Gaps (not done by the workflow)

- **No corpus release check in CI.** TARGETS §2.5 asks for the corpus × 6 on all three platforms
  (about 3 CPU hours each); only Linux can run it today, by hand in the cloud. A manual workflow
  for it is a follow-up.
- **No build attestations** (supply-chain audit finding 15): `actions/attest-build-provenance` needs
  a pinned commit of a new action, added in its own PR.
- **No tag ruleset** (TODO.md parked table): anyone with write access can push a `v*` tag. Only
  Kajetan has write access today, and the job makes drafts only. Before other people get write
  access, add a tag ruleset for `v*` (Settings > Rules > Rulesets > New tag ruleset).
- **Unsigned programs**: no Apple notarization or Windows code signing (both need paid
  certificates). The notes say so.
- No "update available" check in the add-on (not planned for 0.x).
