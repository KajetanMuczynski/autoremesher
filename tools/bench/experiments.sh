#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Targeted experiments behind the REFERENCE.md bottleneck claims. Run on an
# otherwise idle machine (timings). Assumes build.sh and fetch_meshes.sh/make_synthetic.py ran.
#
#   tools/bench/experiments.sh <meshes-dir> <work-dir>/build <out-dir>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
meshes="$1"; build="$2"; out="$3"
py="${PYTHON:-python3}"
run() { "$py" -I "$here/run_corpus.py" --meshes "$meshes" --bench "$build/ar_bench" "$@"; }

# E1 / P1: single island vs islands, 1 vs all threads (3 repeats, median).
for t in 1 0; do
    run --out "$out/threads" --only koala,human_neutral,spot_x8 --targets 10000 --threads "$t" \
        --repeat 3 --tag "thr$t-" --no-metrics
done

# E2 / P4, P6: input-size ladder at a fixed target (koala subdivided 0..3 times).
cat > "$out/ladder-corpus.json" <<'EOF'
{"meshes": [
 {"id": "koala_sub0", "file": "downloads/koala.obj", "category": "ladder 0.1M"},
 {"id": "koala_sub1", "file": "synthetic/koala_sub1.obj", "category": "ladder 0.4M"},
 {"id": "koala_sub2", "file": "synthetic/koala_sub2.obj", "category": "ladder 1.6M"},
 {"id": "koala_sub3", "file": "synthetic/koala_sub3.obj", "category": "ladder 6.4M"}]}
EOF
run --corpus "$out/ladder-corpus.json" --out "$out/ladder" --targets 10000,50000 --no-metrics

# E3 / P2: SimplicialLDLT (probe build) vs CHOLMOD supernodal (probe+cholmod build), same inputs.
for b in ar_bench_probe ar_bench_probe_cholmod; do
    [ -x "$build/$b" ] || { echo "skipping E3 for $b: not built" >&2; continue; }
    "$py" -I "$here/run_corpus.py" --meshes "$meshes" --bench "$build/$b" --probe "$build/$b" \
        --out "$out/solver" --only spot,koala,cat,nefertiti --targets 10000,50000 --tag "$b-" --no-metrics
done

# E4 / P5: same binary with TBB's scalable allocator preloaded (3 repeats).
tbbmalloc="$(ls /usr/lib/x86_64-linux-gnu/libtbbmalloc_proxy.so.2 2>/dev/null || true)"
if [ -n "$tbbmalloc" ]; then
    run --out "$out/alloc" --only spot,koala,demosthenes --targets 50000 --repeat 3 --tag "glibc-" --no-metrics
    LD_PRELOAD="$tbbmalloc" run --out "$out/alloc" --only spot,koala,demosthenes --targets 50000 --repeat 3 \
        --tag "tbbmalloc-" --no-metrics
fi

# E5 / M7: quad count vs target with the density field off.
run --out "$out/adaptivity" --only spot,koala,csg_bracket --targets 10000 --tag "adapt0-" \
    --bench-arg=--adaptivity=0 --no-metrics
run --out "$out/adaptivity" --only spot,koala,csg_bracket --targets 10000 --tag "adapt0-aniso0-" \
    --bench-arg=--adaptivity=0 --bench-arg=--anisotropy=0 --no-metrics

# E6: perf profiles (software clock; VMs often lack hardware counters).
perf_bin="${PERF:-perf}"
if command -v "$perf_bin" >/dev/null 2>&1; then
    mkdir -p "$out/perf"
    for m in koala:downloads/koala.obj demosthenes:downloads/demosthenes.obj nefertiti:downloads/nefertiti.obj; do
        id="${m%%:*}"; f="${m#*:}"
        "$perf_bin" record -q -e cpu-clock -F 999 -g -o "$out/perf/$id.data" -- "$build/ar_bench" \
            --input "$meshes/$f" --output "$out/perf/$id.obj" --json "$out/perf/$id.json" --target-quads 50000 \
            >/dev/null 2>&1
        "$perf_bin" report -i "$out/perf/$id.data" --no-children --sort symbol --stdio -g none 2>/dev/null \
            > "$out/perf/$id.txt"
        "$py" -I "$here/perf_buckets.py" "$out/perf/$id.txt" > "$out/perf/$id-buckets.md"
        rm -f "$out/perf/$id.data"
    done
fi
echo "experiments done: $out"
