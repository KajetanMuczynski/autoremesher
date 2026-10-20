# Bench and baseline scripts

Build, corpus and measurement scripts behind the 1.2 baseline (plan: `research/baseline-and-profiling.md`
and REFERENCE §4.1). Tested on Ubuntu 24.04 x86_64, GCC 13.3, CMake 3.28, Qt 5.15.13, oneTBB 2021.11,
Python 3.12. Meshes, outputs and builds never go into the repo; everything is written to a work
directory you choose.

| File | What it does |
|---|---|
| `ab.py` | **A/B harness** for quality: builds `autoremesher-cli` from a git ref, runs it over a mesh set (optionally with 1-ulp replicates), adds metrics and topology, and compares two runs as Markdown tables. See [A/B a change](#ab-a-change). |
| `build.sh <work>` | apt deps (skip with `SKIP_APT=1`; `JOBS=2` to keep a laptop cool), out-of-tree qmake build of the Qt app, the Qt-free `ar_bench` build of the same core, and a Python venv. Builds this checkout unless `AR_SOURCE_DIR` points elsewhere. |
| `bench/ar_bench.cpp` | Qt-free driver for time and memory: same OBJ loader and `AutoRemesher::remesh()` call as the app's headless mode; writes JSON with wall/CPU time, peak RSS (overall and per pipeline step), the core's phase report, result counts and UV flip checks on the integer-grid map; `--stage-diagnostics` writes the core's per-stage records (solver sizes and times, rounding passes). |
| `bench/CMakeLists.txt` | Builds `ar_bench` from a source tree (`-DAR_SOURCE_DIR`) with the `.pro` release flags (`-O3 -flto -funroll-loops -march=x86-64-v2`). |
| `fetch_meshes.sh <meshes>` + `meshes.tsv` | Downloads the 12 external meshes (pinned commit of github.com/odedstein/meshes, ~170 MB) and verifies SHA-256. Per-mesh license and attribution are in `meshes.tsv`. |
| `make_synthetic.py` | Generates the procedural meshes (CSG part, symmetric blob, cloth sheet, thin leaf, noisy spot, 8 islands, the closed set, subdivision ladder). |
| `make_suzanne.py` | Generates the Suzanne set with Blender's Python module (`pip install bpy`, Python 3.13) or inside Blender. |
| `corpus.json` | Mesh sets with their default targets and resolutions: `corpus` (the 18-mesh baseline corpus, 72 runs), `closed` (13 thin ellipsoids and tori, 78 runs; genus regressions show here first), `suzanne` (Suzanne + Subdivision 1–3, 9 runs; open, the add-on's first bug report). Categories and symmetry planes per mesh. |
| `run_corpus.py` | Runs `ar_bench` (+ metrics) per mesh and target over the `corpus` set; writes `record.json` per run and `summary.json`. For time and memory; quality A/B goes through `ab.py`. |
| `metrics.py` | Output quality: face/valence statistics, corner angles, scaled Jacobian, degenerate and flipped faces, non-manifold edges, topology against the input (Euler characteristic, components, boundary loops), two-sided Hausdorff, geometric and topological mirror symmetry. |
| `summarize.py` | Markdown tables + CSV from `summary.json`. |
| `claims.py` | Aggregates per REFERENCE claim (stage shares, M1/M2 counts, P3 correlations and scaling slopes, thread/ladder/allocator/adaptivity comparisons). |
| `experiments.sh` | Thread sweep (P1), input-size ladder (P4/P6), allocator swap (P5), adaptivity off (M7), perf profiles. |
| `perf_buckets.py` | Groups a `perf report` listing into allocator / containers / solver / remesher / extractor buckets. |

The counters-only `probes.patch` and the CHOLMOD experiment patch were retired on 2026-10-20: they no
longer applied to master, and `--stage-diagnostics` records what they measured except the extractor's
cleanup rounds (TODO 2.4). Both are in git history.

## Run everything

From the repo root:

```bash
W=~/ar-baseline                       # any folder outside the repo with ~2 GB free
tools/bench/build.sh $W
tools/bench/fetch_meshes.sh $W/meshes
$W/venv/bin/python tools/bench/make_synthetic.py --downloads $W/meshes/downloads --out $W/meshes/synthetic --ladder
$W/venv/bin/python tools/bench/run_corpus.py --meshes $W/meshes --bench $W/build/ar_bench \
    --out $W/runs/corpus --targets 2000,10000,50000
$W/venv/bin/python tools/bench/summarize.py $W/runs/corpus/summary.json --csv $W/runs/corpus/summary.csv
PYTHON=$W/venv/bin/python PERF=perf tools/bench/experiments.sh $W/meshes $W/build $W/runs
$W/venv/bin/python tools/bench/claims.py --runs $W/runs          # numbers behind each REFERENCE claim
```

## A/B a change

Every quality claim in a PR or research note comes from `ab.py`, so anyone can re-run it from the repo.
Commit your change first (a WIP commit is fine), then from the repo root:

```bash
export AR_WORK=~/ar-work                     # meshes in $AR_WORK/meshes (fetch_meshes.sh, make_synthetic.py)
P=$AR_WORK/venv/bin/python                   # numpy, scipy, libigl (build.sh makes this venv)
$P tools/bench/ab.py run master              # base: 72 runs of the corpus set
$P tools/bench/ab.py run HEAD                # your change
$P tools/bench/ab.py compare master HEAD     # Markdown tables, paste into the PR
$P tools/bench/ab.py run HEAD --set closed   # genus check; also --set suzanne
```

- **What it builds.** `ab.py` exports the ref with `git archive` and builds `autoremesher-cli` with CMake
  (Release, `nice`, 2 jobs). Builds and runs are keyed by the git trees of `src/`, `include/`,
  `thirdparty/` and `CMakeLists.txt`, not by the commit, so a rebase or a docs commit reuses them, and
  a finished run is never repeated (delete its folder under `$AR_WORK/runs` to force it).
- **Options.** `--only a,b`, `--skip`, `--targets`, `--resolutions` override the set's defaults;
  `--cli-arg=--adaptivity=0` (repeatable) passes CLI options, and those runs get their own folder, so
  compare folders, not refs: `compare $AR_WORK/runs/<key> $AR_WORK/runs/<key>+<hash>`. `--jobs 2`
  (default) runs two meshes at once, each using all cores; on a hot laptop use `--jobs 1`.
- **What it records.** Per run in `<set>/<mesh>/<resolution>-t<target>/u<k>/`: the output OBJ, the CLI's
  `report.json` and `stages.jsonl`, `metrics.json` and a `record.json` summary. `compare` reports the
  report's UV flips (continuous, rounded, final), degenerate UV triangles, non-quads, SJ ≤ 0 quads,
  irregular vertices, Hausdorff and mean distance, quad count error, rounded/continuous energy and
  time, the runs that fail, and topology (Euler characteristic, components and boundary loops equal to
  the input, no non-manifold edge). `--per-run` adds one row per run.
- **Timing.** The `time` row is the CLI's own total under `--jobs` load. Use it for effects of 20 % or
  more; for anything finer run `--jobs 1` on an idle machine, or `ar_bench` with `--repeat`.

### Noise rule

One ulp of input can change a run's genus or move its flip count by a lot (csg_bracket's topology flips
between 1-ulp copies on master). So:

- **Discrete claims** ("fixes mesh X", "breaks the genus of Y", "holes 3 → 0") need replicates:
  `ab.py run <ref> --only <meshes> --replicates 5` for both sides. Replicate u0 is the plain input; uk
  rounds every coordinate to float32 and moves it one float32 ulp up or down (seed k), which is the
  precision Blender hands the add-on (docs/TARGETS.md §2.5). `compare` calls a run fixed or broken only when all replicates
  agree on both sides and lists the rest as noise; with one replicate it labels its lists candidates.
- **Aggregates** over a whole set (sums, geo-means, "better in 50 of 72 runs") don't need replicates.
  Do add them when the effect is small next to the spread: `compare` prints, per metric, how many
  runs are fully separated and the median coefficient of variation over A's replicates.

The Qt CLI (what the Blender bridge calls) runs headless only with an offscreen Qt platform:
`QT_QPA_PLATFORM=offscreen $W/app/autoremesher --input in.obj --output out.obj --report r.txt
--target-quads 10000`. Without it, on a machine with no display, it aborts (exit 134). `--report`
holds only totals; the per-step phase report goes to stderr.

## Adding your own meshes

Add an entry to `corpus.json` (`file` relative to the meshes folder, optional `"sym": ["x", 0.0]`
or `["x", "auto"]`), then `run_corpus.py --only <id>`. ZBrush sculpts exported as OBJ work as is;
make sure positions are welded (AutoRemesher treats every connected component as an island and
indexes by position, so a triangle soup becomes thousands of islands).
