# WordPress reconciliation, 2026-10-08

Method: public WP REST GET (status=publish, 59 posts) and public Dev.to API (18 articles). The engine's own credentials were tried for status=draft/pending/future/private and WP returned 401 `rest_not_logged_in` (app password not accepted), so non-published WP posts could NOT be read. Nothing was written to WP or Dev.to.

## Reconciliation

| post_id | local status | WP id / status / date / url | Dev.to | verdict |
|---|---|---|---|---|
| dev-002 | approved | 95 publish 2026-06-14 /2026/06/14/a-side-effect-of-a-side-effect/ | 3902551 (matches local) | published-but-local-says-approved |
| dev-003 | approved | 96 publish 2026-09-27 the-privybot-architecture-why-mcp-matters | none | published-but-local-says-approved (local wp_url was ?p=96) |
| dev-004 | approved | 94 publish 2026-06-07 the-spec-is-load-bearing | 3983784 (matches local) | published-but-local-says-approved |
| dev-005 | approved | 97 publish 2026-06-28 borrowing-code-vs-reinventing-the-wheel (title "The grammar of what's possible") | 4025086 (matches local) | published-but-local-says-approved |
| dev-006 | approved | 100 publish 2026-07-05 the-agent-told-me-it-was-done-the-tests-said-otherwise | 4008835 found remotely, missing locally | published-but-local-says-approved; Dev.to id was missing |
| dev-007 | approved | 101 publish 2026-07-12 i-processed-671000-records-in-6-minutes-and-32-seconds | none | published-but-local-says-approved |
| dev-008..dev-033 (26) | draft | no title match among 59 published | no match | local-only draft (not on WP as published; drafts/pending unknown, see caveat) |

Counts: 6 published-but-local-says-approved; 26 local-only drafts; 0 in-sync; 0 approved-never-published.
Note: these 26 files exist only in the live checkout, not on origin/main (main tracks dev-002..007 only).

WP-only (published on WP, no local record): 53 posts, e.g. ids 92 (dev-001, "I built the same game for 20 years"; Dev.to 3844728), 107, 118, 146-148, 152-154, 158-161, 166-168, 190-201, 214 and others. Inventory `.bak` lists 7 posts (dev-001..007) all "published" with wp_post_id null; titles for dev-002/004/005 in the .bak differ from the final published titles. dev-001 has no draft JSON.

Dev.to articles with no local record: 4025004, 4014907, 4008839, 4008836, 4003... (see Dev.to list for author robert_floyddugger_6f9a4), plus 3983782, 3973816/17, 3936119, 4025087, 4035152, 4045541, 4127635, 4243537.

## Date caveat
dev-003 (2026-09-27) and dev-006/007 carry WP dates well after their approved_at (June): they were scheduled later on the WP calendar by hand. dev-002/004/005 `published_at` hold the Dev.to time, not the WP date; left unchanged.

## Applied patch (unambiguous: wp_post_id already matched and the live post was fetched)
- dev-002..007: status approved -> published; wp_url -> real permalink (was `?p=` for 003, 005, 006, 007).
- dev-003, 006, 007: published_at was null -> WP date (local site time, no tz).
- dev-006: devto_id 4008835 + devto_url added (exact title match, only one hit).

## Left untouched / ambiguous
- dev-002/004/005 published_at (Dev.to time vs WP date).
- dev-003, dev-007: no Dev.to article found.
- All 26 drafts: cannot confirm absence of WP draft/pending/future copies without working credentials.
