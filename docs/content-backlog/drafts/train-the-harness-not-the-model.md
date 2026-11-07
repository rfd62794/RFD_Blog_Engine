---
title: "Train the harness, not the model"
excerpt: "Fine-tuning a model is too expensive for one person. Improving the directives, checks and examples around a model is cheap, and it works with whatever model costs least this month."
tags: [aiagents, llm, promptengineering, buildinpublic, automation]
categories: [Build in public]
keyword: improve ai coding agent without fine tuning
lane: dev
status: draft
source: Robert's own words on AgentFlow direction (Nov 2026); Oct 10 research notes on training the harness
---

Every few weeks I'd get the same idea: what if I fine-tuned a model on my own work? It would know my repos, my style, my rules. Then I'd price it, and the idea would go away.

What stuck instead was a phrase I started using in October: train the harness, not the model.

## What I mean by the harness

The harness is everything around the model that turns "a capable model" into "work I can trust":

- the **directive** that describes a task, its scope and what proof will count as done;
- the **checks** that run after the agent finishes, starting with tests and a certified floor;
- the **examples** the agent sees of past work that was accepted or sent back;
- the **gates** that decide what needs a human: merges, spending, anything irreversible.

A model is rented. The harness is mine. When I improve the harness, the improvement survives a model change. When a cheaper model comes out, I can swap it in and keep everything that made the work reliable.

## The training data I already had

By October my agent system had a record of hundreds of directives marked Done, and for most of them I knew whether the result was accepted or sent back, and why. I also had a list of the ways runs died: the agent stopped silently, hit a command limit, refused a deletion it needed to make.

That's labelled data. It's just not labelled for fine-tuning. It's labelled for improving the harness:

1. **The directive template is the thing being trained.** Each change to it is a candidate. An evaluation suite runs past tasks through the new template and compares results to the old one. If quality drops, the change doesn't ship.
2. **Past cases become examples.** When a new task comes in, the harness pulls a few similar past tasks with their outcome and the reason, and shows them to the agent. Retrieval does what fine-tuning would, for a fraction of the cost.
3. **Failure classes become checks.** Every way a run died twice becomes something the harness looks for, so it stops being a surprise.

The commercial coding tools do versions of this too. You don't need their scale to get the benefit.

## Why it fits a solo builder

I can't afford a training run. I can afford to rewrite a template on a Tuesday night and run an eval suite overnight. Improvements are small and constant, and I can see each one in a diff.

It also keeps me model-agnostic, which matters more every month. The cheapest capable model changes often. A harness that's tuned to one model's quirks is a trap. A harness tuned to what good work looks like moves with me.

## Where I'm taking it

My agent harness is being split into pieces that can be installed on any repo. The pieces worth keeping are the trainable ones: the directive format, the proof checks, the accept and send-back record, the gates. The next experiments are on prompt frameworks and on cheaper models, measured against the same evals, so a cost cut has to prove it didn't cost quality.

[ROBERT: if you ran the benchmark comparing plain Claude against harness dispatch, add the result here; otherwise leave it out.]
