---
title: "Don't extract shared code until a second project uses it"
excerpt: "My game studio shares an art module between games because a second game needed it, not because I planned a library. The rule that came out of it: check shared code first, promote on second use."
tags: [architecture, gamedev, typescript, refactoring, buildinpublic]
categories: [Build in public]
keyword: when to extract shared code
lane: dev
status: draft
source: rfd62794/RFDGameStudio docs/adr/ADR-013 and ADR-014 (Aug 2026)
---

I've built shared libraries before anything used them, and they always came out wrong. The library guessed at needs that never arrived and missed the ones that did.

The shared code in my game studio that actually works came about the other way around.

## How the art module happened

One of my TypeScript games, a deckbuilder, needed procedural art: seeded random numbers, polygons, fin shapes, bursts, irregular fragments. I built it inside that game. Later, my reef simulation needed the same kinds of shapes. That was the moment it moved into a shared module, `artGen`, with the reef game as a verified second user and no regressions in either game. A slime game started using its seeded random and polygon helpers too, checked byte for byte by its tests.

Compare that to my earlier plan, where game logic in a shared language would make reuse easy. When I audited it, only 2 of 11 candidate functions were genuinely worth sharing, and both were trivial math. The plan was about reuse. The second user was what produced it.

## The rule I wrote down

In August I made it a standing practice, in both directions:

**Forward:** before writing new game logic, check the shared engine folders for an existing pattern. Use it. Skipping the check because it feels like ceremony is how you end up with three slightly different seeded random functions.

**Backward:** when a game needs something general, and a second game needs it too, promote it to the shared layer as part of that work, not as a separate cleanup project later.

## Why "second use" is the right trigger

- **One user tells you nothing about the interface.** With two, you can see which parts are general and which were specific to the first game.
- **It keeps the shared layer honest.** Everything in it has at least two callers, so nothing there is speculative.
- **It's cheap at the moment it happens.** The code is fresh, the second user is right there, and the tests for both run together.

## The correction I nearly missed

The day I wrote this rule down, I described the reef game's use of the art module as a gap that needed follow-up work. Then I opened the reef game's code. It had been importing and using the module for weeks, with its own config and a caching layer on top. My note was wrong, and it came from memory, not from the files.

That's a good reminder for any rule about shared code: the source of truth is who imports what, today. Check that before you plan the next extraction.
