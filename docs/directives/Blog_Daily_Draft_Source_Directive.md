# Daily draft source: free-lane generation only, sourced from real shipped work

## 1. Why this exists

Robert, 2026-09-27: a daily loop should write drafts automatically, sourced from real repo
activity — never invented — for Claude to fact-check and Robert to approve. See
`docs/superpowers/specs/2026-09-27-daily-draft-loop.md` Stage A for the full design. Two problems
block it today: (1) nothing turns real shipped work into an inventory candidate, and (2) the
generation model router's free-lane fallback quietly includes a paid model.

## 2. Scope

- `blog_engine/infra/model_router.py` (the `generation` role's candidate list only)
- `blog_engine/core/generator.py` (`RFD_CONTENT_FRAME_PROMPT` only — add one instruction, do not
  restructure the frame)
- New file `source_scan.py` under `blog_engine/core/`
- New `blog_engine/cli.py` command `generate-daily`
- Tests under `tests/`

## 3. The work

1. **Fix the paid-model leak.** In `model_router.py`, `role_models["generation"]`'s OpenRouter
   entry is `("openrouter", "anthropic/claude-3-haiku")` — a paid model. Replace it with a
   free-tier OpenRouter slug (an id ending `:free`, matching the convention in
   `C:/Github/AgentFlow/docs/superpowers/specs/2026-09-24-free-lane.md`; pick any currently-free general-purpose
   instruct model, e.g. a Llama or Gemma `:free` variant — check what's actually listed free at
   https://openrouter.ai/api/v1/models is out of scope for this offline run, so pick a
   well-known `:free`-suffixed slug and leave a one-line comment naming it explicitly as free-tier
   so the next person can verify). Do the same check for the `"default"` role's OpenRouter entry
   (`meta-llama/llama-3-8b-instruct` — verify it is not a paid-only listing; if unsure, also give
   it a `:free` suffix). Add a test asserting every model id in `role_models` for role
   `"generation"` and `"default"` either has no `:free` requirement (groq/gemini/ollama, which are
   free by construction in this repo's usage) or, for `"openrouter"` entries, ends in `:free`.
2. **Prompt instruction.** In `generator.py`, add one sentence to `RFD_CONTENT_FRAME_PROMPT`,
   placed right before "Write the full blog post": *"For any number, date, name, or quote you
   cannot find in the post details or context given above, write
   `[ROBERT: fill in — <what's missing>]` instead of inventing it. Never state a fact you were not
   given."* Do not otherwise change the frame's structure, word count, or banned-words list.
   Add/extend a test on `_build_prompt` asserting this sentence is present in the rendered prompt.
3. **`source_scan.py`** (new module in `blog_engine/core/`):
   - `ALLOWED_REPOS: list[str]` — a small constant list of absolute repo paths this scan is allowed
     to read (start with just this repo's own path and `C:/Github/AgentFlow`; read from a
     `SOURCE_SCAN_REPOS` env var if set — comma-separated absolute paths — else fall back to the
     constant). Never scan a path not in this list.
   - `scan_recent_activity(repos: list[str] = None, since_days: int = 2, max_candidates: int = 2) -> list[dict]`:
     for each repo, run `git -C <repo> log --since="<since_days> days ago" --oneline --no-merges`
     (use `subprocess.run`, capture output, never raise on a repo that isn't a git repo — skip it
     and log a warning) and turn each commit line into a candidate dict:
     `{"post_id": <derived, e.g. "src-<shortsha>">, "title": <derived from subject, truncated>,
     "notes": <the raw commit subject, verbatim>, "category": "building", "tags": [],
     "source_repo": repo, "source_ref": <full sha via `git -C <repo> rev-parse <shortsha>`>}`.
     Skip merge/queue-status commits (subjects starting `Merge ` or `Queue: `) — they are not
     "shipped work," they're bookkeeping. Return at most `max_candidates` candidates, most recent
     first. Return `[]` if nothing qualifies — never fabricate a candidate when history is empty.
   - `register_candidates(candidates: list[dict], inventory: InventoryManager) -> list[str]`: for
     each candidate, skip if `inventory.get_post(post_id)` already exists (already registered —
     idempotent, safe to run daily); otherwise call `inventory.add_post(...)` with the candidate's
     fields. Returns the list of newly-registered post_ids.
4. **CLI command** `generate-daily` in `blog_engine/cli.py`:
   - No options beyond `--since-days` (default 2) and `--dry-run` (prints candidates, registers
     nothing, generates nothing).
   - Calls `scan_recent_activity`, then `register_candidates`, then for each newly-registered
     post_id calls the **existing, unchanged** `PostGenerator.generate(post_id)`.
   - If `scan_recent_activity` returns `[]`, print exactly `NO_CANDIDATES` and exit 0 (this exact
     string is required — it is the `skip_if` value a future AgentFlow `[specialists.jobs]` entry
     will match on; do not change or decorate it).
   - Otherwise print one line per generated draft: `generated: <post_id> <title>`.

## 4. What NOT to do

- Do not call any paid model, ever, in this run or in the code you write — verify by reading
  `model_router.py`'s final state, not by running it (no network in this run).
- Do not touch `blog_engine/core/publisher.py`, `content_guard.py`, `draft_manager.py`'s
  approve/publish paths, or anything under `blog_engine/tools/publish_tools.py`. This directive is
  generation-only; the publish gate is out of scope and already correct.
- Do not add real repos to `ALLOWED_REPOS` beyond `RFD_Blog_Engine` and `AgentFlow` — Robert
  expands the list later.
- Do not commit anything under `data/drafts/`, `data/inventory/`, or `data/fact_checks/` (all
  gitignored already — verify `git status` shows none before committing).
- Do not call WordPress, Dev.to, Groq, Gemini, or OpenRouter for real in tests — mock `route()`
  the way existing generator tests do (read `tests/test_generator.py` first for the pattern).
- Do not read or print any `.env` value.
- Create no scratch or debug files. If one is unavoidable, put it under `.devin-scratch/` and leave
  it there.

## 5. Verification

```
uv run pytest -q
```
Record the exact count of passing and failing tests before your changes and after. All existing tests must still
pass; add new tests for: the paid-model assertion (item 1), the prompt sentence (item 2),
`scan_recent_activity` on a fixture git repo with temporary commits (use `tmp_path` + real `git
init`/`git commit` inside the test, not a mock of `subprocess` — this is a case where testing
against a real throwaway repo is more honest than mocking git), `register_candidates` idempotency
(running it twice registers nothing the second time), and `generate-daily --dry-run` printing
candidates without touching `data/inventory/`.

## 6. Rules for this run

- This run is **NON-INTERACTIVE**. Any tool call that needs confirmation is rejected outright and
  the run ends mid-task. Do not install, download, or fetch anything — no network calls of any
  kind, including to check which OpenRouter models are actually free; pick a plausible `:free`
  slug and note it needs human verification.
- Python is 3.12 via uv; always `uv run`, never bare `python`. Confirm with
  `uv run python --version` before writing any test command.
- Never run `uv run python -c ...` — write a test and run `uv run pytest -q <file>` instead.
- Never use `git -C` from outside a test fixture context in the source you write for `cli.py`
  itself unless it's the documented `git -C <repo> log` call in `source_scan.py` — that one is
  required by this spec.
- Work only on your `directive/<slug>` branch; commit and push that branch when done. **Never
  commit to main, never merge, never deploy, never publish anything, never touch WordPress.**
- Update this directive's Status row when you finish or stop partway. If a tool call is genuinely
  blocked, stop and write why in the Status row.

## 7. Completion criteria

- [ ] `model_router.py` generation/default OpenRouter entries are free-tier (`:free` suffix) or
      justified in a code comment
- [ ] `RFD_CONTENT_FRAME_PROMPT` includes the `[ROBERT: ...]`-on-uncertainty instruction
- [ ] `source_scan.py` exists, scans only `ALLOWED_REPOS`, returns real commit-derived candidates
      or `[]`, never fabricates one
- [ ] `generate-daily` CLI command exists, respects the 1-2/day cap via `max_candidates`, prints
      `NO_CANDIDATES` verbatim when empty
- [ ] Tests pass; branch pushed

## 8. Report

Test counts before and after; the exact free-tier model slugs chosen (flagged for human
verification); the full path of every new/changed file; confirmation that `git status` shows
nothing new under `data/`.

## Sandbox needs

- Read(C:/Github/AgentFlow/**)
- Exec(uv run pytest)

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Blocked |
| Assigned to | devin |
| Branch | directive/rfd-blog-engine-blog-daily-draft-source-directive |
| Base branch | spec/daily-draft-loop |

**Status log**
- 2026-09-27 09:30 · robert-claude · none → Queued — written alongside the daily-draft-loop spec; not yet approved or dispatched
- 2026-09-28 19:27 · devin-overseer (delegated) · assignee none -> devin
- 2026-09-28 19:28 · devin-overseer (delegated) · Queued → Approved
- 2026-10-01 16:47 · dispatcher · Approved → Blocked — preflight: needs: Read(C:/Github/AgentFlow/**)
- 2026-10-03 17:08 · robert-claude-laptop · Blocked → Queued — Sandbox needs + lint wording fixed (225c498..51ddf10); preflight block cleared
- 2026-10-03 17:09 · robert-claude-laptop · Queued → Approved
- 2026-10-08 17:02 · dispatcher · Approved → Blocked — preflight: needs: `git -C <repo> log --since="<since_days> days ago" --oneline --no-merges` matches deny rule Exec(git -C), declare Exec(<prefix>) under ## Sandbox needs or rewrite the step
<!-- queue:end -->
