---
title: "Letting a bot play my browser games before I do"
excerpt: "How I test small browser games without a QA team: a seeded bot, two checks for dead ends and stalls, and a real browser pass for what bots miss."
tags: [game-dev, testing, typescript, playtesting, automation, solo-developer]
categories: [How-to]
keyword: automated playtesting browser game
status: draft
---

I have thirteen small games in one arcade, built mostly by AI agents under my direction. I cannot play all of them every time something changes, and I do not have a QA team. On 2026-10-04 I asked for a framework to playtest them automatically "where possible". This is what came out of that, what it found, and where it stops.

A caution first. The design document is a draft for me, and so far only the first of its layers has landed in code. I will say which.

## What I did by hand

Before any framework, I had three kinds of testing, each built separately:

- **A headless bot per game.** Each game had its own loop. For one narrative game the test runs a real session on seeds 1 to 4 with a 500-step cap. The numbers I measured on the day: seed 1 reached victory in 29 steps, seed 2 in 23, and seeds 3 and 4 hit game over in 20. Another game runs 200 seeded simulations and prints `unarmed=0.350 crafted=0.750`, the win rates with and without crafted gear.
- **A real-browser check by an agent.** One session, 13 games, each loaded at 1280 and at 390 pixels wide, screenshotted, console read, one change made. Useful, but not repeatable on demand and not written down as a script.
- **Five Python end-to-end tests.** One flow each, each starting its own dev server.

The cost I noticed was copying. Every new game copied about 80 lines of loop, and every game asserted its sanity rules slightly differently.

## What the browser pass found that tests missed

Two real bugs showed up only in the browser, and both are the reason I do not trust a bot alone:

- One game showed "Time NaN" and a black canvas. The Lua executor had started returning arrays in July, and the unit tests never drove the game loop through the real shell.
- In another, the NEW RUN button was clipped off screen at 390 pixels wide, even though the page's `scrollWidth` was exactly 390. The control sat at x=571 to 637 inside an ancestor with `overflow: hidden`. A scroll-width check cannot see that.

A bot checks that a game can be played. It does not check that a button is visible.

## Layer 1: a bot that cannot crash the test run

The part that exists is the shared contract, commit `99b15571`, with a follow-up fix in `52d0ec40` after review. A game provides a small adapter, about 60 lines, with these pieces: start with a seed, say what a player can see, list the legal actions, take an action, say whether it is over, report the outcome and some numbers, and give a cheap string describing the state.

Four policies drive it: random, first legal move (what my older bot already did), greedy by a score, and scripted, which follows a golden path and fails if the script runs out before the game ends.

Then two checks that cost almost nothing:

- **Dead end.** No legal action while the game is not over.
- **Stall.** The state string has not changed for 25 actions in a row. [VERIFY: 25 is the design value in the spec; I did not confirm the constant in the merged code.]

Plus three more: no non-finite numbers in the metrics, nothing threw, and the game reaches an end within a step limit, 500 by default.

The runner never throws. Every call into a game or a policy is wrapped, and an exception becomes a recorded violation with the seed and step attached. The review caught a hole in that: a custom extra check could still throw out of the runner, so those calls are wrapped too. A run that fails gives me a seed I can replay.

The report is markdown short enough to read on a phone: outcome counts, run length (minimum, median, 95th percentile, maximum), runs that are three times the median, stalls and dead ends.

What this layer does not do is judge balance. The existing balance tests keep the win-rate ranges. This asks only whether the game can be played to the end.

## Tuning needs the same seeds

The same week I wrote down why balance needs numbers fast. On one creature game, 1,000 seeded runs with a baseline of power 90 and endurance 85 win 52.8% of the time. At 80 and 75 it wins 14.8%. At 70 and 70 it wins 1.2%. A ten-point nudge turns a fair game into a hopeless one, and without tooling the way I would find out is by editing a file, running a ten-second suite and reading a log line. A sweep tool (commit `686d6c6f`, 446 lines added) now runs the same seeded simulation across a set of values and reports.

That depends on the games being deterministic. So I added a guard (`fdc184c2`): a baseline file that counts bare `Math.random`, `Date.now` and `performance.now` calls in the simulation code of each game, and a test that fails if any count goes up. The counts may only shrink. The largest entry in that file today is 40, in one space game's engine. Every other entry is 15 or less.

## What is still a plan

The design has four layers. The bot layer and the contract are in. The other three, a Playwright smoke script across all the demos, a seeded monkey that clicks randomly and keeps the exact action log, and a first-minute check on phone width, are described in the spec but I have not seen them built. [VERIFY: check which layers have merged before publishing.] I also have not yet moved my older per-game bots onto the shared adapter; adopting games are separate tasks.

## If you want to copy this

Start small. Make your game's state restorable from a seed. Write one adapter. Run 200 seeds. Count outcomes. Add the dead-end and stall checks, because they catch softlocks you will not find by playing your own game. Keep a human pass for what it feels like and for whether the button is where a thumb can reach it.

## Questions people ask

**Do I need a framework?** No. The first version is a loop, a random number generator you control, and two assertions.

**Does a bot replace a human playtest?** No. The two bugs above were found only by loading the game in a browser at phone width.

**How many runs?** My simulations use 200 and 1,000 seeds depending on the game. Pick the number that finishes in about ten seconds.
