"""Run the degenerate-arguments matrix the way the upstream report measures it.

Each cell reproduces the command from the upstream report:

    hermes chat -Q -t terminal --yolo -q "run echo hi"

against a local stub that returns a real ``terminal`` tool call whose arguments degenerate into
whitespace. The stub's command appends one line to a marker file, so "did the tool run?" has an
answer that does not depend on the harness believing itself.

Two modes per build:
  once   — the first attempt degenerates, the resend is honoured (recovery)
  always — every attempt degenerates (the pathological turn)

The recovery cell is the positive control: the honoured call must run exactly once, or the
"nothing ran" claim in the pathological cell means nothing.

    python repro/run_real_tool_matrix.py --base /p/base --branch /p/branch --patched /p/patched
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, "harness", "fake_terminal_server.py")
CLIENT = os.path.join(ROOT, "harness", "real_tool_client.py")
CAP_BYTES = 200_000


def free_port(start: int) -> int:
    for port in range(start, start + 200):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("no free port")


def run_cell(label: str, checkout: str, mode: str, workdir: str, port: int, rounds: int) -> list[dict]:
    rows = []
    for rnd in range(1, rounds + 1):
        cell = os.path.join(workdir, f"{label}_{mode}{rnd}")
        shutil.rmtree(cell, ignore_errors=True)
        os.makedirs(cell, exist_ok=True)
        server_log = os.path.join(cell, "server.jsonl")
        marker = os.path.join(cell, "marker.txt")
        srv = subprocess.Popen(
            [sys.executable, SERVER, str(port), mode, server_log, marker, str(CAP_BYTES)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(1.5)
            env = dict(os.environ, PYTHONPATH=checkout, PROBE_FEED="1")
            with open(os.path.join(cell, "client.out"), "w", encoding="utf-8") as out:
                subprocess.run([sys.executable, CLIENT, str(port), cell, marker],
                               env=env, stdout=out, stderr=subprocess.STDOUT, timeout=600)
        finally:
            srv.terminate()
            try:
                srv.wait(timeout=10)
            except subprocess.TimeoutExpired:
                srv.kill()
        result = os.path.join(cell, "result.json")
        if os.path.exists(result) and os.path.getsize(result):
            rows.append(json.load(open(result, encoding="utf-8")))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="checkout of the branch this PR targets")
    ap.add_argument("--branch", required=True, help="checkout of the PR branch")
    ap.add_argument("--patched", required=True, help="checkout of the PR branch + the fix under test")
    ap.add_argument("--workdir", default="runs")
    ap.add_argument("--rounds", type=int, default=2)
    args = ap.parse_args()

    os.makedirs(args.workdir, exist_ok=True)
    port = free_port(19100)
    for label, checkout in (("main", args.base), ("branch", args.branch), ("patched", args.patched)):
        for mode in ("once", "always"):
            rows = run_cell(label, checkout, mode, args.workdir, port, args.rounds)
            print(json.dumps({"build": label, "mode": mode, "rounds": len(rows),
                              "identical": len({json.dumps(r, sort_keys=True) for r in rows}) == 1}))
            port = free_port(port + 1)
    print("collect: python repro/collect_matrix_results.py --cells %s --out results/degenerated_tool_args_v2"
          % args.workdir)


if __name__ == "__main__":
    main()
