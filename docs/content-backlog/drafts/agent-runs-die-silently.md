---
title: "When a coding agent's run dies without a word"
excerpt: "185 of my unattended agent runs died unreported. Only 54 had no explanation at all. How I sorted the dead, and why I instrumented before fixing."
tags: [ai-agents, debugging, observability, automation, windows, solo-developer]
categories: [Build in public]
keyword: ai agent process died diagnosis
status: draft
---

I run coding agents unattended. I write a task, approve it, and go to my day job. When I get back, most of the work is there. Some of it is not, because the process that was doing it is simply gone. No error, no final message, no exit code. The log just stops.

This post is about the day I stopped guessing why, wrote down what I actually knew, and found out how little that was.

## The problem in one number

My agent tooling keeps a ledger of every dispatched run. On 2026-10-03 I pointed a small reporter at it and asked for every run that had died without reporting its own end. It returned 185 rows. Sorted by what evidence each row carried:

- **90 explained.** Almost all of these had the same cause, a tool call that needed a confirmation nobody could give. An unattended run is rejected outright on those, and it ends. I already knew about this class. It is not a mystery, it is a rule I had not satisfied yet.
- **41 labelled "power".** The reporter tags a run as a possible power loss when several runs die at the same minute.
- **54 silent.** No exit evidence, no memory evidence, no crash evidence. This is the real question.

The reporter's own verdict line says it plainly: inconclusive, instrumentation required.

## The comfortable explanation did not hold

The 41 "power" rows bothered me. A cluster of deaths at the same minute looks like the machine lost power. But the analysis note records that I also asked Windows for kernel-power and error-reporting events in each of those windows. There were zero. Nothing in the operating system's log agreed with the story.

What the clusters look like instead may be my own tooling. One cluster is three runs at 08:37 on 2026-09-20. Another is a run of deaths across a single afternoon on 2026-09-21. The note's reading, and I will call it a hypothesis because it is one, is that a dispatcher or service restart reaps the child processes it started. I was killing my own agents and then blaming the hardware.

## Why I could not tell

I went and read how a run is launched. This is what I found, all of it in the directive I wrote for the investigation.

- The launcher starts the agent and moves on. It does not wait.
- The run record stores a process id, a start time and a log path. It has no exit code, no exit time and no memory reading.
- The code that checks whether a process is alive already asks Windows for its exit code. Then it throws the code away. That happens in two separate places.
- The classifier that names death causes had no signature for "the process just vanished", so a silent death matched nothing and fell through to a model guess.
- The agent binary I use writes almost nothing to its log. "What were its last words" is useless for those rows. Many end on the first line of output.

So the evidence I wanted was available at the moment of death and I was discarding it. A post-mortem on a ledger that never recorded the cause is just storytelling.

## What I did: instrument, then look

The directive I wrote is explicit about what it must not do. It must not try to fix silent deaths blind. Its job was to add the evidence path and then do one analysis pass.

The instrumentation, merged on 2026-10-04:

1. A small watcher beside each run writes `<log>.exit.json` when the process ends: exit code, timing, and an error field if the watcher itself lost the process.
2. Each launch records free RAM at spawn time and how many other runs were alive.
3. The deaths reporter reads those fields, so a death can be classed as out-of-memory, teardown or crash instead of "silent".

Then I made the analysis pass write down what the data said, which was nothing decisive. The note ends with "no single cause is proven" and no follow-up fix directive, "because the data does not identify a cause". I think that restraint was right. A guessed fix for 54 unknown deaths would have been a new bug with a confident commit message.

## The run that investigated deaths, died

I could not have invented this. The agent run writing the analysis note was dispatched on a different machine on 2026-10-03 at 18:29. That machine was suspended from 20:38 to 22:59 and again from 23:05 to midnight. After the second resume the run's processes were gone. Another session salvaged one staged edit it had not committed, and the commit message records exactly that.

A sleeping laptop is a silent death, and it will not show up as a crash.

## What I would tell you to do

If you run agents unattended, in order:

1. **Record the exit code of every run.** It costs a few lines and it is the only evidence that discriminates.
2. **Record the machine's free memory when you spawn.** You will want it the first time you suspect out-of-memory.
3. **Count how many other runs are alive.** Teardown theories need that number, and my old ledger could only over-count it.
4. **Do not label a cluster of deaths as power without checking the operating system's log.** Mine had none.
5. **Let the verdict say "inconclusive".** An honest "I do not know yet" was worth more to me than a wrong fix.

My note says to rerun the reporter after a few weeks of instrumented runs, and the verdict line will then separate exit codes, memory kills and watcher errors. I have not done that yet, so the 54-silent count above is still the pre-instrumentation number.

## Questions people ask

**Is a silent death the agent's fault?** Not necessarily. In my data the largest class was a rule about confirmations, and the clusters point at my own restarts.

**Can you just retry?** Retries help, and I do resume runs, with a cap. But retrying without a reason repeats the cause.

**Does sleep kill runs?** It did for one of mine, on a machine that was suspended for hours. I only know that from the salvage commit, so I will not guess at a fix.

<!-- fact-checked 2026-10-08: 14 claims confirmed, 2 corrected, 1 removed; remaining notes: 54-silent count not re-run since instrumentation; sleep story rests on one salvage commit; 'teardown' reading stays labelled a hypothesis -->
