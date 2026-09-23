# Robert-only publishing: the engine can draft, it can never publish

## 1. Why this exists

Robert, 2026-09-23: "We've been burned by AI generated content before" and he wants "never publish
without Robert" enforced by the tool, not just stated in `docs/DIRECTION.md` (`do_not: never publish a
draft Robert has not approved`).

Today the engine can publish on its own:
- `blog_engine/core/publisher.py` `publish_wordpress(post_id, publish=False, scheduled_date=None)` sets
  `wp_status = "publish" if publish else "draft"`, and a `scheduled_date` makes it `"future"` (a timed
  publish). Its only gate is `_check_approved(draft)`, i.e. `status == "approved"`.
- `approve_draft(post_id, approved_by="human")` (`blog_engine/core/draft_manager.py`, exposed as an MCP
  tool in `blog_engine/tools/draft_tools.py`) accepts any caller and any `approved_by` string. Any agent
  with the MCP server can approve and then publish.
- `publish_to_devto(post_id, published=False)` can publish on Dev.to.
- On 2026-09-23 four client drafts carry visible `[ROBERT: ...]` placeholders for numbers only Robert
  has. Nothing stops a draft with a placeholder from being pushed.

The hard enforcement is WordPress itself: Robert will switch the engine's WordPress credentials to a
user with the **Contributor** role, which WordPress lets create drafts and submit for review but never
publish. This directive makes the code match that model, so nothing in the engine even tries to
publish, and it adds the checks WordPress can't make.

## 2. Scope

- `blog_engine/core/publisher.py`, `blog_engine/tools/publish_tools.py`, `blog_engine/tools/calendar.py`,
  `blog_engine/devto_sync.py`, `blog_engine/api/wordpress.py` (only where they set or request a
  publishing status)
- New `blog_engine/core/content_guard.py`
- `README.md` (publishing section)
- Tests under `tests/`

## 3. The work

1. **No engine path publishes to WordPress.** Every WordPress create/update the engine makes uses
   status `"draft"` or `"pending"` only. Remove the `publish=True` and `scheduled_date`/`"future"`
   behaviour from `publish_wordpress` and its MCP tool. The tool keeps its name for compatibility but
   now means "push to WordPress for Robert's review": it sends `"pending"` and returns
   `{"status": "pending", "wp_url": ..., "note": "Robert publishes in WordPress"}`. If a caller passes
   `publish=True` or a `scheduled_date`, refuse with
   `ValueError("publishing is Robert's: the engine only creates WordPress drafts; publish or schedule it in WordPress")`.
   Search this repo's `blog_engine/` for every other place that sends `"publish"` or `"future"` to
   WordPress (`calendar.py`, `devto_sync.py`, `api/wordpress.py`) and apply the same rule.
2. **Placeholder and content guard.** New `content_guard.check(draft) -> list[str]` returning one
   reason per problem; an empty list means clean. It flags: any `[ROBERT:` (case-insensitive) in
   title, content or excerpt; `[TODO`, `TBD`, `lorem ipsum`; an empty excerpt (the meta description);
   no categories. `publish_wordpress` refuses when `check()` is non-empty, listing the reasons.
3. **Dev.to only follows a live WordPress post.** `publish_to_devto` and `devto_sync` must check the
   WordPress post's current status through the REST API (GET the post by `wp_post_id`) and refuse
   unless it is `"publish"`. Never send `published=True` to Dev.to for a post that isn't live on
   WordPress; the existing 10-day age gate stays.
4. **Approval records who, and says what it means.** `approve_draft` keeps working but its docstring
   and the MCP tool description say plainly: approval marks a draft ready to push to WordPress as
   pending; it does not publish. Record `approved_by` as given (no change to storage).
5. `README.md`: a short "Publishing" section: the engine drafts, Robert publishes in WordPress; the
   engine's WordPress user should have the Contributor role.

## 4. What NOT to do

- Do not call WordPress or Dev.to for real in tests or during this run; use the existing handler
  seams/mocks. Do not read or print `WP_APP_PASSWORD` or any `.env` content.
- Do not change existing drafts in `data/drafts/`, the inventory YAML, or any WordPress content.
- Do not remove `approve_draft`, the draft/revision system, or the Dev.to age gate.
- Create no scratch or debug files. If one is unavoidable, put it under `.devin-scratch/` and leave it.
- Do not search, glob or hunt outside this worktree.

## 5. Verification

```
uv run pytest -q
```
→ 0 failed, including new tests that:
- `publish_wordpress(..., publish=True)` and `publish_wordpress(..., scheduled_date=...)` raise the
  exact "publishing is Robert's" error and make no WordPress call;
- a normal push sends status `"pending"` (assert on the mocked handler's arguments);
- a draft containing `[ROBERT: fill me]` is refused, naming the placeholder; an empty excerpt is refused;
- `publish_to_devto` refuses when the mocked WordPress status is `"pending"` or `"draft"`, and proceeds
  only when it is `"publish"`;
- no code path under `blog_engine/` sends `"publish"` or `"future"` as a WordPress status (a test that
  greps the package source for those literals next to `status` is acceptable).

Record the test count before and after. `uv run pytest -q` is this repo's runner (Python 3.12).

## 6. Rules for this run

- This run is **NON-INTERACTIVE**. Any tool call that needs a confirmation is rejected outright and
  the run ends mid-task. Do not install, download or fetch anything. Do not read outside this working
  directory, and do not use a search, memory or web tool.
- Python is 3.12 via uv; always `uv run`, never bare `python`.
- Never run `uv run python -c ...` (refused; run 1 died on it). To check a library version, read
  `uv.lock` or `pyproject.toml`; to try code, write a test and run `uv run pytest -q <file>`.
- Never use `git -C` or `git -c`; run git from the worktree. One command per call: no `;` chains,
  no `2>$null`.
- Work only on your `directive/<slug>` branch and push that branch when done. **Never commit to
  main, never deploy, never publish anything.**
- Update this directive's Status row when you finish or stop partway. If a tool call is genuinely
  blocked, stop and write why in the Status row.

## 7. Completion criteria

- [ ] No engine path can set a WordPress post to `publish` or `future`
- [ ] Content guard refuses placeholders, empty meta description, missing category
- [ ] Dev.to syndication requires a live WordPress post
- [ ] Tests pass; branch pushed

## 8. Report

Test counts before and after; every file where a publishing status was removed; the exact refusal
messages.

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Queued |
| Assigned to | devin-laptop |
| Branch | directive/rfd-blog-engine-robert-only-publish-directive |
| Base branch | - |
| Base commit | 6b5edd7ddc9fba100c182b7d8789b432e62ca419 |

**Status log**
- 2026-09-23 12:44 · robert-claude · none → Queued — Robert 2026-09-23: enforce 'never publish without Robert' in the tool
- 2026-09-23 12:44 · robert-claude · Queued → Approved
- 2026-09-23 12:44 · dispatcher · Approved → In progress — dispatched devin-laptop on personal-laptop in C:\GitHub\.worktrees\RFD_Blog_Engine--rfd-blog-engine-robert-only-publish-directive; base origin/main (local main differs)
- 2026-09-23 12:48 · robert-claude · In progress → Blocked — run 1 died on refused `uv run python -c` before any commit; directive now forbids it
- 2026-09-23 12:48 · robert-claude · Blocked → Queued
<!-- queue:end -->
