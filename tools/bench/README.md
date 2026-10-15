# Bench and baseline scripts

Build, corpus and measurement scripts behind the 1.2 baseline (plan: `research/baseline-and-profiling.md`
and REFERENCE §4.1). Tested on Ubuntu 24.04 x86_64, GCC 13.3, CMake 3.28, Qt 5.15.13, oneTBB 2021.11,
Python 3.12. Meshes, outputs and builds never go into the repo; everything is written to a work
directory you choose.

| File | What it does |
|---|---|
| `build.sh <work>` | apt deps (skip with `SKIP_APT=1`; `JOBS=2` to keep a laptop cool), out-of-tree qmake build of the Qt app, and Qt-free CMake builds of the same core: pristine, with probes, with probes + CHOLMOD. Creates a Python venv. Builds this checkout unless `AR_SOURCE_DIR` points elsewhere. |
| `bench/ar_bench.cpp` | Qt-free driver: same OBJ loader and `AutoRemesher::remesh()` call as the app's headless mode; writes JSON with wall/CPU time, peak RSS (overall and per pipeline step), the core's phase report, result counts and UV flip checks on the integer-grid map. |
| `bench/CMakeLists.txt` | Builds `ar_bench` from a source tree (`-DAR_SOURCE_DIR`) with the `.pro` release flags (`-O3 -flto -funroll-loops -march=x86-64-v2`). Options `AR_BENCH_PROBE`, `AR_USE_CHOLMOD`. |
| `bench/probes.patch` | Counters and timers only (no behaviour change; outputs verified identical): per sparse solve sizes and analyze/factor/solve times, per rounding iteration how many integers get fixed and how far they move, rounds of each extractor cleanup loop. Written against upstream `4a49f82`; `build.sh` skips the probe builds if it no longer applies. |
| `bench/cholmod-experiment.patch` | Experiment for P2: swaps `SimplicialLDLT` for `CholmodSupernodalLLT` in `ConstrainedLeastSquares`. Not a proposed change. |
| `fetch_meshes.sh <meshes>` + `meshes.tsv` | Downloads the 12 external meshes (pinned commit of github.com/odedstein/meshes, ~170 MB) and verifies SHA-256. Per-mesh license and attribution are in `meshes.tsv`. |
| `make_synthetic.py` | Generates the procedural meshes (CSG part, symmetric blob, cloth sheet, thin leaf, noisy spot, 8 islands, subdivision ladder). |
| `corpus.json` | The 18-mesh corpus, categories and symmetry planes. |
| `run_corpus.py` | Runs `ar_bench` (+ probe build, + metrics) per mesh and target; writes `record.json` per run and `summary.json`. |
| `metrics.py` | Output quality: face/valence statistics, corner angles, scaled Jacobian, degenerate and flipped faces, non-manifold edges, two-sided Hausdorff, geometric and topological mirror symmetry. |
| `summarize.py` | Markdown tables + CSV from `summary.json`. |
| `claims.py` | Aggregates per REFERENCE claim (stage shares, M1/M2 counts, P3 correlations and scaling slopes, thread/ladder/solver/allocator/adaptivity comparisons). |
| `experiments.sh` | Thread sweep (P1), input-size ladder (P4/P6), CHOLMOD vs SimplicialLDLT (P2, skipped if not built), allocator swap (P5), adaptivity off (M7), perf profiles. |
| `perf_buckets.py` | Groups a `perf report` listing into allocator / containers / solver / remesher / extractor buckets. |

## Run everything

From the repo root:

```bash
W=~/ar-baseline                       # any folder outside the repo with ~2 GB free
tools/bench/build.sh $W
tools/bench/fetch_meshes.sh $W/meshes
$W/venv/bin/python tools/bench/make_synthetic.py --downloads $W/meshes/downloads --out $W/meshes/synthetic --ladder
$W/venv/bin/python tools/bench/run_corpus.py --meshes $W/meshes --bench $W/build/ar_bench \
    --probe $W/build/ar_bench_probe --out $W/runs/corpus --targets 2000,10000,50000
$W/venv/bin/python tools/bench/summarize.py $W/runs/corpus/summary.json --csv $W/runs/corpus/summary.csv
PYTHON=$W/venv/bin/python PERF=perf tools/bench/experiments.sh $W/meshes $W/build $W/runs
$W/venv/bin/python tools/bench/claims.py --runs $W/runs          # numbers behind each REFERENCE claim
```

To A/B a change, build the base commit into one work folder (`AR_SOURCE_DIR=<checkout of the base>
tools/bench/build.sh $W/base`) and your tree into another, then run `run_corpus.py` with each `ar_bench`.

The Qt CLI (what the Blender bridge calls) runs headless only with an offscreen Qt platform:
`QT_QPA_PLATFORM=offscreen $W/app/autoremesher --input in.obj --output out.obj --report r.txt
--target-quads 10000`. Without it, on a machine with no display, it aborts (exit 134). `--report`
holds only totals; the per-step phase report goes to stderr.

## Adding your own meshes

Add an entry to `corpus.json` (`file` relative to the meshes folder, optional `"sym": ["x", 0.0]`
or `["x", "auto"]`), then `run_corpus.py --only <id>`. ZBrush sculpts exported as OBJ work as is;
make sure positions are welded (AutoRemesher treats every connected component as an island and
indexes by position, so a triangle soup becomes thousands of islands).
