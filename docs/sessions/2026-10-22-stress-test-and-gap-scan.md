# 2026-10-22 · Claude (cloud thread "Stress test and gap scan") · Stress test, measured envelope boundaries, gap scan
- Repos/commits: core `0e9bec8` (master, libQEx default, fold repair opt-in); no core change.
- Did: `tools/bench/make_stress.py` (14 seeded stress families: thin capsules as islands and attached, ribbons,
  1,000 crumbs, contact cases, slivers and graded density, topology damage, scale/offset, 1.3M/5.2M
  triangles, spikes, jitter, twists, coarse input, self-intersection) and `tools/bench/stress_report.py`
  (scores any ab.py set: coverage of the input in h0, collapsed islands, cleanup loss, local thickness, and
  whether the add-on panel's own `report.py` shows anything). 199 stress runs x1, 252 replicate-runs (x5) on
  the boundary cases, 238 baseline runs (corpus, closed, sculpt, brush, Kajetan's private sculpts) for false
  alarms. ENVELOPE rows 4, 5, 7, 12–14 measured, rows 17–19 and §3.3 (warning rules) added.
- Found: separate thin parts collapse to 3–10 quads below about 3 h0 diameter, mostly because the last cleanup
  pass (`collapseThreeValenceEdgePairs`) eats a valid libQEx tube (72 → 6 faces); the vines thread owns the fix.
  The cleanup also shrinks eyeball islands (19–45 % of libQEx's faces kept), a likely cause of 2.18. Attached
  limbs vanish below 0.4–0.8 h0 diameter, silently. Wrong genus is never named in the panel (23/238 baseline
  runs). Unwelded input: 23k islands, 90 s, 1.7 GB, garbage. 1,000 crumbs give 14x the target quads.
  A 256-sided CAD cylinder gets 7x too dense a T (52–191 s, 1.5 GB). Robust: scale 1e-4..1e4, offset 1e6,
  12-triangle input, slivers, density ratio 353, self-intersection, 1,000 islands, 5.2M triangles.
- Measured: rule "input point farther than 3 h0 from the output" catches 53 of 64 lost features with 0 false
  alarms on the stress runs and fires on 21/238 baseline runs, each a real far region; with "island under half
  its planned quads" 61 caught, 3 missed, 3 false. A pre-run thin-point check fires on 150/238 baseline runs
  and is not usable without region extent. Peak RSS ≈ 0.6 KB per input triangle + 21 KB per quad.
  Note with tables and gap scan: research/stress-2026-10-22.md (project files).
- Next: the vines thread's cleanup fix and coverage warning; core report change for handles changed per closed
  island and holes on open islands (G2, G8); add-on pre-checks (unwelded, memory, crumb overshoot; G3); stress
  meshes as report-only rows in the output gate (G6); drop scale normalisation from 2.7 (G9). Kajetan decides
  what enters TODO.md.
