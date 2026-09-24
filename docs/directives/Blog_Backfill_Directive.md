# Blog backfill: give every existing post a lane, a category, a featured image and enough tags

Depends on: Blog_Featured_Images_Directive.md

**Read first:** `docs/notes/2026-09-23-blog-redesign-plan.md` section 4.1 (lanes and category
names), section 4.4 (imagery spec), section 6 phase 4 row: "the engine walks every existing post,
assigns lane and category from a mapping Claude drafts and Robert approves, generates the featured
image, writes excerpts where empty, and submits each as a pending revision." Also read
`docs/directives/Blog_Featured_Images_Directive.md` in full — this directive reuses its functions
and copies its Pillow/no-`python -c` rules verbatim (see "Rules for this run" below).

## 1. Why this exists

Live site check, 2026-09-23, `GET https://blog.rfditservices.com/wp-json/wp/v2/posts?per_page=100`
(HTTP 200, `X-WP-Total: 56`, `X-WP-TotalPages: 1` — all 56 fit in one page) and
`GET .../wp-json/wp/v2/categories?per_page=100` (HTTP 200):

- **56 posts total.** All 56 already carry a non-empty `excerpt.rendered` (checked by stripping
  HTML tags and testing for empty string) — the plan's "empty excerpt" case does not currently
  exist, but the code path stays in scope for future posts.
- **Categories that exist on WordPress today**: `ai-automation` (18 posts), `contact-center` (16),
  `game-development` (9), `developer-life` (8), plus `uncategorized` and `business-consulting` at 0.
  **None of these match the plan's nine lane category names** except `contact-center`, which is
  exactly one of the five consulting categories. The other eight lane categories
  (Convoso, DNC & Compliance, Dialer Ops, Sheets Automation, Dev Notes, Games, Agents & Automation,
  Sessions) **do not exist yet on WordPress** — this directive's `get_or_create_category` calls
  will create them the first time `--apply` runs.
