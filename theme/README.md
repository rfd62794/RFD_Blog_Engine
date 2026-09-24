# RFD Blog child theme

`rfd-blog` is a Twenty Twenty-Five child theme that carries the RFD IT
Services / RFD Arcade token system onto the blog: the office tokens, OS-driven
dark mode, and lane-coloured post cards (blue for consulting, cyan for
building).

Build the zip with `uv run python theme/build.py` — it reports which font
files under `rfd-blog/assets/fonts/` are still missing, then writes
`theme/dist/rfd-blog.zip`.

## Install checklist (Robert)

1. Download or build `rfd-blog.zip` (`uv run python theme/build.py` →
   `theme/dist/rfd-blog.zip`).
2. WordPress admin → Appearance → Themes → Add New → Upload Theme → choose the
   zip.
3. Activate "RFD Blog" (Twenty Twenty-Five must be installed as its parent).
4. Appearance → Editor → Navigation: set up the header menu (Consulting ·
   Blog · Arcade · About · Contact, with Contact as the primary button).
5. Settings → Permalinks → Post name.
6. Posts → Categories: create the nine lane categories with matching slugs —
   Consulting: `contact-center`, `convoso`, `dnc-compliance`, `dialer-ops`,
   `sheets-automation`; Building: `dev-notes`, `games`, `agents-automation`,
   `sessions`.
7. Settings → Reading → front page displays the `home` template.
8. Upload the Inter and JetBrains Mono font files into
   `wp-content/themes/rfd-blog/assets/fonts/`
   (`inter-latin-400-normal.woff2`, `inter-latin-600-normal.woff2`,
   `inter-latin-800-normal.woff2`, `jetbrains-mono-latin-400-normal.woff2`) —
   or drop them into the repo's `assets/fonts/` before building the zip.
9. Check light/dark mode follows the OS setting (`prefers-color-scheme`).
10. Check the header and footer cross-links resolve to the office
    (rfditservices.com) and the arcade (games.rfditservices.com).
