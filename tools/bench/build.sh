#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Build the Qt app and the Qt-free bench drivers from this checkout (Ubuntu 24.04, x86_64).
#
#   tools/bench/build.sh <work-dir>
#
# Environment:
#   AR_SOURCE_DIR=<dir>   tree to build instead of this checkout (e.g. a pristine upstream clone)
#   SKIP_APT=1            do not install system packages
#   JOBS=<n>              parallel compile jobs (default: all cores; use 2 on a laptop)
#
# Produces in <work-dir>:
#   app/autoremesher                   Qt app (qmake, release), headless CLI
#   build/ar_bench                     Qt-free driver, core as it is in the source tree
#   build/ar_bench_probe               same core + bench/probes.patch (counters/timers only)
#   build/ar_bench_probe_cholmod       probes + bench/cholmod-experiment.patch (P2 experiment)
# The probe builds are skipped with a warning when the patches no longer apply (they were
# written against upstream 4a49f82, the commit the baseline measured); the CHOLMOD build is
# skipped when cholmod.h is missing.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
src="$(cd "${AR_SOURCE_DIR:-$here/../..}" && pwd)"
work="$(mkdir -p "${1:?usage: build.sh <work-dir>}" && cd "$1" && pwd)"
jobs="${JOBS:-$(nproc)}"

# 1. System packages. README lists libqt5multimedia5-dev, which does not exist on
#    Ubuntu 24.04 (and the .pro does not use QtMultimedia), so it is left out.
if [ "${SKIP_APT:-0}" != 1 ]; then
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential cmake git \
        qt5-qmake qtbase5-dev libqt5opengl5-dev qttools5-dev-tools libqt5svg5-dev libtbb-dev libgl1-mesa-dev \
        libsuitesparse-dev libopenblas-dev linux-tools-generic python3-venv
fi

# 2. Qt app, out of tree.
mkdir -p "$work/app"
(cd "$work/app" && qmake "$src/autoremesher.pro" && make -j"$jobs")

# 3. Pristine Qt-free driver (same sources and release flags as the .pro).
cmake -S "$here/bench" -B "$work/build-pristine" -DAR_SOURCE_DIR="$src"
cmake --build "$work/build-pristine" -j"$jobs"
mkdir -p "$work/build"
ln -sf "$work/build-pristine/ar_bench" "$work/build/ar_bench"

# 4. Patched copies for the probe and CHOLMOD builds (source tree untouched).
copy_patched() {  # <variant> <patch>...
    local dest="$work/autoremesher-$1"; shift
    rm -rf "$dest"; mkdir -p "$dest"
    cp -a "$src/src" "$src/include" "$src/thirdparty" "$dest/"
    local p
    for p in "$@"; do
        if ! patch -s --dry-run -d "$dest" -p1 < "$p" >/dev/null; then
            echo "warning: $(basename "$p") does not apply to $src; skipping this build" >&2
            return 1
        fi
        patch -s -d "$dest" -p1 < "$p"
    done
}
if copy_patched probe "$here/bench/probes.patch"; then
    cmake -S "$here/bench" -B "$work/build-probe" -DAR_SOURCE_DIR="$work/autoremesher-probe" -DAR_BENCH_PROBE=ON
    cmake --build "$work/build-probe" -j"$jobs"
    ln -sf "$work/build-probe/ar_bench_probe" "$work/build/ar_bench_probe"
fi
if [ ! -f /usr/include/suitesparse/cholmod.h ]; then
    echo "warning: cholmod.h not found (libsuitesparse-dev); skipping the CHOLMOD build" >&2
elif copy_patched cholmod "$here/bench/probes.patch" "$here/bench/cholmod-experiment.patch"; then
    cmake -S "$here/bench" -B "$work/build-cholmod" -DAR_SOURCE_DIR="$work/autoremesher-cholmod" \
        -DAR_BENCH_PROBE=ON -DAR_USE_CHOLMOD=ON
    cmake --build "$work/build-cholmod" -j"$jobs"
    ln -sf "$work/build-cholmod/ar_bench_probe_cholmod" "$work/build/ar_bench_probe_cholmod"
fi

# 5. Python for metrics and mesh generation.
python3 -m venv "$work/venv"
"$work/venv/bin/pip" install -q numpy scipy libigl manifold3d scikit-image
echo "Built in $work. The headless CLI needs QT_QPA_PLATFORM=offscreen on a machine without a display."
