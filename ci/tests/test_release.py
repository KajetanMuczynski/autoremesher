# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""ci/release.py (tag rule, zip checks, notes) and ci/check_linux_libs.py's decision."""
import os
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import check_linux_libs  # noqa: E402
import release  # noqa: E402

MANIFEST = """schema_version = "1.0.0"
id = "quadami"
version = "%s"
blender_version_min = "4.2.0"
platforms = ["%s"]
"""


def make_zip(folder, version, platform, build_id, drop=()):
    path = os.path.join(folder, release.zip_name(version, platform))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("blender_manifest.toml", MANIFEST % (version, platform))
        z.writestr("build-id.txt", build_id + "\n")
        z.writestr("bin/autoremesher-cli" + (".exe" if platform.startswith("windows") else ""), "x")
        for name in release.LICENSES:
            if name not in drop:
                z.writestr("licenses/" + name, "text")
    return path


class TagTest(unittest.TestCase):
    def test_release_and_prerelease(self):
        self.assertEqual(release.parse_tag("v0.1.0", "0.1.0"), ("0.1.0", False))
        self.assertEqual(release.parse_tag("v0.1.0-rc.1", "0.1.0"), ("0.1.0", True))
        self.assertEqual(release.parse_tag("v0.1.0-test.1", "0.1.0"), ("0.1.0", True))

    def test_refused(self):
        for tag in ("v0.1.1", "0.1.0", "v0.1", "v0.1.0+abc", "v01.1.0", "v0.1.0-"):
            with self.assertRaises(release.ReleaseError, msg=tag):
                release.parse_tag(tag, "0.1.0")
        with self.assertRaises(release.ReleaseError):
            release.parse_tag("v0.1.0", "0.1.0+abc")


class ZipTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.version = release.manifest_version()
        self.tag = "v%s-test.1" % self.version
        self.build_id = self.tag + " abc1234 2026-10-22"

    def tearDown(self):
        self.tmp.cleanup()

    def all_zips(self, **kw):
        for p in release.PLATFORMS:
            make_zip(self.dir, self.version, p, self.build_id, **kw)

    def test_good(self):
        self.all_zips()
        self.assertEqual(release.verify(self.tag, self.dir), self.build_id)
        out = os.path.join(self.dir, "out")
        text = release.notes(self.tag, self.dir, "abc1234" * 5 + "abcde", out, previous="4a49f82")
        self.assertIn("Pre-release", text)
        self.assertIn(self.build_id, text)
        self.assertNotIn("${", text)
        with open(os.path.join(out, "SHA256SUMS.txt"), encoding="utf-8") as f:
            sums = f.read().splitlines()
        self.assertEqual(len(sums), 3)
        for line in sums:
            digest, name = line.split("  ")
            self.assertIn("| `%s` | `%s` |" % (name, digest), text)

    def test_missing_platform(self):
        make_zip(self.dir, self.version, "linux-x64", self.build_id)
        make_zip(self.dir, self.version, "windows-x64", self.build_id)
        with self.assertRaises(release.ReleaseError):
            release.verify(self.tag, self.dir)

    def test_missing_license(self):
        self.all_zips(drop=("OpenMesh-LICENSE",))
        with self.assertRaisesRegex(release.ReleaseError, "OpenMesh"):
            release.verify(self.tag, self.dir)

    def test_build_id_without_tag(self):
        self.build_id = "abc1234 2026-10-22"
        self.all_zips()
        with self.assertRaisesRegex(release.ReleaseError, "build id"):
            release.verify(self.tag, self.dir)

    def test_wrong_platform_in_manifest(self):
        self.all_zips()
        # A Linux zip under the Windows name.
        os.remove(os.path.join(self.dir, release.zip_name(self.version, "windows-x64")))
        os.rename(make_zip(self.dir, self.version, "linux-x64", self.build_id),
                  os.path.join(self.dir, release.zip_name(self.version, "windows-x64")))
        make_zip(self.dir, self.version, "linux-x64", self.build_id)
        with self.assertRaisesRegex(release.ReleaseError, "platforms"):
            release.verify(self.tag, self.dir)


class NotesTest(unittest.TestCase):
    def test_full_release_needs_finished_notes(self):
        notes = os.path.join(release.RELEASES, release.manifest_version() + ".md")
        if not os.path.isfile(notes):
            with self.assertRaises(release.ReleaseError):
                release.version_notes(release.manifest_version(), False)
        # A pre-release goes out with whatever is there.
        self.assertIn("## What changed", release.version_notes(release.manifest_version(), True))


class LinuxLibsTest(unittest.TestCase):
    DYNAMIC = """ 0x0000000000000001 (NEEDED)             Shared library: [libstdc++.so.6]
 0x0000000000000001 (NEEDED)             Shared library: [libc.so.6]
"""

    def test_ok(self):
        versions = "  0x0010:   Name: GLIBC_2.28  Flags: none\n  Name: GLIBCXX_3.4.25\n  Name: CXXABI_1.3.11\n"
        self.assertEqual(check_linux_libs.problems(self.DYNAMIC, versions), [])

    def test_ubuntu_2404_build(self):
        versions = "Name: GLIBC_2.38  Flags: none\nName: GLIBCXX_3.4.32\n"
        self.assertEqual(sorted(check_linux_libs.problems(self.DYNAMIC, versions)),
                         ["needs GLIBCXX_3.4.32 (at most 3.4.25)", "needs GLIBC_2.38 (at most 2.28)"])

    def test_shared_tbb(self):
        dynamic = self.DYNAMIC + " 0x1 (NEEDED)             Shared library: [libtbb.so.12]\n"
        self.assertEqual(check_linux_libs.problems(dynamic, ""), ["needs libtbb.so.12"])


if __name__ == "__main__":
    unittest.main()
