---
title: "My arcade lists the games that didn't make it"
excerpt: "Four of the 28 entries on my game arcade are origin projects: earlier games that became the current ones. Why I gave them their own status instead of deleting them."
tags: [gamedev, portfolio, buildinpublic, indiedev, design]
categories: [Build in public]
keyword: game portfolio show old projects
lane: dev
status: draft
source: games.rfditservices.com (read Nov 4 2026); rfd62794/RFDGameStudio docs/adr/ADR-023 (Aug 23 2026)
---

My game arcade has 28 entries. Six are featured, twelve are in development, six are prototypes, and four sit in a section called Origins.

The Origins are games that aren't really games anymore. They became other games.

## What's in Origins

- **Slimegarden**, the early breeding sandbox that became SlimeWorld.
- **SlimeBreeder**, a TypeScript take on the same loop, later merged into SlimeWorld.
- **CorpWorld**, the fork that became Planet of Greed.
- **Kingmaker Squads**, where Planet of Greed's culture wheel came from.

## Why not just delete them?

That was the default. When a project gets merged into something newer, you archive the old one and move on.

The problem showed up while I was planning which old demos to port to the arcade. Slimegarden and SlimeBreeder were on the list as ordinary candidates, as if they were two more games. They weren't. They were SlimeWorld's history. Listing them as separate games would have misrepresented what they are, and putting them side by side with SlimeWorld would have looked like three versions of the same thing.

So I asked the question properly: is "origin" a new kind of status, or is it just another label on an external game? The code made the answer clear. The game selector had a flat list of statuses (stable, beta, in development and so on), and an origin project behaves differently from all of them. It isn't trying to become stable. It's finished, in the sense that it already turned into something. It got its own status and its own section.

## Why it's worth the space

**It tells the true story.** Games don't arrive fully formed. SlimeWorld's genetics, missions and planet nodes came from somewhere. A visitor who's curious can see the earlier attempt and play it.

**It's a better portfolio.** A hiring manager or a client learns more from "this rough sandbox became that game" than from a list of finished products. It shows iteration, which is most of the actual work.

**It keeps me honest about merging.** If I can't say which current game an old project became, it probably didn't become one. It's just abandoned, and abandoned projects don't belong in Origins.

## The rule I use now

When an old project is superseded, I ask one question: did its ideas go somewhere? If yes, it's an origin, and it links to the game it became. If no, it gets archived quietly.

Every build on the arcade, origins included, passes the same automated check that it loads and renders before it's listed. Old doesn't mean broken.
