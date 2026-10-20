"""Run one crewAI cell against the public harness fault server (E3 before/after).

usage: python run_cell.py MODE OUTDIR VENV_PY HARNESS_REPO
Writes OUTDIR/server.jsonl, OUTDIR/client.txt, OUTDIR/counter.txt and prints the
chat request count, which is read from server.jsonl only.
"""
import json
import os
import pathlib
import socket
import subprocess
import sys
import time

mode, outdir, venv_py, repo = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3], pathlib.Path(sys.argv[4])
outdir.mkdir(parents=True, exist_ok=True)
s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
log = outdir / "server.jsonl"
srv = subprocess.Popen(
    [sys.executable, str(repo / "harness" / "fault_server.py"), str(port), mode, str(log)],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(1.0)
work = outdir / "work"
work.mkdir(exist_ok=True)
env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
t0 = time.time()
try:
    r = subprocess.run(
        [venv_py, str(repo / "harness" / "e1_client.py"), "crewai", str(port), str(work)],
        cwd=str(work), capture_output=True, text=True, timeout=1500, env=env,
    )
    txt = (r.stdout or "") + (r.stderr or "") + f"exit={r.returncode}\n"
except subprocess.TimeoutExpired:
    txt = "exit=TIMEOUT\n"
txt += f"wall_s={round(time.time() - t0, 2)}\n"
(outdir / "client.txt").write_text(txt, encoding="utf-8")
time.sleep(0.3)
srv.terminate()
try:
    srv.wait(timeout=10)
except subprocess.TimeoutExpired:
    srv.kill()
cf = work / "counter.txt"
if cf.exists():
    (outdir / "counter.txt").write_text(cf.read_text(encoding="utf-8"), encoding="utf-8")
rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
reqs = [x for x in rows if "chat/completions" in (x.get("path") or "") or "responses" in (x.get("path") or "")]
tools = len((outdir / "counter.txt").read_text(encoding="utf-8").splitlines()) if (outdir / "counter.txt").exists() else 0
print(f"{mode} requests={len(reqs)} tools={tools} {txt.strip().splitlines()[-1] if txt.strip() else ''}")
