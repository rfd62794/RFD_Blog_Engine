---
title: "A ten-point nudge swung my game from 52.8% to 14.8%"
excerpt: "I lowered two stats by ten points and a fair 52.8% win rate collapsed to 14.8%. A bit further and it hit 1.2%. So I built a sweep tool that tunes game numbers from evidence, not feel."
tags: [game-balance, game-dev, simulation, testing, tooling]
categories: [How-to]
keyword: game balance tuning sweep
status: reviewed
---

I lowered two numbers in my creature-battler by ten points each, and the game went from fair to nearly hopeless. The win rate for a bot player fell from 52.8% to 14.8%. Push the same stats down a little further and it hits 1.2%. That is not a tuning change. That is a different game.

That is why I built a small tool that sweeps a number across a range and shows the result in seconds.

## The measurement

The game is Chimera Wilds. Its baseline player has power 90 and endurance 85. I ran the same 1,000 seeded games at three settings and recorded how often the bot wins:

| Power / endurance | Win rate |
|---|---:|
| 90 / 85 (baseline) | 52.8% |
| 80 / 75 | 14.8% |
| 70 / 70 | 1.2% |

One step of ten points on both stats moved the win rate by about 38 points. The second setting, 20 points off power and 15 off endurance, took away nearly all the rest. Dropping only one of the two stats by ten gave 34.4%. The first measurement was a scratch probe I reverted, recorded in the design spec as the evidence that tuning by feel does not work on this game.

Tuning by feel means editing a number, rebuilding, playing a few rounds, and guessing. On a curve this steep you could play for an hour and never notice you had slid off the fair zone.

## What was wrong with how I tuned before

Each game kept its balance numbers differently:

- Chimera Wilds keeps them in a data file.
- Scrapcrawl keeps them as constants in code, such as 10 maximum health and 2 damage per lost fight.
- Horse racing keeps a bookmaker margin of 1.12 in a data file.

Each had a test that checked a range written once. Chimera's accepted anything from 35% to 65%. Scrapcrawl's unarmed run accepted 20% to 50% and measured 35.0%, and its crafted run accepted 60% to 90% and measured 75.0%. Finding out a number was off meant editing a file, running a test suite, and reading a log line.

## The tool: a sweep

The idea is small. Declare a knob (a number with a name, a range and a one-sentence note about what the player feels when it moves). Declare a target (a band the result should sit in). Then run the game headless many times for each value of the knob and print a table.

The command looks like this:

```
tune-sweep --game <id> --knob <name> --from 1 --to 4 --step 1 --runs 200
```

For each value it runs the simulation for the number of runs you ask for, with seeds 5000 upward so the results are repeatable, then averages each metric. There is a `--check` flag that exits with an error if any target misses at the defaults, and a `--report` flag that writes a short markdown file I can read on my phone.

The code is split on purpose. The logic is pure functions: parse arguments, build the list of values, average the runs, check targets, render a table and a report. The command-line file is 53 lines of glue, and the pure parts carry the tests, 148 lines for the sweep and 43 for the targets.

The commit that added it touched 7 files with 446 lines added.

## Targets as intent

The target is the idea I like most. Instead of each game having a hand-written range buried in a test, the band lives next to the knobs as a stated intent, for example a win rate between 0.20 and 0.50 for the unarmed scenario. One generic test runs every registered game's targets at its defaults. A retune cannot silently leave the intended band, and I can then delete the one-off range tests.

The report states its own limit in its last line: bot strategy, not human play. A bot's win rate is a guard rail, not a verdict. The tool just tells me where the cliffs are first.

## What it costs

Speed is the limit. By the design spec's measurement, Scrapcrawl runs at about 22 milliseconds per game: 400 runs took 8.9 seconds. A four-value sweep at 200 runs for each of two scenarios comes to roughly 35 seconds. That is fine from a terminal, but too slow to update as I drag a slider, so the design has no live simulation in the panel.

I expose only two to six numbers per game, the ones I actually move. A knob I never touch is clutter.

## How the pieces fit

The full design has five small parts, each useful alone: a knob schema, a store with a dev-only override switch, a dev panel, this sweep tool, and the targets with the report. The sweep commit landed with an empty registry of games, and the plan was to add one game at a time. The registry is still empty on main as I write this, with the first two adoptions queued.

## Try it on your own game

You need a way to run your game headless with a seed, a metric you can average (win rate, rounds survived, gold at the end), and the discipline to use the same seeds each time.

1. Pick one number and one metric.
2. Run 200 seeds at five values of the number.
3. Look for the cliff. If the metric swings by tens of points between neighbours, that number needs a finer step, and probably a smaller range.
4. Write down the band you want, then check it in a test.

## What I have not checked

I reran the 1,000-seed probe on the current Chimera Wilds data and got the same three numbers: 52.8%, 14.8% and 1.2%. I have not seen a human play at those settings, and the speed figures come from the design spec, not a fresh timing.

<!-- fact-checked 2026-10-08: 24 claims confirmed, 2 corrected, 0 removed; remaining notes: headline and lede corrected (a ten-point nudge gives 14.8%, 1.2% needs 20/15 points); 22 ms/game and 8.9 s timings are from the spec, not re-timed -->
