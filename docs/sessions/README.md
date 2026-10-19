# Session log

One file per working session or thread: `docs/sessions/YYYY-MM-DD-<slug>.md`, where the date is the
session's start (UTC) and the slug is a few words of its title (lowercase, hyphens). Add a new file;
never append to another session's file and never keep an index here. Every PR used to append to one
shared `SESSIONS.md`, so each merge made every other open PR conflict there; separate files cannot
conflict. If two sessions pick the same name, add `-2`.

The latest entries are the last names in `ls docs/sessions/`. Within one day the order is not
recorded; the entry says what it builds on.

Converted from `docs/SESSIONS.md` on 2026-10-19 without changing the entries' text (relative links
gained `../`).

Template:
```
# YYYY-MM-DD · <who / device> · <short title>
- Repos/commits: core <sha>, bridge <sha>
- Did:
- Found:
- Measured: (numbers or "nothing measured")
- Next:
```
