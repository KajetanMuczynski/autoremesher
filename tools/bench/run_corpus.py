#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run AutoRemesher (ar_bench) over the corpus and collect one record per run.

    python run_corpus.py --corpus corpus.json --meshes meshes --bench build/ar_bench \
        --out runs --targets 2000,10000,50000 \
        [--only spot,koala] [--threads 4] [--repeat 1] [--tag name] [--no-metrics] \
        [--bench-arg --adaptivity=0 ...]

Writes runs/<mesh>/<tag>t<target>/{out.obj,bench.json,bench.log,stages.jsonl,metrics.json,record.json}
and runs/summary.json (all records). Runs the "corpus" set of corpus.json; quality A/B
of a change goes through ab.py, this script is for time and memory.
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = re.compile(r"^( *)(.+?): ([0-9.]+) ms$")
SIMPLIFIER = re.compile(r"RAN on (\d+) of (\d+) islands, (\d+) -> (\d+) triangles")
SINGULAR = re.compile(r"Simplified cross field singularities: (\d+) -> (\d+) \((\d+) pair")


def parse_phases(lines):
    phases, steps, extra = {}, {}, {}
    for line in lines:
        m = PHASE.match(line)
        if m and "Mesh simplifier" not in line:
            (steps if m.group(1) else phases)[m.group(2)] = float(m.group(3))
        if line.startswith("Cores kept busy"):
            extra["cores_busy"] = float(line.split(":")[1].split("(")[0])
        if line.startswith("Islands:"):
            extra["islands"] = int(line.split(",")[0].split(":")[1])
        m = SIMPLIFIER.search(line)
        if m:
            extra["decimated_islands"], _, extra["decimate_in"], extra["decimate_out"] = map(int, m.groups())
        if line.startswith("Mesh simplifier"):
            extra["decimate_ms"] = float(line.rsplit(",", 1)[1].replace("ms", ""))
    return phases, steps, extra


def summarize_stages(path):
    """Solver and rounding figures from the core's stage diagnostics (what probes.patch measured)."""
    recs = [json.loads(line) for line in open(path) if line.strip()]
    by_stage = {}
    for r in recs:
        if "solve_total_ms" not in r:
            continue
        s = by_stage.setdefault(r["stage"], {"solves": 0, "factorizations": 0, "max_n": 0, "max_factor_nnz": 0,
                                             "build_ms": 0.0, "factorize_ms": 0.0, "solve_ms": 0.0,
                                             "total_ms": 0.0, "kkt_fallbacks": 0})
        s["solves"] += int(r["solve_solves"])
        s["factorizations"] += int(r["solve_factorizations"])
        s["max_n"] = max(s["max_n"], int(r["solve_n"]))
        s["max_factor_nnz"] = max(s["max_factor_nnz"], int(r["solve_factor_nnz"]))
        s["kkt_fallbacks"] += int(r["solve_kkt_fallback"])
        for k in ("build_ms", "factorize_ms", "solve_ms", "total_ms"):
            s[k] += r["solve_" + k]
    # One rounding run per island cover solve: its passes are the island's rounding_iteration records.
    passes = {}
    for r in recs:
        if r["stage"] == "rounding_iteration":
            passes.setdefault(r.get("island"), []).append(r)
    rounding = [{"iterations": len(its), "integer_variables": int(its[0]["kernel_integers"]),
                 "fixed_per_iteration": [int(e["newly_fixed"]) for e in its],
                 "max_rounding_shift": max(e["max_rounding_shift"] for e in its),
                 "mean_rounding_shift": max(e["mean_rounding_shift"] for e in its)} for its in passes.values()]
    return {"solver_by_stage": by_stage, "rounding": rounding}


