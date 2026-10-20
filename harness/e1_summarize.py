"""Build results/e1/TABLE.md and results/e1/cells.json from results/e1/*/*/ (E1); results/SUMMARY.md quotes them.

Counts come from server.jsonl (written by fault_server.py, the source of truth); tool executions from counter.txt
(the tool's own side effect); the client's outcome (exception / final output / elapsed) from client.txt.

Per cell:
  requests        model requests the server received
  logical         distinct request bodies (body_sha); a retry of the same call re-sends the same body
  per_logical     requests per logical call, as a list (e.g. [3, 3, 3] for three calls retried twice each)
  inner_gaps      gaps (s) before requests whose x-stainless-retry-count > 0 (the OpenAI SDK's own retries)
  outer_gaps      gaps (s) before requests with retry count 0 that repeat an earlier body (a retry above the SDK)
  span_s          first to last request (s)
  tools           tool executions"""
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "results", "e1")


def cell(d):
    recs = [json.loads(l) for l in open(os.path.join(d, "server.jsonl"))] if os.path.exists(os.path.join(d, "server.jsonl")) else []
    reqs = [r for r in recs if "action" in r]
    closes = [r for r in recs if r.get("event") == "client_closed_held_connection"]
    order, seen, counts = [], set(), {}
    inner, outer = [], []
    for i, r in enumerate(reqs):
        sha = r["body_sha"]
        counts[sha] = counts.get(sha, 0) + 1
        if sha not in seen:
            seen.add(sha)
            order.append(sha)
        if i:
            gap = round(r["t"] - reqs[i - 1]["t"], 2)
            rc = int(r.get("retry_count_hdr") or 0)
            if rc > 0:
                inner.append(gap)
            elif counts[sha] > 1:
                outer.append(gap)
    client = open(os.path.join(d, "client.txt"), errors="replace").read() if os.path.exists(os.path.join(d, "client.txt")) else ""
    m = re.search(r"^RESULT (.*)$", client, re.M)
    res = json.loads(m.group(1)) if m else {}
    wall = re.search(r"wall_s=([\d.]+) cap_s=(\d+)", client)
    capped = bool(wall) and not m and float(wall.group(1)) >= float(wall.group(2)) - 2
    tools = sum(1 for _ in open(os.path.join(d, "counter.txt"))) if os.path.exists(os.path.join(d, "counter.txt")) else 0
    return {
        "requests": len(reqs), "logical": len(order), "per_logical": [counts[s] for s in order],
        "retry_hdrs": [r.get("retry_count_hdr") for r in reqs],
        "inner_gaps": inner, "outer_gaps": outer,
        "span_s": round(reqs[-1]["t"] - reqs[0]["t"], 2) if reqs else None,
        "held_closed_after_s": [round(c["t"] - reqs[j]["t"], 1) for j, c in zip(range(len(closes)), closes)] if closes else [],
        "tools": tools, "capped": capped, "wall_s": float(wall.group(1)) if wall else None,
        "client_elapsed_s": res.get("elapsed_s"),
        "outcome": ("CAPPED (killed at cap, still running)" if capped else
                    (res.get("exception") or "").split(":")[0] if res.get("exception") else
                    f"returned {res.get('final_output')!r}"[:60]),
    }


def main():
    cells = {}
    for row in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, row)
        if not os.path.isdir(p):
            continue
        for mode in sorted(os.listdir(p)):
            cells[f"{row}/{mode}"] = cell(os.path.join(p, mode))
    json.dump(cells, open(os.path.join(ROOT, "cells.json"), "w"), indent=1)
    lines = ["| cell (row/mode) | requests | per logical call | SDK-retry gaps (s) | gaps of retries above the SDK (s) "
             "| first→last request (s) | client wall (s) | tool runs | outcome |", "|---|---|---|---|---|---|---|---|---|"]
    for k, v in cells.items():
        f = lambda g: ", ".join(f"{x:g}" for x in g) if g else "–"
        lines.append(f"| {k} | {v['requests']} | {v['per_logical']} | {f(v['inner_gaps'])} | {f(v['outer_gaps'])} | "
                     f"{v['span_s']} | {v['wall_s']} | {v['tools']} | {v['outcome'].replace('|', '/')} |")
    open(os.path.join(ROOT, "TABLE.md"), "w").write("\n".join(lines) + "\n")
    if "--print" in sys.argv:
        for k, v in cells.items():
            print(k, json.dumps({x: v[x] for x in ("requests", "per_logical", "inner_gaps", "outer_gaps", "span_s", "tools", "outcome")}))


if __name__ == "__main__":
    main()
