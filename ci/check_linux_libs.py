#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""Fail unless a Linux program runs on every Linux that runs Blender 4.2.

    python3 ci/check_linux_libs.py <program>

Checks with readelf (binutils) that the program needs no shared library outside glibc and
libstdc++/libgcc, and no symbol version newer than glibc 2.28 or the libstdc++ of GCC 8
(GLIBCXX_3.4.25, CXXABI_1.3.11): the floor of Blender 4.2's own Linux builds. Catches a build
on a newer distro (Ubuntu 24.04 needs glibc 2.38 through C23's __isoc23_strtol) or a TBB
linked as a shared library. Standard library only.
"""
import re
import subprocess
import sys

ALLOWED_LIBS = {"libc.so.6", "libm.so.6", "libpthread.so.0", "libdl.so.2", "librt.so.1",
                "libstdc++.so.6", "libgcc_s.so.1", "ld-linux-x86-64.so.2"}
MAX_VERSION = {"GLIBC": (2, 28), "GLIBCXX": (3, 4, 25), "CXXABI": (1, 3, 11), "GCC": (8, 0)}


def problems(dynamic, versions):
    """dynamic: `readelf -d` output; versions: `readelf -V` output. Returns a list of strings."""
    found = []
    for lib in re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", dynamic):
        if lib not in ALLOWED_LIBS:
            found.append("needs %s" % lib)
    seen = set()
    for name, number in re.findall(r"Name: ([A-Z]+)_([0-9.]+)", versions):
        if name in MAX_VERSION and (name, number) not in seen:
            seen.add((name, number))
            if tuple(int(n) for n in number.split(".")) > MAX_VERSION[name]:
                found.append("needs %s_%s (at most %s)" % (name, number, ".".join(map(str, MAX_VERSION[name]))))
    return found


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    program = sys.argv[1]
    dynamic = subprocess.run(["readelf", "-d", program], capture_output=True, text=True, check=True).stdout
    versions = subprocess.run(["readelf", "-V", program], capture_output=True, text=True, check=True).stdout
    print("".join(line + "\n" for line in dynamic.splitlines() if "(NEEDED)" in line), end="")
    newest = {}
    for name, number in re.findall(r"Name: ([A-Z]+)_([0-9.]+)", versions):
        key = tuple(int(n) for n in number.split("."))
        if name in MAX_VERSION and key > newest.get(name, ()):
            newest[name] = key
    for name, key in sorted(newest.items()):
        print("newest %s: %s" % (name, ".".join(map(str, key))))
    found = problems(dynamic, versions)
    for p in sorted(found):
        print("ERROR: %s %s" % (program, p))
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
