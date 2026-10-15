#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Remesh a 16k-triangle UV sphere to 2,000 target quads and check the output.
#
#   ci/smoke_test.sh <binary> [work-dir]
#
# <binary> is the Qt app (run headless with QT_QPA_PLATFORM=offscreen) or the Qt-free
# tools/bench ar_bench driver; both take --input/--output/--target-quads.
# 1.2 gives 1,624 quads and no other faces. The accepted range is wide on purpose: it should
# not flake across compilers or runners, and it already allows the planned count fix
# (TODO 2.11, 0.9-1.1x target). Override with MIN_QUADS / MAX_QUADS / MAX_NON_QUADS.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bin="${1:?usage: smoke_test.sh <autoremesher|ar_bench> [work-dir]}"
work="${2:-$(mktemp -d)}"
mkdir -p "$work"
min="${MIN_QUADS:-1200}"; max="${MAX_QUADS:-2400}"; max_other="${MAX_NON_QUADS:-20}"

python3 "$here/make_sphere.py" "$work/sphere.obj"
args=(--input "$work/sphere.obj" --output "$work/sphere-quads.obj" --target-quads 2000)
case "$(basename "$bin")" in
    ar_bench*) args+=(--json "$work/sphere-quads.json") ;;
esac
start=$(date +%s.%N)
QT_QPA_PLATFORM=offscreen "$bin" "${args[@]}" > "$work/smoke.log" 2>&1 || {
    status=$?; tail -n 30 "$work/smoke.log"; echo "FAIL: $bin exited with $status"; exit 1; }
end=$(date +%s.%N)

[ -s "$work/sphere-quads.obj" ] || { tail -n 30 "$work/smoke.log"; echo "FAIL: no output mesh"; exit 1; }
read -r quads other < <(awk '$1 == "f" { if (NF == 5) q++; else o++ } END { print q + 0, o + 0 }' \
    "$work/sphere-quads.obj")
awk -v b="$(basename "$bin")" -v q="$quads" -v o="$other" -v s="$start" -v e="$end" \
    'BEGIN { printf "smoke: %s -> %d quads, %d other faces, %.2f s\n", b, q, o, e - s }'
if [ "$quads" -lt "$min" ] || [ "$quads" -gt "$max" ]; then
    echo "FAIL: quad count $quads outside [$min, $max]"; exit 1
fi
if [ "$other" -gt "$max_other" ]; then
    echo "FAIL: $other non-quad faces (allowed $max_other)"; exit 1
fi
echo "PASS"
