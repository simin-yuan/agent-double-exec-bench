"""Collect the real-tool matrix results into publishable artifacts (no local paths).

Reads the per-cell directories written by the driver, keeps only what a reader needs:
request kinds per cell, whitespace the client accepted, executions observed by two
independent instruments (executor probe + marker file), and the exact text the user saw.

    python repro/collect_matrix_results.py --cells /path/to/cells --out results/degenerated_tool_args_v2
"""
from __future__ import annotations

import argparse
import json
import os


def cell_row(cell_dir: str) -> dict | None:
    result = os.path.join(cell_dir, "result.json")
    if not os.path.exists(result) or not os.path.getsize(result):
        return None
    with open(result, encoding="utf-8") as fh:
        res = json.load(fh)

    kinds: dict[str, int] = {}
    server = os.path.join(cell_dir, "server.jsonl")
    if os.path.exists(server):
        with open(server, encoding="utf-8") as fh:
            for line in fh:
                try:
                    kind = json.loads(line).get("kind")
                except Exception:
                    continue
                kinds[kind] = kinds.get(kind, 0) + 1

    # What the client actually consumed, read where the parser consumed it.
    whitespace = chunks = 0
    feed = os.path.join(cell_dir, "feed_log.jsonl")
    if os.path.exists(feed):
        with open(feed, encoding="utf-8") as fh:
            for line in fh:
                obj = json.loads(line)
                whitespace += obj.get("arg_len") or 0
                chunks += 1

    visible = os.path.join(cell_dir, "user_visible.txt")
    text = ""
    if os.path.exists(visible):
        with open(visible, encoding="utf-8") as fh:
            text = fh.read().strip()

    return {
        "cell": os.path.basename(cell_dir),
        "degenerate_attempts": kinds.get("degenerate", 0),
        "final_text_replies": kinds.get("final_text", 0),
        "whitespace_accepted": whitespace,
        "arg_chunks": chunks,
        "executor_probe_records": res.get("probe_records"),
        "marker_file_lines": res.get("marker_lines"),
        "user_visible": text,
        "user_visible_last_line": text.splitlines()[-1] if text else "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", required=True, help="directory holding one subdirectory per cell")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for name in sorted(os.listdir(args.cells)):
        d = os.path.join(args.cells, name)
        if os.path.isdir(d):
            row = cell_row(d)
            if row:
                rows.append(row)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "table.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")

    for row in rows:
        d = os.path.join(args.out, "cells", row["cell"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "metrics.json"), "w", encoding="utf-8") as fh:
            json.dump({k: v for k, v in row.items() if k != "user_visible"}, fh, indent=1,
                      ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        with open(os.path.join(d, "user_visible.txt"), "w", encoding="utf-8") as fh:
            fh.write(row["user_visible"] + "\n")
    print(json.dumps({"cells": len(rows), "out": args.out}))


if __name__ == "__main__":
    main()
