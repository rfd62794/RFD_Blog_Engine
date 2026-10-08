---
title: "A baseline file that only lets the count go down: guarding seeded randomness"
excerpt: "How a 20-line JSON file and three tests stop new Math.random calls from creeping into my game simulations, without fixing the old ones first."
tags: [testing, determinism, game-dev, typescript, code-quality]
categories: [How-to]
keyword: deterministic simulation seeded random testing
status: draft
---

A simulation is only useful for balance work if the same seed gives the same game. Every bare `Math.random()` inside the simulation code breaks that. I had a lot of them, and I did not want to fix them all in one go.

So I froze them. I recorded how many each file had, and wrote a test that fails if any count goes up. This is called a ratchet: the number can only move one way. Here is how to build one.

## The problem in numbers

My studio's design review counted about 199 uses of `Math.random` across the TypeScript code, against one shared seeded random helper that is 42 lines long. Of those, 119 sat in the simulation core: the shared engine folder plus each game's `simulation` folder. About 236 more uses of `Date.now` or `performance.now` read the clock.

Determinism was per game and unenforced. Nothing stopped the next change from adding another bare call.

I also had a concrete reason to care. Two tests were flaky because they leaned on `Math.random`. One needed an opponent to win at least once across 10 matches. The other needed at least one hit in 50 attack cycles. The fix was to seed the random function, and afterwards both passed 10 times in a row.

## Why a ratchet and not a cleanup

The honest options were:

1. Fix every use now. Large, risky, and it touches a dozen games.
2. Ban new uses with a lint rule. Does nothing about the existing ones, and the rule would fail on day one.
3. Freeze the current count and only allow it to fall.

Option 3 is cheap and it works immediately. New bare randomness fails the test today. Old randomness can be removed whenever it is convenient, and each removal tightens the lock.

## Step 1: the baseline file

The baseline is a JSON map from file path to the number of allowed uses, plus a note at the top saying what it is: counts may only shrink; lower a number when you remove a use.

Mine lists 16 files that add up to 128 uses. The biggest is one space game's simulation engine with 40. A particle sandbox's grid file has 15, and a gladiator game's economy file has 11.

## Step 2: the counting test

The test walks the shared engine folder and every game's `simulation` folder. It skips sound-effect and component folders, since cosmetic randomness is allowed. For each TypeScript file it strips comments first, so a note that mentions the function does not count, then counts matches of `Math.random`, `Date.now` and `performance.now`.

It uses only Node's built-in file tools. No new dependency.

## Step 3: three checks

The test file has three small tests.

**No new violations.** Any file with a count above zero must be in the baseline, and its count must not exceed the allowance. A new file or a higher count fails, and the message tells you the fix: use the seeded generator, or pass the clock in.

**Baseline can only shrink.** This is the ratchet. If a file's real count is lower than its baseline, the test fails and says to lower the number in the file. Without this check, you could remove three uses, leave the allowance at five, and later add three back without anyone noticing. Failing on improvement forces you to bank the gain.

**Baseline is real.** No entry may have a count of zero or point at a missing file. Dead entries make a ratchet meaningless, because they give someone free headroom.

## A number that turned out wrong

The directive that asked for the guard said there were 119 uses in 17 files. The baseline that shipped lists 128 uses in 16 files. The directive was written from a `grep -c`; that command counts lines containing a match, and the test counts every match. Two calls on one line count as one in grep and two in the test. The file that dropped out, a one-use file in the mutant ball game, probably had its single use in a comment that the test strips. [VERIFY: that this explains the whole gap.]

I think this is a good argument for building the test and not trusting the note. The test counts what it will enforce, so whatever the real number is, that is the number locked in.

## What I have not done

The baseline has not gone down. The file has had one commit, the one that created it, so every count in it is the original. The guard works, but I have not yet used it to remove anything. [VERIFY: git history of the baseline on current main.]

The next step in my engine plan is to add replay: record a seed plus the inputs, and replay it to the same result. That plan names its own exit check, which includes the baseline count being lower than when I started. Until the number drops, the guard is a fence, not a cleanup.

## Reuse it for any count

The pattern fits anything you can count and want to shrink: skipped tests, TODO comments, `any` types.

1. Measure the count per file with the exact method the test will use.
2. Write it to a baseline file with a note.
3. Fail on any increase.
4. Fail on any decrease that is not recorded, so improvements stick.
5. Fail on dead entries.

## What I have not checked

The 199 and 236 totals come from the roadmap document and I did not recount them. [VERIFY: recount on current main.] The scope of the 119 number is as defined there. I also have not run the guard against a deliberate violation for this post. [VERIFY: add a bare call and confirm the failure message.]
