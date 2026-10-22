# 2026-10-22 · Claude (cloud) · Remaining defect ledger after libQEx
- Repos/commits: quadami master ae27301 (first pass on 0e9bec8); tool `tools/bench/defect_ledger.py` + tests.
- Did: `ab.py` corpus, closed, sculpt, brush and the private realsculpt/realsword sets, 5 replicates each, on a
  probe build that dumps per island T and the orientation of every map triangle (outputs byte-identical to master,
  closed 468/468); brush/realsculpt/realsword again with `--fold-repair on` (1,704 replicate-runs, 0 failures).
  Every defect located and classed: folded input within 2h, tip, part thinner than a quad, libQEx fallback,
  flipped map within h, else extractor; repair runs paired against runs without repair.
- Found: 91 % of the remaining defect score sits on an input trigger (folded input 28 %, tips 29 %, parts thinner
  than a quad 34 %); flipped maps without an input trigger and the extractor on a valid map are 8 %, fallback islands
  under 1 % (after #78 the real sword has 0 fallbacks and 0 non-quads, was 17 per run). Thin/tip defects of spot_x8,
  plane and human_neutral vanish from 2k to 10k quads (resolution); the real sword's barely move up to 24k
  (structural). Fold repair: brush −28 %, real sculpts −45 %, sword −2 % (no longer worse after #80).
- Measured: research note `research/defect-ledger-2026-10-22.md` (project files) with tables per set, the top 5,
  and the ranking.
- Next (Kajetan's call): thin-part warning with the target that resolves it; Solidify-the-vines run to tell sizing
  from map as the lever for the sword; fold repair default on closed sculpt islands.
