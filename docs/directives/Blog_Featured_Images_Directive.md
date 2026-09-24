# Featured images and the metadata gate: every push carries a branded card, a lane, a category and tags

**Read first:** `docs/notes/2026-09-23-blog-redesign-plan.md` — section 4.1 (lanes and category
names), section 4.4 (imagery spec: 1200x630, lane colour on dark navy `#0b1220`, title in Inter 800,
category label, brand mark bottom-left).

## 1. Why this exists

The plan's section 3, verbatim:

> Content audit in `data/state/current.md`: zero tags, zero featured images, no meaningful
> categories across the whole blog.

Section 4.4: "Featured images are generated, not sourced... This is the single biggest
professional-appearance lever because it fixes the index grid, social previews and syndication at
once." This directive builds the generator and makes it, plus a real category and three tags,
mandatory before any post reaches WordPress — a hard gate, not a suggestion, so the zero-tags/
zero-images state in the audit cannot recur.

## 2. Scope

- `blog_engine/core/lanes.py` (new)
- `blog_engine/core/featured_image.py` (new)
- `blog_engine/api/wordpress.py` (add `upload_media`, add `featured_media` to `create_post`)
- `blog_engine/tools/validate_metadata.py` (new hard-gate function)
- `blog_engine/core/publisher.py` — `Publisher.publish_wordpress` (the call site that pushes to
  WordPress) and `Publisher._update_draft_publish_fields`
- `pyproject.toml` (add `pillow>=10` — see "Pillow" below)
- `tests/test_lanes.py` (new)
- `tests/test_featured_image.py` (new)
- `tests/test_wordpress_media.py` (new)
- `tests/test_publisher.py` (extend for the gate)

## Pillow

Checked 2026-09-23 16:10: `pyproject.toml` `[project].dependencies` lists `"pillow>=10"` (Pillow
12.3.0 in `uv.lock`) and the environment carries it. Do not run `uv sync`, `uv add` or `pip`; if
`import PIL` fails in the worktree, stop and write that in the Status row. No network access at all.
Never run `python -c ...` to check it either — bare `python` is not an allowed shape, its
confirmation prompt kills the run (this already happened once at 16:13). The test suite imports
PIL itself; that is the only verification needed.

## Sandbox needs

