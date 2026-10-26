# Does a configured backup provider rescue the turn?

Every cell runs the real agent against a local stub, with one backup provider
(`fallback_model` pointing at a second local stub). Primary request counts come
from the stub's own request log; backup counts from the second stub.

| cell | build | primary requests | backup requests | turn completed | user saw |
|---|---|---|---|---|---|
| responses_main_degenerate_with_backup | main | 3 | 2 | True | Done |
| responses_branch_patch_degenerate_with_backup | 0a3807e + patch | 6 | 2 | True | Done |
| chat_main_degenerate_with_backup | main | 5 | 0 | False | The model's reply was cut off before it finished (it hit its |
| responses_main_dropped_stream_with_backup | main | 3 | 2 | True | Done |
| responses_main_connection_reset_with_backup | main | 8 | 2 | True | Done |
| chat_main_dropped_stream_with_backup | main | 4 | 0 | False | Hel
Hel
Hel
Hel |

Reading:

- A dropped stream on the Responses path does reach the backup: three primary requests, then the turn finishes on the backup.
- A TCP reset does the same.
- On the branch that adds the whitespace guard, a degenerate tool call also reaches the backup, on both paths, and the turn completes.
- The chat line on main has no guard: it treats the truncated stream as an output-length cut, so no error is raised and nothing switches.

Harness note: an earlier run of the Responses cells reported no switch because the client was built without a fallback model at all.
The fix here is in the harness, not in Hermes.