def run(cmd, log_path, timeout):
    start = time.time()
    with open(log_path, "w") as log:
        try:
            rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    return rc, time.time() - start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join(HERE, "corpus.json"))
    ap.add_argument("--meshes", required=True)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--targets", default="2000,10000,50000")
    ap.add_argument("--only")
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--repeat", type=int, default=1, help="timing repeats of the pristine run (median kept)")
    ap.add_argument("--tag", default="")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--no-metrics", action="store_true")
    ap.add_argument("--bench-arg", action="append", default=[], help="extra ar_bench option, e.g. --adaptivity=0")
    args = ap.parse_args()

    corpus = [m for m in json.load(open(args.corpus))["meshes"] if m.get("set", "corpus") == "corpus"]
    only = set(args.only.split(",")) if args.only else None
    extra = []
    for a in args.bench_arg:
        k, v = a.split("=", 1)
        extra += [k, v]
    summary_path = os.path.join(args.out, "summary.json")
    summary = json.load(open(summary_path)) if os.path.exists(summary_path) else []
    for mesh in corpus:
        if only and mesh["id"] not in only:
            continue
        src = os.path.join(args.meshes, mesh["file"])
        for target in [int(t) for t in args.targets.split(",")]:
            d = os.path.join(args.out, mesh["id"], "%st%d" % (args.tag, target))
            os.makedirs(d, exist_ok=True)
            base = [src, "--target-quads", str(target), "--threads", str(args.threads)] + extra
            reps = []
            for r in range(args.repeat):
                rc, wall = run([args.bench, "--input"] + base[:1] + ["--output", os.path.join(d, "out.obj"),
                               "--json", os.path.join(d, "bench.json"), "--stage-diagnostics",
                               os.path.join(d, "stages.jsonl")] + base[1:], os.path.join(d, "bench.log"),
                               args.timeout)
                if rc != 0 or not os.path.exists(os.path.join(d, "bench.json")):
                    reps.append({"rc": rc, "wall": wall})
                    break
                b = json.load(open(os.path.join(d, "bench.json")))
                reps.append({"rc": rc, "wall": wall, "remesh_s": b["time_s"]["remesh"], "bench": b})
            ok = [x for x in reps if "bench" in x]
            record = {"mesh": mesh["id"], "category": mesh["category"], "target": target, "tag": args.tag,
                      "threads": args.threads, "extra_args": extra, "rc": reps[-1]["rc"]}
            if ok:
                med = sorted(ok, key=lambda x: x["remesh_s"])[len(ok) // 2]
                b = med["bench"]
                record["bench"] = {k: v for k, v in b.items() if k != "phase_report"}
                record["remesh_s_runs"] = [x["remesh_s"] for x in ok]
                record["remesh_s_median"] = statistics.median(record["remesh_s_runs"])
                phases, steps, ext = parse_phases(b["phase_report"])
                record["phases_ms"], record["steps_ms"], record["phase_extra"] = phases, steps, ext
                log = open(os.path.join(d, "bench.log")).read()
                sing = [tuple(map(int, m)) for m in SINGULAR.findall(log)]
                record["singularity_simplifier"] = {"islands": len(sing), "before": sum(s[0] for s in sing),
                                                    "after": sum(s[1] for s in sing), "pairs": sum(s[2] for s in sing)}
            if ok and os.path.exists(os.path.join(d, "stages.jsonl")):
                record["stages"] = summarize_stages(os.path.join(d, "stages.jsonl"))
            if ok and not args.no_metrics:
                cmd = [sys.executable, "-I", os.path.join(HERE, "metrics.py"), "--input", src, "--output",
                       os.path.join(d, "out.obj"), "--target-quads", str(target), "--json", os.path.join(d, "metrics.json")]
                if mesh.get("sym"):
                    axis, center = mesh["sym"]
                    if center == "auto":
                        import numpy as np
                        sys.path.insert(0, HERE)
                        from metrics import read_obj
                        V, _ = read_obj(src)
                        a = "xyz".index(axis)
                        center = float((V[:, a].min() + V[:, a].max()) / 2)
                    cmd += ["--sym-axis", axis, "--sym-center", str(center)]
                subprocess.run(cmd, check=False)
                if os.path.exists(os.path.join(d, "metrics.json")):
                    record["metrics"] = json.load(open(os.path.join(d, "metrics.json")))
            json.dump(record, open(os.path.join(d, "record.json"), "w"), indent=1)
            summary = [r for r in summary if not (r["mesh"] == mesh["id"] and r["target"] == target
                                                  and r.get("tag", "") == args.tag)]
            summary.append(record)
            with open(summary_path + ".tmp", "w") as f:
                json.dump(summary, f, indent=1)
            os.replace(summary_path + ".tmp", summary_path)  # readers never see a half-written file
            q = record.get("bench", {}).get("result", {})
            print("%-14s t=%-6d rc=%s time=%.2fs quads=%s nonquads=%s" % (
                mesh["id"], target, record["rc"], record.get("remesh_s_median", float("nan")),
                q.get("quads"), q.get("non_quads")), flush=True)


if __name__ == "__main__":
    main()
