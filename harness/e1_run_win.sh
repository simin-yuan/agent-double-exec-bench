#!/bin/sh
# e1_run_win.sh PYTHON FRAMEWORK MODE [stream] — Windows-adapted copy of e1_run.sh.
# Differences from e1_run.sh: (1) takes the python executable path directly instead of a venv
# directory — a symlink to a venv's python.exe loses the venv (pyvenv.cfg is resolved relative
# to the executable), and (2) every path handed to a native python.exe comes from `pwd -W`
# (C:/...) because this host does not translate MSYS /c/... arguments for native programs.
PYBIN=$1; FW=$2; MODE=$3; ST=${4:-}
CAP=${CAP:-1500}
HERE=$(cd "$(dirname "$0")/.." && pwd -W)
ROW=$FW; [ "$ST" = stream ] && ROW=$FW-stream
OUT="$HERE/results/e1/$ROW/$MODE"; rm -rf "$OUT"; mkdir -p "$OUT/work"
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
python3 "$HERE/harness/fault_server.py" "$PORT" "$MODE" "$OUT/server.jsonl" & SP=$!
sleep 0.5
S=$(date +%s.%N)
( cd "$OUT/work" && timeout -s KILL "$CAP" "$PYBIN" "$HERE/harness/e1_client.py" "$FW" "$PORT" "$OUT/work" $ST \
    > ../client.txt 2>&1; echo "exit=$?" >> ../client.txt )
E=$(date +%s.%N)
echo "wall_s=$(python3 -c "print(round($E-$S,2))") cap_s=$CAP" >> "$OUT/client.txt"
sleep 0.3; kill $SP 2>/dev/null; wait $SP 2>/dev/null
[ -f "$OUT/work/counter.txt" ] && mv "$OUT/work/counter.txt" "$OUT/counter.txt"
rm -rf "$OUT/work"
echo "$ROW $MODE requests=$(grep -c '\"action\"' "$OUT/server.jsonl") tools=$([ -f "$OUT/counter.txt" ] && wc -l < "$OUT/counter.txt" || echo 0) $(tail -1 "$OUT/client.txt")"
