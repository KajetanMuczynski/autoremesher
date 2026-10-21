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
- Measured: nothing new; numbers come from the genus, sculpt, untangling and nonquads notes.
- Next: Kajetan's answers (§6); E1 after TODO 1.14; link ENVELOPE from TARGETS after the TARGETS V1
  PR merges.
