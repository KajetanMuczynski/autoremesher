#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
"""Run autoremesher-cli once the way the add-on does (--stdin-control) and time what the user sees.

    python progress_probe.py <cli> <in.obj> <target> <out.json> [--cancel-at S] [--cpus 0-1] [-- extra CLI args]

Timestamps every "<percent>% done. <step>" line, so the JSON shows how far the progress bar is from the
share of time actually spent (`max_lag`: largest |percent - elapsed share|; `half_at`: share of the run
time when the bar reaches 50 %; `longest_silent`: longest gap between two lines and its step). With
`--cancel-at S` it writes "cancel" to stdin after S seconds, like the add-on's Esc, and records how long
the process takes to exit (`cancel_latency`) and in which step the cancel arrived; the add-on kills the
process after addon/quadami/worker.py CANCEL_GRACE_SECONDS, so a latency above that is a kill, not a
clean stop. `--cpus` runs it under `taskset -c` (oneTBB sizes its pool from the affinity mask), for
thread-scaling runs. Output files go next to out.json in <out.json>.d/.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time

PROGRESS = re.compile(r"^(\d+)% done\.(?: (.*))?$")


def main():
    args = sys.argv[1:]
    extra = []
    if "--" in args:
        extra = args[args.index("--") + 1:]
        args = args[:args.index("--")]
    if len(args) < 4:
        sys.exit(__doc__)
    cli, inp, target, out = args[:4]
    cancel_at, cpus = None, None
    rest = args[4:]
    for i in range(0, len(rest), 2):
        if rest[i] == "--cancel-at":
            cancel_at = float(rest[i + 1])
        elif rest[i] == "--cpus":
            cpus = rest[i + 1]
        else:
            sys.exit(f"unknown option {rest[i]}")
    tmp = out + ".d"
    os.makedirs(tmp, exist_ok=True)
    cmd = [cli, "-i", inp, "-o", os.path.join(tmp, "out.obj"), "--target-quads", target,
           "--report-json", os.path.join(tmp, "report.json"), "--stdin-control"] + extra
    if cpus:
        cmd = ["taskset", "-c", cpus] + cmd
    lines = []
    t0 = time.monotonic()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def reader():
        for line in p.stdout:
            m = PROGRESS.match(line.strip())
            if m:
                lines.append((time.monotonic() - t0, int(m.group(1)), m.group(2) or ""))
    th = threading.Thread(target=reader, daemon=True)
    th.start()
    sent = None
    while p.poll() is None:
        if cancel_at is not None and sent is None and time.monotonic() - t0 >= cancel_at:
            p.stdin.write("cancel\n")
            p.stdin.flush()
            sent = time.monotonic() - t0
        time.sleep(0.01)
    wall = time.monotonic() - t0
    th.join()
    try:
        status = json.load(open(os.path.join(tmp, "report.json"))).get("status")
    except (OSError, ValueError):
        status = None
    result = {"cmd": cmd, "wall": wall, "rc": p.returncode, "status": status}
    if lines:
        result["max_lag"] = max(abs(pct / 100 - t / wall) for t, pct, _ in lines)
        result["half_at"] = next((t / wall for t, pct, _ in lines if pct >= 50), None)
        gaps = [(lines[i + 1][0] - lines[i][0], lines[i][2]) for i in range(len(lines) - 1)]
        if gaps:
            result["longest_silent"] = max(gaps)
    if sent is not None:
        before = [step for t, _, step in lines if t <= sent]
        result.update(cancel_sent=sent, cancel_latency=wall - sent, step_at_cancel=before[-1] if before else None)
    result["progress"] = lines
    with open(out, "w") as fp:
        json.dump(result, fp, indent=0)
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in result.items()
                      if k not in ("progress", "cmd")}))


if __name__ == "__main__":
    main()
