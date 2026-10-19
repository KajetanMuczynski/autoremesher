# 2026-10-19 · Claude (cloud thread "SESSIONS.md conflicts") · One file per session, ruleset plan
- Repos/commits: fork master `d1d65c4` → this PR (docs(docs), TODO 0.9).
- Did: resolved PR #26's `SESSIONS.md` conflict (merge commit, both entries kept). Split `docs/SESSIONS.md` into one file per entry in `docs/sessions/` (text unchanged, links gained `../`), with a README holding the format and template; updated CLAUDE.md, docs/README.md, REFERENCE.md and TODO.md. Added TODO 0.9, the master branch ruleset plan.
- Found: every PR appended to the end of one file, so every merge conflicted with every other open PR. No ruleset is active on `master` (API). Merge queue is for organization-owned repositories only.
- Measured: nothing measured.
- Next: Kajetan sets up the ruleset (0.9). PRs #26 and #28 move their session entries into `docs/sessions/` once this lands, or this PR does so if they land first.
