# 2026-10-21 · Claude (cloud thread) · Automatic re-run of dropped macOS jobs
- Repos/commits: quadami master a5e983a
- Did: `.github/workflows/rerun-dropped.yml` + `ci/rerun_dropped.py`: when a ci run fails only
  because jobs never got a runner, re-run that run's failed jobs (same run, new attempt), at most
  to attempt 3. Unit tests on recorded runs in `ci/tests` (run by `qt-app`). CLAUDE.md CI section;
  TODO 0.9 status.
- Found (measured, REST API, all 160 ci runs): every drop is the same signature: macOS arm64 job,
  `runner_id` 0, no steps, cancelled after 902 s, annotation "The job was not acquired by Runner of
  type hosted even after multiple attempts" and GitHub's notice "Due to capacity constraints, jobs
  targeting macOS arm64 runners may experience longer queue times". Drops per day: 10-15 1, 10-19
  10, 10-20 0, 10-21 19. From 13:02 UTC on 10-21, 16 of 17 macOS requests dropped, including all 6
  manual re-runs; in the morning 2 of ~30, and the one re-run then got a runner after 606 s.
  A job cancelled by a newer push while queued has the same job signature but its run's conclusion
  is "cancelled" (run 39576439988), so the run conclusion has to be part of the test.
- Found (checked): the `master` ruleset (25411110) requires a PR and blocks force pushes and
  deletion, but has no required status check; CLAUDE.md said **CI passed** was required.
- Rejected: a retry job inside ci.yml (the dropped check stays cancelled on the PR page, so the
  merge box shows "unstable"); another macOS label (every arm64 image draws on the same capacity;
  Intel doesn't test the arm64 zip that ships); paid or self-hosted macOS runners (no Mac, cost).
- Inferred, to check on the first drop after merge: GITHUB_TOKEN with `actions: write` may call
  rerun-failed-jobs; a re-run made by GITHUB_TOKEN likely starts no further `workflow_run`, so
  probably one automatic retry, not two. Dependabot-triggered runs get a read-only token there,
  so their drops still need a manual re-run.
- Measured: nothing on quality.
- Next: Kajetan adds the **CI passed** status check to the ruleset (TODO 0.9), or CLAUDE.md keeps
  saying it isn't there.
