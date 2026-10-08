---
title: "How long does my game take to finish? A headless AI-vs-AI soak test"
excerpt: "I made every faction in my strategy game an AI and ran 12 full campaigns in seconds. Ten ran to the calendar cap, two ended early, and none broke a rule."
tags: [game-dev, simulation, testing, game-balance, typescript]
categories: [How-to]
keyword: game balance simulation soak test
status: draft
---

I wanted to know how long my strategy game, Planet of Greed, takes to finish. I did not want to play it twelve times to find out. So I let the computer play it: every faction run by the AI, no human, no screen, twelve full campaigns with fixed seeds.

This is how to build that kind of soak test, and what mine found.

## What a soak test is

A soak test runs the real game logic for a long time with no one watching, and checks that it never breaks. It does not tell you whether the game is fun. It tells you three things: it always ends, it never reaches an impossible state, and how long a run takes in game time.

## Step 1: make the engine callable without the screen

This was the real prerequisite. My turn logic lived inside the main app component, with the yearly logic duplicated in two places. A soak test cannot run code that is welded to the user interface.

So the first job was an extraction. Over three stages the random-number context, campaign state, the AI's weekly orders, combat and the daily turn step each moved into their own module. One of those commits added a test suite of 38 tests for the turn engine alone. Only after that could a headless runner exist.

The design note called the order out: extraction goes first, because the soak test needs injectable randomness.

## Step 2: route all randomness and time through one seed

The runner builds one context from a seed. All randomness and clock inputs come from it. The same seed gives the same campaign every time, and the test proves it by running seed 1 twice and comparing the final game state as text.

That determinism is what makes the numbers worth anything. A failing seed can be replayed exactly.

## Step 3: write the driver

The driver is 175 lines. It creates a campaign, lets the AI plan the first week, then loops: advance one day, resolve any combats, and plan again when a new week begins. Where a human would confirm their orders, the AI does it.

It stops when the campaign is over or a step bound of 1,100 days is hit, so a bug cannot hang the test. The result records how it ended, how many days and weeks passed, how many combats were fought, and how many map cells each faction owned at the end.

## Step 4: check rules every day

After each day, the driver checks invariants, and a violation records the day and the broken rule. It never silently repairs.

- No number anywhere in cells, corporations or transits is infinite or not-a-number.
- No treasury is below zero.
- No unit count, fortification or transit timer is negative.
- Public opinion stays between 0 and 100.
- Every cell owner is a real corporation, and every transit points at real cells.

This is what turns a simulation into a test. A person cannot watch every day of twelve campaigns, but a rule can.

## Step 5: run it for 12 seeds and print the number

The test runs 12 campaigns, one per seed and starting culture, and prints one line each, plus a summary. It asserts only soundness: every run finishes inside the bound, with no violations, and different seeds produce different outcomes, so the random generator is not stuck.

It deliberately does not assert on a target length. The test prints weeks; deciding what length is right is a design call.

## What it found

From the implementation log of the run:

- Weeks to finish: minimum 40, median 144, maximum 144.
- Ten of 12 runs ended at the year cap. Two ended because the player's house was eliminated.
- Zero rule violations. Zero runs hit the step bound.
- The surrounding test suite passed: 14 files, 215 tests, and the type check was clean.

Two things stand out.

**The calendar was wrong in my notes.** My design note said a campaign is 156 weeks. The engine's calendar is 7 days a week, 4 weeks a month, 12 months a year, ending when the date reaches year 4. That is 3 × 12 × 4 = 144 weeks, or 1,008 days. The soak test measured the real number and the note was off. The directive that built it said to report what is measured, and not to trust the note.

**Most runs end because time runs out.** Ten of 12 ended at the cap. In those games, the AIs did not finish the conflict; the calendar did. That tells me the campaign length is set by the cap, not by play. The two early endings are the interesting runs, because the AIs finished the player off before the clock did. [VERIFY: that the 40-week run is one of the two elimination endings; the log gives the minimum but not which seed.]

## What it cannot tell you

Weeks are not minutes. A bot advances a day instantly. How long a human spends per week is still unmeasured, and the directive says so in so many words: the test measures weeks, so do not claim minutes. I need a real playthrough to turn weeks into a time, and to see whether 144 weeks fits the 5 to 15 minute target I wrote down.

It also says nothing about fun. A campaign that always runs to the cap could mean the AIs are passive. The design note lists that as the trigger for adding AI aggression, but only if measured.

## What I have not checked

The numbers above come from the implementation log, not from a run I did for this post. [VERIFY: rerun `test_planetofgreed_soak.ts` and compare the SOAK lines.] I have no per-seed breakdown of which cultures ended early. [VERIFY: the 12 per-run lines.]
