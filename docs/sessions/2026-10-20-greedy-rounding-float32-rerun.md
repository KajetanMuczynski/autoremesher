# 2026-10-20 · cloud thread · Full corpus re-run of #37 with float32 replicates
- Repos/commits: core 04e83ba (before #37), 0480366 (after), 47529e1 (master, with #40); harness `tools/bench/ab.py` (#39)
- Did: `ab.py run --replicates 5` on the corpus and closed sets for all three refs (2700 runs, none
  failed); `run_compare.py --tools ours_quality` on master for all 18 meshes × 2k/10k/50k; replaced the
  "today" columns of docs/TARGETS.md; corrected #37's numbers in TODO 3.3 and REFERENCE M1.
- Found: greedy rounding makes no discrete genus claim (no run fixed or broken in all 6 replicates);
  its earlier "boat and sword fixed, thin_leaf broken" came from float64 replicates. #40 is
  bit-identical on Linux. Adding csg_bracket moves hard-surface p99 distance to 0.90, above the 0.8 min.
- Measured: corpus final flips ×0.79, non-quads ×0.80, SJ ≤ 0 315 → 258; genus 60.5 → 61.5/72, closed
  76.7 → 75.5/78 (replicate means); count spread over replicates median 1.9 %, worst 11.7 %.
  Details: research/greedy-rounding-rerun-2026-10-20.md (project files).
- Next: decide whether §4 min values are re-derived on 18 meshes; wall-time ratio needs a same-machine
  Blender run.
