---
title: "How do I stop an automation from publishing WordPress posts by accident?"
excerpt: "Give the automation a Contributor-role WordPress user, so it can save drafts and submit for review but cannot publish. Add code checks on top."
tags: [wordpress, contributor-role, automation, rest-api, content-safety]
categories: [How-to]
keyword: wordpress contributor role automation
status: draft
---

Create a separate WordPress user for the automation and give it the Contributor role. WordPress then lets that account write drafts and submit posts for review, but not publish them. That gives you a hard limit that holds even if your script has a bug or an AI tool tells it to do the wrong thing. Then add your own checks in the code as a second layer.

I learned this the practical way. I run a blog engine that writes drafts with AI help, and I had been burned by AI-generated content before. I wanted "never publish without me" enforced by the tool, not just written in a note.

## What you need

- WordPress with the REST API on, and permission to add users.
- An application password for the new user. Keep it in an environment variable and out of your code.
- A script that creates posts through `/wp-json/wp/v2/posts`.

## Step 1: Add a user with the Contributor role

Use a new user, not your own account. Do not reuse your administrator login for scripts. Choose Contributor as the role. By default, WordPress documents this role as able to write and edit its own posts but not publish them. [VERIFY: confirm against the current WordPress roles documentation.]

My README says the engine's user "should have" this role. I have not got proof in the repo that the switch was made on the live site, and the directive that introduced it says I would "switch" the credentials. [VERIFY: confirm the live user's role before trusting the setup]

## Step 2: Never ask for any status but draft or pending

Role limits are the wall. Code limits are the door lock. My WordPress wrapper has a validator:

```python
WRITABLE_WP_STATUSES = {"draft", "pending"}

def validate_writable_status(status):
    if status in ("publish", "future"):
        raise ValueError("publishing is Robert's: the engine only creates "
                         "WordPress drafts; publish or schedule it in WordPress")
    if status not in WRITABLE_WP_STATUSES:
        raise ValueError(f"Invalid status: {status}")
```

`future` matters as much as `publish`: it means scheduled, which is publishing later. Both create and update calls go through this check. The push tool sends `pending`, so the post waits in the review queue. The tool also refuses a `publish=True` or a scheduled date argument before it makes any network call. The directive asked for a test that searches the package for those two status words, so a later edit cannot add them quietly. [VERIFY: confirm that test exists]

## Step 3: Block drafts that are not finished

A draft can be harmless to publish by role and still be wrong. My content guard refuses to push a draft that has:

- a `[ROBERT: ...]` placeholder, the marker I leave where a fact needs a human,
- `[TODO`, `TBD` or `lorem ipsum`,
- an empty excerpt (the page's meta description), or
- no categories.

There is a second gate for metadata: a featured image, a category that is not Uncategorized, and at least three tags.

I added the placeholder rule because four client drafts on 2026-09-23 had visible placeholders for numbers only I had.

## Step 4: Make downstream steps wait for the live post

My cross-posting to Dev.to checks the WordPress post's status through the REST API first and refuses unless it is `publish`. So nothing is syndicated before I have published and the canonical page exists.

## Step 5: Test the refusals

The test suite for this change passed 214 tests, per the run record, and covers: publish and scheduled arguments raising the exact message with no network call, a normal push sending `pending`, a placeholder draft being refused with the placeholder named, and cross-posting being refused when WordPress reports `draft` or `pending`.

## What the Contributor role broke

There are two lessons here.

**It cannot edit posts that are already live.** I had a backfill script built to add categories, tags and excerpts to 56 existing posts. WordPress answers a Contributor's edit of a published post with 403. The directive I wrote for it says plainly that every one of the 56 would be skipped, and that is correct behavior. The CLI ends with `apply: 0 updated, 56 skipped (403) - credential lacks edit_published_posts`. Fixing that needs a different credential, a decision I keep for myself.

**Images may not upload.** My engine uploads a featured image through the media endpoint. As far as I know, the stock Contributor role lacks the capability to upload files. [VERIFY: nothing I read shows what happens live with the Contributor credential. Test an upload before relying on this setup.]

## Common problems

- **A 403 on an update.** Check whether the post is already published.
- **Scheduling sneaks in as `future`.** Block it in code as well as by role.
- **The application password leaks.** Keep it in `.env`, and never print it in logs or tests.

## FAQ

**Is the Contributor role enough on its own?** It stops publishing. It does not stop a bad draft being submitted for review, so you still need to read what arrives.

**Can I use the Author role?** My understanding is that Authors can publish their own posts, so it would not give this protection. [VERIFY]

**Do I still need the code checks?** I think so. Role mistakes happen, and the code checks give clear messages.

**Can the automation edit its own pending posts?** I believe so, but I have not verified it. [VERIFY]
