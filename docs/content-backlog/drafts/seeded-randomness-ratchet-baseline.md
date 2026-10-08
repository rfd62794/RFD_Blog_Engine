---
title: "A baseline file that only lets the count go down: guarding seeded randomness"
excerpt: "How a 19-line JSON file and three tests stop new Math.random calls from creeping into my game simulations, without fixing the old ones first."
tags: [testing, determinism, game-dev, typescript, code-quality]
categories: [How-to]
keyword: deterministic simulation seeded random testing
status: reviewed
---

A simulation is only useful for balance work if the same seed gives the same game. Every bare `Math.random()` inside the simulation code breaks that. I had many, and did not want to fix them all in one go.

So I froze them. I recorded how many each file had, and wrote a test that fails if any count goes up. This is called a ratchet: the number can only move one way. Here is how to build one.

## The problem in numbers

My studio's engine review counted bare uses of `Math.random`, `Date.now` and `performance.now` across the TypeScript code, against one shared seeded random helper that is 42 lines long. Recounting on current main, the game and engine source has about 155 `Math.random` calls and 137 clock reads. The simulation core, meaning the shared engine folder plus each game's `simulation` folder, held 119 lines containing one of the three at the time of the review.

Determinism was per game and unenforced. Nothing stopped another bare call.

I also had a concrete reason to care. Two tests were flaky because they leaned on `Math.random`. One needed an opponent to win at least once across 10 matches. The other needed at least one hit in 50 attack cycles. The fix was to replace `Math.random` in those tests with a seeded generator, and afterwards both passed 10 times in a row. I reran them 10 times on current main and they still do.

## Why a ratchet and not a cleanup

The honest options were:

1. Fix every use now. Large, risky, and it touches a dozen games.
2. Ban new uses with a lint rule. Does nothing about the existing ones, and the rule would fail on day one.
3. Freeze the current count and only allow it to fall.

Option 3 is cheap and works immediately. New bare randomness fails the test today, and each old one removed tightens the lock.

## Step 1: the baseline file

The baseline is a JSON map from file path to the number of allowed uses, plus a note at the top saying what it is: counts may only shrink; lower a number when you remove a use.

Mine lists 16 files that add up to 128 uses. The biggest is one space game's simulation engine with 40. A particle sandbox's grid file has 15, and a gladiator game's economy file has 11.

## Step 2: the counting test

The test walks the shared engine folder and every game's `simulation` folder. It skips sound-effect and component folders, since cosmetic randomness is allowed. For each TypeScript file it strips comments first, so a note that mentions the function does not count, then counts matches of `Math.random`, `Date.now` and `performance.now`.

It uses only Node's built-in file tools, so there is no new dependency.

## Step 3: three checks

The test file has three small tests.

**No new violations.** Any file with a count above zero must be in the baseline, and its count must not exceed the allowance. A new file or a higher count fails, and the message tells you the fix: use the seeded generator, or pass the clock in.

**Baseline can only shrink.** This is the ratchet. If a file's real count is lower than its baseline, the test fails and says to lower the number in the file. Without this check, you could remove three uses, leave the allowance at five, and later add three back without anyone noticing. Failing on improvement forces you to bank the gain.

**Baseline is real.** No entry may have a count of zero or point at a missing file. Dead entries make a ratchet meaningless, because they give someone free headroom.

## A number that turned out wrong

The directive that asked for the guard said there were 119 uses in 17 files. The baseline that shipped lists 128 uses in 16 files. The directive was written from a `grep -c`; that command counts lines containing a match, and the test counts every match. Nine lines hold two calls each, which counts as one in grep and two in the test: 119 plus 9 is 128. The file that dropped out, `mbbTick.ts` in the mutant ball game, had its single match inside a comment, which the test strips. The implementation log gives the same explanation.

I think this is a good argument for building the test and not trusting the note. The test counts what it will enforce, so whatever the real number is, that is the number locked in.

## What I have not done

The baseline has not gone down. The file has had one commit, the one that created it, so every count in it is the original. The guard works, but I have not yet used it to remove anything.

The next step in my engine plan is replay: record a seed plus the inputs and replay it to the same result. Its exit check includes the baseline count being lower than when I started. Until the number drops, the guard is a fence, not a cleanup.

## Reuse it for any count

The pattern fits anything you can count and want to shrink: skipped tests, TODO comments, `any` types.

1. Measure the count per file with the exact method the test will use.
2. Write it to a baseline file with a note.
3. Fail on any increase.
4. Fail on any decrease that is not recorded, so improvements stick.
5. Fail on dead entries.

## What I have not checked

I could not reproduce the review's earlier totals of about 199 and 236, so I replaced them with my own recount. The 119 and 128 figures I did reproduce. I also ran the guard against a deliberate violation: a throwaway file with one bare `Math.random` in a simulation folder failed the first check, naming the file and the fix. I deleted it afterwards.

<!-- fact-checked 2026-10-08: 20 claims confirmed, 3 corrected, 2 removed; remaining notes: review totals of 199 and 236 not reproducible and removed in favour of a recount (about 155 and 137 in ts/src); 119 in the roadmap counts all three patterns, not just Math.random -->
