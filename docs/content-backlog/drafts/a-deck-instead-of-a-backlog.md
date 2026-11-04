---
title: "I replaced my project backlog with a deck of cards"
excerpt: "A backlog made every unfinished idea feel like a debt. A deck of project cards, built on reusable primitives with a reroll rule, made it feel like a game again."
tags: [productivity, sideprojects, buildinpublic, gamedev, motivation]
categories: [Build in public]
keyword: side project idea list
lane: dev
status: draft
source: Primitive project deck doc and deck app (Nov 3-4 2026); Robert's rules in his own words
---

For years my side projects lived in a backlog. Every idea I didn't finish stayed on the list, and the list only grew. Opening it felt like opening a bill.

This week I replaced it with a deck of cards.

## The problem with a backlog

A backlog assumes everything on it will eventually be done. For a solo builder with a day job and a family, that's never true, so the list turns into a record of things I didn't do. It also hides the thing I actually care about: the reusable pieces I get better at every time I build something.

I'd already started thinking of each project as a disposable shell, with the real build being the primitives underneath: a proof-check runner, a merge gate, an MCP server pattern, a dated rules table, a logging library I already put on PyPI. A finished game is nice. A primitive I can reuse in the next five projects is the actual progress.

## How the deck works

There are 29 primitives, each with a short code, grouped by kind. There are 32 project cards. Fifteen are sized for a weeknight evening and seventeen for a weekend morning. Each card names the primitives it uses, the one thing it adds, and who it's for. A few real ones:

- "Request-id middleware for FastAPI." One evening. Adds a middleware module.
- "Merge gate as a pre-merge check on any repo." One weekend. Adds a GitHub check-run output.
- "Time-zone tagging by area code." One evening. Adds an area-code to time-zone table.

The rules are mine, and they're short:

1. **Every project reuses at least one primitive and adds or improves one.** That's what makes a two-hour build count.
2. **I don't have to build every day.** Some weeks I won't draw at all.
3. **I can reroll any card,** as long as the old idea goes back into the pool.

The third rule is the one that changed how it feels. Rerolling isn't quitting. The idea isn't gone; it's back in the deck, and I might draw it again on a night when it fits.

## Where the cards came from

I didn't invent 32 ideas from nothing. They came from places like the classic "build your own X" lists, small-project books, coding challenge newsletters, game jams like the 20 Games Challenge, and the growing list of MCP servers people have published. Each source idea got rewritten as a card that uses my primitives, so every card connects to something I've already built.

## From a document to a toy

The deck started as a document with a table. Within a day I wanted to play with it, so it became a tiny web app: draw a card, see the hand, mark it done or put it back. It remembers what I've drawn. It took less time to build than I've spent reorganizing backlogs in the past.

## Why this fits me

I've written before that I lose interest the moment an engine works. The deck works with that instead of against it. A card is small enough to finish before the interest fades, and the primitive it improves carries forward into the next card, so the momentum lives in the pieces rather than in any one project.

I also thought about putting fixed build slots on my calendar, three a week. I decided against it for now. A calendar turns the deck back into obligations, and that's the feeling I was trying to get rid of.

If your project list feels like debt, try making it a deck. Keep the rule that rerolling returns the idea to the pool. It's a small change in wording that changed how I feel about every idea I haven't built yet.