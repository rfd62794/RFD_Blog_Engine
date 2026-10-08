---
title: "How do I bulk update meta descriptions, tags and categories in WordPress?"
excerpt: "Use the REST API: map each post to a category, tags and excerpt in a reviewed file, run a dry run, then update every post without touching its status."
tags: [wordpress, rest-api, seo, python, bulk-edit]
categories: [How-to]
keyword: wordpress bulk update meta description tags
status: draft
---

Write a mapping file with one row per post (its ID, a category, a few tags and an excerpt), review it by hand, and then let a script send one REST API update per post. Preview first. Never include a `status` field in the update, so the script cannot change whether a post is live. WordPress treats the excerpt as the place for a short summary; many themes and SEO plugins use it as the meta description.

I did this for my own blog. An audit I ran showed zero tags, zero featured images and no meaningful categories across the whole blog. The script exists and its dry run works. I have found no record in the repo that I ran it live, so treat the live result as unproven.

## What you need

- WordPress with the REST API, and an application password for a user who can edit posts. Editing posts that are already published needs a role with that right (see the problems list below).
- A list of your posts with their IDs. A request to `/wp-json/wp/v2/posts?per_page=100` returns up to 100 at a time. I had 56 and the response header reported that total.
- Python, with an HTTP library.

## Step 1: Look before you change

My live check found 56 posts. All 56 already had an excerpt. Five had no category at all. Four categories held the other 51 posts, and the other two (including Uncategorized) were empty. That check is from 2026-09-23, so redo it. Check your numbers the same way; they decide how big the job is.

## Step 2: Write the mapping file

```yaml
posts:
  - slug: my-first-post
    wp_id: 17
    category: "How-to"
    tags: [python, automation, data]
    excerpt: keep
```

`excerpt: keep` is what every row of mine says. One thing I found while checking my own code: the apply step does not read that field. It always sends back the post's existing excerpt (tags stripped), or the fallback below if there is none, so editing the field in the file changes nothing. A category and tags you invent now become permanent site structure, so decide the set first. I drafted my mapping with AI help and then reviewed every row myself. The header of my file says nothing in it is final until I approve it.

Keep categories few: mine use a small fixed set. Aim for three to six tags per post.

## Step 3: Resolve names to IDs

The REST API wants term IDs, not names. For each name, list the existing terms, match them ignoring case, and create one only if nothing matches. Two details bit me:

- **Names come back HTML-encoded.** An ampersand arrives as `&amp;`, so compare after unescaping or you will create a duplicate of "Agents & Automation" on every run.
- **Lists stop at 100.** My list function adds a `truncated` marker when exactly 100 come back, so it cannot silently miss the rest.

Look each name up once per run and keep the answer in a dictionary.

## Step 4: Build the update

```python
fields = {
    "categories": [category_id],
    "tags": [tag_id_1, tag_id_2, tag_id_3],
    "excerpt": excerpt,
}
# deliberately no "status" key
```

For an empty excerpt, my fallback is the first 30 words of the post's rendered content with the HTML tags stripped. That is serviceable, not good. Read those by hand.

## Step 5: Dry run, then apply

The command takes exactly one of `--dry-run` or `--apply` and refuses both or neither. The dry run prints one line per post: ID, slug, lane, category, tags and the excerpt value from the file. It makes no writes, and it does not even create categories, because creating a term is a write too.

One bad row must not stop the rest. My walker runs a metadata gate on each row (a category that is not Uncategorized, at least three tags, a featured image). If a row fails, it logs why and moves on. If the post has been deleted since you wrote the mapping, the 404 is logged and skipped as well.

## Common problems

- **403 on every update.** If the account is a Contributor, WordPress will not let it edit posts that are already published. My script treats this as an expected outcome and logs "needs manual approval". When all 56 fail, it ends with `apply: 0 updated, 56 skipped (403) - credential lacks edit_published_posts`. You then need a credential with that right, used only for this job.
- **The meta description does not change.** The excerpt is what my engine uses. Whether your theme or SEO plugin reads it varies, so check one post's page source after an update.
- **Duplicate tags.** Almost always the HTML-encoding issue above.
- **Featured images.** I attached a generated image to each post at the same time. Uploading media is a separate permission (`upload_files`, which WordPress does not give Contributors), so test it separately.

## FAQ

**Is there a plugin for this?** Yes, several exist. I did not compare them, so I cannot say which is best.

**Will changing categories change my URLs?** It can, if your permalink structure includes the category. Check yours before a bulk change.

**Should I back up first?** Yes. I would export the posts or take a database backup first. My script never changes content or status, but I have not tested a rollback.

**How long does it take?** I have no timing for a full run. Each post needs several calls (a fetch, term lookups, an image upload and the update), so I would expect it to take a while.

<!-- fact-checked 2026-10-08: 17 claims confirmed, 3 corrected, 1 removed; remaining notes: live apply never confirmed; apply ignores the mapping excerpt field (post says so); held at draft until a live run -->
