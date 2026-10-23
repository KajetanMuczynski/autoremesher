<!-- Release notes template, filled in by ci/release.py (string.Template, $$name is a
     literal $). The hand-written part comes from docs/releases/<version>.md. -->
${prerelease_note}Quadami ${version}: automatic quad remeshing for Blender 4.2 or newer, as an extension zip with
the remesher program inside. Free software under the GNU GPL, version 3 or later.

${notes}

## Download

Pick the zip for your system. Do **not** unpack it: Blender installs the zip itself
(**Edit > Preferences > Get Extensions**, the **⌄** menu top right, **Install from Disk...**, then
restart Blender). The [user guide](https://github.com/KajetanMuczynski/quadami/blob/${tag}/docs/USER-GUIDE.md)
explains every setting and warning.

| System | File | SHA-256 |
|---|---|---|
${downloads}

- **Linux x64:** any distribution with glibc 2.28 or newer (the floor of Blender 4.2 itself; e.g.
  Ubuntu 20.04+, Debian 10+, Fedora 29+, RHEL/Rocky/Alma 8+). Built on AlmaLinux 8, checked to need
  nothing newer.
- **Windows x64:** Windows 10 or 11. The remesher is **not code-signed**. Blender unpacks it itself, so
  Windows SmartScreen should not ask; if your antivirus quarantines `autoremesher-cli.exe`, restore it
  or build from source.
- **macOS, Apple silicon (M1 or newer), macOS 11.2+: experimental, untested.** It passes the
  automatic tests in Blender without a window, but nobody has tried it on a real Mac yet, and the
  remesher is **not signed or notarized by Apple**. Installed through Blender it should run; if macOS
  says it "cannot be opened because the developer cannot be verified", see the user guide, §2
  (macOS). Intel Macs: build from source.

Check a download with `sha256sum -c SHA256SUMS.txt` (Linux), `shasum -a 256 -c SHA256SUMS.txt`
(macOS) or `Get-FileHash <zip>` (Windows PowerShell), against the table above. To check that a zip
was built by this project's GitHub Actions from the commit below (with the
[GitHub CLI](https://cli.github.com)): `gh attestation verify <zip> -R KajetanMuczynski/quadami`.

**Build line.** The bottom of the Quadami panel shows `Add-on build ${build_id}`. Put that line in
every bug report.

## Source and licenses

Built by GitHub Actions from commit `${commit}` (tag `${tag}`):
[source](https://github.com/KajetanMuczynski/quadami/tree/${tag}),
[changes since ${previous}](https://github.com/KajetanMuczynski/quadami/compare/${previous}...${tag}).
Each zip holds `licenses/`: the GPL (Quadami and libQEx), upstream AutoRemesher's MIT notice
(Jeremy Hu), and the licenses of OpenMesh, oneTBB, Eigen, meshoptimizer, isotropicremesher and
tinyobjloader compiled into the remesher, plus `SOURCE.txt` naming the source commit.
