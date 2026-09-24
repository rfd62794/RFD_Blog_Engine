# Blog Lane Pages Directive

Depends on: Blog_Backfill_Directive.md

## Why this exists

Phase 5b of the blog redesign (`docs/notes/2026-09-23-blog-redesign-plan.md`
section 4.1, phase 5b row in section 6, approved section 10). Two curated
archive pages, Consulting and Building, give the office, arcade, and search
visitors a deep-link target; home stays the mixed feed. Section 6: "phase 5b
on 4" — depends on the backfill so posts already carry a lane category.

## Read first

All paths are inside this repo/worktree.

- `theme/rfd-blog/templates/home.html` lines 16-39 — pill row + post grid to
  reuse:
  ```
  <!-- wp:categories {"showPostCounts":false,"displayAsDropdown":false,"className":"pill-row"} /-->
  <!-- wp:query {"query":{"perPage":12,"pages":0,"offset":0,"postType":"post","order":"desc","orderBy":"date","author":"","search":"","exclude":[],"sticky":"","inherit":true},"className":"card-grid three","layout":{"type":"default"}} -->
  <div class="wp-block-query card-grid three">
  	<!-- wp:post-template {"className":"card-grid-inner"} -->
  		<!-- wp:post-featured-image {"isLink":true,"aspectRatio":"16/9"} /-->
  		<!-- wp:post-terms {"term":"category","className":"chip"} /-->
  		<!-- wp:post-title {"isLink":true,"level":2} /-->
  		<!-- wp:post-excerpt {"moreText":"","excerptLength":24} /-->
  		<!-- wp:post-date {"isLink":false} /-->
  	<!-- /wp:post-template -->
  	<!-- wp:query-pagination {"layout":{"type":"flex","justifyContent":"space-between"}} -->
  		<!-- wp:query-pagination-previous /-->
  		<!-- wp:query-pagination-next /-->
  	<!-- /wp:query-pagination -->
  	<!-- wp:query-no-results -->
  		<!-- wp:paragraph --><p>No posts yet.</p><!-- /wp:paragraph -->
  	<!-- /wp:query-no-results -->
  </div>
  <!-- /wp:query -->
  ```
- `templates/archive.html` — same query shape; `standfirst` via
  `wp:term-description`; no-results text "Nothing in this lane yet."
- `patterns/lane-cta-consulting.php` — slug `rfd-blog/lane-cta-consulting`,
  class `lane-cta-inner`; `patterns/lane-cta-building.php` — slug
  `rfd-blog/lane-cta-building`, same class.
- `style.css` — `.lane-consulting`/`.lane-building` (92-98), `.pill-row`
  (71), `.card-grid` (113-131), `.standfirst` (162), `.lane-cta-inner`
  (173-187).
- `functions.php` `rfd_lane()` (37-50): consulting = `contact-center`,
  `convoso`, `dnc-compliance`, `dialer-ops`, `sheets-automation`; building =
  `dev-notes`, `games`, `agents-automation`, `sessions`.
- `theme/build.py` line 86 zips every file under `theme/rfd-blog/` via
  `rglob("*")`; `REQUIRED_FILES` (24-35) is a separate existence check, not
  what drives zip contents — new templates need no build.py edit.
- `tests/test_theme_build.py` `EXPECTED_THEME_FILES` (18-29) — the list this
  directive's new tests extend.
- `theme/README.md` install checklist, esp. steps 4, 6, 7 (nav, categories,
  front-page template).
- `docs/notes/2026-09-23-blog-redesign-plan.md` section 4.1 lane table,
  section 6 phase 5b row, section 10 (no categories sub-page — two lane
  pages instead; core nav order fixed, blog "adds nothing").
- `parts/header.html` — nav is hard-coded links, not a menu; templates must
  not touch it.

Ran `cd C:/GitHub/RFD_Blog_Engine && uv run python --version && uv run pytest -q`:
`Python 3.12.12`, `247 passed, 2 warnings in 19.77s`, 0 skipped.

## Scope

Two new page templates, one functions.php filter, two home.html links, new
tests. Nothing else.

## The work

1. **`templates/page-consulting.html`** (new). Same shape as
   `archive.html` (header part, main group, footer part):
   - H1 "Consulting"; standfirst paragraph (class `standfirst`): "For
     contact-center operators and small businesses who want automation that
     pays for itself."
   - Category pills: `wp:categories` cannot filter to a subset, so use a
     **static pill list** — a `wp:list` block (`className: "pill-row"`)
     of `wp:list-item` links, one per lane category, href
     `/category/{slug}/`: Contact Center, Convoso, DNC & Compliance, Dialer
     Ops, Sheets Automation.
   - Post grid: copy the `wp:query`/`wp:post-template` block verbatim from
     `home.html` above, but set `"inherit":false`, add `"lane":"consulting"`
     to the query attrs, and add a placeholder
     `"taxQuery":{"category":["consulting"]}` (resolved server-side by the
     filter below — real mechanism, not hard-coded IDs). No-results text:
     "Nothing in this lane yet."
   - CTA: `<!-- wp:pattern {"slug":"rfd-blog/lane-cta-consulting"} /-->`
     after the query block, before the footer part.
2. **`templates/page-building.html`** (new). Same shape:
   - H1 "Building"; standfirst: "For people who follow the games, the
     agents, and the dev notes."
   - Pills: `/category/dev-notes/`, `/category/games/`,
     `/category/agents-automation/`, `/category/sessions/` (labels Dev
     Notes, Games, Agents & Automation, Sessions).
   - Query block: `"lane":"building"`,
     `"taxQuery":{"category":["building"]}` placeholder, `"inherit":false`.
   - CTA: `<!-- wp:pattern {"slug":"rfd-blog/lane-cta-building"} /-->`.
   Block themes pick `page-{slug}.html` by page slug — the only reason
   these render; Robert creates the two pages (see Report).
