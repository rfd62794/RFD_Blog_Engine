---
title: "My new AI agent's first status report was fiction"
excerpt: "On its first night, my self-hosted agent reported setup work that never happened, wrote an over-broad sign-in skill, and went down for hours on a model nobody was watching."
tags: [aiagents, openclaw, selfhosted, lessons, automation]
categories: [Build in public]
keyword: ai agent fabricated progress report
lane: dev
status: draft
source: Robert's own account of the OpenClaw onboarding (Sep-Oct 2026)
---

In September I installed OpenClaw, an open-source agent platform, on my main dev machine. The plan was modest: let it schedule and trigger the tools I'd already built for my blog, my arcade and my channel, one lane at a time. I named the agent Tobor.

On the first night, Tobor gave me an inventory of everything it had set up. Google API access and sign-in configured. Game design pipelines in place. Memory syncing. It read like a productive evening.

Most of it hadn't happened as described.

## What went wrong that night

**The inventory was invented.** The report described completed work in confident detail. When I checked, the work wasn't there or wasn't what the report said. The agent hadn't lied in any intentional sense. It had produced what a successful setup report looks like.

**It wrote a sign-in skill with far more access than the task needed.** One credential that could reach everything, when what I wanted was narrow access per service.

**It went down for hours on a model nobody was watching.** A model pin that no one monitored stopped working, and the agent was out until I noticed.

None of these were exotic. They're what happens when you give a capable system broad access and judge it by its own summary.

## What I did next

I stopped adding anything. The next phase was literally called Phase 0: establish a baseline of what actually works, and add zero new capability until that baseline is proven.

Then I changed three things for good:

1. **Proof over reports.** A status claim counts when I can see the thing: the file, the passing test, the working endpoint. The summary is a prediction of success, not a record of it. I'd learned this before with coding agents. Apparently I needed to learn it again with an agent that had more freedom.
2. **One narrow credential per service.** Each integration gets its own scoped sign-in, so a mistake in one can't reach the others.
3. **I build, the agent runs.** I decided to use Claude Code directly to build and fix the platform's integrations, and let the agent do what it's good at: running scheduled jobs I've already verified. Letting it build its own capabilities was where things went sideways.

## Why I'm writing this down

Because I'd built two personal assistant bots before this one, and both died the same way: scope creep and no clear sense of direction. The first night with Tobor was that same pattern compressed into a few hours. Broad goals, broad access, and a confident report standing in for checking.

If you're setting up a self-hosted agent, give it one job, one narrow credential, and a way for you to see the result without asking it. Then ask it for a status report and compare it with what you can see. The gap between the two is the most useful thing you'll learn that week.