Pillow is already a dependency on main (added 2026-09-23 with `uv add "pillow>=10"`; the worktree's environment carries it). Do not run `uv sync` or `uv add`; if `import PIL` fails, stop and write that in the Status row.

- Exec(uv run pytest -q tests/test_lanes.py)
- Exec(uv run pytest -q tests/test_featured_image.py)
- Exec(uv run pytest -q tests/test_wordpress_media.py)
- Exec(uv run pytest -q tests/test_publisher.py)
- Exec(uv run pytest -q)

## 3. The work

### `blog_engine/core/lanes.py`

Data + one function, from the plan's section 4.1, category names exactly as written there:

```python
LANE_CATEGORIES = {
    "consulting": ["Contact Center", "Convoso", "DNC & Compliance", "Dialer Ops", "Sheets Automation"],
    "building": ["Dev Notes", "Games", "Agents & Automation", "Sessions"],
}

def lane_for(categories: list[str]) -> str | None:
    """
    First category in `categories` that matches a lane (case-insensitive exact
    match against LANE_CATEGORIES) wins. Returns "consulting", "building", or
    None if nothing matches. `categories` are the plain-string category names
    as stored on a draft (see blog_engine/core/draft_manager.py), not WP IDs.
    """
```

### `blog_engine/core/featured_image.py`

Pure function, Pillow-based:

```python
def render(title: str, category: str, lane: str | None, out_path: str, font_path: str | None = None) -> None:
```

- Canvas 1200x630, background `#0b1220` (dark navy, per plan section 4.4 — fixed regardless of
  site light/dark mode, since this is a static social/OG image).
- A lane colour band (e.g. a left or top accent bar) using `#93b4ff` for `lane == "consulting"`,
  `#8ed5ff` for `lane == "building"`, falling back to `#93b4ff` if `lane` is `None`. These are the
  plan's section 4.2 dark-mode `--lane-consulting`/`--lane-building` values, since the card always
  renders on the dark background.
- Title wrapped (simple word-wrap to fit the canvas width) in `font_path` at a large size if
  `font_path` is given and loads; if `font_path` is `None`, missing, or `ImageFont.truetype` raises
  `OSError`, fall back to `ImageFont.load_default()` — the render must succeed either way, since no
  font file is guaranteed present in this run (same constraint as the theme directive's font doctor
  check).
- `category` rendered as a small label.
- The text "RFD IT Services" bottom-left.
- Saves PNG to `out_path`.

### `blog_engine/api/wordpress.py`

Add, on `WordPressHandler`:

```python
async def upload_media(self, path: str, alt: str) -> int:
```

WordPress's media POST endpoint accepts multipart. `self._make_request` only supports a JSON body
(no `files=`), so build this call with `httpx.AsyncClient` directly inside `upload_media` — do not
change `_make_request` or any other handler (out of scope). Read `path` as bytes, POST to
`{self.base_url}/wp-json/wp/v2/media` with `auth=self.auth` and
`files={"file": (Path(path).name, data, "image/png")}`, parse the JSON response for `"id"`. Then set
`alt_text` via `self._make_request("POST", f"{self.base_url}/wp-json/wp/v2/media/{id}", auth=self.auth,
json={"alt_text": alt})` (reuses the existing retry/backoff path for this second, ordinary JSON
call). Return the media id (`int`).

Add a `featured_media: int = None` parameter to `create_post`; include `"featured_media": featured_media`
in the payload only when it is not `None`. `update_post` already takes an arbitrary `fields` dict —
no change needed there; a caller sets `fields={"featured_media": media_id}` to update it.

Keep `validate_writable_status` and every Robert-only rule in this file exactly as they are — this
directive adds a capability, it does not touch the publish-status guard.

### `blog_engine/tools/validate_metadata.py`

Add a new function alongside the existing (WordPress-side, post-push) `validate_post_metadata`:

```python
def check_draft_gate(draft: dict) -> list[str]:
    """
    Hard gate checked before any WordPress push. Operates on the local draft
    dict, not on data fetched from WordPress — the post does not exist on
    WordPress yet at this point in the publish flow. Returns the names of the
    failing checks (empty list = passes):
      - "has_featured_image": draft.get("featured_media_id") is falsy
      - "has_meaningful_category": draft has no categories, or every one is
        the literal string "Uncategorized" (case-insensitive)
      - "has_minimum_tags": fewer than 3 entries in draft.get("tags", [])
    """
```

This is a synchronous, dependency-free function (no aiohttp, no DB) so `Publisher.publish_wordpress`
can call it directly on the in-memory draft dict.

### `blog_engine/core/publisher.py` — `Publisher.publish_wordpress`

Current order (verified 2026-09-23): load draft → `_check_approved` → `content_guard.check(draft)`
→ build `tags_to_send`/`categories_to_send` → `self.wp.create_post(...)`. Insert the new steps
**between** the `content_guard.check` block and the `tags_to_send`/`categories_to_send` block:

1. `lane = lanes.lane_for(draft.get("categories", []))`
2. If `draft.get("featured_media_id")` is falsy: render an image with `featured_image.render` to a
   `tempfile`-created path (do not write it into the repo or into `data/`), using
   `title=draft["title"]`, `category=draft["categories"][0] if draft.get("categories") else ""`,
   `lane=lane`; upload it with `media_id = await self.wp.upload_media(path=tmp_path, alt=draft["title"])`;
   persist it with `self._update_draft_publish_fields(post_id=post_id, featured_media_id=media_id)`
   (extend that method's signature and body to accept and write `featured_media_id`, same pattern as
   the existing `wp_post_id`/`wp_url` fields); set `draft["featured_media_id"] = media_id` locally so
   the next step sees it without a re-read.
3. `gate_problems = validate_metadata.check_draft_gate(draft)` — if non-empty, `raise ValueError(f"draft
   {post_id} failed the metadata gate: " + ", ".join(gate_problems))`, same failure style as the
   existing content-guard raise, and **before** any WordPress call.
4. Pass `featured_media=draft["featured_media_id"]` into the existing `self.wp.create_post(...)` call.

Also add `"featured_media_id": None` to the draft schema's default fields in
`blog_engine/core/draft_manager.py`'s `create_draft` (`draft_data` dict) so older/new drafts have a
consistent key to read with `.get(...)` either way — this one line in `draft_manager.py` is in scope
as part of wiring the gate even though the file is not separately listed above.

## 4. What NOT to do

- The engine's WordPress user stays Contributor. Nothing in this directive may set WordPress status
  to `publish` or `future` — `validate_writable_status` and `WRITABLE_WP_STATUSES` are untouched.
- Do not backfill existing posts with generated images — that is a separate, later directive.
- No network access — no `uv sync`, no live WordPress calls, no font downloads. All new tests
  mock HTTP.
- No changes to `content_guard.py` — the metadata gate is new and separate from it; both run.
- No Playwright, no visual/screenshot testing.

## 5. Verification

Real output from this repo, 2026-09-23, before this directive's changes:
```
$ uv run python --version
Python 3.12.12
$ uv run pytest -q
214 passed, 2 warnings in 12.59s
```

After the changes:
```
uv run pytest -q tests/test_lanes.py
uv run pytest -q tests/test_featured_image.py
uv run pytest -q tests/test_wordpress_media.py
uv run pytest -q tests/test_publisher.py
uv run pytest -q
```
Expect every file to pass on its own, and the full suite to show 214 plus every test this directive
adds, all passing, zero failed, zero errored.

### Test content

- `tests/test_lanes.py`: each category name in the plan's section 4.1 list maps to the right lane;
  an unknown category returns `None`; an empty list returns `None`.
- `tests/test_featured_image.py`: `render(...)` into `tmp_path`, assert the output file is a PNG
  sized exactly 1200x630, and that a pixel inside the lane band matches the expected lane RGB
  (`#93b4ff` for consulting, `#8ed5ff` for building) for both lanes, plus one case with
  `font_path=None` that still succeeds.
- `tests/test_wordpress_media.py`: mock `httpx.AsyncClient` (same style as `tests/test_wordpress.py`
  patches `_make_request` — here patch the client used inside `upload_media`), assert the upload
  request carries a multipart `file` field, and that `create_post(..., featured_media=123)` includes
  `"featured_media": 123` in its JSON payload.
- `tests/test_publisher.py` additions: a draft missing tags/category/featured image causes
  `publish_wordpress` to raise before `wp.create_post` is ever called (mock and assert
  `mock_req.assert_not_called()` or equivalent); a complete draft without a prior
  `featured_media_id` causes `featured_image.render` and `wp.upload_media` to be called once each
  (mock both) and `create_post` to receive the resulting `featured_media`.

## 6. Rules for this run

The run is NON-INTERACTIVE and any tool call needing confirmation ends it. Never install, download,
or fetch. Never read outside the worktree. Do not search, glob,
or hunt — stop and write it in the Status row if something named here is missing. Never commit to
main, never push, never deploy; work stays on
`directive/rfd-blog-engine-blog-featured-images-directive`. Free models only, no model config is
touched. Create no scratch or debug files outside `.devin-scratch/` and never delete files. If a
tool call is blocked, stop and write why in the Status row.

## 7. Completion criteria

- [ ] `blog_engine/core/lanes.py` exists with `LANE_CATEGORIES` and `lane_for`.
- [ ] `blog_engine/core/featured_image.py` exists with `render`, works with and without `font_path`.
- [ ] `wordpress.py` has `upload_media` and `create_post` accepts `featured_media`.
- [ ] `validate_metadata.py` has `check_draft_gate`.
- [ ] `Publisher.publish_wordpress` renders/uploads a featured image when missing, runs the gate
      before any WordPress push, and passes `featured_media` through to `create_post`.
- [ ] `import PIL` works in the worktree (Pillow is already on main).
- [ ] All five new/extended test files pass; `uv run pytest -q` is all-green with no regressions.

## 8. Report

State: files created/edited (paths), the Pillow version imported, and the final `uv run pytest -q` line.

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | In progress |
| Assigned to | devin |
| Branch | directive/rfd-blog-engine-blog-featured-images-directive |
| Base branch | - |
| Base commit | f01d4282dc2f15309de0468b803d88a29526b89d |

**Status log**
- 2026-09-23 16:08 · robert-claude-laptop · none → Queued — Blog redesign phase 3; Pillow added via uv sync grant; engine stays Contributor, no publish
- 2026-09-23 16:09 · robert-claude-laptop · Queued → Approved
- 2026-09-23 16:10 · dispatcher · Approved → In progress — dispatched devin-laptop on personal-laptop in C:\GitHub\.worktrees\RFD_Blog_Engine--rfd-blog-engine-blog-featured-images-directive
- 2026-09-23 16:26 · agentflow-tick · In progress → Blocked — process gone while the directive still reads In progress; the worktree holds uncommitted files; resume cap reached (2/2)
- 2026-09-23 17:00 · robert-claude-laptop · Blocked → Queued
- 2026-09-23 17:00 · robert-claude-laptop · Queued → Approved
- 2026-09-23 20:33 · dispatcher · Approved → In progress — dispatched devin on personal-laptop in C:\GitHub\.worktrees\RFD_Blog_Engine--rfd-blog-engine-blog-featured-images-directive; lane=strong
<!-- queue:end -->
