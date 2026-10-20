# results/hermes — Hermes Agent control row (E1), run on Windows

The E1 matrix in `results/e1/` was run by the cloud coding session on Linux. The `hermes` row
could not be run there (its working environment refused to execute code from an external
repository), so it was run here instead, on the same fault server and the same client.

## What was pinned

| Item | Value |
|---|---|
| Source | NousResearch hermes-agent |
| Commit | `c5a3c0f8767a72203363d249add14142dbcf3cc7` (2026-10-20 11:58:56 +0530) |
| How obtained | `git archive <commit> \| tar -x` from the local checkout — the installed copy that runs on this machine was **not** modified |
| Interpreter | `hermes-agent/venv/Scripts/python.exe` (Python 3.11.16; has dotenv/openai/rich/httpx/pydantic) |
| Harness | `harness/e1_client.py` (unchanged, the same file the other rows use) |
| Server | `harness/fault_server.py`, one fresh instance per cell on 127.0.0.1 |
| Network | loopback only. No real API, no keys, no spend |

Import resolution was verified before the run: with `PYTHONPATH` set to the exported tree,
both `run_agent` and `tools.registry` resolve inside `scratch/hermes-c5a3c0f/`, not the live install.

## Two Windows deviations (both in `harness/e1_run_win.sh`)

1. **Path form.** This host does not translate MSYS `/c/...` arguments for native programs, so
   every path handed to `python.exe` comes from `pwd -W` (`C:/...`). `e1_run.sh` passes POSIX
   paths and fails with a `can't open file` error pointing at a mangled `/c/...` path.
2. **Interpreter, not venv dir.** `e1_run.sh` calls `"$VENV/bin/python"`. Pointing a symlink at a
   venv's `python.exe` loses the venv — `pyvenv.cfg` is resolved relative to the executable, so
   the child falls back to the base interpreter and dies on `No module named 'dotenv'`.
   `e1_run_win.sh` takes the interpreter path directly.

No other logic differs: same fresh server per cell, same 25-minute cap, same
`server.jsonl` / `client.txt` / `counter.txt` layout.

## Layout

```
results/hermes/plain/<mode>/    the nine non-streaming cells
results/hermes/stream/<mode>/   the four streaming cells
```

The cloud session's `harness/e1_matrix.sh` writes such cells under `results/e1/<row>/<mode>/`;
these were moved here on purpose so the Hermes row cannot be mistaken for a cloud-run row, and so a
re-run of the matrix does not silently overwrite them.

## Redaction

Seven `client.txt` files contain a dump path Hermes prints on its own line
(`Request debug dump written to: ...`). The local repository prefix in that path has been replaced
with `<repo>`; nothing else in those files was changed, byte for byte, and no other file needed it.
`harness/hermes_row.sh` takes its paths from `HERMES_SRC` / `HERMES_PY` for the same reason.

## Reading the numbers

- `requests` = lines in `server.jsonl` that are chat requests (an `action` is set and the path is
  `/v1/chat/completions`) — the server's own count, not the client's claim. `server.jsonl` is a log,
  so `wc -l` overcounts: this row also contains one `/api/show` start-up probe per cell and, in the
  `timeout` cells, `action: null` lines that record the client disconnecting from a held request.
  `SUMMARY.md` has the full breakdown line by line.
- `tools` = lines in `counter.txt` (the tool's own side effect, not the framework's claim).
- `wall_s` = client wall time for the cell.

The `stream` variants are included because the matrix has them, but `e1_client.py`'s `hermes`
branch does not consult the `stream` flag — Hermes streams internally. Those four cells differ
from their plain counterparts only in the server's delivery mode, not in the client code path.
