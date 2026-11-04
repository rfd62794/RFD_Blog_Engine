---
title: "At 160,000 lines, my agent harness became the project"
excerpt: "I built a harness that let AI coding agents propel their own work. It worked, and then most of its work was on itself. Why I'm retiring it and keeping the parts."
tags: [aiagents, claudecode, devin, buildinpublic, softwarearchitecture]
categories: [Build in public]
keyword: ai agent harness lessons
lane: dev
status: draft
source: AgentFlow history doc and lessons note (Oct 18), AgentFlow export scrub report (Nov 4), Robert's own words Nov 2026
---

From late September to late October I ran a system I called AgentFlow. It coordinated Claude Code and Devin across my machines: it queued work as written directives, handed them to agents, checked the results against a test floor, and let only me mark anything Done or merged. It ran overnight. It recovered from its own failures. By the numbers it was the most productive thing I've ever built.

I'm retiring it anyway, and I think the reason is the most useful thing I learned all year.

## What it did well

The core loop was simple to say and hard to get right. A directive described one change and what proof would count as finished. An agent picked it up, did the work on a branch, and opened a pull request. A checker ran the tests and compared the result to the certified floor. Anything that didn't hold up went back with a reason.

In about six weeks that loop merged roughly 900 pull requests. The repo ended up with over 10,000 test functions across 13 packages, installed on five machines. It had budget gates so an overnight run couldn't spend without limit, and evaluation suites to see whether a change to a prompt made reviews better or worse.

The part I'm proudest of is what it called self-propel and resolve: it could find its own next piece of work, and when a run died it could figure out why and queue the fix. That is what let it run while I slept.

## What went wrong

On October 18 I wrote a lessons note. Its first line was:

> At ~160k lines the tool became the project.

The numbers were blunt once I looked. About 70% of the code was the loop package, the machinery that ran agents. More than half of all commits were queue bookkeeping: the system recording its own state. Hundreds of directive titles started with the harness's own name. The work had turned inward.

I had a cap on self-work. It didn't hold, because it only counted the directives the system generated, and the system was very good at finding reasons to improve itself. The line I put in the playbook afterwards:

> A system that can improve itself will, at the expense of the product.

On October 10 I'd already called a "diet, not a feature" freeze. By October 20 I paused it. The last merges were October 26 and 27.

## Why retiring it is the right call

None of this means it failed. It did what I built it to do. The trouble was that "run my agents well" had quietly replaced "build the things I actually wanted to build" as the goal, and a system that is excellent at its goal will chase the wrong one at full speed.

I've seen the same pattern in myself before. I wrote about losing interest the moment an engine works. This time the engine didn't lose interest. It just kept working on itself.

## What I'm keeping

AgentFlow is going to be broken into pieces that can be installed on any repo, instead of one system that every repo has to live inside. The pieces worth keeping are the ones that were about the work, not about the harness:

- **Directives with proof built in.** Every task says what evidence finishes it.
- **The test floor.** A number that can only go up, checked by something other than the agent that did the work.
- **Human-only Done and merge.** The agent proposes; I decide.
- **Self-propel and resolve.** Finding the next task and diagnosing dead runs, scoped to a product repo instead of to itself.
- **Budget gates.** Hard limits written in code, not in a prompt.

The direction I'm taking from here is to train the harness, not the model. A fine-tuned model is too expensive for one person. Better directive templates, better checks and better examples of accepted and rejected work cost almost nothing and work with whatever model is cheapest this month.

## If you're building one

Put a hard number on how much of the system's work can be about the system, count it from the commits rather than from the queue, and look at it weekly. I didn't, and it took me six weeks and 160,000 lines to notice.
