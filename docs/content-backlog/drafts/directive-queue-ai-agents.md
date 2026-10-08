---
title: "How I run AI coding agents through a directive queue"
excerpt: "A directive queue lets one person hand work to AI coding agents and review it later. Here is one real task from Draft to Done, with git hashes."
tags: [ai-agents, workflow, automation, directive-queue, solo-developer]
categories: [Build in public]
keyword: ai coding agent task queue
status: draft
---

I have a day job and a handful of side projects, and I cannot sit and watch an AI agent type. So I stopped trying to. Work goes into a queue as a written directive, an agent picks it up in its own copy of the repo, and I look at the result when I have ten minutes.

This post walks one real task through that queue, using the git history, so you can see what each step actually does. It is not a polished system. It is a set of rules that kept me from losing track of what was running.

## What a directive is

A directive is a markdown file in the repo's `docs/directives/` folder. The ones I write have the same skeleton every time: a "Read first" list of files, a "Why this exists" section with the evidence, a "Scope" in order, and a "Verification" section with the exact commands.

That last section matters more than it looks. Two of my repos had directives without a Verification block, and I ended up committing a change just to add the missing section ("Lint debt: add missing ## Verification section" in PhantomArbiter and SyncBusMCP, 2026-09-27). If an agent does not know how I will check its work, I cannot check it either.

## The task: a memory server using too much RAM

On 2026-10-03 I noticed my memory server was holding 867 MB resident on a 16 GB laptop. The queue refuses to start new agents when free RAM is under 2,048 MB, and free RAM was sitting between 1,827 and 1,949 MB. So the 867 MB meant no agent could start at all.

I wrote the directive (142 lines, commit `8bf2928`), and the rest went through the queue. This is the history, straight from `git log` in RFD_Memory_MCP:

1. `Draft -> Queued` (me, `11a0ca7`). The file exists but nothing runs.
2. `Queued -> Approved` (me, `c0a5aa6`). Approval is a separate step on purpose. Nothing dispatches until I, or a Claude session working under my standing rules, says so.
3. `Approved -> In progress` (the dispatcher, `eb37eb7`). The dispatcher creates a git worktree on its own branch and starts the agent there. My main checkout is never touched.
4. The agent's work commit: `1c6f303`, seven files, 304 lines added and 28 removed.
5. `In progress -> Review` (the agent, `3ca5d93`).
6. Pull request #7 merged (`4ca39aa`).
7. `Review -> Done` (`c599fb4`).

The task went from Draft to Done in one day. I did not watch it run. I read the diff at step 5.

## The rules that make it work

**Every directive gets its own branch and worktree.** An agent that goes wrong goes wrong in a folder I can delete. My live checkout stays on main.

**Statuses are a small closed set.** From the queue log I see Draft, Queued, Approved, In progress, Review, Done, Blocked and Superseded. That is all. When an agent hits something it cannot do, it writes Blocked with a reason instead of improvising. A free-model run that changes nothing reports `Blocked: no edit` rather than claiming success.

**The agent proves its work with commands, not words.** I wrote a whole post about an agent that told me its tests passed when 47 passed and one failed. The fix is boring: the Verification section lists the commands, and the review step re-runs them.

**There is a ceiling on how many run at once.** The admission check counts RAM and CPU headroom before it starts another agent. That is exactly what the memory server was blocking.

**Some repos are off limits.** The tool refuses to dispatch to them at approve time and again at dispatch time. A rule written down once is not enough; I want it checked at more than one point.

## Where it gets messy

The queue is not magic. On 2026-09-28 a run merged its pull request (#360) and then died before it could mark its own row Review. The row said In progress forever. The branch also reads zero commits ahead of main once merged, so the normal "has commits" check refused to move it. I had to add a special case in `docs/QUEUE.md`: when a branch is already merged, accept the move to Review and note the merge sha.

I also keep a report on runs that die with no message. A note from 2026-10-03 lists a dozen dead runs, and most of them have kind `silent`, meaning I cannot say why they stopped. [VERIFY: the exact count and the share labelled silent; I read only the top of the table.] I do not have a clean answer for that yet.

And a pile of waiting work is its own problem. On the board for 2026-10-06 my main project had 10 queued, 9 approved and 8 blocked directives. The queue gives me a list, but I still have to decide what matters.

## What I would tell someone starting

Start with one rule: nothing runs without a written approval step. Add a branch per task. Add a Verification section to every task. Everything else can wait.

Skip the idea that an agent should decide what to work on. Mine do not. I decide, I write it down, and they do the typing. That is the only arrangement where I can leave for my day job and trust what I find when I get back.

If you want the details of the free-model side of this, which is how I keep the cost near zero for low-risk tasks, that is the next post in the series.

## Questions people ask

**Do you need a special tool for a directive queue?** No. A folder of markdown files, a status line in each, and a script that makes a worktree is enough to start. Mine grew from that.

**Who approves?** I do, or a Claude session acting under rules I wrote down. [VERIFY: confirm the current wording of the approval and mark-Done rules before publishing.]

**Does an agent ever merge to main?** Not on its own judgment. The merge rule is still being tightened; a directive dated 2026-10-06 says the default must be defer when anything is unclear.