- **5 posts have no category at all**: ids 190, 191, 193, 194, 214.
- Featured images: not refetched here (the `_fields` query above doesn't carry `featured_media`),
  but the plan's section 3 audit already established "zero featured images... across the whole
  blog" as of 2026-09-23, and phase 3 (this directive's dependency) is the only place a featured
  image can be attached — so every one of these 56 posts needs one.

This directive is the only place these facts get acted on: it is Devin's build of the walker,
Claude's mapping (below), and the actual push, gated so nothing changes on the live blog until
Robert approves each pending revision in WordPress.

## 2. Scope

- `blog_engine/core/backfill.py` (new) — the walker
- `blog_engine/cli.py` — add a `backfill` command to the existing `click.group()` (the repo has no
  `[project.scripts]` entry point; every command runs as `uv run python -m blog_engine.cli <cmd>`,
  same as the existing `serve` and `version` commands)
- `data/backfill_mapping.yaml` (new) — one row per existing post, format below
- `tests/test_backfill.py` (new)

Do not modify `blog_engine/core/lanes.py`, `blog_engine/core/featured_image.py`,
`blog_engine/api/wordpress.py`, `blog_engine/tools/taxonomy.py`, `blog_engine/core/publisher.py`,
or `blog_engine/tools/validate_metadata.py` — this directive is a consumer of all of them, not an
editor. If `blog_engine/core/lanes.py` or `blog_engine/core/featured_image.py` do not exist yet in
this worktree (i.e. Blog_Featured_Images_Directive has not merged to this branch's base), stop and
write that in the Status row — do not reimplement them here.

## Functions this directive calls (paste, not a pointer — confirmed present on
`origin/directive/rfd-blog-engine-blog-featured-images-directive`)

```python
# blog_engine/core/lanes.py
def lane_for(categories: list[str]) -> str | None: ...

# blog_engine/core/featured_image.py
def render(title: str, category: str, lane: str | None, out_path: str, font_path: str | None = None) -> None: ...

# blog_engine/api/wordpress.py (WordPressHandler instance methods)
async def upload_media(self, path: str, alt: str) -> int: ...
async def update_post(self, post_id: str, wp_post_id: int, fields: dict) -> dict: ...
async def get_posts(self, status: str = "any", per_page: int = 20, page: int = 1, search: str = None) -> list[dict]: ...
async def get_post(self, wp_post_id: int) -> dict: ...

# blog_engine/tools/validate_metadata.py
def check_draft_gate(draft: dict) -> list[str]: ...  # keys: featured_media_id, categories, tags

# blog_engine/tools/taxonomy.py — ALREADY resolves name -> WP id, creating if missing
async def get_or_create_category(name: str, parent: int = 0) -> dict: ...  # {id, name, slug, created}
async def get_or_create_tag(name: str) -> dict: ...  # {id, name, slug, created}
```

Construct the WordPress handler exactly the way every other tool module in this repo does (see
`blog_engine/tools/taxonomy.py` lines 22-27):

```python
wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
wp_user = os.getenv("WORDPRESS_USER", "")
wp_pass = os.getenv("WORDPRESS_APP_PASSWORD", "")
db = DBManager()
wp = WordPressHandler(db, wp_url, wp_user, wp_pass)
```

## Sandbox needs

- Exec(uv run pytest -q tests/test_backfill.py)
- Exec(uv run pytest -q)

No network access at all — `--dry-run` must not make any HTTP call, and even `--apply` is not run
in this sandbox (see Verification). All tests mock `WordPressHandler`/`httpx`, same pattern as
`tests/test_wordpress_media.py`.

## 3. The mapping

`data/backfill_mapping.yaml` — **drafted by Claude, Robert approves in WordPress.** One row per
existing post, keyed by slug. `category` is one of the nine names from the plan's section 4.1
exactly as written there (case must match `lanes.LANE_CATEGORIES`); `lane` is derived from it by
`lanes.lane_for([category])` at load time (the file does not need to repeat it, but `backfill.py`
must call `lane_for` to fill it, not trust a stale value if the mapping and lanes.py ever disagree
— if they disagree, treat `lanes.py` as the source of truth and print a warning naming the slug).
`excerpt` is `"keep"` for every row below (all 56 posts already have a non-empty excerpt); the
first-30-words fallback in `## The work` only fires for a future post that has none.

```yaml
# data/backfill_mapping.yaml
# Drafted by Claude 2026-09-23 from the live post titles/slugs at
# https://blog.rfditservices.com/wp-json/wp/v2/posts. Robert approves the
# category/lane call per post as a pending revision in WordPress; nothing
# here is final until he does.
posts:
  - slug: automating-60-of-my-job-data-pipeline-lead-enrichment-lessons
    wp_id: 17
    category: "Dialer Ops"
    tags: [dialer-automation, lead-enrichment, data-pipeline]
    excerpt: keep
  - slug: building-rpgcore-cross-language-architecture-for-multi-genre-games
    wp_id: 18
    category: "Games"
    tags: [rpgcore, game-architecture, rust]
    excerpt: keep
  - slug: solana-arbitrage-what-i-learned-from-400-trades-and-4-in-losses
    wp_id: 19
    category: "Sessions"
    tags: [solana, arbitrage, trading-bot]
    excerpt: keep
  - slug: teaching-pong-to-play-itself-my-first-neural-network-experiment
    wp_id: 64
    category: "Agents & Automation"
    tags: [neural-network, pong, machine-learning]
    excerpt: keep
  - slug: why-i-put-a-genetic-system-in-a-turtle-racing-game
    wp_id: 66
    category: "Games"
    tags: [genetic-algorithm, turtle-racing, game-design]
    excerpt: keep
  - slug: from-genetics-to-tactics-how-a-breeding-system-became-a-squad-game
    wp_id: 65
    category: "Games"
    tags: [breeding-system, squad-game, genetics]
    excerpt: keep
  - slug: the-insight-lens-visualizing-the-dialer-blindspot
    wp_id: 57
    category: "Contact Center"
    tags: [chrome-extension, contact-center, dialer-visibility]
    excerpt: keep
  - slug: the-hybrid-engine-rust-performance-python-agility
    wp_id: 58
    category: "Dev Notes"
    tags: [rust, python, game-engine]
    excerpt: keep
  - slug: the-engine-legacy-from-asteroids-to-rpgcore
    wp_id: 59
    category: "Games"
    tags: [rpgcore, game-history, engine-design]
    excerpt: keep
  - slug: what-ants-taught-me-about-systems-design
    wp_id: 63
    category: "Dev Notes"
    tags: [systems-design, emergence, software-architecture]
    excerpt: keep
  - slug: building-a-mobile-idle-game-in-rust-bevy-without-a-game-engine-background
    wp_id: 62
    category: "Games"
    tags: [bevy, rust, idle-game]
    excerpt: keep
  - slug: i-built-a-cli-to-replace-expensive-ai-directive-generation
    wp_id: 61
    category: "Agents & Automation"
    tags: [cli-tools, ai-agents, automation]
    excerpt: keep
  - slug: from-pong-ai-to-play-store-how-a-childhood-hobby-became-a-rust-game-engine
    wp_id: 16
    category: "Games"
    tags: [rust, game-engine, pong-ai]
    excerpt: keep
  - slug: i-built-the-same-game-for-20-years-without-knowing-it
    wp_id: 92
    category: "Sessions"
    tags: [game-design, career-reflection, patterns]
    excerpt: keep
  - slug: the-spec-is-load-bearing
    wp_id: 94
    category: "Sessions"
    tags: [specs, ai-agents, software-process]
    excerpt: keep
  - slug: the-verification-phase-nobody-builds
    wp_id: 107
    category: "Sessions"
    tags: [verification, testing, ai-agents]
    excerpt: keep
  - slug: a-side-effect-of-a-side-effect
    wp_id: 95
    category: "Sessions"
    tags: [debugging, systems-thinking, session-log]
    excerpt: keep
  - slug: how-to-automate-dnc-removal-requests-in-convoso
    wp_id: 146
    category: "Convoso"
    tags: [convoso, dnc-compliance, automation]
    excerpt: keep
  - slug: zero-wasnt-zero
    wp_id: 118
    category: "Sessions"
    tags: [debugging, data-integrity, session-log]
    excerpt: keep
  - slug: how-to-monitor-dialer-list-health-in-convoso
    wp_id: 147
    category: "Convoso"
    tags: [convoso, dialer-ops, list-health]
    excerpt: keep
  - slug: borrowing-code-vs-reinventing-the-wheel
    wp_id: 97
    category: "Dev Notes"
    tags: [code-reuse, software-design, engineering]
    excerpt: keep
  - slug: how-to-forecast-end-of-day-call-center-performance
    wp_id: 148
    category: "Contact Center"
    tags: [forecasting, contact-center, kpi]
    excerpt: keep
  - slug: eight-shorts-same-timeslot-the-engine-found-them
    wp_id: 190
    category: "Agents & Automation"
    tags: [content-automation, youtube-shorts, pipeline]
    excerpt: keep
  - slug: i-didnt-plan-a-curriculum-i-just-kept-solving-problems
    wp_id: 191
    category: "Sessions"
    tags: [learning, problem-solving, career]
    excerpt: keep
  - slug: the-agent-told-me-it-was-done-the-tests-said-otherwise
    wp_id: 100
    category: "Agents & Automation"
    tags: [ai-agents, testing, verification]
    excerpt: keep
  - slug: how-to-automate-call-log-extraction-from-convoso
    wp_id: 152
    category: "Convoso"
    tags: [convoso, call-logs, automation]
    excerpt: keep
  - slug: i-processed-671000-records-in-6-minutes-and-32-seconds
    wp_id: 101
    category: "Agents & Automation"
    tags: [data-pipeline, performance, python]
    excerpt: keep
  - slug: how-much-should-dnc-compliance-automation-cost-to-run
    wp_id: 193
    category: "DNC & Compliance"
    tags: [dnc-compliance, cost-analysis, automation]
    excerpt: keep
  - slug: a-120-bill-for-a-service-that-runs-sixty-seconds-a-day
    wp_id: 194
    category: "DNC & Compliance"
    tags: [cloud-costs, dnc-compliance, infrastructure]
    excerpt: keep
  - slug: how-to-build-a-contact-center-performance-dashboard-in-google-sheets
    wp_id: 153
    category: "Sheets Automation"
    tags: [google-sheets, contact-center, dashboard]
    excerpt: keep
  - slug: building-in-the-margins
    wp_id: 102
    category: "Sessions"
    tags: [side-projects, time-management, session-log]
    excerpt: keep
  - slug: the-bug-that-looked-like-slow-and-was-actually-broken
    wp_id: 195
    category: "Dev Notes"
    tags: [debugging, performance, root-cause]
    excerpt: keep
  - slug: how-to-automate-list-management-in-telesero-vicidial
    wp_id: 154
    category: "Dialer Ops"
    tags: [vicidial, list-management, dialer-ops]
    excerpt: keep
  - slug: i-shipped-my-second-demo-tonight-and-the-relief-was-out-of-proportion
    wp_id: 214
    category: "Sessions"
    tags: [game-dev, shipping, session-log]
    excerpt: keep
  - slug: the-pipeline-that-runs-while-i-sleep
    wp_id: 103
    category: "Agents & Automation"
    tags: [automation, pipeline, scheduling]
    excerpt: keep
  - slug: two-forecasting-systems-and-only-one-of-them-was-real
    wp_id: 196
    category: "Contact Center"
    tags: [forecasting, contact-center, data-validation]
    excerpt: keep
  - slug: i-shipped-a-game-to-android-and-the-web-from-the-same-codebase
    wp_id: 104
    category: "Games"
    tags: [cross-platform, android, game-dev]
    excerpt: keep
  - slug: the-number-was-wrong-by-2x-and-i-found-it-by-predicting-the-wrong-number-in-advance
    wp_id: 197
    category: "Dev Notes"
    tags: [debugging, forecasting, data-validation]
    excerpt: keep
  - slug: how-to-integrate-convoso-with-zoom-contact-center
    wp_id: 158
    category: "Convoso"
    tags: [convoso, zoom, contact-center]
    excerpt: keep
  - slug: weekend-warrior-mode
    wp_id: 105
    category: "Sessions"
    tags: [side-projects, work-life-balance, session-log]
    excerpt: keep
  - slug: the-rule-said-0-25-the-math-said-it-was-actually-enforcing-0-056
    wp_id: 198
    category: "DNC & Compliance"
    tags: [compliance, dnc, math-bug]
    excerpt: keep
  - slug: how-to-automate-lead-list-import-in-convoso
    wp_id: 159
    category: "Convoso"
    tags: [convoso, lead-lists, automation]
    excerpt: keep
  - slug: i-lost-the-plot-on-my-own-project
    wp_id: 106
    category: "Sessions"
    tags: [project-management, reflection, session-log]
    excerpt: keep
  - slug: every-room-looked-different-and-thats-exactly-what-told-me-they-were-all-the-same-bug
    wp_id: 199
    category: "Games"
    tags: [game-dev, debugging, level-design]
    excerpt: keep
  - slug: how-to-build-a-tcpa-compliance-audit-trail-for-your-contact-center
    wp_id: 160
    category: "DNC & Compliance"
    tags: [tcpa, compliance, audit-trail]
    excerpt: keep
  - slug: i-didnt-build-the-pipeline-i-planned-i-built-the-one-that-worked
    wp_id: 109
    category: "Sessions"
    tags: [pipeline, iteration, session-log]
    excerpt: keep
  - slug: two-numbers-that-looked-close-enough-to-share-a-formula-until-i-checked
    wp_id: 200
    category: "Dev Notes"
    tags: [debugging, data-validation, formulas]
    excerpt: keep
  - slug: how-to-handle-reassigned-phone-numbers-in-outbound-calling
    wp_id: 161
    category: "DNC & Compliance"
    tags: [tcpa, phone-numbers, compliance]
    excerpt: keep
  - slug: a-year-in-i-realized-i-had-automated-my-job-away
    wp_id: 111
    category: "Sessions"
    tags: [automation, career, reflection]
    excerpt: keep
  - slug: the-boring-layer-that-made-the-other-two-work
    wp_id: 201
    category: "Dev Notes"
    tags: [infrastructure, architecture, engineering]
    excerpt: keep
  - slug: how-to-manage-ai-coding-agents-without-losing-control
    wp_id: 166
    category: "Agents & Automation"
    tags: [ai-agents, directive-format, engineering-process]
    excerpt: keep
  - slug: the-dnc-request-that-used-to-take-15-minutes-now-takes-3-seconds
    wp_id: 112
    category: "DNC & Compliance"
    tags: [dnc-compliance, automation, contact-center]
    excerpt: keep
  - slug: how-to-automate-youtube-shorts-with-python-and-ffmpeg
    wp_id: 167
    category: "Agents & Automation"
    tags: [youtube-automation, ffmpeg, python]
    excerpt: keep
  - slug: i-stopped-watching-the-dialer-and-built-something-to-watch-it-for-me
    wp_id: 113
    category: "Dialer Ops"
    tags: [dialer-ops, monitoring, automation]
    excerpt: keep
  - slug: how-to-build-an-idle-game-in-rust-with-bevy
    wp_id: 168
    category: "Games"
    tags: [bevy, rust, idle-game]
    excerpt: keep
  - slug: by-4pm-i-know-exactly-where-well-close-at-6pm
    wp_id: 114
    category: "Contact Center"
    tags: [forecasting, contact-center, kpi]
    excerpt: keep
```

56 rows above cover all 56 live posts (verified by count). Several category calls are a judgment
mapping onto the plan's nine names where the current WordPress category (`AI & Automation`,
`Game Development`, `Developer Life`, or none) doesn't correspond 1:1 — Robert can move any row to
a different one of the nine names before running `--apply`; the walker reads whatever the file says
at run time.