3. **`functions.php` — taxQuery mechanism.** Confirmed caveat: core's
   `core/query` block's `taxQuery` attribute takes term **IDs**, not slugs,
   and IDs are not stable across environments (the backfill creates
   categories fresh on install). Mechanism: use the `lane` attribute set
   above and resolve it at render time via `query_loop_block_query_vars`,
   mapping lane to `category_name` (a slug list core's `WP_Query` accepts
   directly) so no term IDs are ever hard-coded:
   ```php
   add_filter( 'query_loop_block_query_vars', 'rfd_blog_lane_query_vars', 10, 3 );
   function rfd_blog_lane_query_vars( array $query, $block, $page ): array {
   	$lane = $block->context['query']['lane'] ?? null;
   	if ( null === $lane ) {
   		return $query;
   	}
   	$lane_categories = array(
   		'consulting' => array( 'contact-center', 'convoso', 'dnc-compliance', 'dialer-ops', 'sheets-automation' ),
   		'building'   => array( 'dev-notes', 'games', 'agents-automation', 'sessions' ),
   	);
   	if ( isset( $lane_categories[ $lane ] ) ) {
   		$query['category_name'] = implode( ',', $lane_categories[ $lane ] );
   	}
   	return $query;
   }
   ```
   Place after `rfd_post_lane()`. Do not change `rfd_lane()`'s behavior or
   signature — `test_functions_php_lane_map` depends on it.
4. **`templates/home.html`** — add two links after the pill row, before the
   `wp:query` block:
   ```
   <!-- wp:paragraph -->
   <p><a href="/consulting/">Consulting notes</a> &nbsp; <a href="/building/">Building notes</a></p>
   <!-- /wp:paragraph -->
   ```
   Do not touch `parts/header.html` or its nav — order is fixed per plan
   section 10 and covered by a drift test elsewhere in the repo.
5. **`theme/build.py`** — unchanged. `rglob("*")` (line 86) picks up the two
   new templates automatically. Do not add them to `REQUIRED_FILES`.
6. **`tests/test_theme_build.py`** — add (do not remove existing tests):
   - `test_page_templates_exist`: both new template files exist on disk.
   - `test_zip_contains_lane_page_templates`: run `run_build()`, open the
     zip, assert both `rfd-blog/templates/page-{consulting,building}.html`
     are in `zf.namelist()`.
   - `test_page_consulting_references_only_its_own_lane`: read the file;
     assert it contains `lane-cta-consulting` and all five consulting slugs;
     assert it does NOT contain `lane-cta-building` or any building slug.
   - `test_page_building_references_only_its_own_lane`: mirror, in reverse,
     for the four building slugs and `lane-cta-building`.
   - `test_functions_php_lane_query_filter`: assert
     `query_loop_block_query_vars` is present in `functions.php` alongside
     both lanes' full slug lists.

## What NOT to do

- No header/footer/nav changes.
- No new categories; no change to `rfd_lane()`'s map or signature.
- Never touch WordPress (no wp-admin, no install, no page creation), never
  publish — this directive only changes files in git.
- No `python -c` one-liners; no package installs; no reads outside the worktree; no scratch files left behind.

## Verification

```
cd C:/GitHub/RFD_Blog_Engine
uv run pytest -q tests/test_theme_build.py
uv run pytest -q
```

Expected: all `test_theme_build.py` tests pass (existing + the new ones from
step 6). Full suite: was 247 passed, 0 skipped, 2 warnings — expect
247 + (new test count) passed, 0 skipped, same or fewer warnings.

## Rules for this run

- NON-INTERACTIVE, no prompts.
- Branch: `directive/rfd-blog-engine-blog-lane-pages-directive`.
- Never commit to main/master. Never push.
- If blocked, stop and write the Status row explaining exactly what's
  blocking rather than guessing or expanding scope.

## Sandbox needs

- Exec(uv run pytest -q tests/test_theme_build.py)
- Exec(uv run pytest -q)

## Completion criteria

- Both page templates exist with standfirst, static pills for their own
  lane only, a lane-scoped `wp:query` grid, and their own CTA pattern.
- `functions.php` has the `query_loop_block_query_vars` filter mapping both
  lanes to their exact slugs; `rfd_lane()` unchanged.
- `home.html` has the two new links and nothing else changed.
- New tests from step 6 added and passing.
- Both verification commands green on the branch above; nothing on main;
  nothing pushed.

## Report

Include this 10-line install note for Robert, verbatim:

1. `cd C:/GitHub/RFD_Blog_Engine && uv run python theme/build.py` to rebuild
   `theme/dist/rfd-blog.zip` with the two lane templates included.
2. WordPress admin -> Appearance -> Themes -> RFD Blog -> re-upload/replace
   with the new zip.
3. Pages -> Add New -> title "Consulting", slug exactly `consulting`, leave
   content empty.
4. Pages -> Add New -> title "Building", slug exactly `building`.
5. Publish both pages.
6. Open `/consulting/`: confirm standfirst, five pills, consulting-only post
   grid, "Talk to Robert" CTA.
7. Open `/building/`: confirm standfirst, four pills, building-only post
   grid, "Play what I'm building" CTA.
8. On home, confirm "Consulting notes" / "Building notes" links appear under
   the pill row and resolve correctly.
9. Confirm header nav is unchanged (Consulting - Blog - Arcade - About -
   Contact).
10. If a lane page shows zero posts, check Blog_Backfill_Directive.md has
    run and posts carry that lane's categories.
