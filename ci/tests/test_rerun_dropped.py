# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""ci/rerun_dropped.py's decision on recorded ci runs (fixtures/, trimmed from the REST API):
drop       run 39631234238 attempt 1 (PR #64), macOS never got a runner
drop-attempt2  run 39627475791 attempt 2 (PR #65), the same after a manual re-run
superseded run 39576439988, cancelled by a newer push while macOS was still queued
cancelled-with-runner  run 39422860138, cancelled by a newer push mid-build
success    run 39613095074 (PR #58)
"""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import rerun_dropped  # noqa: E402


def load(name):
    with open(os.path.join(HERE, "fixtures", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def decide(case, max_attempts=3, pr_heads=None):
    if pr_heads is None:
        pr_heads = {p["number"]: p["head_sha"] for p in case["pull_requests"]}
    return rerun_dropped.decide(case["run"], case["jobs"], pr_heads, max_attempts)


def job(case, prefix):
    return next(j for j in case["jobs"] if j["name"].startswith(prefix))


class Decide(unittest.TestCase):
    def test_dropped_macos_job_is_rerun(self):
        rerun, reason = decide(load("drop"))
        self.assertTrue(rerun, reason)
        self.assertIn("macos-arm64", reason)

    def test_second_attempt_is_rerun_below_the_cap(self):
        self.assertTrue(decide(load("drop-attempt2"))[0])
        self.assertFalse(decide(load("drop-attempt2"), max_attempts=2)[0])

    def test_superseded_runs_are_left(self):
        self.assertFalse(decide(load("superseded"))[0])
        self.assertFalse(decide(load("cancelled-with-runner"))[0])

    def test_success_is_left(self):
        self.assertFalse(decide(load("success"))[0])

    def test_real_failure_next_to_a_drop_stays_red(self):
        case = load("drop")
        job(case, "qt-app")["conclusion"] = "failure"
        rerun, reason = decide(case)
        self.assertFalse(rerun)
        self.assertIn("qt-app", reason)

    def test_macos_job_that_ran_stays_red(self):
        # A timeout or a failure had a runner and steps, whatever its conclusion.
        for conclusion in ("cancelled", "failure", "timed_out"):
            case = load("drop")
            macos = job(case, "addon (macos")
            ran = job(load("success"), "addon (macos")
            macos.update(conclusion=conclusion, runner_id=ran["runner_id"], steps=ran["steps"])
            self.assertFalse(decide(case)[0], conclusion)

    def test_runner_without_steps_or_steps_without_runner_stay_red(self):
        for field, value in (("runner_id", 1000001332), ("steps", ["Set up job"])):
            case = load("drop")
            job(case, "addon (macos")[field] = value
            self.assertFalse(decide(case)[0], field)

    def test_stale_pr_head_is_left(self):
        case = load("drop")
        self.assertFalse(decide(case, pr_heads={64: "0" * 40})[0])

    def test_pending_job_is_left(self):
        case = load("drop")
        job(case, "addon (windows")["status"] = "in_progress"
        self.assertFalse(decide(case)[0])

    def test_failing_gate_alone_is_left(self):
        # "CI passed" red with every other job green is not a drop.
        case = copy.deepcopy(load("success"))
        case["run"]["conclusion"] = "failure"
        job(case, "CI passed")["conclusion"] = "failure"
        self.assertFalse(decide(case)[0])

    def test_dropped_job_on_any_os_is_rerun(self):
        # The test is "never ran", not the OS: a dropped Windows job is re-run as well.
        case = load("drop")
        windows = job(case, "addon (windows")
        windows.update(conclusion="cancelled", runner_id=0, steps=[])
        self.assertTrue(decide(case)[0])


if __name__ == "__main__":
    unittest.main()
