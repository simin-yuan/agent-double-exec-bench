#!/bin/sh
# e1_matrix.sh VENVDIR [JOBS] — run every E1 cell, JOBS at a time (default 16), each with its own server and port.
# VENVDIR holds one venv per framework: agents lg smol crew pai adk (see results/e1/VERSIONS.txt).
V=$1; J=${2:-16}; HERE=$(cd "$(dirname "$0")/.." && pwd)
ROWS="agents:agents-chat agents:agents-responses lg:langgraph smol:smol-openai smol:smol-litellm crew:crewai pai:pydantic-ai adk:adk"
MODES="timeout 429-hard 429 429-neutral-body 500-neutral 500-ratelimit-text 500-text-429 drop after-tool-500 after-tool-drop"
{ for m in $MODES; do for r in $ROWS; do echo "$V/${r%%:*} ${r#*:} $m"; done; done
  for m in drop after-tool-drop drop-chunked after-tool-drop-chunked; do for r in $ROWS; do echo "$V/${r%%:*} ${r#*:} $m stream"; done; done
} | xargs -P "$J" -L 1 sh "$HERE/harness/e1_run.sh"
