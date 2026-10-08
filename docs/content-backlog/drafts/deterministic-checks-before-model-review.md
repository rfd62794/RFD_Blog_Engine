---
title: "Deterministic first: code checks before any model reads the diff"
excerpt: "A model review is the expensive step. A plain-code pre-check first blocks branches with no commits, mass deletions, skipped tests or a red suite."
tags: [code-review, ai-agents, automation, testing, python, solo-developer]
categories: [Build in public]
keyword: pre-check before ai code review
status: reviewed
---

When AI agents write most of your code, someone has to review it, and the someone is often another model. That costs money and time. It also wastes both on branches that were never reviewable.

My rule is simple: if a program can decide it, a program decides it. A model only sees a branch after plain code has said the mechanical questions have good answers.

## The number that started it

The comment at the top of my pre-check module gives the reason, and I wrote it from a day's data. Of 18 unattended Claude runs on 2026-09-21, 15 were reviews of branches in Review. A lot of what those runs did was mechanical: does the branch have commits, do the declared files exist, does the check command pass, do the report's numbers match.

I added the pre-check that same day (the commit says "block provably-broken branches before spending a Claude run"). It was 164 lines at first, with a 140-line test file beside it. The module now runs about 560 lines, plus a second small module for the merge re-check.

The design in one sentence, from the module itself: a branch that fails these checks is Blocked with the precise reason without spending a model run; one that passes reaches the model with the facts attached, so it only judges design.

## What the checks are

They run in a fixed order, and each is either a block, a pass, or a fact written down.

1. **Does the branch have commits beyond the base?** If not, block. This uses a count of commits, not a guess. The check hit a real snag: on 2026-09-26 a task was blocked as "no commits beyond main" with seven work commits sitting on the remote, because a stale local ref pointed at the base. I restored the row by hand once I saw the remote branch.
2. **Do the declared outputs exist in the diff?** A directive can name the files it must produce. If one is missing, block.
3. **Is this a mass deletion?** A branch that deletes most of the tree would wipe the repository on merge. The comment in the code cites the reason: my game studio's PR #10 on 2026-09-22, the night a test deleted my repository. That cost me 3,823 files for about eight minutes. The check exists so it cannot reach a model, or me, as a surprise.
4. **Is the test suite honest?** Look at the diff for deleted tests, skip markers, removed assertions and commands that mask failure. This is what lets "0 failing" mean something.
5. **Does the check command pass?** The directive names one, or the install has a per-repo default. A non-zero exit blocks. So does a green exit with a non-zero skipped count, because my floor is zero skipped.
6. **Did the branch stay in scope?** If the directive declares a list of file patterns, every changed file must match one.
7. **Do the tests that the completion criteria name actually exist?** A report cannot claim a criterion is done against a test that was never written.

There is also a timeout rule. A suite that runs longer than the limit is reported as "unknown", never as a failure. A nine-to-twelve-minute suite once hit an old 900-second ceiling and sat Blocked, and the key that marked it handled meant it was never re-checked. Timing out proves nothing about whether a change is wrong.

## What deterministic does not mean right

Deterministic code has its own bugs, and mine failed in a way that taught me something.

On 2026-09-28 and again on 2026-09-29 a task was bounced from Review to Blocked by the pre-check, with 17 failures in one test file on the second record. The branch's head was already verified green upstream. The pre-check had run the suite on the branch's stale base, not on the merged tree, so reds that existed on main, and failures from the machine's environment, were charged to the branch. When the branch was merged with main and the file was rerun, it passed: 39 of 39.

I wrote the fix as a directive: make the check run against the merged tree, or compare failures to a control run on main. Keep the honest-red behavior, so a failure the branch introduces still bounces. It landed on 2026-09-30, and the logic moved to its own module with 33 tests added a few days later.

The lesson was that a deterministic check must also be right about what it is measuring. A wrong block from code feels authoritative, and it takes a human to see that. The overseer that refused to flip the row a third time, after two identical bounces, was behaving correctly.

## Why not just ask the model

I have two answers, and one is not about money.

**Cost and speed.** The pre-check costs a test run and a few git commands. It needs no model call at all. A model review of a branch that has no commits, or deletes the repo, is spend with no information in it.

**Trust.** A model reads a diff and sounds confident. A model can be wrong the way a person is wrong, in fluent prose. A check that says "no commits beyond main" or "check shows 2 skipped" is wrong only when its code is wrong, and I can read the code. I want my reviewer to start from facts it cannot argue with.

I have also been measuring whether a small model can review code at all. The scorecard in my agent repo says INCONCLUSIVE, with fewer than ten graded trials, so I make no accuracy claim here.

## How to start

You do not need my 560 lines. Begin with three checks:

1. Count commits beyond the base. Zero means stop.
2. Count deletions. If a branch removes more than a set share of the tree, stop.
3. Run the suite and read the **skipped** number as well as the exit code.

Add the rest when something bites. Mine arrived one incident at a time. Each gets a sentence in the code about the day it happened, so the next person knows why the rule exists.

<!-- fact-checked 2026-10-08: 17 claims confirmed, 2 corrected, 1 removed; remaining notes: none -->
