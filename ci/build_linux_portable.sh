#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
#
# Builds the Linux x64 core, CLI and core tests the way the add-on zip ships them, so the
# zip runs on any Linux that runs Blender 4.2 (glibc 2.28, the floor Blender itself builds
# against): inside AlmaLinux 8 (glibc 2.28) with GCC 13 from gcc-toolset, oneTBB built from
# source and linked statically (AUTOREMESHER_BUNDLED_TBB). gcc-toolset links the parts of
# libstdc++ newer than the system's GCC 8 into the program, so autoremesher-cli needs only
# glibc 2.28 and libstdc++.so.6 of GCC 8 or newer (ci/check_linux_libs.py checks both).
#
#   ci/build_linux_portable.sh [BUILD_ID]
#
# Run from the repository root on a Linux host with Docker; writes build/cli (build tree)
# and build/cli-install (install prefix for addon/package.py), owned by the calling user.
# BUILD_ID: as -DAUTOREMESHER_BUILD_ID (empty: from git, cmake/BuildId.cmake).
# DOCKER_RUN_ARGS: extra `docker run` arguments (e.g. a proxy's CA bundle mounted in).
# Used by ci.yml (job addon, linux-x64) on every PR and tag; works the same on a laptop.
set -eu

# AlmaLinux 8.10, pinned by digest (bump by hand, CLAUDE.md "Dependency updates").
IMAGE=almalinux:8.10-20261002@sha256:8b469a3a78515e8a18ea8fc727e6a3679e1d0c5ba6f58d5b30be3d0d9b86cffe
BUILD_ID=${1:-}
JOBS=${JOBS:-4}

# Two steps: packages as root, then the build as the calling user, so build/ is not
# owned by root on the host. HOME=/tmp: git and CMake want a writable home. The checkout
# is mounted at its own path, so ctest on the host finds the build tree's absolute paths.
container=quadami-linux-build-$$
# shellcheck disable=SC2086  # DOCKER_RUN_ARGS holds several arguments
docker run -d --name "$container" --network host -v "$PWD:$PWD" -w "$PWD" ${DOCKER_RUN_ARGS:-} \
    -e https_proxy -e HTTPS_PROXY -e http_proxy -e HTTP_PROXY -e no_proxy -e NO_PROXY \
    "$IMAGE" sleep infinity > /dev/null
trap 'docker rm -f "$container" > /dev/null' EXIT
docker exec "$container" dnf install -y -q gcc-toolset-13-gcc-c++ cmake git make
docker exec -u "$(id -u):$(id -g)" -e HOME=/tmp -e BUILD_ID="$BUILD_ID" -e JOBS="$JOBS" "$container" \
    scl enable gcc-toolset-13 -- sh -euc '
        git config --global --add safe.directory "$PWD"
        g++ --version | head -n 1; cmake --version | head -n 1; ldd --version | head -n 1
        cmake -S . -B build/cli -DCMAKE_BUILD_TYPE=Release -DAUTOREMESHER_BUILD_TESTS=ON \
            -DAUTOREMESHER_BUNDLED_TBB=ON \
            "-DAUTOREMESHER_BUILD_ID=$BUILD_ID"
        cmake --build build/cli --parallel "$JOBS"
        cmake --install build/cli --prefix build/cli-install'