## 4. The work

### `blog_engine/core/backfill.py`

```python
async def walk(mapping_path: str, dry_run: bool) -> list[dict]:
    """
    Load mapping_path (YAML, schema above). For each row:
      1. Fetch the live post via wp.get_post(wp_id) — skip with a logged
         warning if the fetch 404s (post deleted since the mapping was drafted).
      2. lane = lanes.lane_for([row["category"]]).
      3. If dry_run: print one line "{wp_id} {slug} -> lane={lane} category={category} "
         "tags={tags} excerpt={excerpt}" and continue — no HTTP writes, no
         get_or_create_category/tag calls (those can create WP terms even on
         a "read"), no featured_image.render call.
      4. Otherwise (apply):
         a. category = await taxonomy.get_or_create_category(row["category"])
         b. tag_results = [await taxonomy.get_or_create_tag(t) for t in row["tags"]]
         c. Render the featured image with featured_image.render(title=<live post
            title>, category=row["category"], lane=lane, out_path=<tempfile path>)
            and upload it with wp.upload_media(...) — same pattern as
            Publisher.publish_wordpress step 2, but there is no draft_manager
            here, so nothing is persisted to a local draft.
         d. excerpt = existing excerpt if non-empty, else the first 30 words of
            the live post's `content.rendered` with HTML tags stripped
            (`re.sub(r"<[^>]+>", "", content)`) joined by a single space —
            write this helper in backfill.py, no new dependency.
         e. Build fields = {"categories": [category["id"]],
            "tags": [t["id"] for t in tag_results],
            "featured_media": media_id, "excerpt": excerpt} — deliberately no
            "status" key: the live post's status is never touched.
         f. Run validate_metadata.check_draft_gate({"featured_media_id": media_id,
            "categories": [row["category"]], "tags": row["tags"]}) before the
            WordPress call; if it returns anything, skip this post, log the
            gate failure, and continue to the next row rather than raising —
            one bad row must not stop the other 55.
         g. await wp.update_post(post_id=row["slug"], wp_post_id=row["wp_id"], fields=fields).
         h. If update_post raises (e.g. HTTP 403 — the engine's WordPress user
            is Contributor and may lack edit_published_posts on an
            already-published post, which is exactly the "pending revision"
            path WordPress uses for Contributors editing live content),
            catch it, log "post {wp_id} needs manual approval: {error}", and
            continue — this is an expected outcome for a live post, not a bug.
      5. Return a list of per-post result dicts (slug, wp_id, action taken,
         and error if any) for the CLI to print a summary line.
    """
```

