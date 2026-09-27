# Robert's approve CLI, and a test proving an unapproved draft cannot publish

## 1. Why this exists

Robert's per-post approval is the only publish trigger; nothing publishes without it
(`docs/superpowers/specs/2026-09-27-daily-draft-loop.md` Stage C/D). The approval gate already
exists in code (`Publisher._check_approved`, `docs/directives/Robert_Only_Publish_Directive.md`),
but there is no way for Robert to approve a draft except calling an MCP tool by hand, and no test
exercises the *whole* daily-loop path (a freshly generated, unapproved draft attempting to publish)
end to end — only the unit-level `_check_approved` is covered today.

## 2. Scope

- `blog_engine/cli.py` (new `approve` command only)
- Tests under `tests/` (new end-to-end test; do not weaken any existing test)
- `README.md` (one line documenting the new command, next to the existing "Publishing" section
  from the Robert-Only-Publish directive)

## 3. The work

1. Add to `blog_engine/cli.py`:
   ```
   @cli.command()
   @click.argument("post_id")
   def approve(post_id):
       """Approve a draft so it can be pushed to WordPress as pending. Does not publish anything."""
   ```
   Implementation: construct `DraftManager` the same way `blog_engine/tools/draft_tools.py`'s
   `_get_draft_manager()` does (`DBManager()` then `DraftManager(db=db)`), call
   `draft_manager.approve_draft(post_id, approved_by="robert")`, and `click.echo` the resulting
   `status` and `approved_at`. On `ValueError` (draft not found, or already not in `"draft"`
   status), catch it and `click.echo` the message via `click.UsageError` (non-zero exit, readable
   message) rather than a raw traceback.
2. Do not change `DraftManager.approve_draft` itself — it already does exactly what's needed
   (`approved_by` recorded as given, raises if status isn't `"draft"`).
3. **End-to-end publish-gate test** (new test file or add to `tests/test_publisher.py` — read that
   file first for the existing mock/fixture pattern for `WordPressHandler`/`DevToHandler`):
   - Arrange: create a draft via `DraftManager.create_draft(...)` with `status` left at its default
     `"draft"` (do not approve it).
   - Act: call `Publisher.publish_wordpress(post_id)` (mocked WP/DevTo handlers, same pattern as
     existing tests).
   - Assert: it raises `ValueError` containing "must be approved before publishing"; assert the
     mocked WordPress handler's `create_post` (or equivalent) was **never called** — not just that
     an exception was raised, but that no WP call was attempted. This is the specific gap: prove
     the *call itself* never reaches WordPress, not only that an error surfaces.
   - Add a second case: approve the draft via the CLI's underlying `approve_draft`, then confirm
     `publish_wordpress` still refuses if `content_guard.check()` finds a `[ROBERT: ...]`
     placeholder in the (now-approved) draft's content — approval alone is not sufficient; content
     guard and the metadata gate still apply after approval. (This may already exist somewhere in
     `tests/test_publisher.py` or `tests/test_robert_only_publish.py` — if so, don't duplicate it;
     just confirm it in your Report and skip re-adding it.)
4. Add a CLI-level test (Click's `CliRunner`) invoking `approve <post_id>` against a temp
   `drafts_dir` fixture: confirm it flips status to `"approved"` and errors cleanly for an unknown
   `post_id` or a draft already `"approved"`.

## 4. What NOT to do

- Do not add a mailbox, Telegram, or TUI approval path — CLI only, per the spec's "smallest
  surface" decision. If you think one of those is obviously better, say so in your Report; don't
  build it unasked.
- Do not change `Publisher.publish_wordpress`, `_check_approved`, `content_guard.py`, or the
  metadata gate — they are correct as-is; this directive only adds a CLI entry point and proves the
  existing gate end to end.
- Do not call WordPress, Dev.to, or any model API for real. Use the existing mock patterns in
  `tests/test_publisher.py` / `tests/test_robert_only_publish.py`.
- Do not approve, publish, or push any *real* draft under `data/drafts/`. Any draft you create for
  a test lives under a `tmp_path`/fixture directory, never `data/drafts/` itself.
- Do not read or print any `.env` value.
- Create no scratch or debug files. If one is unavoidable, put it under `.devin-scratch/` and leave
  it there.

## 5. Verification

```
uv run pytest -q
```
Record the exact pass/fail count before your changes and after — must be 0 failed both times, with
the new tests adding to the count, not replacing any.

## 6. Rules for this run

- This run is **NON-INTERACTIVE**. Any tool call that needs confirmation is rejected outright and
  the run ends mid-task.
- Python is 3.12 via uv; always `uv run`, never bare `python`. Confirm with
  `uv run python --version` before writing any test command.
- Never run `uv run python -c ...` — write a test and run `uv run pytest -q <file>` instead.
- Never use `git -C` or `git -c`; run git from the worktree.
- Work only on your `directive/<slug>` branch; commit and push that branch when done. **Never
  commit to main, never merge, never deploy, never publish anything, never touch WordPress.**
- Update this directive's Status row when you finish or stop partway. If a tool call is genuinely
  blocked, stop and write why in the Status row.

## 7. Completion criteria

- [ ] `uv run rfd-blog-engine approve <post_id>` exists, wraps `approve_draft` unchanged, gives a
      clean error (not a traceback) for a bad `post_id` or wrong status
- [ ] A test proves an unapproved draft's `publish_wordpress` call raises **and** never reaches the
      mocked WordPress `create_post`
- [ ] A test proves approval alone doesn't bypass content guard / metadata gate
- [ ] Tests pass; branch pushed

## 8. Report

Test counts before and after; the exact refusal message text for each new test case; whether the
"approval alone doesn't bypass content guard" case already existed elsewhere (name the file/test if
so).

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Queued |
| Assigned to | - |
| Branch | directive/rfd-blog-engine-blog-approve-cli-and-publish-gate-test-directive |
| Base branch | spec/daily-draft-loop |
| Base commit | - |

**Status log**
- 2026-09-27 09:30 · robert-claude · none → Queued — written alongside the daily-draft-loop spec; not yet approved or dispatched
<!-- queue:end -->
