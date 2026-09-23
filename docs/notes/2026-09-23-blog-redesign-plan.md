# Blog redesign plan: the reading room between the office and the arcade

Date: 2026-09-23. Status: proposal for Robert's review. Nothing here is built.

## 1. Goal

Make blog.rfditservices.com look like it belongs to the same person as
rfditservices.com (the office) and games.rfditservices.com (the arcade), and
read as a professional publication rather than a stock WordPress install.

Success looks like:

- A visitor moving between the three properties sees one brand: same dark
  navy, same blue accent family, same type, same footer, same cross-links.
- The blog switches light/dark with the OS exactly as the main site does.
- Every post has a branded featured image, a real category and tags, so
  cards, social previews and Dev.to syndication all look intentional.
- Robert's total hands-on time is about two hours: one to install the theme,
  one to approve the backfilled drafts.

## 2. What the office and the arcade already share (the bridge)

The two Hugo themes in RFD_IT_Services_Site do not share one token file, but
they agree on more than they look like they do. The blog should build on the
overlap, not on either theme alone.

| Token | Office (`themes/rfd/assets/css/main.css` 8-16) | Arcade (`tailwind.config.js` 11-64) | Blog takes |
|---|---|---|---|
| Dark background | `#0b1220` | `#0b1326` | `#0b1220` |
| Dark surface | `#111a2e` | `#171f33` | `#111a2e` |
| Dark text | `#e5e9f2` | `#dbe2fd` | `#e5e9f2` |
| Dark muted | `#9aa6bd` | `#bdc8d1` | `#9aa6bd` |
| Dark border | `#1f2a44` | `#3e484f` | `#1f2a44` |
| Accent (dark) | `#93b4ff` | `#8ed5ff` primary, `#bccbff` tertiary | `#93b4ff` base, `#8ed5ff` for the dev lane |
| Second accent | `#5eead4` result | `#4edea3` emerald | `#5eead4` for results and success callouts |
| Light mode | white / `#f8fafc` / `#0f172a` / accent `#1e3a8a` | none, dark only | office light tokens, OS-driven |
| Headings | Inter 800 | Sora 700 | Inter 800 |
| Body | Inter 400, 16px/1.55, 17px at 768px | Hanken Grotesk 400 | Inter, same scale |
| Mono | `ui-monospace, Consolas` | JetBrains Mono | JetBrains Mono (code is a first-class citizen on a dev blog) |
| Radius | 8px buttons, 10px cards, 999px pills | 4px to 12px scale | 8 / 10 / 999 |
| Content width | 1080px, 720px narrow | 1440px | 1080px index, 720px reading column |
| Card | `.card`, 1px border, 10px radius | `.arcade-card`: same plus a 4px top border in `--game-color` | the arcade card: 4px top border in the post's lane colour |
| Cross-links | footer links Blog and Games; nav has Games | footer links main site and "Writing" (the blog) | header and footer link both |

The `.arcade-card` in `static/css/arcade.css` is the one component that already
renders on both properties using the office's variables with fallbacks. It is
the natural post card.

## 3. The blog today

- Theme: stock Twenty Twenty-Five, no child theme, no custom CSS, WordPress
  7.1.1, Site Kit plugin. Default palette (`#FFFFFF` base, `#111111` contrast,
  vivid cyan-blue, vivid purple), Manrope body at weight 300, Fira Code.
- White only. No dark mode. Default block spacing. No sidebar.
- No link back to the office or the arcade anywhere on the page.
- Content audit in `data/state/current.md`: zero tags, zero featured images,
  no meaningful categories across the whole blog. The sampled post confirms it.