### `blog_engine/cli.py`

Add to the existing `@click.group()`:

```python
@cli.command()
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--apply", "do_apply", is_flag=True, default=False)
@click.option("--mapping", default="data/backfill_mapping.yaml")
def backfill(dry_run, do_apply, mapping):
    """Backfill lane/category/tags/featured-image/excerpt onto existing posts."""
    if dry_run == do_apply:
        raise click.UsageError("pass exactly one of --dry-run or --apply")
    import asyncio
    from blog_engine.core.backfill import walk
    results = asyncio.run(walk(mapping, dry_run=dry_run))
    for r in results:
        click.echo(r)
```

Run as `uv run python -m blog_engine.cli backfill --dry-run` (no console-script entry point exists
in `pyproject.toml`; do not add one — out of scope).

## 5. What NOT to do

- Never call `wp.update_post` with a `status` field, and never call any endpoint that would set a
  live post to `publish` or `future` — `validate_writable_status` in `wordpress.py` stays the only
  status gate and this directive does not touch it.
- Never delete WordPress media, never delete a post, never touch a post whose `wp_id` is not a row
  in `data/backfill_mapping.yaml`.
- No `python -c ...` for anything, ever — bare `python` is not an allowed shape and its confirmation
  prompt kills the run (this already happened once on 2026-09-23 at 16:13 on the phase-3 directive).
  If you need to check `import PIL` or anything else, write it into a test and run pytest.
