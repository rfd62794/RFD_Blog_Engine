---
title: "Designing a game with AI as the builder and me as the captain"
excerpt: "How I settled a two-mode design for my fish game: what I decided, what the AI checked in the code, and what it left as open questions for me."
tags: [game-design, ai-assisted-development, indie-games, shoal, process]
categories: [Build in public]
keyword: ai assisted game design process
status: reviewed
---

I have a small fish game called Shoal. On 2026-10-05 I made the design calls that turn it from a toy into two games on one page. The interesting part is not the design. It is how the work split between me and the AI, because that split is the process I now use for every game I touch.

## Where the game was

Shoal began as an ecosystem you watch. Fish graze, sharks hunt, algae rises and falls with the grazing. There is no win state. The direction note written the day before says the intent stayed "ecosystem toy" while about 80% of the effort went into performance and rendering, not into giving a player a reason to come back.

The numbers in that note are specific. When the note was written the game was about 2,820 lines of TypeScript, 716 of them in the main app file. A swap from a Lua interpreter to a native TypeScript sim made it 151.7 times faster. That is a lot of engineering for a game with no goal.

The note named the biggest turn-off in one line: with no goal or score, a 30-second visit has no "I did something" receipt.

## What I decided

The settled decisions, as recorded in the direction note:

- One engine, one page, two modes. Same URL, same entry. Evolve is not a separate title.
- **Aquarium** is the original ambient reef, nobody in control. It must always stay playable and shippable. No Evolve work may land if it breaks it.
- **Evolve** starts when you click any fish and become it. Eat, grow, evolve traits. No real death: being eaten sets you back one stage. The mood stays calm.
- Evolution is visual and optional, with branching paths. It never gates the aquarium. You can ignore it and just watch.
- Progress is saved in the browser only. No accounts, nothing to host or support.
- The world keeps running around you. You are one creature among many.

It is also a free game, built by one person with a day job: no promised dates, no multiplayer, no content updates.

None of that came from the AI. These are taste and scope decisions, and they are the part only I can make.

## What the AI did

The agent answered a different question: can the existing code do this, and how much work is it? It read the sim and came back with a verdict of "moderate" plus evidence against a specific commit.

- The sim is already separate from rendering. It has no canvas or DOM references, and a headless test already runs it for 2,000 ticks across 4 scenarios.
- The fish type already has per-fish radius, speed and steering strength. Size and speed traits are data, not new code.
- Movement is force-based, so a player fish needs one hook: a steering force toward the pointer for the controlled fish only.
- Input today only spawns or culls things. Click-to-pick needs new fields.
- There is no camera, and no stage or trait system. Those are new.

It also flagged two risks I would not have spotted by feel. Many places identify fish by checking whether the id starts with "fish", which is fragile, so the new hook should sit beside it. And if camouflage becomes an ability, shark targeting has to read it.

Then it proposed the build as small new modules: a controller, growth stages, traits, mode state, a save file, and a thin UI. That follows a rule I set: new behaviour goes in small new files, not into the 716-line app file or the 737-line sim.

## What it refused to decide

The most useful part of the note is the list it left for me. Seven open questions, including how many evolutionary paths exist and where they split, the exact trait list (it suggested three per category to start), how many growth stages (it suggested four), whether there is sound, and which touch controls to use on a phone.

It also marked what it did not know. Whether touch works on a real device is "UNVERIFIED". The cost of per-fish shapes against the drawing cache is "UNKNOWN". Whether the save format fits an evolved fish is "UNKNOWN".

I trust that more than a confident plan. "I do not know yet" tells me where to spend my own time.

## The roadmap, in playable slices

The milestones are proposed, not agreed. Each is something a stranger could play in a browser for minutes: the existing Aquarium; then "be a fish"; then growth; then traits; then a keepsake with saving. The gate for every step is that the Aquarium still plays and the headless test still passes.

The first Aquarium item has already landed. The next day, a commit added a hint card that asks portrait-phone players to rotate their device, with a test.

## The rule underneath

Here is the working split.

1. I decide what the game is for, and what it must never become.
2. The agent reads the code and tells me the real cost, with line-level evidence and the unknowns marked.
3. The agent drafts. I answer the open questions, or overrule.
4. Builders, human or otherwise, work from small written directives, and every step has a check that can fail.

The mistake I try to avoid is letting the plan outrun the evidence. The feasibility note is dated, tied to a commit, and says "moderate", not "easy".

## What I have not checked

Everything above is about the plan, not a shipped Evolve mode. As of 2026-10-08 nothing in Evolve is built: there is no evolve folder in the game and no Evolve commit. The game has since grown to about 2,900 lines. The 151.7x figure is from the game's changelog, not something I re-ran. I spot-checked four of the feasibility note's line references and they match the code.

<!-- fact-checked 2026-10-08: 19 claims confirmed, 1 corrected, 0 removed; remaining notes: 151.7x speedup taken from CHANGELOG, not re-benchmarked; touch behaviour on a real device and Path2D cache cost remain unknown, as the post says -->
