---
title: "How to publish a clean public copy of a private repo"
excerpt: "Before showing a private project publicly, copy it without git history, cut what doesn't belong, replace names, and scan it. My checklist from a real export."
tags: [git, github, security, portfolio, opensource]
categories: [How-to]
keyword: publish private repo publicly without history
lane: client
status: draft
source: AgentFlow export scrub report (Nov 4 2026)
---

The safest way to show a private project in public is to make a new repository from a copy of its current files, with no git history, after cutting everything that isn't the product and scanning what's left. Flipping the old repo from private to public publishes every commit it ever had, including the ones you forgot about.

I just did this for my agent harness, which I want in my portfolio. Here is the checklist I used.

## Step 1: Copy files, not history

Take the current tree at a known commit and copy it to a fresh folder. Don't clone, and don't keep `.git`. Write down the source commit so you can trace the public copy back later.

Old history is where the surprises live: a config file committed once and deleted, a token pasted into a commit message, an early README that named people. Even if today's files are clean, the history may not be.

## Step 2: Leave whole folders out

Most of what I removed wasn't secret. It just wasn't the product. From mine:

- the `docs/` folder, which had grown to over 2,000 files of notes, directives and memory exports;
- agent instruction files and agent config folders (`.claude`, `.devin` and similar);
- a committed config backup and a stray probe file;
- status files that described the state of my machines on one particular day.

A visitor wants the code, the tests and a README that explains them. Everything else is a liability that adds nothing.

## Step 3: Replace names everywhere

Search the remaining files for anything that identifies people, accounts or machines, and replace each with a neutral stand-in:

| Found | Replaced with |
|---|---|
| Organization and account names | `mirror-org`, `mirror-user` |
| A collaborator's first name | `Teammate` |
| A home server's host name | `homeserver` |
| Private network IPs | addresses from a reserved range |
| The Windows user name in paths | `you` |

Keep a list of what you replaced. You will want it when something in the public copy reads oddly six months from now.

## Step 4: Check what you deliberately kept

Some things look alarming and aren't. My test files contain fake keys on purpose (strings shaped like `sk-...` and `ghp_...`) so the secret-detection tests have something to detect. GitHub push protection may block the first push because of them. Decide in advance whether to mark them as test values or allow them.

Also read any setup scripts once before publishing. Mine are Windows bootstrap scripts written for my own machines.

## Step 5: Scan before the first push

Run a secret scanner over the folder (gitleaks and trufflehog are the common ones), then search for your own email addresses, IP ranges and any name you replaced. A scrub that relied on a find-and-replace list will miss the variant you didn't think of.

## Step 6: Write the README for a stranger

The original README was written for me and my agents. The public one is a case study: what the system did, what the numbers were, what went wrong, and what I'd reuse. A good public copy answers "why should I read this code" in the first screen.

## Step 7: Get the OK from anyone with a stake

If the project ever touched work, a client or someone else's systems, ask before you publish, even when you're sure the copy is clean.

## The short version

Copy the files, cut what isn't the product, rename what identifies anyone, scan, and write the README last. Publishing an old repo as-is publishes its whole past.