- Do not run `uv sync`, `uv add`, or `pip` — Pillow is already a dependency (added 2026-09-23,
  `pillow>=10` in `pyproject.toml`, Pillow 12.3.0 in `uv.lock`); if `import PIL` fails in the
  worktree, stop and write that in the Status row.
- No live WordPress calls of any kind in this sandbox run — `--apply` is exercised only through
  mocks in `tests/test_backfill.py`. Do not attempt to reach `blog.rfditservices.com`.
- Do not create WordPress categories or tags outside `get_or_create_category`/`get_or_create_tag` —
  do not hand-write a new taxonomy endpoint call.
- Do not modify `data/backfill_mapping.yaml`'s content beyond what's specified above — if a slug
  looks miscategorized, leave it and note it in the Report; recategorizing is Robert's call in
  WordPress, not a reason to hand-edit the file mid-run.
- No scratch or debug files outside `.devin-scratch/`, and never delete files.

## 6. Verification

Real output from this repo, 2026-09-23:
```
$ uv run python --version
Python 3.12.12
$ uv run pytest -q
214 passed, 2 warnings in 14.88s
```
(This is main's baseline. The phase-3 branch this directive depends on adds its own new tests on
top of these 214 — expect that count plus this directive's additions, not exactly 214, once both
branches are combined.)

