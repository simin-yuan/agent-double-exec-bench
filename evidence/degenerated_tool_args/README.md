# Degenerated tool-call arguments — what a turn costs when the stream never recovers

A model can stream a tool call whose arguments turn into an endless run of whitespace. Every
delta is non-empty, so stall watchdogs count it as progress, and the request bills until the
provider's output cap. This scenario measures what one turn costs when **every** attempt
degenerates — the case a "retry and it recovers" test cannot see.

## Method

The measurement reproduces the command from the report it answers:

```
hermes chat -Q -t terminal --yolo -q "run echo hi"
```

The client is built in-process (`AIAgent(enabled_toolsets=["terminal"])` with yolo approvals
frozen, the same code path the CLI takes), and the local stub answers with a real `terminal`
tool call whose `arguments` degenerate into whitespace. The stub's command appends one line to
a marker file — a harmless, verifiable side effect — so "did the tool run?" is answered by the
filesystem, not by the harness trusting itself.

Two modes per build:

| mode | first attempt | resend | purpose |
|---|---|---|---|
| `once` | degenerates | honoured | recovery — also the **positive control** |
| `always` | degenerates | degenerates again | the pathological turn |

**The positive control has to pass before any "nothing ran" claim counts.** In `once` the
honoured call must run exactly once: marker file 1 line **and** executor probe 1 record. If the
instruments cannot see a call that definitely happened, their silence in `always` means nothing.

A second instrument watches the argument accumulator (`feed_log.jsonl`), which is where the
client actually consumed characters — this is what the "whitespace accepted" column counts.
Server-side byte counts are deliberately **not** used (see Limits).

## Measured (two rounds per cell, identical in every round)

`main` = the branch the PR targets, `branch` = the PR under review, `patched` = that branch
plus the follow-up fix. Stub cap: 200 KB of SSE per attempt.

| build | mode | provider requests | whitespace accepted | tool executions | last line the user sees |
|---|---|---|---|---|---|
| main | always | 5 | 706,560 | 0 | "The model's reply was cut off before it finished … so Hermes didn't run the incomplete action. Nothing was changed." |
| branch | always | 9 | 36,864 | 0 | "OpenRouter didn't answer after 3 attempts — it looks temporarily unavailable … send /retry" |
| patched | always | 6 | 24,576 | 0 | "OpenRouter sent a tool call made only of whitespace — nothing was run, and sending the same request again won't change the answer." |
| main | once | 1 | 141,403 | 1 | "Done" |
| branch | once | 1 | 4,185 | 1 | "Done" |
| patched | once | 1 | 4,186 | 1 | "Done" |

What the table says:

- **The cut works.** An attempt stops at ~4 KB of whitespace instead of running to the 200 KB
  the harness allows per attempt: 36,864 vs 706,560 across a whole turn.
- **The count moves the wrong way.** The abort is raised as a `RemoteProtocolError`, so it rides
  the transport retry ladder: 9 attempts on the PR branch where `main` spends 5, for output that
  is identical every time.
- **The last line is the wrong diagnosis.** It names a provider outage and recommends `/retry`
  for a stream that was connected the whole time and returned the same blank arguments on each
  attempt.
- **Recovery is intact.** In `once` every build ends with the terminal call executed exactly
  once and the user reading "Done" — the guard doesn't eat the good call.

`patched` reflects two changes: a resend budget of one for this error (2 per outer attempt
instead of 3), and exhausted-turn copy that names the blank tool call instead of the provider.
The outer retry policy is untouched.

## Rerun

```bash
python repro/run_real_tool_matrix.py \
    --base /path/to/base --branch /path/to/branch --patched /path/to/patched
python repro/collect_matrix_results.py --cells runs --out results/degenerated_tool_args_v2
```

Each cell writes `server.jsonl` (one line per provider request: kind, bytes written, whether the
client closed early), `feed_log.jsonl` (characters the client consumed), `marker.txt` and
`user_visible.txt`. Run every cell twice; the numbers should be identical.

## Limits

- The stub is local and deterministic: a cost/accounting harness, not a sample of real model
  behaviour. It cannot estimate how often real requests degenerate.
- **Do not read server-written bytes.** An aborting client stops at 4 KB, but the stub keeps
  writing into the socket buffer until the write errors, so each aborted request carries roughly
  64 KB of buffer in that number. Any measurement that uses "how much the server sent" to judge
  "how much the cut saved" underestimates the saving, and a real provider — which streams a few
  hundred characters per second — never gets that far ahead. Use the client-side count.
- Retry *timings* are meaningless here: every reconnect has nothing to wait for. Nothing in this
  file is a wall-clock claim.
- Attempt counts belong to the client configuration shipped here. Running the same client with a
  different tool selection changes how many streams a turn spends. An earlier version of this
  file quoted 5/9/6 from a configuration in which the stubbed tool was not visible to the agent
  at all — not a reachable state for a user — so those rows are void and this file's rows
  replace them.
- The 200 KB per-attempt figure is this harness's cap, not a provider's.

## Files

- `harness/fake_terminal_server.py` — stub server: real `terminal` call, `once`/`always` modes,
  per-request log.
- `harness/real_tool_client.py` — one turn, the CLI's toolset and approval settings, instruments
  on the argument accumulator and the tool executor.
- `repro/run_real_tool_matrix.py` — matrix driver (three builds × two modes × N rounds).
- `repro/collect_matrix_results.py` — turns cell directories into the table above.
- `results/degenerated_tool_args_v2/` — per-cell metrics and the exact text the user saw.
