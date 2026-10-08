---
title: "How my AI agents leave each other notes: a mailbox with a git relay"
excerpt: "My coding agents run on separate machines and restart often. Here is the mailbox they use to hand off work, and why a git branch carries the mail."
tags: [ai-agents, multi-agent, git, mailbox, handoff, python]
categories: [Build in public]
keyword: multi agent handoff mailbox
status: draft
---

I run several AI coding agents across more than one machine. They restart, they die mid-task, and a cloud one cannot always see my home network. The problem I keep hitting is simple: how does one agent leave a note for another so the note is still there tomorrow?

My answer is a mailbox. Every agent has one. Under it, mail travels over a git branch that always works, with optional small servers on top that make it faster.

## What a message looks like

You send and read with two commands, `agentflow mailbox send --to <name> "text"` and `agentflow mailbox read`. A Claude session gets the same thing as two tools, `mailbox_send` and `mailbox_read`. A `to` can be a name, `all`, or a specific agent or work id.

Each message gets an id the moment it is written: a ULID plus the name of the machine that sent it. A ULID sorts by time, and the machine suffix means two machines can never mint the same id. That one decision makes the rest easy. A message keeps the same id on every server and on the relay, so when three machines copy the same mail around it still lands once.


## Two roads, and the harness picks

The mail takes one of two roads and the sender does not choose.

1. **A hub.** Any machine can run a small server that listens only on its local or private network address and checks a shared token on every request. Faster, but it needs the machines to reach each other.
2. **The git relay.** A branch in my private repo. This is the standing transport, not a fallback of last resort.

If no hub answers, the send writes straight to the branch and prints `queued ... on the relay`. If a hub answers, the send prints `sent`. A hub that refuses a message (bad token, bad address) is an error to fix, not something to route around.

## Why git

My brief was one sentence: I need a secure way for cross-agent communication to start and continue. A private repo meets it with four properties: no extra service to keep alive, nothing to configure, designed to survive container restarts, and the same access boundary that already guards the code.

The writes are plain git plumbing: hash an object, build a private index, make a commit, push with a retry. It never touches the working tree, the index or the branch you have checked out, so it is safe to run inside a clone where real work is happening. It also sets the flag that stops git from prompting for credentials, so a background read can never hang waiting for a password.

Each send writes one commit that holds the sender's outbox line and a copy in each recipient's inbox file. Reading asks every configured hub, merges that with the relay inbox, removes duplicates by id and sorts.

A replicator runs every 60 seconds on any machine that hosts a hub. It copies relay lines the hub is missing and publishes hub lines the relay is missing. Everything is keyed by id, so arrival order does not matter and two hubs converge.

## When mail goes quiet

On 2026-09-24 a wedged bridge held all mail for 45 minutes and nobody could see it. Mail systems fail by going quiet, not by throwing errors.

So the health check now looks for the two places mail can pile up. It warns when three replication rounds in a row fail, when there has been no success for 10 minutes, and when a hub is serving with no replicator running. It also reports each hub's lag behind the relay and any outbox line older than five minutes with no inbox copy.

## Mail is information, not instruction

Two rules keep this from becoming an attack surface.

First, every message is signed. Each machine holds an Ed25519 key and signs the time, sender, recipient and text. A read marks each message verified, failed, or unsigned. A strict mode drops bad signatures and unsigned mail from senders who have published a key. Secrets never go in mail; if one must cross machines, it is encrypted to the receiver's public key and only the ciphertext is committed.

Second, nothing that arrives by mail runs by itself. An agent treats a message the way it treats a note in the repo: something to read and decide about.

## The cost of everything talking

Once mail was easy there was a lot of it. Over one week of hub records I measured 901 messages, and 699 of them were routine "for your information" notes. Each unread message was waking a full model turn whose only job was to read the note and move on.

So there is now a fold. Routine mail from known senders, with no question mark in the text and no failed signature, collapses into one digest line. The rule is an allow-list, not a noise filter: only messages explicitly marked `fyi` or `ack` fold, and requests, holds, verdicts and handoffs never do. Before the read cursor moves, every folded message is written in full to a file, so nothing disappears. The first version was 241 lines of code with 192 lines of tests; after a review pass it is 291 and 317. It ships switched off, in dry-run, counting what it would fold while changing nothing.

## What I have not verified

The fold is switched off in my own config, so I have no measured number for how many model turns it saves. I have not timed end-to-end relay delivery. "Survives restarts" is the design claim, not a test I ran for this post.

## The takeaway

Start with the boring transport that always works, and put the fast one on top. Mint the id at the sender so every copy can be deduplicated. Build the "mail is piling up silently" check before you need it.

<!-- fact-checked 2026-10-08: 17 claims confirmed, 1 corrected, 1 removed; remaining notes: 901/699 counts come from the fold directive (hub store not re-counted); restart survival and delivery time disclosed as untested -->
