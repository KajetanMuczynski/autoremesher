# 2026-10-21 · Claude (cloud) · TARGETS V1 for sculpts
- Repos/commits: core master `124aeb8`
- Did: applied Kajetan's answers on the sculpt note's V1 proposal (research/sculpt-inputs-2026-10-21.md §5)
  to docs/TARGETS.md: provisional V1 (hard surface all-quad; elsewhere no 6+-gon and non-quad clusters ≤ 2),
  H2 counts vertices, new H8 (no 6+-gons), headline redefined, §6 item 5. New TODO 2.18 (sunk-eyeball caps).
- Found: the "touches no folded quad" clause is implied by V2 at run level and only `sculpt_report.py`
  computes it, so it was dropped from the pass condition and kept as a diagnostic. V2 never tests non-quads.
- Measured: `ab.py run origin/master --set corpus` and `--set closed`, then `sculpt_report.py`: largest
  non-quad cluster ≤ 2 in all 150 runs, no 6+-gon, no non-manifold vertex. V1–V5 together 21/72 → 32/72
  (corpus), 37/78 → 40/78 (closed). Aggregation in research/targets-v1-2026-10-21/ (../docs only).
- Next: re-derive the cluster limit on Kajetan's own sculpts (1.12); H2 vertex gate after 2.18.
