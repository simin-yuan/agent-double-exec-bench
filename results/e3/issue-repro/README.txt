The minimal repro from upstream/ISSUE_DRAFT.md, wrapped only to take the port and print the outcome and elapsed time.
Installed package: unpatched smolagents main @ 96f33fa (non-editable install of a clean worktree), openai 2.54.0, Python 3.13.
Each run: python3 harness/fault_server.py PORT MODE <mode>-server.jsonl & ; python repro.py PORT > <mode>-output.txt
  ok   -> the scripted text reply, 1 request (sanity check that the snippet runs)
  429  -> raised RateLimitError after 9 requests (x-stainless-retry-count 0,1,2 three times), elapsed 1063.7 s
