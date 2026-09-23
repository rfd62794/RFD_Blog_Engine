# Blog child theme: Twenty Twenty-Five child that carries the office tokens and the lane cards

**Read first:** `docs/notes/2026-09-23-blog-redesign-plan.md` (the approved plan) — section 3
diagnosis, section 4.1 lanes, section 4.2 tokens, section 4.3 page anatomy. Decisions taken since
that plan was written: hosting is self-hosted WordPress behind Cloudflare, so **Path A** (the child
theme) applies, not Path B. The theme lives in **this repo** under `theme/`, not in a new
`RFD_Blog_Theme` repo as the plan's phase table assumed.

## 1. Why this exists

The plan's section 3 diagnosis, verbatim:

> Theme: stock Twenty Twenty-Five, no child theme, no custom CSS, WordPress 7.1.1... White only. No
> dark mode... No link back to the office or the arcade anywhere on the page... The clash is total:
> font, palette, mode, spacing and navigation all differ from both sister properties.

This directive builds the child theme that fixes it. It must match two properties, not invent a
third: the office (`RFD_IT_Services_Site/themes/rfd`) for tokens, type and page chrome, and the
arcade (`RFD_IT_Services_Site/static/css/arcade.css`) for the one card pattern the blog borrows.

## 2. Scope

- `theme/rfd-blog/style.css`
- `theme/rfd-blog/theme.json`
- `theme/rfd-blog/functions.php`
- `theme/rfd-blog/templates/home.html`
- `theme/rfd-blog/templates/single.html`
- `theme/rfd-blog/templates/archive.html`
- `theme/rfd-blog/parts/header.html`
- `theme/rfd-blog/parts/footer.html`
- `theme/rfd-blog/patterns/lane-cta-consulting.php`
- `theme/rfd-blog/patterns/lane-cta-building.php`
- `theme/build.py`
- `theme/README.md`
- `tests/test_theme_build.py`

## Sandbox needs

- `Exec(uv run pytest -q tests/test_theme_build.py)`
- `Exec(uv run pytest -q)`
- `Exec(uv run python theme/build.py)`

## 3. The work

### `theme/rfd-blog/style.css`

Child-theme header block first:

```css
/*
Theme Name: RFD Blog
Template: twentytwentyfive
Version: 0.1.0
Author: Robert Dugger
Description: Child theme carrying the RFD IT Services / RFD Arcade token
system onto the blog: office tokens, dark mode, and lane-coloured post cards.
*/
```

Then the `:root` tokens and dark-mode block, pasted verbatim from the office's
`themes/rfd/assets/css/main.css` (lines 8-16), plus the two lane tokens from the plan's section 4.2:

```css
:root {
  --bg:#ffffff; --surface:#f8fafc; --text:#0f172a; --muted:#475569; --line:#e2e8f0;
  --accent:#1e3a8a; --accent-soft:#eef2ff; --result:#0f766e;
  --lane-consulting:#1e3a8a; --lane-building:#0e7490;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#0b1220; --surface:#111a2e; --text:#e5e9f2; --muted:#9aa6bd; --line:#1f2a44;
          --accent:#93b4ff; --accent-soft:#1a2748; --result:#5eead4;
          --lane-consulting:#93b4ff; --lane-building:#8ed5ff; }
}
```

Type scale copied from `main.css` (plan section 4.2): body 16px/1.55, 17px at 768px; h1 28px/800
rising to 44px at 768px; h2 22px/700; h3 17px/700. Font stacks: `Inter, system-ui, -apple-system,
"Segoe UI", sans-serif` for body/headings, `"JetBrains Mono", ui-monospace, Consolas, monospace` for
code. Reading column 720px, index 1080px, one breakpoint at 768px — same widths as the office
(`.container` / `.container-narrow` in `main.css`).

Card and lane rules, built on the arcade's `.arcade-card` (`RFD_IT_Services_Site/static/css/arcade.css`
lines 5-8), pasted verbatim as the base pattern:

```css
.arcade-card { display: flex; flex-direction: column; gap: 6px; padding: 12px; border: 1px solid var(--line, #e2e8f0);
  border-top: 4px solid var(--game-color, var(--accent, #1e3a8a)); border-radius: 10px;
  background: var(--surface, #f8fafc); color: var(--text, #0f172a); text-decoration: none; }
.arcade-card:hover, .arcade-card:focus-visible { border-color: var(--game-color, var(--accent, #1e3a8a)); }
```

