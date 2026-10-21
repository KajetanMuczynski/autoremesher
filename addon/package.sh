#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
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

# Build the remesher CLI and the installable add-on zip with the CLI bundled
# for this machine, then print the zip's path. Linux and macOS; Windows builds
# come from CI (the addon jobs of .github/workflows/ci.yml). Run from anywhere:
#
#     sh addon/package.sh
#
# The CLI is built with CMake in build/cli (Release, nice -n 10, two jobs:
# the laptop runs hot), and not while another build is running. Rebuilds are
# incremental.
set -eu

repo=$(cd "$(dirname "$0")/.." && pwd)
build_dir="$repo/build/cli"
prefix="$repo/build/cli-install"

if pgrep -a 'cc1plus|lto1|make|ninja' >/dev/null; then
    echo "Another build is running; not starting the CLI build now:" >&2
    pgrep -a 'cc1plus|lto1|make|ninja' >&2
    exit 1
fi
echo "Building the CLI in $build_dir (nice -n 10, 2 jobs)..." >&2
mkdir -p "$build_dir"
{
    cmake -S "$repo" -B "$build_dir" -DCMAKE_BUILD_TYPE=Release \
        && nice -n 10 cmake --build "$build_dir" --parallel 2 \
        && cmake --install "$build_dir" --prefix "$prefix"
} >"$build_dir/build.log" 2>&1 || {
    echo "CLI build failed; see $build_dir/build.log" >&2
    exit 1
}

python3 "$repo/addon/package.py" --cli-prefix "$prefix"
