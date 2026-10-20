#!/bin/sh
# e5_isolation.sh GROUP_CONFIG — E5 layering isolation: run only two cells
# (plain/500-neutral and stream/drop-chunked) with some retry layers switched off.
#
# usage: GROUP=name CONFIG=<yaml path|none> [STREAM_RETRIES=0] sh harness/e5_isolation.sh
#
# Config goes through $HERMES_HOME/config.yaml (HERMES_HOME is set per-cell by e1_client.py),
# which is how Hermes reads agent.api_max_retries / agent.auto_recovery_cycles.
# Nothing here reaches a real API: e1_client.py only points at 127.0.0.1:<port>.
set -u
: "${GROUP:?set GROUP}"
CONFIG="${CONFIG:-none}"
HERE=$(cd "$(dirname "$0")/.." && pwd -W)
PYBIN="${HERMES_PY:?set HERMES_PY}"
SRC="${HERMES_SRC:?set HERMES_SRC}"
export PYTHONPATH="$SRC"
export CAP="${CAP:-900}"
PY3=$(command -v python3 || command -v python)

run_cell() {  # $1=mode  $2=stream|''
  MODE=$1; ST=${2:-}
  OUT="$HERE/results/hermes/e5-isolation/$GROUP/$MODE"
  WORK="${TMPDIR:-/tmp}/e5-$GROUP-$MODE"
  rm -rf "$OUT" "$WORK"; mkdir -p "$OUT" "$WORK/.hermes"
  [ "$CONFIG" != none ] && cp "$CONFIG" "$WORK/.hermes/config.yaml"
  # Hermes materialises memory/config files into HERMES_HOME; keep WORK outside the
  # repo so a run interrupted mid-flight can never commit agent state as evidence.
  PORT=$($PY3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
  $PY3 "$HERE/harness/fault_server.py" "$PORT" "$MODE" "$OUT/server.jsonl" & SP=$!
  sleep 0.5
  S=$(date +%s.%N)
  ( cd "$WORK" && timeout -s KILL "$CAP" "$PYBIN" "$HERE/harness/e1_client.py" hermes "$PORT" "$WORK" $ST \
      > "$OUT/client.txt" 2>&1; echo "exit=$?" >> "$OUT/client.txt" )
  E=$(date +%s.%N)
  echo "wall_s=$($PY3 -c "print(round($E-$S,2))") cap_s=$CAP" >> "$OUT/client.txt"
  sleep 0.3; kill $SP 2>/dev/null; wait $SP 2>/dev/null
  [ -f "$WORK/counter.txt" ] && mv "$WORK/counter.txt" "$OUT/counter.txt"
  rm -rf "$WORK"
  echo "  $GROUP/$MODE requests=$(grep -c '"action"' "$OUT/server.jsonl" 2>/dev/null) $(tail -1 "$OUT/client.txt")"
}

run_cell 500-neutral ""
run_cell drop-chunked stream
echo "GROUP_DONE $GROUP $(date)"