Adapt it into two post-card classes that set the 4px top edge from the lane token instead of
`--game-color`:

```css
.lane-consulting { border-top-color: var(--lane-consulting); }
.lane-building { border-top-color: var(--lane-building); }
```

`functions.php` (below) adds `lane-consulting` / `lane-building` to `post_class()`, so a card markup
of `class="arcade-card lane-consulting"` (or `lane-building`) gets both the base card and its edge
colour with no per-post inline style.

Add code block styles (`pre`/`code` on `--surface`, 1px `--line` border, JetBrains Mono, matching
`main.css`'s `.prose pre`/`code`) and a callout/proof-box style from `main.css`'s `.proof`/`.note`
(`--surface` background, `--line` border, `--result` teal for a "what changed" callout variant).

### `theme/rfd-blog/theme.json`

`settings.color.palette` entries named **exactly**: `bg`, `surface`, `text`, `muted`, `line`,
`accent`, `accent-soft`, `result`, `lane-consulting`, `lane-building` — light-mode values from the
`:root` block above (dark mode is the media query in `style.css`; block themes have no native
dark-palette swap).

`settings.typography.fontFamilies`: two self-hosted `fontFace` entries, Inter and JetBrains Mono,
pointing at files under `assets/fonts/` (e.g. `assets/fonts/inter-latin-400-normal.woff2`, `-600-`,
`-800-`, `assets/fonts/jetbrains-mono-latin-400-normal.woff2`). **These font files are REQUIRED
INPUTS Robert supplies** — this run has no network access and cannot download them; do not attempt
to fetch them. `build.py` must succeed with the files absent, reporting them missing (see below).

`settings.layout`: `contentSize: "720px"`, `wideSize: "1080px"`.

### `theme/rfd-blog/functions.php`

- Enqueue `style.css` via `wp_enqueue_style` on `wp_enqueue_scripts`, parent Twenty Twenty-Five
  stylesheet enqueued first as its dependency (standard child-theme pattern).
- `rfd_lane( string $category_slug ): ?string` maps category slug to `"consulting"`/`"building"`/
  `null` from the plan's section 4.1 lists (slugified): consulting = `contact-center`, `convoso`,
  `dnc-compliance`, `dialer-ops`, `sheets-automation`; building = `dev-notes`, `games`,
  `agents-automation`, `sessions`.
- A `body_class` filter adds `lane-consulting`/`lane-building` when the current post/archive's
  primary category maps to a lane; a `post_class` filter does the same per-post so a card template
  gets `arcade-card lane-consulting`/`lane-building` from `post_class()` alone.

### Templates and parts

Block markup (HTML, using `<!-- wp:... -->` comments) following the plan's section 4.3 page anatomy:

- `parts/header.html`: text brand "Robert Dugger" left; nav "Consulting · Blog · Arcade · About ·
  Contact" with Contact rendered as `.btn-primary`; Consulting links to the office
  (`https://rfditservices.com`), Arcade to the arcade (`https://games.rfditservices.com`), Blog is
  the current item (no link or `aria-current="page"`).
- `parts/footer.html`: three lists — Consulting (Services, Case studies, Contact), Building (Arcade,
  GitHub, Studio), Elsewhere (LinkedIn, Dev.to, RSS) — plus a copyright line with "RFD IT Services".
  Same structure as the office footer (`.site-footer` in `main.css`).
- `templates/home.html`: standfirst ("Notes from a contact-center automation engineer who also ships
  games"), a query loop rendering `.arcade-card` post cards three across at 1080px, one across on
  phones (reuse `.card-grid.three`), a category-pill filter row.
- `templates/single.html`: 720px column, category chip, title, excerpt as dek, byline row (`.photo`
  reduced to 40px via inline override), featured image full column width, content, the matching
  `lane-cta-*` pattern, then an author box.
- `templates/archive.html`: same card grid as home, filtered to one category/lane.

### Patterns

- `patterns/lane-cta-consulting.php`: "Talk to Robert about your contact center" linking to
  `https://rfditservices.com/contact`.
- `patterns/lane-cta-building.php`: "Play what I'm building" linking to
  `https://games.rfditservices.com` plus a GitHub link.

### `theme/build.py`

A pure-Python script (stdlib only — `zipfile`, `json`, `pathlib`; no new dependency) that:

1. Parses `theme/rfd-blog/theme.json`, fails loudly if it is not valid JSON.
2. Checks every file `style.css`'s header and `functions.php`'s enqueue call reference exists on
   disk (`style.css`, `functions.php`, the template/part/pattern files above).
3. Reports (print, do not raise) which `assets/fonts/*` files listed in `theme.json`'s `fontFace`
   entries are missing — the "doctor" check the font-files-absent case needs.
4. Writes `theme/dist/rfd-blog.zip` containing the theme directory contents.
5. Exits 0 whether or not the font files are present; exits non-zero only on a real build defect
   (invalid `theme.json`, a referenced non-font file missing).

### `theme/README.md`

Ten-step install checklist for Robert: 1) download/build `rfd-blog.zip`, 2) WordPress admin →
Appearance → Themes → Add New → Upload, 3) activate, 4) Appearance → Editor → Navigation, set up
the header menu, 5) Settings → Permalinks to post name, 6) create the nine categories from the
plan's section 4.1 with matching slugs, 7) Settings → Reading → front page displays the `home`
template, 8) upload the Inter and JetBrains Mono font files into `assets/fonts/` (this directive
cannot do this step), 9) check light/dark mode against OS setting, 10) check header/footer
cross-links resolve to the office and arcade.

