# Rules for any agent working in this repository (read first, obey always)

## Identity and authorship (hard rules)
- Every commit: author and committer = `Simin (Simon) Yuan <yleven120@gmail.com>`.
  Run first: `git config user.name "Simin (Simon) Yuan" && git config user.email yleven120@gmail.com`
- NEVER add `Co-Authored-By`, "Generated with", tool names, AI names or agent names to commits, files, PR text or comments.
- Before every push run: `git log --format='%an <%ae>%n%b' origin/main..HEAD | grep -iE 'co-authored|generated|claude|anthropic|gpt|copilot' && echo STOP`
  If it prints STOP, rewrite those commits before pushing.
- Never mention how or by whom the tests were run. Never mention usage data, memory, consciousness or personal projects.

## Scope
- Work ONLY in this repository. Do not open issues, PRs, comments or forks anywhere else. Do not change repo visibility or settings.
- Work on branch `e1`; push only to `e1`. Never push to `main`.
- `evidence/` is append-only: never edit or delete an existing file there.
- Stop and report instead of improvising when a stop condition in TASKS.md is hit.

## Engineering
- Zero spend: fake local servers only, never a real model API, never real API keys.
- Pin every framework version you test and record it next to its results.
- One measurement = server-side log written by the fake server (source of truth) + client stdout. Never infer counts from client output.

## Before this repository can ever be made public (owner's step, not yours)
Scan the FULL history, not only the working tree: `git log --all -p` and every blob, for names, paths, keys, tokens,
AI/agent names and Co-Authored-By. Visibility changes only after that scan is clean.
