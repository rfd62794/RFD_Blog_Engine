---
title: "I designed my games to run in three languages. Then I retired the idea."
excerpt: "RFDGameStudio started as one game format running unchanged in Python, TypeScript and Rust through pure Lua. Months later the evidence said otherwise. What I kept."
tags: [gamedev, lua, typescript, architecture, buildinpublic]
categories: [Build in public]
keyword: cross language game logic lua
lane: dev
status: draft
source: rfd62794/RFDGameStudio README and docs/adr/ADR-013 (Aug 2026), ADR-014 (read Nov 4 2026)
---

The pitch for my game studio project fit on one line: one format, three runtimes.

Every game would be three files. A `data.yaml` with entities, constants and lookup tables. A `ui.yaml` with layout intent that doesn't care which renderer draws it. And a `logic.lua` file of pure functions: no I/O, no rendering, no side effects. Python, TypeScript and Rust would each implement a small bridge with three calls (load a game, call a function, read a schema), and the same game files would run in all of them unchanged.

It worked as a contract. The horse racing game's name generator and odds math ran through the Python bridge, and the tests pinned down exactly what any other bridge would have to do.

By August, I'd retired the requirement anyway.

## What the format promised

Two things. Portability: write the rules once, run them on desktop in Python, in the browser in TypeScript, and on a phone in Rust. And reuse: pure Lua functions would be easy to share between games.

Both are good goals. The question was whether either was happening.

## What actually happened

**The Rust ports stalled.** Lua was mandatory for two named cases: my Rust game VoidDrift and another Rust/Python project. When I checked in August, neither port had moved, and neither was a priority. The reason was plain: building games natively in TypeScript was much faster. Several games had gone from idea to playable in the browser that way.

**The reuse was thinner than I thought.** I ran an audit across the Lua games looking for functions that should be shared. Of 11 flagged as possible candidates, 2 were real, and both were trivial math helpers. Lua wasn't enabling meaningful sharing even between games already written in it.

**Real sharing came from somewhere else.** A procedural art module, built for one TypeScript game and then used by a second with no regressions, became the model for what sharing actually looks like here: promote code to a shared module once a second game genuinely needs it.

So I wrote a decision record retiring the Lua requirement. New games are TypeScript-native by default. Lua stays where it's already in use. Nothing was deleted.

## What I kept

The idea underneath survived: separate the rules from everything else. Game logic stays pure, with no rendering and no I/O inside it, so it can be tested headlessly, simulated thousands of times, and balanced from numbers. That's what made bot playtests and soak tests possible later. The language that logic is written in turned out to matter much less than the discipline of keeping it pure.

## The lesson I'd pass on

A portability layer is a bet on a future you haven't built yet. It's worth checking whether that future is arriving. Mine wasn't, and I was paying for it in every new game: an extra language, an extra bridge, an extra place for bugs to hide.

The check that settled it was simple. List the cases the abstraction exists for, and look at whether those cases are still real. If they aren't, keep the principle and drop the machinery.
