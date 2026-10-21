# 2026-10-21 · Claude (cloud thread "Supported-input envelope for the remesher") · Envelope proposal
- Repos/commits: core master 124aeb8
- Did: wrote docs/ENVELOPE.md (proposal): 15 limits, each with how it is measured, threshold tagged
  [M]/[I], evidence, test and canary mesh, what is exempt outside and what the user would see; a
  never-exempt list; local (2 h₀) instead of run-wide exemptions; the harness design for ab.py
  (descriptor per input, inside/outside per run, bug vs expected per defect); experiments E1–E7 for
  every [I]; open questions for Kajetan. Index row in docs/README.md.
- Found: the Target Quads guard is 200,000 warn / 2,000,000 refuse (not 300,000); #51 has no
  orientation repair, so flipped patches stay a temporary limit; most of today's sculpt failures
  (eyeball caps, degenerate triangles, flipped patches) are bugs or temporary limits, not envelope
  exemptions.
- Handles (§3.1), reconciled with the seam-lattice thread: by continuous meridian holonomy H,
  H < 2 permanent limit, 2 ≤ H < 3 known limit owned by 7.2 (ℤ² alone regressed, not adopted), H ≥ 3 bug.
- Measured: nothing new; numbers come from the genus, sculpt, untangling and nonquads notes.
- Decided (Kajetan, 10:00): warn and run; handle bands; eyeball caps inside + runtime warning follow-up (§3.2); 2 h₀ provisional; row 15 ratchet only.
- Next: E1 after TODO 1.14; link ENVELOPE from TARGETS after the TARGETS V1
  PR merges.
