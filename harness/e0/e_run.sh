#!/bin/sh
# run.sh ROW SCENARIO CMD...  — start a fresh cut_server.py, run one client from an empty directory,
# and keep everything in results/ROW/SCENARIO: the server log, the client's output, and the file it wrote.
# In CMD, the word PORT becomes the server's port and REPO the repository root.
ROW=$1; SC=$2; shift 2
OUT="eresults/$ROW/$SC"; rm -rf "$OUT"; mkdir -p "$OUT/work"
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
TOOL=write_file; [ "$ROW" = "codex-cli" ] && TOOL=codex
python3 /tmp/d/e_server.py "$PORT" "$SC" "$OUT/server.jsonl" "$TOOL" & SP=$!
sleep 0.5
HERE=$(pwd)
CMD=$(echo "$*" | sed "s/PORT/$PORT/g; s#REPO#$HERE#g")
( cd "$OUT/work" && timeout 120 sh -c "$CMD" > ../client.txt 2>&1; echo "exit=$?" >> ../client.txt )
kill $SP 2>/dev/null; wait $SP 2>/dev/null
if [ -f "$OUT/work/notes.txt" ]; then mv "$OUT/work/notes.txt" "$OUT/notes.txt"; fi
rm -f "$OUT/work/calls.jsonl.tmp"; [ -f "$OUT/work/calls.jsonl" ] && mv "$OUT/work/calls.jsonl" "$OUT/tool_calls.jsonl"
rmdir "$OUT/work" 2>/dev/null; rm -rf "$OUT/work"
L=$([ -f "$OUT/notes.txt" ] && wc -l < "$OUT/notes.txt" || echo -)
echo "$ROW $SC notes.txt_lines=$L"
