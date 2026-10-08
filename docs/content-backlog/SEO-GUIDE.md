# SEO checklist for how-to posts (matched to this engine)

Short and practical. One person, under an hour a week. Apply it to the client lane first; dev-identity posts follow the RFD Content Frame and only need items 1, 3, 9 and 10.

## What the engine has today (read from the code, 2026-10-08)

A draft is a JSON file in `data/drafts/` with: `post_id`, `title`, `status`, `content`, `excerpt`, `tags`, `categories`, `tags_source`, `categories_source`, timestamps, `wp_post_id`, `wp_url`, `devto_id`, `devto_url`, `generation_source`, `revision_count`. The publish gate (`validate_metadata.check_draft_gate`) also reads `featured_media_id` and requires a featured image, a category that is not "Uncategorized", and at least 3 tags. `content_guard.check` fails an empty `excerpt` and calls it "the meta description".

**The engine has no SEO fields.** The excerpt is doing double duty as the meta description, and nothing stores the target keyword, slug, search intent, FAQ, schema or internal links. [VERIFY: whether `slug` is stored anywhere in `data/inventory/*.yaml`, which is gitignored and was not available.]

## Checklist

1. **One keyword per post.** Pick a phrase a real person types. Put it in the title, the first 100 words, one H2, the slug and the excerpt. Do not stuff it. If you cannot say what the reader will be able to do afterwards, the post is not ready.
2. **Title patterns (50-60 characters).** How-to: `How to <verb> <object> with <tool>`. Fix: `<Symptom>: why it happens and how to fix it`. Decision: `<A> or <B>: how to choose for <situation>`. Put the keyword first. No colons with a subtitle explainer, no "ultimate guide".
3. **Excerpt = meta description, 120-155 characters, hard cap 155.** One plain sentence that says what the reader gets. Include the keyword once. No quotes, no "In this post". Validator: fail over 155, warn under 100.
4. **Answer first.** The first paragraph states the answer in 40-60 words so a search snippet or an answer engine can quote it (ROADMAP M5.2 asks for exactly this).
5. **H2 structure.** 4 to 7 H2s. For how-to: `What you need`, `Step 1 ... Step N` (each an H2 or an ordered list), `Common problems`, `FAQ`. H3 only under an H2. One H1 (the title, supplied by WordPress). Headings carry the keyword family, not the keyword repeated.
6. **FAQ and HowTo JSON-LD, only where the page really has them.** FAQPage for 3 to 5 genuine questions that appear as visible text on the page. HowTo for numbered steps with a clear tool or supply list. Never add schema for content the reader cannot see. Store the data (see fields below) and render the JSON-LD from it at publish time, so the visible text and the markup cannot drift apart. [VERIFY: current Google guidance on FAQ rich-result eligibility before relying on it for traffic; the markup is still valid for answer engines.]
7. **Internal links: 2 to 4 per post.** One to the series hub or the previous post, one to a related how-to, one to the matching case study on rfditservices.com (ROADMAP M5.1). Descriptive anchor text, never "click here". Add a "Related" line to the older post that now points at the new one.
8. **Categories and tags.** Exactly one primary category from a small fixed set: the two lanes (`Build in public`, `How-to`) plus at most one topic category. 3 to 6 tags, lower case, reused from the existing tag list (`list_wordpress_tags`) before inventing a new one. The gate already enforces category and 3-tag minimum; add a 6-tag ceiling and a "tag exists already" warning.
9. **Featured image.** Required by the gate. Add alt text that describes the image, not the keyword.
10. **Syndication.** Dev.to copy carries the blog canonical URL (ROADMAP M5.2). Syndicate after the delay the engine already enforces, so the blog is indexed first.
11. **Update, don't duplicate.** If a post goes stale, edit it and record why in `updated_reason`; do not publish a near-copy.
12. **Truth rules still win.** No invented numbers, clients or quotes (DIRECTION `do_not`). Unverified bits stay marked `[VERIFY]` and the content guard should block publishing while any remain.

## Proposed new fields (draft JSON and inventory YAML)

| Field | Type | Rule |
|---|---|---|
| `slug` | string | lower-case, hyphens, 3 to 6 words, contains the keyword. Stored explicitly so it never silently changes. |
| `keyword` | string | the single target phrase. Required for the client lane. |
| `secondary_keywords` | list[str] | 0 to 4. Informational. |
| `search_intent` | enum | `informational`, `how-to`, `diagnosis`, `decision`, `narrative`. |
| `lane` | enum | `dev` or `client`. Drives which structure the generator and validator apply. |
| `meta_description` | string | optional override; if empty, fall back to `excerpt`. Max 155. This keeps today's drafts valid. |
| `seo_title` | string | optional override for the `<title>` tag, max 60. Falls back to `title`. |
| `faq` | list of `{q, a}` | 0 or 3 to 5 items. Each answer 20 to 60 words. Also appended to the body as visible text. |
| `howto_steps` | list of `{name, text}` | for HowTo JSON-LD; must match the numbered steps in `content`. |
| `internal_links` | list of `{post_id or url, anchor}` | 2 to 4 for the client lane. The validator checks each target exists. |
| `canonical_url` | string | blog URL; used for the Dev.to copy. |
| `updated_reason` | string | required when a published post is edited. |

## Validator additions (extend `validate_metadata.check_draft_gate`)

- `excerpt_length_ok`: 100 to 155 characters.
- `keyword_present`: `keyword` appears in the title, the first 100 words and the slug (client lane only).
- `h2_count_ok`: 4 to 7 H2 headings in `content`.
- `faq_matches_page`: every `faq.q` appears as visible text in `content`.
- `has_internal_links`: at least 2 (client lane only).
- `no_verify_markers`: fail while `[VERIFY]` remains in title, content or excerpt.

All checks are warnings first, then promote to hard gates one at a time, as ROADMAP M3.3 does for category, tags and image.

## Where the work goes

Roadmap M3 (taxonomy, image, validator) is the right home. Add the fields in M3.1 and the checks in M3.3. This file is the spec; nothing in the engine has been changed.