After this directive's changes:
```
uv run pytest -q tests/test_backfill.py
uv run pytest -q
```
Expect every test in `test_backfill.py` to pass, and the full suite to show no regressions from
whatever count the branch started with.

### Test content

- A dry run over a 2-3 row fake mapping (tmp_path fixture, not the real 56-row file) prints one
  line per post naming lane/category/tags/excerpt and asserts `wp.update_post`,
  `taxonomy.get_or_create_category`, `taxonomy.get_or_create_tag`, and `featured_image.render` are
  never called (mock all four).
- An apply run over the same fake mapping asserts `get_or_create_category`/`get_or_create_tag` are
  called once per unique name, `featured_image.render` and `wp.upload_media` are each called once
  per post, and `wp.update_post` receives `fields` containing `categories`, `tags`,
  `featured_media`, and `excerpt` keys but never `status`.
- A row whose gate fails (mock `check_draft_gate` to return `["has_minimum_tags"]`) is skipped:
  `wp.update_post` is not called for that row, and the walk continues to the next row.
- `wp.update_post` raising (mock a raised exception, e.g. representing an HTTP 403) is caught, the
  post is recorded as "needs manual approval", and the walk continues rather than raising out.
- The excerpt fallback: a fake live post with an empty `excerpt.rendered` and a `content.rendered`
  of more than 30 words produces exactly the first 30 words, HTML-stripped, in the `excerpt` field
  sent to `update_post`.

