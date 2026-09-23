# M1.1: make `uv run pytest -q` work

## 1. Why this exists

Roadmap M1.1 (`docs/ROADMAP.md`). On a fresh checkout `uv run pytest -q` fails with 13 collection
errors (`No module named 'structlog'`): pytest is only in `[project.optional-dependencies] dev`, so
`uv run` falls through to a system pytest that cannot see the project's packages. With
`uv run --extra dev pytest -q` the suite is **188 passed**.

## 2. The work

1. In `pyproject.toml`, move `pytest`, `pytest-asyncio`, `pytest-cov` and `ruff` from
   `[project.optional-dependencies] dev` to a PEP 735 `[dependency-groups] dev` table (uv installs
   the `dev` group by default). Keep version constraints unchanged. Update `uv.lock` accordingly.
2. README: the test command becomes `uv run pytest -q`.
3. `.env.example`: list the variable names the code actually reads (`WORDPRESS_URL`,
   `WORDPRESS_USER`, `WORDPRESS_APP_PASSWORD`, `DEVTO_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`,
   `OPENROUTER_API_KEY`, `OLLAMA_MODEL`, `LOG_LEVEL`); keep the old `WP_*` names only if code reads
   them (grep first). Names only, no values.

## 3. Completion criteria

- [ ] `uv run pytest -q` passes with 188 tests (or more), 0 failed, 0 skipped.

## 4. Rules for this run

- This run is **NON-INTERACTIVE**. Any tool call that needs a confirmation is rejected outright and
  the run ends mid-task. The lock update must come from what is already in the uv cache; if `uv lock`
  needs a download, stop and say so in the Status row instead.
- Do not read outside this working directory. Never read or print `.env`.
- Never use `git -C` or `git -c`; run git from the worktree.
- These are the only commands available to you: `uv run pytest`, `uv lock`, `git status`, `git diff`,
  `git log`, `git show`, `git add`, `git commit`, `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `mkdir`.
- Work only on your `directive/<slug>` branch. **Never commit to main, never push, never deploy.**
- If a tool call is genuinely blocked, stop and write why in the Status row.

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | In progress |
| Assigned to | devin |
| Branch | directive/rfd-blog-engine-blog-m1-1-test-command-directive |
| Base branch | - |
| Base commit | bcde8ece241cca81e045353b45715a155eff2b1a |

**Status log**
- 2026-09-23 07:50 · robert-claude · none → Queued — Fix first (work order): fresh-checkout test command broken. Robert: keep projects moving.
- 2026-09-23 12:22 · robert-claude · Queued → Approved
- 2026-09-23 12:22 · dispatcher · Approved → In progress — dispatched devin on personal-laptop in C:\GitHub\.worktrees\RFD_Blog_Engine--rfd-blog-engine-blog-m1-1-test-command-directive; base origin/main (local main differs)
<!-- queue:end -->
