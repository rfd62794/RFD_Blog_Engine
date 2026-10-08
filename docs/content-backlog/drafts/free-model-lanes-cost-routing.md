---
title: "Free models first: how I route AI work by cost"
excerpt: "How I route AI coding work by risk and cost: free models for bounded tasks, stronger ones for judgment, and a rule that nothing routes itself."
tags: [ai-agents, model-routing, free-models, cost, automation]
categories: [How-to]
keyword: ai model routing by cost
status: draft
---

I do not want a surprise bill, and I do not want an agent on my strongest model renaming variables. So I split my AI work into lanes and decide the lane by the kind of task, not by how I feel that day.

Here is what the lanes are, how the free one works, and the part I got wrong the first time.

## The lanes

My orchestration tool keeps a table of lanes in `docs/LANES.md`. The code is the source of truth and the page is a readable copy. As of this week there are eight:

| Lane | Who runs it | How it is chosen |
|---|---|---|
| haiku | Claude, small | a `Model` row or a task kind |
| sonnet | Claude, mid | the default |
| opus | Claude, large | only if a row says so |
| fable | Claude, largest | only if a row says so |
| cheap | Devin | a backlog policy entry |
| strong | Devin | fallback when nothing else is named |
| default | Devin | opt in |
| free | Aider on free models | assigned by hand |

The two top Claude lanes are never a default. Someone has to ask for them by name.

## Pick the lane by the kind of step

When a task spawns a helper, the helper takes a lane from the kind of work:

- inventory, verify, mechanical and merge steps go to haiku. These are search sweeps, running a test suite and reporting the tail, edits with an exact spec, and commit messages.
- review, spec and debug steps go to sonnet. A first review of a diff, writing a directive from settled requirements, finding why a test fails.
- plan has no default. Planning wants an explicit choice of a large model.
- build has no default either. Self-contained build work goes to the Devin lane or the free lane, not to a Claude helper.

There is also a ceiling. Lanes rank haiku, sonnet, opus, fable, and a helper can sit at or below its parent, never above. A helper started under a haiku parent is stamped haiku so the sonnet default cannot slip past. The rule closes the case where a cheap parent quietly spawns expensive children.

## The free lane

The free lane exists so that bounded, well-described tasks cost nothing. It is documented in `docs/free-agent.md`. The short version:

1. I set a task's `Assigned to` row to `aider`. Nothing routes there on its own. There is no fallback from a failed paid run, no automatic assignment, no usage pool.
2. A wrapper runs Aider over a list of free models in order. The first model whose run exits cleanly and leaves commits wins. Each model gets up to 20 minutes. A failure is classified (not found, rate limit, auth, timeout) and the wrapper moves to the next model.
3. The wrapper then re-runs the task's check command itself. It does not take Aider's word for it.
4. On success it pushes the task's branch only, never main, never a force-push, and writes Review. On failure it writes Blocked with the reason, such as `no edit` when Aider exited cleanly but changed nothing.

The model list in the example config is two entries, a Gemini Flash model and a Groq-hosted Qwen model. [VERIFY: the live config on each machine, since the example file may differ.] API keys come from the environment or a secrets file. They are never logged or written into a queue note, and the wrapper redacts anything the child process echoes back.

The honest limit, in the doc itself: free models are weaker. Plan for small, well-scoped tasks.

## What I measure, and what I do not know yet

The open question is whether a free model's draft is as good as a stronger one's. I wrote a task to build a blind-grading harness: a reader sees a free draft next to a reference and says which they would accept. The goal is one number before any free model is allowed to do more than advise. [VERIFY: whether the blind-grade work has produced results; I only read the task and its merge, not an output.]

For the paid lane I added a different guard. A commit on 2026-10-06 (`c69f15ba8`) changed my evaluation allowance so only paid Devin models consume it, with a share setting that defaults to 0.10 of the allowance. Free models do not count against it. The point is that the allowance tracks real spend.

## The thing I got wrong

The brief for an audit of my small router service described fallbacks, pricing and throttling. When the audit ran on 2026-09-23, the code had none of them. The audit's first line says the code is much smaller than the charter implied: one provider per task type, two network entry points, and a request log in SQLite. There was no fallback chain, no pricing and no throttling.

The same thing was hiding in my blog engine. Its draft-generation role tried Groq, then Gemini, then OpenRouter, and the OpenRouter fallback was a paid Claude Haiku model. The "free lane only" rule I thought I had was not true for that one role. I found it while reading the code for a spec, not from any alert. [VERIFY: whether the paid fallback has since been removed.]

That is the lesson I keep re-learning. A note that says "this runs on the free tier" is a claim. The config file and the code are the fact.

## A small starting setup

To copy the idea without my tooling:

- Write down three lanes: free, cheap, strong.
- Give each kind of task a default lane. Mechanical edits and checks go to the cheapest.
- Make the strongest lane opt-in, by name, every time.
- Keep keys in one secrets file and never print them.

## Questions people ask

**Is free good enough for code?** For small, well-scoped changes with a check command, often yes. When it is not, the run says Blocked and I pick a different lane. I have not measured the rate. [VERIFY]

**Why not just use the strongest model everywhere?** Cost and speed, and because a strong model is not needed to run a test suite and read the last lines.

**Does a router service help?** Mine did less than I thought. Put the lane rules in your task format and check them in code.
