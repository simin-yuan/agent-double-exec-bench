# smolagents contribution requirements (read from the local clone)

Source: `upstream/smolagents` at commit 96f33faaf028479119ec8d34507b47694cf14e34 (main, 2026-10-06):
`CONTRIBUTING.md`, `AGENTS.md`, `Makefile`, `.github/workflows/quality.yml`, `.github/workflows/tests.yml`.
There is **no pull-request template** in the repository (no `pull_request_template.md` anywhere, `.github/` has only
`ISSUE_TEMPLATE/`, `dependabot.yml`, `workflows/`).

## Process rules (CONTRIBUTING.md, "Before you open a pull request")
1. **Issue first.** Anything larger than a typo needs an issue labelled `status:accepted` by a maintainer before the
   patch is written. PRs without a linked accepted issue get `needs-issue` and are closed after 14 days.
2. **One open PR at a time** until the contributor's first PR is merged.
3. **Disclose use of an AI assistant** and stand behind the diff: a person must have read the change, run the tests,
   be able to explain it, and answer review comments. Bulk generated patches are closed.
   -> Owner's decision: this repository's own rules forbid naming tools in *this* repository; the upstream rule
      requires a disclosure in the upstream PR. Both can be satisfied only by the owner writing that PR text.
4. **First reviewable PR wins**, not the first submitted: complete, tested, correctly scoped.
5. **Core ships primitives, not integrations** (no new provider wrappers / built-in tools in core).
6. Bug issues must include OS, versions, a minimal self-contained reproduction and the full traceback;
   search existing issues first.

## Code rules
- AGENTS.md: follow OOP principles, be Pythonic, write unit tests for new functionality.
- Quality gate = `make quality` = `ruff check examples src tests` and `ruff format --check examples src tests`
  (CI: Python 3.12, `uv pip install "smolagents[quality] @ ."`). `make style` fixes formatting.
- Tests = `make test` = `pytest ./tests/` (CI: Python 3.10 and 3.12, `uv pip install "smolagents[test] @ ."`).
- Dev install: `uv pip install -e "smolagents[dev] @ ."`.