- The engine can only create drafts and pending posts (Robert-only publishing,
  merged today in PR #1). It cannot touch the theme, and should not.

The clash is total: font, palette, mode, spacing and navigation all differ
from both sister properties.

## 4. Design direction

One sentence: the office's calm token system, with the arcade's one playful
move (a coloured card edge) used to signal which lane a post belongs to.

### 4.1 Two lanes, two accents

The blog already has two kinds of post with opposite structures (the dev
identity Content Frame and the client-facing search-intent posts). The design
makes the lane visible without two themes:

| Lane | Categories | Accent | Card edge | End-of-post CTA |
|---|---|---|---|---|
| Consulting | Contact Center, Convoso, DNC & Compliance, Dialer Ops, Sheets Automation | office blue `#1e3a8a` / `#93b4ff` | blue | "Talk to Robert about your contact center" to rfditservices.com/contact |
| Building | Dev Notes, Games, Agents & Automation, Sessions | arcade cyan `#8ed5ff` | cyan | "Play what I'm building" to games.rfditservices.com plus GitHub |

Category is the only thing a post needs to carry; the theme derives colour
and CTA from it.

### 4.2 Tokens

Custom properties named exactly as the office names them, so a future move
to a shared token file is a copy, not a translation:

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

Fonts: Inter 400/600/800 and JetBrains Mono 400, self-hosted in the theme
(no Google Fonts request, same as both sister sites). Type scale copied from
`main.css` lines 20-27: body 16px/1.55 rising to 17px at 768px, h1 28px/800
rising to 44px, h2 22px/700, h3 17px/700. Reading column 720px, index 1080px,
one breakpoint at 768px.

### 4.3 Page anatomy

Header (same on every page): text brand "Robert Dugger" left, nav
"Consulting · Blog · Arcade · About · Contact", Contact as the one `.btn-primary`.
Consulting links to the office, Arcade to the arcade. Blog is the current
item. No icon rail, no glass: the blog is the quiet property.

Home / index: a short standfirst ("Notes from a contact-center automation
engineer who also ships games"), then a card grid, three across at 1080px,
one across on phones. Each card: lane-coloured top edge, featured image
(16:9), category chip in lane colour, title, one-line excerpt, date and read
time. No sidebar. A single filter row of category pills, styled like the
arcade's `.arcade-filter`.

Post page: 720px column. Category chip, h1, dek (the excerpt), byline row with
the office's 88px circular headshot reduced to 40px, date, read time.
Featured image full column width. Body with the office's proof-box style for
callouts and `--result` teal for "what changed" summaries. Code blocks in
JetBrains Mono on `--surface` with a 1px `--line` border. End of post: lane
CTA block, then three related cards from the same lane, then the author box.

Footer: identical structure to the office footer, three lists: Consulting
(Services, Case studies, Contact), Building (Arcade, GitHub, Studio),
Elsewhere (LinkedIn, Dev.to, RSS). One line of copyright with the RFD IT
Services name. The arcade footer gets its "Writing" link relabelled "Blog" so
all three sites use one word.

### 4.4 Imagery

Featured images are generated, not sourced: a 1200x630 card in the lane
colour on `--bg` dark navy, title in Inter 800, small category label, the
brand mark bottom-left. Same image serves as the OpenGraph and Dev.to cover.
This is the single biggest professional-appearance lever because it fixes
the index grid, social previews and syndication at once, and it never needs
a stock photo.

Icons: thin outline SVGs at stroke 1.7 using `currentColor`, the office's
style, not the arcade's filled glyphs.

## 5. Implementation paths (decision gate)

Nothing in either repo records where WordPress is hosted or on what plan.
That single fact chooses the path.

Path A, self-hosted or WordPress.com Business and above (child theme):
a `twentytwentyfive-child` theme with `theme.json` (palette, fonts, spacing,
layout widths), `style.css` (the custom properties above, dark mode media
query, card and lane rules), and three block templates exported from the Site
Editor (home, single, archive). Installed once by Robert as a zip. Everything
else lives in git and re-uploads as a zip on change. This is the recommended
path and the one the phases below assume.

Path B, WordPress.com Personal or Premium (no custom themes): Site Editor
global styles for palette, fonts and widths, plus the Additional CSS panel
for the lane rules and dark mode. About 80 percent of the look. The header
and footer are built as synced patterns in the editor. Font choice is limited
to what the plan offers; Inter is available on WordPress.com.

Either path leaves the blog engine untouched at the WordPress level.

## 6. Phases

Each phase is one directive unless noted. Devin builds, Claude reviews,
Robert installs and approves.

| Phase | What | Who | Robert's time |
|---|---|---|---|
| 0 | Confirm hosting and plan. Confirm the two lanes and their category names. | Robert | 5 min, one Telegram reply |
| 1 | New repo `RFD_Blog_Theme`: child theme scaffold, `theme.json`, `style.css` with the tokens, self-hosted Inter and JetBrains Mono, block templates for home, single, archive, synced header and footer patterns, a `build.py` that zips it. Playwright screenshot test against a local `wp-env` in light and dark. | Devin | 0 |
| 2 | Install: upload the zip, activate, set the menus, drop the Site Kit ads if any, set permalinks. Written as a ten-step checklist in the theme README. | Robert | 45 min |
| 3 | Engine: `featured_image.py` generates the 1200x630 card per lane (Pillow, Inter bundled), uploads via the media endpoint, sets `featured_media` on create and update. `validate_metadata.py` becomes a hard gate: no featured image, no meaningful category, fewer than three tags means no push. Lane derived from category in one mapping file. | Devin | 0 |
| 4 | Backfill: the engine walks every existing post, assigns lane and category from a mapping Claude drafts and Robert approves, generates the featured image, writes excerpts where empty, and submits each as a pending revision. | Devin builds the walker, Claude drafts the mapping, Robert approves in WordPress | 60 min across a week |
| 5 | Sister-site alignment in RFD_IT_Services_Site: arcade footer "Writing" becomes "Blog"; office nav gains "Blog" next to "Games"; both footers get the same three-list structure as the blog. | Devin | 0, merge is Robert's |
| 6 | QA: Lighthouse on home and one post per lane, both modes, phone width; check OG images on LinkedIn and Dev.to; check every cross-link resolves; check RSS validates. Results as a note in the theme repo. | Claude via a Haiku agent | 0 |

Phases 1, 3 and 5 are independent and can run in parallel. Phase 2 waits on
1; phase 4 on 2 and 3; phase 6 on 4.

## 7. What is deliberately left out

- No custom fonts beyond Inter and JetBrains Mono. No Sora on the blog.
- No glass panels, scanlines or glow. Those stay the arcade's signature.
- No comments system, no newsletter popup, no sidebar, no share buttons
  beyond the OpenGraph image.
- No migration off WordPress. The publishing guarantee (engine drafts, Robert
  publishes, Contributor role) depends on staying there.
- No theme changes to the office. The blog moves toward the office, not the
  other way round.

## 8. Risks

- Hosting plan blocks Path A: then Path B ships the tokens and cards and the
  featured images still carry most of the effect.
- Twenty Twenty-Five updates overwrite nothing in a child theme, but block
  template exports drift between WordPress versions; pin the template files
  in git and re-export only when a WordPress upgrade breaks them.
- The backfill touches every old post: it goes out as pending revisions, so
  nothing changes on the live blog until Robert approves each one.
- Generated featured images are uniform by design; if they read as flat, the
  lane colour and a single subtle grid texture from the arcade's palette is
  the only embellishment to add, not photos.

## 9. Decisions needed from Robert before phase 1

1. Hosting and plan (chooses Path A or B).
2. The two lane names and the category list in section 4.1.
3. Whether the office's nav should gain "Blog" (phase 5) or keep the
   footer-only link.
