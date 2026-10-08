---
title: "Cutting a game down without deleting work: park features behind a flag"
excerpt: "I hid three features in my card-and-court game with a flag, kept their code and tests, and used a simulation to prove every start still wins."
tags: [game-design, feature-flags, scope, testing, typescript]
categories: [Build in public]
keyword: scope cutting game prototype feature flag
status: reviewed
---

My court-intrigue game, Succession, had too many choices on screen. Each turn offered three persuasion methods, a scout action, an indictment panel and a discredit move, against three court figures. The design note put it plainly: the menu is the load.

I did not want to delete anything. Two of those features are the seed of a later mystery mode. So I parked them behind a flag, and let a simulation tell me whether the game still worked. Here is how, with the numbers.

## What got parked

Three systems:

1. **Discredit**, a move that mirrors the rival's slander. The note says it is not really a persuasion method and was the sixth choice on the menu.
2. **The indictment panel**, a 354-line screen for accusing a figure. Each councilor has his own fixed case, so it is three separate mysteries rather than one, and a wrong accusation permanently exposes you to that figure. It is the seed of a later mystery mode, so it is parked, not cut.
3. **Domain ripple friction**, a small favor penalty that hits an opposing councilor when you push one figure hard. The rule for this one was "park only if the measurement says balance holds without it". Decide by harness, not by argument.

The note's rule for all three was: nothing is deleted, parked code stays with its tests, and any item revives by flipping the flag.

## The flag is a tiny module

The whole mechanism is a file of 21 lines. It has a type for the three ids, a record of booleans that all default to false, and four functions: ask if a feature is parked, read all flags, set some, reset to defaults.

Two decisions made it safe.

First, the default is "nothing parked". With no change to the flags, the shipped game behaves exactly as before. The commit that added the flag did not change what players see. Flipping a default is a separate decision, to be made from data.

Second, each gate is a single early return or a single conditional, placed at the point of use:

- The two panels in the audience screen render only if their feature is not parked.
- `deliverIndictmentTo` returns the state untouched when indictment is parked.
- Where domain ripple is looked up, the lookup becomes undefined when parked, so the penalty code below it simply does not run.

The whole change touched 7 files with 249 lines added and 3 removed. Most of that is new tests.

## Proving the code still works while hidden

Hidden code rots. So the parked-feature tests check both states. A parked discredit returns the identical state object; unparked, it changes the state. With domain ripple on, a push on one councilor drops the opposing councilor's favor below 10. With it parked, favor stays at exactly 10.

That second test matters. It shows that the parked path is really off, and that the unparked path still does what it did.

## Proving the game still works

Hiding features can quietly break balance, so I ran an ablation. The balance sim plays 7 strategies across 3 starting origins, 21 deterministic runs. The ablation test imports that sim five times, once per flag setting, and counts how many strategies win from each origin.

The "player wins per origin" results. I reran the ablation test on current main for this post and got the same table:

| Setting | Bastard scion | Disgraced knight | Merchant banker |
|---|---:|---:|---:|
| nothing parked | 1 | 1 | 1 |
| discredit parked | 1 | 1 | 1 |
| indictment parked | 1 | 1 | 1 |
| domain ripple parked | 2 | 1 | 2 |
| all three parked | 2 | 1 | 1 |

The bar was that every origin still wins at least once in every setting. It holds. The test asserts it for each of the five settings, so a future change cannot silently break it.

Two readings are worth saying out loud. Parking indictment changed nothing, because the sim never plays it. The directive says so itself: the lack of a difference is the finding, and it also means the sim does not cover that feature. And the counts are small. One win per origin out of 7 strategies is a thin margin, so "still wins" is a guard rail, not proof the game is fun.

## The session-time estimate, honestly labelled

The same change added a function that estimates how long a run takes. The engine is headless and deterministic, so it cannot measure how long a human takes to read. The function says so in its own comment: these seconds are stated assumptions, not measurements.

The assumptions: 60 seconds of setup, 90 seconds of ending, and 20, 45 or 90 seconds per move depending on how fast the player is. With 8 segments of one move each, that gives 5.2, 8.5 and 14.5 minutes for fast, typical and slow. The test pins those three numbers.

The 5 to 10 minute target is therefore plausible on paper and unmeasured in practice. A stopwatch run replaces the assumptions. I would rather ship a labelled guess than a number that sounds like a measurement.

## When to use this pattern

Use a flag when you want to cut load but might want the feature back. Use plain deletion when you are sure. The cost is a small module and some tests; the benefit is that "cut" stops being a one-way door.

Keep the flag module tiny and the gates at the edges. Test both states. Run the whole system with each flag combination before you decide what the default should be.

## What I have not checked

I have not timed a real playthrough, so the session estimate is still assumptions. All three defaults are still "not parked": the flag file has had one commit, so players currently see no change.

<!-- fact-checked 2026-10-08: 22 claims confirmed, 1 corrected, 0 removed; remaining notes: indictment panel is 354 lines (draft said 329, the design note's older figure); session estimate remains assumption-based by design and is labelled as such -->
