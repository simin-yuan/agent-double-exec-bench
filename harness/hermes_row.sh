#!/bin/sh
# hermes_row.sh — run the whole E1 Hermes Agent row (13 cells) against the local fault server.
#
# Requirements, set as environment variables (nothing machine-specific is hardcoded here):
#   HERMES_SRC  path to an exported checkout of NousResearch/hermes-agent, pinned to commit
#               c5a3c0f8767a72203363d249add14142dbcf3cc7. Export it WITHOUT touching a live
#               install:  git -C <clone> archive c5a3c0f... | tar -x -C "$HERMES_SRC"
#   HERMES_PY   the python executable that runs Hermes; it must be able to import dotenv,
#               openai, rich, httpx and pydantic (the venv next to a Hermes install works).
#               Pass the executable path itself, not a venv directory: a symlink to a venv's
#               python.exe loses the venv, because pyvenv.cfg resolves relative to the exe.
#
# Example:
#   HERMES_SRC=/tmp/hermes-c5a3c0f HERMES_PY=/tmp/hermes-venv/bin/python sh harness/hermes_row.sh
#
# Optional: CAP (per-cell wall cap in seconds, default 1500), JOBS (cells in flight, default 4).
# Nothing here reaches a real API: e1_client.py only points at 127.0.0.1:<port>.
set -u
: "${HERMES_SRC:?set HERMES_SRC to an exported hermes-agent checkout (commit c5a3c0f...)}"
: "${HERMES_PY:?set HERMES_PY to a python executable that can import Hermes}"
HERE=$(cd "$(dirname "$0")/.." && pwd -W)
PY="$HERMES_PY"
export PYTHONPATH="$HERMES_SRC"
export CAP="${CAP:-1500}"
JOBS="${JOBS:-4}"
LOG="$HERE/results/hermes_run.log"
mkdir -p "$HERE/results"

run_one() {  # $1=MODE $2=plain|stream
  if [ "$2" = stream ]; then
    sh "$HERE/harness/e1_run_win.sh" "$PY" hermes "$1" stream >> "$LOG" 2>&1
  else
    sh "$HERE/harness/e1_run_win.sh" "$PY" hermes "$1" >> "$LOG" 2>&1
  fi
}

n=0
for m in timeout 429-hard 429 429-neutral-body 500-neutral 500-ratelimit-text 500-text-429 after-tool-500 after-tool-drop; do
  run_one "$m" plain & n=$((n+1))
  [ $((n % JOBS)) -eq 0 ] && wait
done
wait
for m in drop after-tool-drop drop-chunked after-tool-drop-chunked; do
  run_one "$m" stream & n=$((n+1))
  [ $((n % JOBS)) -eq 0 ] && wait
done
wait
echo "DRIVER_DONE $(date)"
