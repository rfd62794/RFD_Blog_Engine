---
title: "The same wrong fact showed up twice in one day. Now every claim in my docs carries a date."
excerpt: "An agent copied a stale 'not done yet' claim from one doc into another, twice. My fix: status claims carry the date they were last checked, and the status board shows its age."
tags: [documentation, aiagents, buildinpublic, process, gamedev]
categories: [Build in public]
keyword: keeping documentation up to date with ai agents
lane: dev
status: draft
source: rfd62794/RFDGameStudio docs/adr/ADR-015 and ADR-016 (Aug 15 2026)
---

On August 15 my game studio's docs said a shared art module was "built but not yet consumed" by two of my games. Both games had been using it for weeks.

The claim was caught and corrected in one document that morning. By the afternoon, the same wrong sentence had appeared again in another. That same day, a different doc pointed at an outdated version of my design document as the current one.

Nobody lied. Each wrong claim came from the same habit: an agent, or I, citing what an earlier document said instead of checking the repo.

## Why this happens more with agents

When I work with coding agents, documents get written fast and read back constantly. An agent starts a session, reads the status file, and treats it as truth. If the status file is wrong, the agent builds on the error, and the next document it writes repeats it with more confidence.

A "not done yet" claim is the worst kind, because it decays silently. Work gets finished, and nothing updates the sentence that says it isn't.

## Fix 1: every claim says when it was checked

The rule I wrote down that day: a status claim carries the date it was last verified against the live repo, and "not yet done" claims especially. Something like "artGen: consumed by Shoal and SlimeWorld (checked Aug 15 by reading the imports)".

That does two things. A reader can tell a fresh claim from an old one. And an agent copying the claim forward copies its age too, which makes it obviously suspect three weeks later.

## Fix 2: the status board shows its age in public

My studio's status rollup used to be a hand-written markdown file. To see it you had to know it existed. To notice it was stale you had to remember to check, which never happens reliably.

I moved it onto the arcade site as a page, generated from data, with a last-updated field on each entry. Now staleness is visible to anyone who looks, including me. The principle in the decision record: make it visible, don't make someone remember to ask.

## Fix 3: check the repo, not the conversation

The deeper rule is about where facts come from. Both wrong claims were inferred from conversation history and earlier documents. Both were disproved in under a minute by opening the actual files. So when a claim matters, the source is the code, the test output or the import line, not what someone said about it.

## What it costs

A little friction. Writing "(checked Aug 15)" feels fussy. Regenerating a page instead of editing a table took some setup. But the alternative was a documentation set that slowly turns into fiction, read every morning by agents that believe every word.

If you run agents against your repos, look at your status file today and ask how you'd know if half of it were wrong.
