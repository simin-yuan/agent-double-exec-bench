#!/bin/sh
# run_e1.sh MODE RUN — one double-exec cell with NAT. Mirrors agent-double-exec-bench/harness/e1_run.sh
# (fresh fault_server.py per cell, client capped at CAP s, server log is the source of truth).
# Env: BENCH_A (agent-double-exec-bench checkout), NATPY (python of the NAT venv), OUTBASE, CAP (default 1500).
MODE=$1; RUN=$2; CAP=${CAP:-1500}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT="$OUTBASE/nat-tool_calling_agent-stream/$MODE/run$RUN"; rm -rf "$OUT"; mkdir -p "$OUT/work"
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
python3 "$BENCH_A/harness/fault_server.py" "$PORT" "$MODE" "$OUT/server.jsonl" & SP=$!
sleep 0.5
S=$(date +%s.%N)
( cd "$OUT/work" && NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost timeout -s KILL "$CAP" \
    "$NATPY" "$HERE/nat_bench.py" e1 "$PORT" "$OUT/work" > ../client.txt 2>&1; echo "exit=$?" >> ../client.txt )
E=$(date +%s.%N)
echo "wall_s=$(python3 -c "print(round($E-$S,2))") cap_s=$CAP" >> "$OUT/client.txt"
sleep 0.3; kill $SP 2>/dev/null; wait $SP 2>/dev/null
[ -f "$OUT/work/counter.txt" ] && mv "$OUT/work/counter.txt" "$OUT/counter.txt"
rm -rf "$OUT/work"
echo "$MODE run$RUN requests=$(grep -c '"action"' "$OUT/server.jsonl") tools=$([ -f "$OUT/counter.txt" ] && wc -l < "$OUT/counter.txt" || echo 0) $(tail -1 "$OUT/client.txt")"
