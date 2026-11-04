---
title: "How to change the author name and email on old git commits"
excerpt: "A .mailmap file changes how git shows authors but not what GitHub stores. To change the commits themselves, rewrite with git filter-repo and force-push. Steps and caveats."
tags: [git, github, filterrepo, privacy, howto]
categories: [How-to]
keyword: change author email on all git commits
lane: client
status: draft
source: Nov 4 2026 author-identity cleanup across public repos
---

To change the author name or email on commits you've already pushed, rewrite the history with `git filter-repo --mailmap` and force-push every branch. A `.mailmap` file on its own only changes what `git log` and `git shortlog` display locally. GitHub keeps showing the original identity until the commits themselves change.

I did this across seven of my public repos last week, where old commits carried an identity I no longer wanted attached to public work.

## Step 1: Back up first

```bash
git clone --mirror https://github.com/you/repo.git repo.git
git -C repo.git bundle create ../repo-before.bundle --all
```

A rewrite changes every commit hash after the first changed commit. The bundle is your way back.

## Step 2: Write a mailmap

Each line maps an old identity to a new one:

```
New Name <new@example.com> Old Name <old@example.com>
```

If you want your commits linked to your GitHub account without exposing an email, use your GitHub noreply address as the new email. You'll find it in your GitHub email settings.

## Step 3: Rewrite

```bash
cd repo.git
git filter-repo --mailmap ../my-mailmap
```

If the old identity also shows up inside commit messages, for example in sign-off lines, add `--replace-message` with a replacements file to fix those too.

## Step 4: Force-push and check

```bash
git push --force --mirror origin
```

Then clone fresh and run `git shortlog -sne --all`. Every commit should show the new identity.

## What this won't change

- **Forks.** Anyone who forked the repo keeps the old history. Two of mine had a fork each.
- **Archived repos.** You can't push to an archived repo. Unarchive it first, or decide to leave it. I left fourteen old archived repos alone.
- **Open pull requests and their refs.** Old pull request refs keep pointing at old commits.
- **Collaborators' clones.** Anyone with a clone needs to re-clone or reset, because their history no longer matches.

## Should you do it at all?

Rewriting history is disruptive. On a repo other people use, it breaks their clones and their open branches. On a solo repo nobody depends on, it's cheap.

My test was simple: is this identity something I'd be uncomfortable seeing on a public profile next to my name? For the seven active repos, yes. For the archived ones, the old commits weren't worth a rewrite, and I left them.

Keep the backup bundles until you're sure nothing else needed the old hashes. Mine sit in a folder named by date.