## 4. What NOT to do

- No PHP execution, no `wp-env`, no Playwright, no WordPress runtime of any kind — none is
  available in this run. Verification is `build.py` plus `tests/test_theme_build.py` only.
- No network calls: do not attempt to download Inter, JetBrains Mono, or anything else.
- No changes under `blog_engine/` — this directive is theme-only.
- No new Python dependencies — `theme/build.py` is stdlib-only.
- Do not create a new repo. Everything lives under `theme/` in this repo.

## 5. Verification

```
uv run pytest -q tests/test_theme_build.py
```
Expect: all tests in that file pass.

```
uv run python theme/build.py
```
Expect: exits 0, prints which font files under `assets/fonts/` are missing, writes
`theme/dist/rfd-blog.zip`.

```
uv run pytest -q
```
Expect: no fewer than the pre-existing 214 passed (verified 2026-09-23 with `uv run python
--version` → `Python 3.12.12` and `uv run pytest -q` → `214 passed, 2 warnings in 12.59s`), plus the
new theme-build tests, all passing.

## 6. Rules for this run

The run is NON-INTERACTIVE and any tool call needing confirmation ends it. Never install, download,
or fetch. Never read outside the worktree. Do not search, glob, or hunt — stop and write it in the
Status row if something named here is missing. Never commit to main, never push, never deploy; work
stays on `directive/rfd-blog-engine-blog-theme-child-directive`. Free models only, no model config is
touched. Create no scratch or debug files outside `.devin-scratch/` and never delete files. If a tool
call is blocked, stop and write why in the Status row.

## 7. Completion criteria

- [ ] `theme/rfd-blog/style.css` exists with the child-theme header, `:root`/dark-mode tokens,
      type scale, `.lane-consulting`/`.lane-building` rules, code block and callout styles.
- [ ] `theme/rfd-blog/theme.json` has the eleven palette slugs (bg/surface/text/muted/line/accent/
      accent-soft/result/lane-consulting/lane-building) and two self-hosted `fontFace` entries.
- [ ] `functions.php`, all five templates/parts, both lane-CTA patterns exist.
- [ ] `theme/build.py` runs, reports missing fonts without failing, writes `theme/dist/rfd-blog.zip`.
- [ ] `theme/README.md` has the ten-step checklist.
- [ ] `tests/test_theme_build.py` passes: zip contains the expected files, `theme.json` has the
      eleven palette slugs, `style.css` contains both `prefers-color-scheme: dark` and
      `--lane-building`.
- [ ] `uv run pytest -q` is all-green.

## 8. Report

State: files created (paths), `theme/build.py` output including which fonts it reported missing,
`uv run pytest -q` final line, and confirmation that no WordPress runtime was invoked at any point.