## 7. Rules for this run

Copied verbatim from `docs/directives/Blog_Featured_Images_Directive.md` section 6:

> The run is NON-INTERACTIVE and any tool call needing confirmation ends it. Never install,
> download, or fetch. Never read outside the worktree. Do not search, glob, or hunt — stop and
> write it in the Status row if something named here is missing. Never commit to main, never push,
> never deploy; work stays on `directive/rfd-blog-engine-blog-backfill-directive`. Free models only,
> no model config is touched. Create no scratch or debug files outside `.devin-scratch/` and never
> delete files. If a tool call is blocked, stop and write why in the Status row.

Plus, from the same directive's Pillow note: do not run `uv sync`, `uv add`, or `pip`; if
`import PIL` fails in the worktree, stop and write that in the Status row. Never run `python -c ...`
to check anything — bare `python` is not an allowed shape and its confirmation prompt ends the run.
The test suite importing `PIL` (via `featured_image.py`, indirectly exercised through mocks here)
is the only verification needed for that dependency.

## 8. Completion criteria

- [ ] `blog_engine/core/backfill.py` exists with `walk(mapping_path, dry_run)`.
- [ ] `blog_engine/cli.py` has a `backfill` command taking `--dry-run` xor `--apply`.
- [ ] `data/backfill_mapping.yaml` exists with the 56 rows above, unmodified in content.
- [ ] `--dry-run` makes zero HTTP calls and zero WordPress term creations (enforced by the mocks
      in the test above being asserted not-called).
- [ ] `--apply` never sends a `status` field to `update_post` and skips (does not raise on) both a
      failed gate and a 403-style update failure.
- [ ] `tests/test_backfill.py` passes; `uv run pytest -q` is all-green with no regressions.

## 9. Report

State: files created/edited (paths), whether `blog_engine/core/lanes.py` and
`blog_engine/core/featured_image.py` were present in this worktree (and if not, say so — do not
reimplement them), the final `uv run pytest -q` line, and a one-line note per skipped/failing
mapping-file assumption you found while writing `test_backfill.py`'s fakes (there is no live call
in this run, so this is about internal consistency, not what WordPress will actually do).

## 10. Role gate (added by laptop Claude 2026-09-23 20:10, read before `--apply`)

The plan's phrase "submit as a pending revision" does not exist in WordPress core for an
already-published post: a Contributor cannot edit someone else's published post at all, and
the REST update returns 403 for every one of the 56 posts. So under the engine's current
Contributor credential, `--apply` will skip all 56 and change nothing. That is the correct
behaviour for this run, not a bug to work around:

- Build everything, make the dry-run and the tests green, and treat `--apply` against the
  live blog as out of scope for this run. Do not try a different endpoint, a different
  credential, or a role change.
- In the Report, state plainly that live apply needs a credential with `edit_published_posts`
  (an Editor-role application password used only by the backfill, or a role change on the
  engine's user), and that even with it the code never sends `status`, so nothing can be
  published by this path. Robert decides which credential, and when.
- If `--apply` is ever run with such a credential, the first post that 403s still skips and
  continues, and a run where every post 403s must end with the summary line
  `apply: 0 updated, 56 skipped (403) - credential lacks edit_published_posts` and exit 0.

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Approved |
| Assigned to | devin |
| Branch | - |
| Base branch | - |
| Depends on | Blog_Featured_Images_Directive.md |

**Status log**
- 2026-09-23 20:07 · robert-claude-laptop · none → Queued — Phase 4 of the blog redesign; Robert approved the design 2026-09-23 ("full push"). Depends on Blog_Featured_Images; live --apply is gated on an Editor-capable credential (section 10), Robert's call.
- 2026-09-23 20:08 · robert-claude-laptop · Queued → Approved — approved; held for: Blog_Featured_Images_Directive.md is Approved
<!-- queue:end -->
