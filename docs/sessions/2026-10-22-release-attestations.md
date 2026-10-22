# 2026-10-22 · Claude (cloud, thread "Release workflow for 0.1") · Release attestations, macOS experimental
- Repos/commits: quadami master ae27301
- Did: the release job attests the three zips (`actions/attest-build-provenance` v4.2.2, pinned by
  commit, released 2026-08-06); release notes and RELEASING.md say how to verify a download; macOS is
  "experimental, untested" in the 0.1.0 notes, the notes template, README and user guide (Kajetan,
  2026-10-22); RELEASING.md has the click path for the `v*` tag ruleset Kajetan approved.
- Found: the attest step can be tested only on a tag run. Test tag `v0.1.0-test.2` on 99d716b (pushed
  by Kajetan, after he created the `v*` ruleset; his bypass worked): release (draft) green, "Attestation
  created for 3 subjects", Rekor log index 3391015643, repository attestation 58679733.
- Measured: nothing measured.
- Next: corpus release check on Windows and macOS (own PR).
