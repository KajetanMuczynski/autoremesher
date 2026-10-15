#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Download the external part of the baseline corpus into <meshes>/downloads and
# verify checksums. All files come from github.com/odedstein/meshes pinned at
# one commit; per-object license and attribution are in meshes.tsv (and in the
# README-<name>.md files fetched alongside). Total ~170 MB.
#
#   ./fetch_meshes.sh <meshes-dir>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="${1:?usage: fetch_meshes.sh <meshes-dir>}/downloads"
mkdir -p "$dest"
commit=835213277571d625722d25880c9c3010c6f45a5a
base="https://raw.githubusercontent.com/odedstein/meshes/$commit/objects"
tail -n +2 "$here/meshes.tsv" | while IFS=$'\t' read -r file object sha license attribution; do
    if [ ! -f "$dest/$file" ] || ! echo "$sha  $dest/$file" | sha256sum -c --status; then
        echo "fetching $object/$file"
        curl -sSfL --retry 3 -o "$dest/$file" "$base/$object/$file"
        curl -sSfL --retry 3 -o "$dest/README-$object.md" "$base/$object/README.md"
    fi
    echo "$sha  $dest/$file" | sha256sum -c --quiet
done
echo "all meshes present and verified in $dest"
