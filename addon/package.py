# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 AutoRemesher fork contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Build the installable Blender extension zip. Python 3.11+, any OS.

    python addon/package.py [--cli-prefix PREFIX [--platform TAG]] [--output DIR]

Without --cli-prefix the zip holds only the add-on, which then needs the path
to a remesher in its preferences, and installs on every platform.

With --cli-prefix (a `cmake --install` prefix of this repository's CMake
build) the zip also holds PREFIX/bin/autoremesher-cli[.exe] and the licenses
in PREFIX/licenses, and its manifest names the one platform the program was
built for, so Blender refuses it elsewhere. Platform tags are Blender's
(https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html):
windows-x64, windows-arm64, linux-x64, macos-x64, macos-arm64. The default is
the machine running this script.

Prints the zip's path.
"""

import argparse
import os
import platform
import re
import subprocess
import sys
import tomllib
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PACKAGE = os.path.join(HERE, "autoremesher_blender")
PLATFORMS = ("windows-x64", "windows-arm64", "linux-x64", "macos-x64", "macos-arm64")
CLI_NAME = "autoremesher-cli"


def host_platform():
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(platform.system())
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine)
    tag = "%s-%s" % (system, arch)
    if tag not in PLATFORMS:
        sys.exit("unknown platform %s/%s; pass --platform" % (platform.system(), machine))
    return tag


def manifest_for(text, platform_tag):
    """The manifest text, with `platforms` set when a program is bundled."""
    if platform_tag is None:
        return text
    if re.search(r"^platforms\s*=", text, re.M):
        sys.exit("blender_manifest.toml already sets platforms; package.py sets it per zip")
    line = 'platforms = ["%s"]\n' % platform_tag
    text, count = re.subn(r"^(blender_version_min\s*=.*\n)", lambda m: m.group(1) + line, text, flags=re.M)
    if count != 1:
        sys.exit("blender_manifest.toml has no blender_version_min line")
    return text


def source_note(website):
    """GPL: say where the source of the bundled program is."""
    commit = os.environ.get("SOURCE_COMMIT", "")
    if not commit:
        try:
            commit = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True,
                                    text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            commit = ""
    note = ("bin/%s is free software under the GNU General Public License,\n"
            "version 3 or later (licenses/LICENSE). Its source code, with build\n"
            "instructions, is at %s" % (CLI_NAME, website))
    if commit:
        note += "\n(commit %s)" % commit
    return note + ".\nThe other files in licenses/ cover the libraries compiled into it.\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cli-prefix", help="cmake --install prefix holding bin/%s" % CLI_NAME)
    parser.add_argument("--platform", choices=PLATFORMS, help="Blender platform tag (default: this machine)")
    parser.add_argument("--output", default=os.path.join(REPO, "build", "addon"), help="folder for the zip")
    args = parser.parse_args()
    if args.platform and not args.cli_prefix:
        parser.error("--platform needs --cli-prefix")

    manifest_path = os.path.join(PACKAGE, "blender_manifest.toml")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_text = f.read()
    manifest = tomllib.loads(manifest_text)

    platform_tag = None
    files = []  # (path in the zip, path on disk)
    if args.cli_prefix:
        platform_tag = args.platform or host_platform()
        program = CLI_NAME + (".exe" if platform_tag.startswith("windows") else "")
        program_path = os.path.join(args.cli_prefix, "bin", program)
        if not os.path.isfile(program_path):
            sys.exit("no %s; run cmake --install <build> --prefix %s first" % (program_path, args.cli_prefix))
        files.append(("bin/" + program, program_path))
        licenses = os.path.join(args.cli_prefix, "licenses")
        if not os.path.isfile(os.path.join(licenses, "LICENSE")):
            sys.exit("no license files in %s" % licenses)
        for name in sorted(os.listdir(licenses)):
            files.append(("licenses/" + name, os.path.join(licenses, name)))
    for name in sorted(os.listdir(PACKAGE)):
        if name.endswith(".py"):
            files.append((name, os.path.join(PACKAGE, name)))

    manifest_out = manifest_for(manifest_text, platform_tag)
    tomllib.loads(manifest_out)  # still valid TOML

    suffix = "-" + platform_tag if platform_tag else ""
    os.makedirs(args.output, exist_ok=True)
    zip_path = os.path.join(args.output, "%s-%s%s.zip" % (manifest["id"], manifest["version"], suffix))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        # Blender wants blender_manifest.toml at the root of the zip.
        archive.writestr("blender_manifest.toml", manifest_out)
        for arcname, path in files:
            info = zipfile.ZipInfo.from_file(path, arcname)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as f:
                archive.writestr(info, f.read())
        if platform_tag:
            archive.writestr("licenses/SOURCE.txt", source_note(manifest["website"]))
    print(zip_path)


if __name__ == "__main__":
    main()
