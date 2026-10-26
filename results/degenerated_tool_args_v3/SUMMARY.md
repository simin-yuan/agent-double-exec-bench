# Degenerate tool-call arguments v3 — two paths, three builds

Same experiment as v2, extended to both request paths this change touches (chat completions and the
Codex/Responses stream), with a positive control per build, and one extra configuration: a backup
provider pointed at a healthy endpoint.

Each cell is one real agent turn. The stub answers every attempt with the same `terminal` call whose
arguments are whitespace only. No API cost, no network.

**How the cells were produced.** The runner instantiates the same agent entry point the CLI uses
(`run_agent.AIAgent`) and passes the settings that `hermes chat -Q -t terminal --yolo -q "run echo hi"`
would apply: `enabled_toolsets=["terminal"]`, yolo mode, quiet mode, one user query, the same stub
endpoint, no backup provider unless the row says otherwise. The `hermes chat` binary itself is not what
drove these six rows, so what they measure is the agent loop, not CLI argument parsing or config
loading. The table below was re-run through the actual binary afterwards; see
[Re-run through the real CLI](#re-run-through-the-real-cli-2026-10-27).

| path | build | requests / turn | whitespace accepted per request | tool runs | final line the user reads |
|---|---|---|---|---|---|
| chat | `main` | 5 | 141,312 | 0 | "reply was cut off … didn't run the incomplete action" |
| chat | `#144745` | 9 | 4,096 | 0 | "didn't answer after 3 attempts — temporarily unavailable" |
| chat | `#144745` + patch | 6 | 4,096 | 0 | "tool call made only of whitespace — nothing was run" |
| Responses | `main` | 3 | 200,192 | 0 | "didn't answer after 3 attempts — temporarily unavailable" † |
| Responses | `#144745` | 6 | 4,096 | 0 | same outage line |
| Responses | `#144745` + patch | 6 | 4,096 | 0 | "tool call made only of whitespace — nothing was run" |

† On the Responses path `main` already ends with the outage line: the stub stops the stream at its
own byte cap, and that path reads an unterminated stream as a transport failure. That is the harness
being fair to it, not a finding about `main`. What `#144745` changes there is that the stop becomes
Hermes's own decision — reported the same way as a provider fault — and that each attempt now costs
two streams instead of one (6 requests against 3).

Two rounds per cell, identical numbers. Positive control (`once` cells): first attempt degenerate,
then a valid call — the executor probe fires once and the marker file gains exactly one line, so
"tool runs = 0" above means the tool really did not run, not that the probe was broken.

## Backup provider configured (chat path, `always` cells)

| build | primary requests | fallback requests | tool runs | final line |
|---|---|---|---|---|
| `main` | 5 | 0 | 0 | cut-off line (no failover) |
| `#144745` | 9 | 2 | 1 | `Done` |
| `#144745` + patch | 6 | 2 | 1 | `Done` |

**Corrected 2026-10-26.** An earlier version of this page said the Responses path "never fails over".
That was wrong: the client used for those five lines was built without a backup model, so that side
had no backup configured at all. Re-run with a backup configured
([results/responses_fallback](../responses_fallback/SUMMARY.md)): `main` 3 primary + 2 backup,
`#144745` 6 + 2, `#144745` + patch 6 + 2, a mid-stream cut 3 + 2, a first-frame TCP reset 8 + 2. Every
case finished on the backup and the user read `Done`. The request counts in the table above are
unaffected; only the failover sentence was wrong.

## The shape the PR describes (normal opening, then degeneration)

The cells above answer every attempt with a tool call that is whitespace from the first character.
The failure described upstream starts normally and then degenerates, so the same four cells were run
again with that shape: arguments begin `{"command": "echo hi"` and then stream whitespace deltas for
the rest of the stream (`partial_shape/`).

| path | build | requests / turn | final line the user reads |
|---|---|---|---|
| chat | `#144745` | 9 | outage line, detail: "tool-call arguments degenerated into 4096 consecutive whitespace characters" |
| chat | `#144745` + patch | 6 | "The model sent a tool call whose arguments degenerated into whitespace …" |
| Responses | `#144745` | 6 | outage line, same detail |
| Responses | `#144745` + patch | 6 | same new sentence |

Same counts as the whitespace-from-the-start shape, and the cut still lands at 4096 on both builds,
so the numbers in the report do not depend on how the degeneration is introduced.

## Scope of the patch

The patch caps a degenerate-arguments abort at one reconnect per stream attempt. That is a real
reduction on chat (3 streams per attempt → 2). On the Responses wire the stream layer already allows
exactly one reconnect (`max_stream_retries = 1`), so the request count there is unchanged and only
the wording differs; taking it lower would mean editing the turn-level retry policy, which the patch
does not touch on either path.

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

## Re-run through the real CLI (2026-10-27)

Every row in the table above was re-run through the actual `hermes chat` binary, twice, against the
same stub and the same prompt, in a hermes home of its own:

| path | build | requests through `hermes chat` (run 1 / run 2) | requests in the table above |
|---|---|---|---|
| chat | `main` 9b904dcc | 5 / 5 | 5 |
| chat | `#144745` 0a3807ec | 9 / 9 | 9 |
| chat | `#144745` + patch 53b577f4 | 6 / 6 | 6 |
| Responses | `main` 9b904dcc | 3 / 3 | 3 |
| Responses | `#144745` 0a3807ec | 6 / 6 | 6 |
| Responses | `#144745` + patch 53b577f4 | 6 / 6 | 6 |

The counts agree row for row; nothing in the table changed. Three things about how this was run, so a
reader can judge it:

- **Counting.** Requests are counted from the stub's own log, not from client output. The Responses stub
  writes two log lines per request (one carries the request path), so the count is taken from the lines
  that carry a path; counting every line would have doubled it.
- **Which build actually ran.** The CLI re-executes itself into its managed runtime on first start, and
  that path drops `PYTHONPATH`, so a cold home loads the installed build instead of the checkout under
  test. The probe log records the `agent/__init__.py` each turn loaded; the values in this table come
  only from turns whose probe line points at the checkout named in the row. Cold-home runs are discarded.
- **The Responses rows** use a custom provider entry that declares `api_mode: codex_responses` and points
  at the stub. The built-in `openai-codex` provider wants stored OAuth credentials, which is not something
  this bench should hold; the transport is the same one either way, the provider entry is not.

The backup-provider rows above were not re-run through the binary; they are harness-only.
