#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""Checks and assembles a GitHub release of the Blender add-on from a tag's ci run.

    python3 ci/release.py check-tag <tag>
    python3 ci/release.py verify <tag> <zip-dir>
    python3 ci/release.py notes <tag> <zip-dir> <commit> <out-dir>

Called by the job "release" in .github/workflows/ci.yml after every other job of a tag run
succeeded; docs/RELEASING.md is the procedure around it.

check-tag: the tag must be v<version> or v<version>-<suffix>, where <version> is the add-on
manifest's (addon/quadami/blender_manifest.toml); with a suffix it is a pre-release. A full
release needs its notes, docs/releases/<version>.md, with every required section and no "TBD".
Writes version= and prerelease= to GITHUB_OUTPUT when set.

verify: <zip-dir> must hold exactly the zips of PLATFORMS, each with that version, its own
platform, the bundled program, a build id naming the tag and the license files of LICENSES.

notes: writes <out-dir>/notes.md (docs/releases/TEMPLATE.md filled in) and
<out-dir>/SHA256SUMS.txt (sha256sum format). Standard library only, Python 3.11+.
"""
import hashlib
import os
import re
import string
import subprocess
import sys
import tomllib
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO, "addon", "quadami", "blender_manifest.toml")
RELEASES = os.path.join(REPO, "docs", "releases")
UPSTREAM_FORK_POINT = "4a49f82"  # huxingyi/autoremesher v1.2.0, where the fork starts
PLATFORMS = ("linux-x64", "windows-x64", "macos-arm64")
LICENSES = ("LICENSE", "LICENSE-MIT-upstream", "SOURCE.txt", "OpenMesh-LICENSE", "libQEx-README.md",
            "libQEx-PATCHES.md", "oneTBB-LICENSE.txt", "eigen-COPYING.MPL2", "meshoptimizer-LICENSE.md",
            "isotropicremesher-LICENSE", "tinyobjloader-LICENSE.txt")
SECTIONS = ("## What changed", "## Warnings in the panel", "## Known limits")
SEMVER = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"


class ReleaseError(Exception):
    pass


def manifest_version():
    with open(MANIFEST, "rb") as f:
        return tomllib.load(f)["version"]


def parse_tag(tag, version):
    """Returns (version, prerelease?) or raises ReleaseError."""
    if not re.fullmatch(SEMVER, version):
        raise ReleaseError("manifest version %r is not MAJOR.MINOR.PATCH" % version)
    m = re.fullmatch(r"v(%s)(-[0-9A-Za-z.-]+)?" % SEMVER, tag)
    if not m:
        raise ReleaseError("tag %r is not v<MAJOR.MINOR.PATCH>[-<suffix>]" % tag)
    if m.group(1) != version:
        raise ReleaseError("tag %s does not match the manifest version %s; bump "
                           "addon/quadami/blender_manifest.toml in a PR first" % (tag, version))
    return version, m.group(5) is not None


def version_notes(version, prerelease):
    """The hand-written part of the notes, docs/releases/<version>.md."""
    path = os.path.join(RELEASES, version + ".md")
    if not os.path.isfile(path):
        if prerelease:
            return ("## What changed\n\nTest build of %s; there are no release notes for it yet.\n"
                    % version)
        raise ReleaseError("no %s; a release needs its notes" % os.path.relpath(path, REPO))
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not prerelease:
        missing = [s for s in SECTIONS if not re.search(r"^%s\s*$" % re.escape(s), text, re.M)]
        if missing:
            raise ReleaseError("%s lacks the sections %s" % (os.path.relpath(path, REPO), ", ".join(missing)))
        if re.search(r"\bTBD\b", text):
            raise ReleaseError("%s still says TBD" % os.path.relpath(path, REPO))
    # The file's own title line is replaced by the release's.
    return re.sub(r"\A# .*\n+", "", text).rstrip() + "\n"


def zip_name(version, platform):
    return "quadami-%s-%s.zip" % (version, platform)


def verify(tag, zip_dir):
    version, _ = parse_tag(tag, manifest_version())
    expected = {zip_name(version, p): p for p in PLATFORMS}
    found = sorted(n for n in os.listdir(zip_dir) if n.endswith(".zip"))
    if found != sorted(expected):
        raise ReleaseError("expected zips %s, found %s" % (sorted(expected), found))
    ids = {}
    for name, platform in sorted(expected.items()):
        with zipfile.ZipFile(os.path.join(zip_dir, name)) as z:
            names = set(z.namelist())
            manifest = tomllib.loads(z.read("blender_manifest.toml").decode("utf-8"))
            if manifest["id"] != "quadami" or manifest["version"] != version:
                raise ReleaseError("%s: manifest id/version %s %s" % (name, manifest["id"], manifest["version"]))
            if manifest.get("platforms") != [platform]:
                raise ReleaseError("%s: manifest platforms %s" % (name, manifest.get("platforms")))
            program = "bin/autoremesher-cli" + (".exe" if platform.startswith("windows") else "")
            if program not in names:
                raise ReleaseError("%s: no %s" % (name, program))
            missing = [n for n in LICENSES if "licenses/" + n not in names]
            if missing:
                raise ReleaseError("%s: no licenses/%s" % (name, ", licenses/".join(missing)))
            build_id = z.read("build-id.txt").decode("utf-8").strip()
            if not build_id.startswith(tag + " "):
                raise ReleaseError("%s: build id %r does not name the tag %s" % (name, build_id, tag))
            ids[platform] = build_id
    if len(set(ids.values())) != 1:
        raise ReleaseError("the zips have different build ids: %s" % ids)
    return ids[PLATFORMS[0]]


def previous_release(tag, commit):
    """The newest full-release tag before this one, else the upstream fork point."""
    try:
        return subprocess.run(["git", "-C", REPO, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*",
                               "--exclude", "*-*", "--exclude", tag, commit + "^"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return UPSTREAM_FORK_POINT


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def notes(tag, zip_dir, commit, out_dir, previous=None):
    version, prerelease = parse_tag(tag, manifest_version())
    build_id = verify(tag, zip_dir)
    sums = [(sha256(os.path.join(zip_dir, zip_name(version, p))), zip_name(version, p), p) for p in PLATFORMS]
    rows = "\n".join("| %s | `%s` | `%s` |" % (p, name, digest) for digest, name, p in sums)
    with open(os.path.join(RELEASES, "TEMPLATE.md"), encoding="utf-8") as f:
        template = string.Template(re.sub(r"\A<!--.*?-->\n", "", f.read(), flags=re.S))
    text = template.substitute(
        version=version, tag=tag, commit=commit, build_id=build_id, downloads=rows,
        notes=version_notes(version, prerelease).rstrip(),
        previous=previous or previous_release(tag, commit),
        prerelease_note=("> **Pre-release / test build.** Not for general use.\n\n" if prerelease else ""))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "notes.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(out_dir, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        f.writelines("%s  %s\n" % (digest, name) for digest, name, _ in sums)
    return text


def main():
    args = sys.argv[1:]
    try:
        if len(args) == 2 and args[0] == "check-tag":
            version, prerelease = parse_tag(args[1], manifest_version())
            version_notes(version, prerelease)
            print("version=%s\nprerelease=%s" % (version, str(prerelease).lower()))
            output = os.environ.get("GITHUB_OUTPUT")
            if output:
                with open(output, "a", encoding="utf-8") as f:
                    f.write("version=%s\nprerelease=%s\n" % (version, str(prerelease).lower()))
        elif len(args) == 3 and args[0] == "verify":
            print("build id: %s" % verify(args[1], args[2]))
        elif len(args) == 5 and args[0] == "notes":
            print(notes(*args[1:]))
        else:
            sys.exit(__doc__)
    except ReleaseError as e:
        sys.exit("ERROR: %s" % e)


if __name__ == "__main__":
    main()
