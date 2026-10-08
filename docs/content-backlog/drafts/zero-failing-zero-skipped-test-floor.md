---
title: "Zero failing, zero skipped: a test floor a solo developer can enforce"
excerpt: "My rule is zero failing and zero skipped tests. A skip counts as a failure. Here is how I enforce it, where it leaks, and what it costs."
tags: [testing, quality, ai-agents, solo-developer, python, process]
categories: [Build in public]
keyword: zero skipped tests policy
status: reviewed
---

On 2026-09-22 I wrote one rule at the top of my priorities file and told every agent to follow it:

> 0 failing and 0 skipped tests in every checked repo's suite. A failing or skipped test is a defect, never a state to leave. Nothing may skip a test to get green; a test whose behaviour is gone is deleted with the reason in the report.

I call it the floor. This post is about why skips are in it, how a machine enforces it, and the places where I have not met it.

## Why a skip counts as a failure

A red test tells you something is broken. A skipped test tells you nothing, and it looks the same as a pass in a summary line that says "all passed".

I have AI agents writing most of the code. An agent under pressure to get a suite green has two cheap options: fix the code, or mark the awkward test as skipped. The second is faster and the result looks identical in a pull request. The backlog policy I wrote that same day says it directly: a skipped test is "a hidden failure". The directive that fixes one must make it run and pass, or delete it with a reason when the behaviour is gone. "Never re-skip."

So the floor is not about perfection. It is about removing the one exit that hides a problem.

## Three places the floor is written down

A rule only I remember is not a rule, so it is in three places.

1. **The priorities file.** Fix work comes first in my ordering: broken imports, failing tests, skipped tests. Everything else, such as new tests, direction documents and roadmap steps, waits behind it.
2. **The backlog policy.** The generator that proposes work has a `floor` setting of 0 failed and 0 skipped, and it has a kind of task called `skipped-test` for exactly this. The failing-test version of that directive forbids deleting or skipping the test. The only way to satisfy it is to fix the code or prove the test wrong in the report.
3. **The review pre-check.** This is the one that bites. A branch in Review is run through a check before any model reads it. The priorities file says the pre-check blocks a branch whose check shows a failure or a skip. The code does it in a few lines: a green exit code with a non-zero skipped count is treated as a block, with the message that "the floor is 0 skipped".

## The cheat the floor invites

Once a skip is not allowed, the next cheap move is to make the number disappear without fixing anything. Delete the failing test. Weaken its assertions. Append `|| true` to the test command.

So the pre-check also runs a test-integrity pass over the diff. Its header comment describes the scenario: a branch can "satisfy the 0 failing / 0 skipped floor while cheating". It looks for deleted test files, removed test definitions, skip markers for pytest and for JavaScript test runners, commands that mask failure, and a net drop of at least three assertion lines in a test file. The assertion rule is labelled a heuristic: "review by hand".

A directive can opt out for one case, with an `allow-test-removal` marker, when the behaviour a test covered is genuinely gone. The finding is still reported as a fact. It just stops being a block.

## Where I do not meet it

This is the section most floor posts leave out.

- **A documented exception.** My memory server's agent notes say the suite is at "126 passed / 1 known-fail" as of 2026-09-24. The failing test compares a recorded commit hash against the current head, so it can only pass after a verification pass records the hash with no further edits. I documented it instead of hiding it, and I told agents not to report the suite as broken because of it. A later task on 2026-10-03 still listed the same single failure as known, and I found no change to that test file since. That is still a failure under the floor. It is honest, but it is a failure.
- **Skips I have not cleared.** On 2026-10-04 a run on my game studio reported its pre-push hook's TypeScript gate as "2148 passed | 25 skipped". That is 25 skips in a suite that is supposed to have none. I have not counted the studio's current skips, so treat 25 as a floor I was missing on that day, not a measurement of today.
- **A condition that skips itself.** A deploy-readiness test checked that a branch was up to date with origin/main. Agent branches read "behind" the moment main moves, so the pre-push hook failed green branches. Three pushes were lost on 2026-09-24. I changed the test so the check only runs on main. That is a legitimate scope fix, not a skip, but it is also a place where I was tempted by the wrong one.

I put these here because the floor is only useful if the exceptions are visible. A floor with secret holes is a slogan.

## What it costs

It is not free. An agent whose job is "add a test" can end up in a loop with a flaky test it is not allowed to skip. The pre-check takes time to run the suite.

But the cost is smaller than the alternative. When the floor is zero and one thing is red, there is no argument about whether red is acceptable today.

## Doing this on your own

You do not need my tooling.

1. Write the rule in one sentence and count a skip as a failure.
2. Make your CI or pre-merge check read the **skipped** number as well as the exit code. Most runners exit 0 with skips.
3. Diff the test files, not just the suite. A green suite after a deleted test is the cheat.
4. Keep a short, public list of known exceptions with a date, so the floor stays honest.
5. Give "fix the skipped test" its own kind of task, so it competes for attention with new features.

The floor is a promise to my future self that a green result means what it says.

<!-- fact-checked 2026-10-08: 14 claims confirmed, 2 corrected, 1 removed; remaining notes: studio current skip count not measured; memory-server known-fail still listed at 2026-10-03 -->
