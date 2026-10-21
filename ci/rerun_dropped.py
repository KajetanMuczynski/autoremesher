#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""Re-run the failed jobs of a ci run whose only failures are jobs that never got a runner.

    python3 ci/rerun_dropped.py <run-id>     (GITHUB_REPOSITORY, GITHUB_TOKEN; MAX_ATTEMPTS)

DRY_RUN=1 prints the decision without re-running anything.

Called by .github/workflows/rerun-dropped.yml when a ci run completes. GitHub drops a job that
waits about 15 minutes for a hosted runner (macOS arm64, when GitHub is short of them): the job is
cancelled with no runner and no steps, and "CI passed" turns red although no code ran. This
re-runs the failed jobs of that same run (a new attempt, which the PR page and the merge box
follow), and only when all of this holds:
  - the run completed with conclusion "failure" (a run cancelled by a newer push is "cancelled");
  - its attempt is below MAX_ATTEMPTS (default 3);
  - every job other than "CI passed" that did not succeed or skip was cancelled with no runner and
    no steps, so it never ran any code (a real failure or a timeout always had a runner);
  - for a pull request run, the run is still on the PR's current head.
Anything else is left as it is, so a real failure stays red. Standard library only.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
GATE_JOB = "CI passed"  # fails because the dropped job did; re-run with it
OK = {"success", "skipped", "neutral"}


def never_ran(job):
    """A job GitHub cancelled before any runner picked it up."""
    return job["conclusion"] == "cancelled" and not job.get("runner_id") and not job.get("steps")


def decide(run, jobs, pr_heads, max_attempts):
    """Returns (re-run?, reason). run and jobs as the REST API gives them for one attempt;
    pr_heads: the current head SHA of each PR the run belongs to."""
    if run["status"] != "completed" or run["conclusion"] != "failure":
        return False, "run is %s/%s, not a failure" % (run["status"], run["conclusion"])
    if run["run_attempt"] >= max_attempts:
        return False, "attempt %d of at most %d" % (run["run_attempt"], max_attempts)
    pending = [j["name"] for j in jobs if j["status"] != "completed"]
    if pending:
        return False, "jobs not completed: %s" % ", ".join(pending)
    bad = [j for j in jobs if j["name"] != GATE_JOB and j["conclusion"] not in OK]
    if not bad:
        return False, "no failed job besides %s" % GATE_JOB
    ran = [j["name"] for j in bad if not never_ran(j)]
    if ran:
        return False, "failed after running (not a dropped job): %s" % ", ".join(ran)
    stale = [n for n, head in pr_heads.items() if head != run["head_sha"]]
    if stale:
        return False, "PR #%s has a newer head than %s" % (stale[0], run["head_sha"][:7])
    return True, "dropped without a runner: %s" % ", ".join(j["name"] for j in bad)


def request(path, token, method="GET"):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(API + path, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read()
    return json.loads(body) if body else None


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    run_id = int(sys.argv[1])
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ.get("GITHUB_TOKEN", "")
    max_attempts = int(os.environ.get("MAX_ATTEMPTS", "3"))
    base = "/repos/%s/actions/runs/%d" % (repo, run_id)

    run = request(base, token)
    jobs = []
    while True:
        page = request("%s/attempts/%d/jobs?per_page=100&page=%d"
                       % (base, run["run_attempt"], len(jobs) // 100 + 1), token)
        jobs += page["jobs"]
        if len(jobs) >= page["total_count"] or not page["jobs"]:
            break
    pr_heads = {}
    if run["event"] == "pull_request":
        for pr in run["pull_requests"]:
            pr_heads[pr["number"]] = request("/repos/%s/pulls/%d" % (repo, pr["number"]),
                                             token)["head"]["sha"]

    for job in jobs:
        print("%-60s %-10s runner %s" % (job["name"][:60], job["conclusion"], job.get("runner_id")))
    rerun, reason = decide(run, jobs, pr_heads, max_attempts)
    print("%s attempt %d: %s" % ("re-run" if rerun else "leave", run["run_attempt"], reason))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("[ci run %d](%s) attempt %d: **%s**, %s\n"
                    % (run_id, run["html_url"], run["run_attempt"],
                       "re-run failed jobs" if rerun else "left as it is", reason))
    if rerun and os.environ.get("DRY_RUN") != "1":
        try:
            request(base + "/rerun-failed-jobs", token, method="POST")
        except urllib.error.HTTPError as e:
            sys.exit("rerun-failed-jobs: HTTP %d %s" % (e.code, e.read().decode(errors="replace")))


if __name__ == "__main__":
    main()
