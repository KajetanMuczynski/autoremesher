# AutoRemesher fork

Notes for Claude working in this repository.

## What this is
- Field-guided automatic quad remesher by Jeremy Hu (huxingyi/autoremesher, MIT), forked at `4a49f82` (v1.2.0).
- Pipeline core is Qt-free C++14 in `src/AutoRemesher/` (public headers in `include/AutoRemesher/`):
  isotropic remesh, frame field, singularity simplification, mixed-integer quad parameterization
  (Eigen `SimplicialLDLT` + own rounding), quad extraction. Parallelism via TBB.
- GUI (`src/*.cpp`, Qt 5.15 or Qt 6 + OpenGL) wraps the core; built with qmake (`autoremesher.pro`).
- Vendored in `thirdparty/`: eigen, tbb (2017-era), isotropicremesher, meshoptimizer, QtAwesome,
  QtWaitingSpinner. Upstream README mentions Geogram/libigl, but the `.pro` uses neither.
- `origin` = Kajetan's fork (github.com/KajetanMuczynski/autoremesher), `upstream` = huxingyi. Never push upstream.
- Commit trailer: `Co-Authored-By: Claude <noreply@anthropic.com>` (short form, Kajetan's choice).

## License policy
- The fork is **GPL-3.0-or-later**. Keep Jeremy Hu's MIT notices (`LICENSE-MIT-upstream`, file headers)
  intact; new files get a GPL-3.0-or-later header.
- **No GPL-3.0-only code** (CoMISo, igl/copyleft/comiso, quadwild-bimdf, etc.).
- **No code from repos without a LICENSE file**: re-implement from the paper or get written permission.
- Check every new dependency against the plan's `LICENSES.md` before adding it.

## Build (checked 2026-10-15: Ubuntu 24.04, GCC 13.3, Qt 5.15.13, oneTBB 2021.11)
Deps: `qt5-qmake qtbase5-dev libqt5opengl5-dev qttools5-dev-tools libqt5svg5-dev libtbb-dev libgl1-mesa-dev`
(`libqt5opengl5-dev` comes only as a recommend of `qtbase5-dev`; without it qmake fails with "Unknown module(s) in QT: opengl").
README's `libqt5multimedia5-dev` does not exist on 24.04 and is not needed.

Qt app, out-of-tree (`build/` is gitignored), no extra flags (~2.5 min on 4 cores, 24 harmless warnings):

    mkdir -p build/app && cd build/app && qmake ../../autoremesher.pro && make -j4
    # -> build/app/autoremesher (links system libtbb.so.12; the vendored thirdparty/tbb is Windows-only)

Headless mode of the Qt app (what the old autoremesher-blender-bridge calls; our add-on uses `autoremesher-cli` below); `offscreen` avoids needing a display:

    QT_QPA_PLATFORM=offscreen build/app/autoremesher -i in.obj -o out.obj --target-quads 2000
    # 16k-tri UV sphere -> 1624 quads, 0 non-quads, 0.55 s. Other flags: --report, --edge-scaling,
    # --sharp-edge, --smooth-normal, --adaptivity, --anisotropy (see src/main.cpp)

Qt-free core and benchmarks: `tools/bench/` (`ar_bench` driver, corpus, metrics; see its README).
`tools/bench/build.sh <work-dir>` builds the app and the bench drivers out of tree.

Qt-free core and CLI with CMake (top-level `CMakeLists.txt`, target `autoremesher_core` + `autoremesher-cli`,
the Blender add-on's worker; Windows builds static oneTBB and /MT, so no DLLs):

    cmake -S . -B build/cli -DCMAKE_BUILD_TYPE=Release && nice -n 10 cmake --build build/cli --parallel 2

The core source list exists three times: `autoremesher.pro` (app), top-level `CMakeLists.txt`
(explicit list) and `tools/bench/bench/CMakeLists.txt` (glob, kept separate on purpose so the
bench can build other checkouts for A/B). A new core `.cpp` goes into the first two.

Core tests (`tests/`, Qt-free, link `autoremesher_core`): configure with `-DAUTOREMESHER_BUILD_TESTS=ON`,
build all targets (ctest reports a test whose executable wasn't built as failed), run
`ctest --test-dir <build> --output-on-failure`.

Blender add-on (`addon/`, working name Quadami): `python addon/package.py --cli-prefix <install-prefix>`
builds the extension zip with the CLI bundled; see `addon/README.md`.

CI (`.github/workflows/`):
- `ci.yml` (every PR, push to master, manual run): all checks in one workflow. Its last job,
  **CI passed**, is green only if every other job succeeded; it is the one check branch protection
  requires. Branch pushes without a PR get no run (use Actions > ci > Run workflow).
  - `format`: `ci/lint.sh` (src/ and tests/) with clang-format pinned to 23.1.3 (pip); bump on purpose.
  - `core (linux|macos)`: CMake Release build with tests, `ctest --no-tests=error`, then
    `ci/output_gate.py` (procedural sphere, torus, box, open tube, two islands; fails on exit status,
    quads outside 0.6-1.5x target, >2 % non-quads, any non-manifold edge, report/OBJ mismatch;
    folded faces and empty islands are reported in the job summary, not gated yet).
  - `qt-app (linux)`: qmake app and `ar_bench`, `ci/smoke_test.sh` on both (1,200-2,400 quads).
  - `addon (linux-x64|windows-x64)`: CLI, worker tests, zip installed into a real Blender
    (4.2 LTS on Linux, 5.2 on Windows).
- `release.yml` (upstream's packaging: AppImage, Windows zip, macOS DMG, armadillo at 50k quads):
  push to master and tags only, not on PRs.

Running the binary with no args opens the GUI. The core needs `setTargetTriangleCount(n > 0)` or
`remesh()` fails.

## Keep the machine cool
Kajetan's laptop has 4 cores and runs hot. The heavy part is the release build: `-O3 -flto` with
`make -j4` (or `-j$(nproc)`) holds all cores at 100 % for minutes, and the LTO link is one long
single-file job on top. For routine work:
- Build with `nice -n 10 make -j2`.
- Day-to-day app builds can drop LTO (checked: removes `-flto` from the generated Makefile):
  `qmake ../../autoremesher.pro -after "QMAKE_CXXFLAGS_RELEASE-=-flto" "QMAKE_LFLAGS_RELEASE-=-flto"`.
  Keep the full LTO build for release checks and for timings that go into the baseline.
- Rebuild incrementally in the same build folder; don't wipe it between runs.
- Don't run the full corpus or `experiments.sh` while other builds or sessions are busy, and quit
  the GUI or any leftover `autoremesher` process after testing.

## Plan and context
`docs/` holds the plan, copied from Kajetan's `../docs/` on 2026-10-15. The research reports and
`archive/` stay in `../docs/` only, so links to `research/` and `archive/` don't resolve in the repo.
- `docs/README.md` (index) and `docs/TODO.md` ("Order at a glance", critical path) first.
- `docs/REFERENCE.md`: pipeline map with line numbers, known performance and math issues, baseline.
- Log each working session in `docs/SESSIONS.md`.
