# Degenerate tool-call arguments v3 — two paths, three builds

Same experiment as v2, extended to both request paths this change touches (chat completions and the
Codex/Responses stream), with a positive control per build, and one extra configuration: a backup
provider pointed at a healthy endpoint.

Each cell is one real agent turn. The stub answers every attempt with the same `terminal` call whose
arguments are whitespace only; the agent binary, toolset and prompt are the ones in the upstream PR
(`hermes chat -Q -t terminal --yolo -q "run echo hi"`). No API cost, no network.

| path | build | requests / turn | whitespace accepted per request | tool runs | final line the user reads |
|---|---|---|---|---|---|
| chat | `main` | 5 | 141,312 | 0 | "reply was cut off … didn't run the incomplete action" |
| chat | `#144745` | 9 | 4,096 | 0 | "didn't answer after 3 attempts — temporarily unavailable" |
| chat | `#144745` + patch | 6 | 4,096 | 0 | "tool call made only of whitespace — nothing was run" |
| Responses | `main` | 3 | 200,192 | 0 | "didn't answer after 3 attempts — temporarily unavailable" |
| Responses | `#144745` | 6 | 4,096 | 0 | same outage line |
| Responses | `#144745` + patch | 6 | 4,096 | 0 | "tool call made only of whitespace — nothing was run" |

Two rounds per cell, identical numbers. Positive control (`once` cells): first attempt degenerate,
then a valid call — the executor probe fires once and the marker file gains exactly one line, so
"tool runs = 0" above means the tool really did not run, not that the probe was broken.

## Backup provider configured (chat path, `always` cells)

| build | primary requests | fallback requests | tool runs | final line |
|---|---|---|---|---|
| `main` | 5 | 0 | 0 | cut-off line (no failover) |
| `#144745` | 9 | 2 | 1 | `Done` |
| `#144745` + patch | 6 | 2 | 1 | `Done` |

On the Responses path with the same backup configured, `#144745` never fails over: 6 primary
requests, 0 fallback requests, outage line — the abort never reaches the failover classifier there.

## How the numbers were taken

- **requests / turn**: one record per stream in `cells/<label>/server.jsonl` with a non-zero byte count.
- **whitespace accepted per request**: the arguments string the client actually assembled, read from
  the guard itself (`guard_watch`) and from the codex assembler (`assembler`). One stream can be
  observed by more than one accumulator instance, so `accepted.json` may hold the same value several
  times; the value is identical across instances, which is why `table.json` lists it deduplicated in
  `accepted_values`. `main` has no whitespace guard at all, hence the assembler-only reading there.
- **tool runs**: an executor probe (`executor_calls.jsonl`) plus a marker file the stub's command
  appends to (`marker_lines` in `result.json`). Both must agree.
- **final line**: `cells/<label>/user_visible.txt`, verbatim.

Raw per-delta logs are kept out of the repo (they are megabytes and add nothing); the aggregated
per-request values plus the raw server records are in `table.json` and each cell directory.

## What this does not show

- The stub is deterministic and instant, so no timing, no streaming-interleaving and no sampling
  variance is compared. A real model usually recovers on a retry; these cells are the persistent case.
- Nothing here says the cut itself is wrong — it is the abort path and the attribution that misfire.
- No claim about other providers' behaviour; only the two paths this change touches.
