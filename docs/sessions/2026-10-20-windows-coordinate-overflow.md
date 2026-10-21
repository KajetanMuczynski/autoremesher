# 2026-10-20 · Claude (cloud thread) · Windows coordinate overflow
- Repos/commits: core master 0480366 + this PR
- Did: gap-scan item 3. `PositionKey` (crossing-point weld in the quad extractor) kept scaled coordinates
  in `long`, 32-bit under MSVC, so beyond about ±21,475 units every coordinate wrapped and far points
  shared one key. It now keeps them as `std::trunc(x * 1e5)` in doubles: no integer, so no overflow at
  any range, and below 2^53 the values equal the old 64-bit cast. New core test `position_key`; the
  output gate gained `far_sphere` (unit sphere centred at (1e5, 1e5, 1e5)) so the Windows CLI is checked
  end to end.
- Found: no other `long` in the core (only `long long`), none in vendored isotropicremesher or meshoptimizer.
- Measured: `position_key` fails on master on Linux (1e14 cases: 15 points, 1 key) and, with `long`
  replaced by `int` to mimic MSVC, also at 3e4 and 1e5; passes with the fix. Linux output byte-identical
  old vs new (md5) on the gate corpus plus spheres at 3e4 and 1e5; gate passes, `far_sphere` 2052 quads.
  Windows itself only checked by CI.
- Next: TODO 2.7 (scale normalisation) still needed: the 1e-5 cell is absolute, so very large or tiny
  meshes weld at the wrong scale.
