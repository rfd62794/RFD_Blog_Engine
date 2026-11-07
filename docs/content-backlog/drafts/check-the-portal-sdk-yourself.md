---
title: "I was wrong about Y8's game SDK. Check a portal's dashboard before you plan around it."
excerpt: "My publishing plan called Y8 a low-friction portal with an optional SDK. Its developer dashboard showed a full SDK with auth, five ad-break types, achievements and a QA review."
tags: [gamedev, html5games, y8, publishing, indiedev]
categories: [Build in public]
keyword: y8 sdk html5 game publishing
lane: dev
status: draft
source: rfd62794/RFDGameStudio docs/RFDGameStudio_MultiPortalPublishing.md v0.2 (Aug 2026)
---

In August I wrote a plan for publishing my browser games beyond itch.io: Poki, CrazyGames, Y8 and a few others. In the first version I put Y8 near itch.io, as an open-upload portal where integrating their SDK was optional.

The same week, I opened Y8's actual developer dashboard. I was wrong, and the corrected version of the plan says so in its first lines rather than quietly fixing the table.

## What Y8 actually requires

From the developer dashboard itself, not a search result:

- **A real SDK**, loaded from their CDN and initialized with an app config and an ad config.
- **Auth.** Players can sign in with a Y8 account, and the game gets a callback.
- **Ad breaks with five types:** reward, next, start, pause and browse. You call them at natural breaks in play.
- **Native achievements**, self-service: title, description, an icon of at least 256 by 256 pixels, a secret flag and an Easy, Medium or Hard difficulty. Y8 shows them on its own game page, not inside your game.
- **Native leaderboards**, with a sort direction and a score limit to block obvious cheating.
- **A QA review** after each build upload, which checks the SDK and ad integration specifically.

Local development is easy: `localhost` and `127.0.0.1` work on any port with no setup. Opening the game from `file://` does not, because the SDK's network calls are blocked there.

## The design problem it exposed

My plan had a single `portalAdapter` interface with a `requestAdBreak()` call, designed against Poki and CrazyGames, which mostly distinguish a normal break from a rewarded one. Y8's five types don't map onto that one-to-one. The adapter needs real logic that knows the context (game start, returning from a menu, a reward moment) and picks the right type. A pass-through won't do.

That's exactly the kind of thing you want to find out on paper, before writing the adapter.

## The upside I'd have missed

Y8's built-in achievements are a much cheaper path to having some achievements than the custom, account-backed system I'd scoped. They only live on Y8, so they don't replace that plan. But for games shipping there, they're free.

## The lesson

Search results and other people's summaries describe a platform as it was, or as someone remembered it. A developer dashboard describes it as it is today. Before you plan an integration, log in and read the source. When you find out you were wrong, write the correction where the mistake was, so nobody builds on the old version.

[ROBERT: confirm whether the Shoal entry on Y8 is live or still in review before publishing.]
