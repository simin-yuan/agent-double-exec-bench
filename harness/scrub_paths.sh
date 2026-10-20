#!/bin/sh
# scrub_paths.sh VENVDIR FILE... — replace machine-specific paths in client logs with placeholders:
# VENVDIR -> $VENVS, the repository root -> $REPO. Applied to every client.txt before it is committed.
V=$1; shift; R=$(cd "$(dirname "$0")/.." && pwd)
for f in "$@"; do sed -i "s#$V#\$VENVS#g; s#$R#\$REPO#g" "$f"; done
