---
title: "The rule my AI agents follow before they merge: when unsure, defer"
excerpt: "I let my agents merge pull requests, but only if a tool says yes on every check. Any doubt, missing fact or failed lookup means defer to me."
tags: [ai-agents, git, code-review, automation, safety, solo-developer]
categories: [Build in public]
keyword: ai agent merge rules human approval
status: reviewed
---

For months I was the only one who merged. Every pull request from an AI agent waited for me, and I had a day job. The queue of finished-but-unmerged work grew faster than I could read it.

On 2026-10-06 I settled the goal in one sentence: let the second agent merge safe, verified pull requests under the same rules the first one follows, with a deferral instinct. When it is unsure, it hands the decision back instead of merging.

The word that matters there is instinct. I did not want a list of things the agent is forbidden to do. I wanted the default to be "no".

## Why the written rule was not enough

I wrote the directive for this the same day. Its first section is a list of four gaps between the rule I had written down and the rule my code enforced. Reading it back, three of them are embarrassing.

**1. Identity.** The merge command hard-coded its actor as `cli`. Whether it was me, a Claude session or the delegated overseer, the merge log said `cli`. Nothing stopped a headless run from calling the command either. The only barrier was that one allow-list did not contain the command. A rule enforced by a missing line is one edit from gone.

**2. No deferral.** The code had a few fixed holds: a draft, the wrong base branch, a comment starting `needs-robert:`. It had no single decision that covered a failed lookup, a verified commit that is not the current head, a missing review verdict or a pull request GitHub had not finished computing. A tool that merges on "I found no objection" has the wrong default.

**3. Three descriptions of the same role.** My agent instructions, my collaboration doc and the overseer's persona each said something slightly different about who may merge and who may mark work Done. Two said "only on Robert's explicit instruction" while the install config already let the delegate mark Done after a verified merge.

**4. Nothing pinned the sandbox.** The dispatched agent's rules deny a local git merge, but no test said so. A future edit could grant a merge silently.

## The design: one pure function that returns a reason

The core is a function with a deliberately boring signature. You give it the facts the caller already fetched. It returns the first reason to defer, or nothing.

Every field is optional, because "the lookup failed" has to be representable. The rule the tests prove: **uncertainty always defers, never merges.** A missing field defers. A failed lookup defers. A mergeable state of `UNKNOWN`, `CONFLICTING` or nothing defers. Only the exact string `MERGEABLE` passes. An actor of `unknown`, empty, `cli` or `dispatched` defers.

The directive lists twelve checks, in order. A few of them:

- a protected repo;
- a blog or posts path, because publishing is mine alone;
- changes to dependencies, the allow-list or the sandbox code, which an existing helper already holds;
- deploy, publish, image, audio and gameplay paths, matched broadly on purpose, because "a false defer costs one glance, a false merge costs trust";
- added lines that look like secrets, where the reason names the pattern class and never the matched text;
- the verified commit is not the head any more, or there is no stored verify report, or no review verdict that meets the existing eligibility check.

The last item is a catch-all: any required field still empty. I added it so a field someone adds later cannot pass by being absent.

## What deferral looks like

On a defer the tool posts exactly one comment, `needs-robert: <reason>`, writes one line to the merge log and exits with code 4. I chose a distinct exit code so an overseer can tell "deferred, hand to Robert" from an error and from a clean merge. Running it again with the comment already present posts nothing new. A deferred pull request never reaches the merge call, and it does not even trigger a test run.

The same command also refuses to run at all when the environment says it is a dispatched, headless run. A dispatched run does not get a dry run either.

## One command, and it is the only one

The role section of the directive is a single paragraph that I want pasted verbatim into the instructions, the collaboration doc and the persona: merge means one command, from an interactive session or the delegated overseer only, never squashing and never merging locally. Done is set only after the merge verifies, on non-protected repos, and never for blog publishing.

That also covers a lesson I already paid for. On 2026-10-01 my mark-Done step refused five squash-merged pull requests, because a squash makes a new commit and the branch tip never becomes an ancestor of main. A later fix teaches the step to prove a squash landed by comparing trees, but the rule still says never squash.

## Where it actually stands

This is a work in progress, and I should say so. As of the last queue entry I read, the directive is In progress: dispatched on 2026-10-06 at 19:22 to my second agent, with a 600-line limit per file and two modules that it must barely touch (the safe-merge file at 486 lines, and the merge-ready file, which was 591 lines when I wrote the directive and is 519 on main now). When I looked on 2026-10-07, neither main nor the directive's branch had the new modules, so none of this is shipped yet.

It will probably also defer on its own pull request. The directive edits the agent instructions and the collaboration doc, which are held paths. I wrote that into the directive: "that is correct."

## What to take from this

If you want an agent to merge, write the default first. Not "merge unless a check fails", but "defer unless every check positively passes". Make a missing fact a reason, not a pass. And give deferral its own exit code and its own comment, so it is a visible outcome and not a silent skip.

<!-- fact-checked 2026-10-08: 18 claims confirmed, 3 corrected, 1 removed; remaining notes: directive not yet landed (no merge_defer/merge_identity on main or branch as of 2026-10-07); line counts are as of directive time -->
