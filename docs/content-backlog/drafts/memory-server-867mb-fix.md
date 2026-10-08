---
title: "Giving AI agents a memory without eating 867 MB of RAM"
excerpt: "My agent memory server held 867 MB of RAM from startup and blocked other agents. The fix: load the embedding model on demand, release it when idle."
tags: [mcp, memory, embeddings, python, ai-agents, performance]
categories: [How-to]
keyword: mcp memory server sqlite embeddings
status: draft
---

My AI agents share one memory server. It stores notes in SQLite, searches them with full-text search plus embeddings, and any agent connected over MCP can recall what an earlier session wrote. It has been useful. It also quietly held 867 MB of RAM from the moment it started, and on 2026-10-03 that stopped other work from running.

## How I noticed

The tool that starts my coding agents has an admission floor: it will not launch another agent unless 2,048 MB of RAM is free. On the 16 GB laptop, free RAM was sitting between 1,827 and 1,949 MB. Dispatch was held at zero agents. Nothing was broken. The machine was roughly 100 to 220 MB short of the floor.

The directive I wrote for the fix says 867 MB resident, from the SentenceTransformer model `nomic-ai/nomic-embed-text-v1.5`.

One caveat on that number. The project's own recall notes put the model at about 547 MB on disk. The 867 MB figure is what the process held in memory, so it includes the runtime around the model. [VERIFY: the split between model weights and runtime; I did not profile it.]

## The cause was a thread I forgot I had

The code already loaded the model lazily. The function that returns the model does a double-checked lock and builds it only on first use. That is the right design.

Then `main_http()` started a daemon thread at boot whose only job was to call that same function. As far as I can tell it exists so the first recall is not slow. The comment in the code said "Background model warm-up started (non-blocking)". It was non-blocking and it made the lazy loading pointless. The model was resident from second one, even if nobody ever recalled or stored anything.

I found this by reading the code, not by profiling. The real problem was a few lines, not the size of the model.

## Why I did not switch to a smaller model

I had already been through that. The earlier model was `all-MiniLM-L6-v2`, with a 256-token limit. When I checked, it was silently truncating 29 or more stored memories, one of them losing about 97% of its content. That note was an estimated 8,765 tokens long. I moved to the nomic model, which reads up to 8,192 tokens, and I tested the claim instead of trusting the documentation: a 5,000-token string produces a different vector from its first 256 tokens alone.

So the memory cost of 867 MB bought me recall that actually reads whole notes. The right fix was to pay for it only when needed.

## The fix

The directive had six parts, and the work commit (`1c6f303`) touched seven files for 304 added lines and 28 removed.

1. **No eager load.** The warm-up thread now starts only if an environment variable, `RFD_MEMORY_WARMUP=1`, is set. The default is off.
2. **Idle release, in a new small module.** `rfd_memory_mcp/model_lifecycle.py` is 86 lines and does one thing. It records the last time the model was used and runs a single daemon reaper thread. After `RFD_MEMORY_MODEL_IDLE_SECONDS` of no use, which defaults to 600, it drops the model. Setting it to 0 turns release off.
3. **Two small hooks in the embeddings file.** Getting the model records a use. A new release function takes the lock, clears the model and runs garbage collection. An encode that is already running keeps its own reference, so it finishes safely.
4. **The reaper starts only from `main_http()`**, not on import, so tests and tools that import the package do not start a thread.
5. **Tests that never sleep.** The reaper takes an injected clock, so a test can check "not released before the threshold, released after, never released at zero" without waiting ten minutes. There are 108 lines of new tests in `tests/test_model_lifecycle.py`, and two existing server tests changed to assert the warm-up is not started by default.
6. **Stored vectors untouched.** Same model, same prefixes, same 768 dimensions, same blob format. Nothing in the database changes.

I put the new behaviour in its own module on purpose. That file is the only place that knows about idle time, and the existing 393-line embeddings file grew by 16 lines.

## What it costs

The first recall after a release has to reload the model. The directive measured the load at 12 to 26 seconds. The recall call has a 30-second timeout, and recall degrades to full-text search only if the embedding times out, so a cold call returns something and flags that embeddings failed instead of hanging.

That is a real trade. A search right after a quiet ten minutes can be slower or less precise. I accepted it because RAM headroom was what was blocking work.

## One more thing about empty results

While I was in that code, I re-read the rule I wrote about recall: an empty list is a real answer. An earlier version OR-joined its full-text terms with no confidence threshold, so it returned something for any query, including a completely unrelated memory. The notes call that a dangerous near-miss regression. Now recall filters by a threshold, and callers should read `[]` as "not found" and not retry.

## What I have not checked

I have not measured resident memory after the change, and I have not confirmed the running service picked it up. [VERIFY: measure resident MB after restart and check the deployed commit; the service's own version endpoint was reporting an unknown commit in September.] The merge is in git. The result in production is still a claim.

## Questions people ask

**Can I run embeddings on a laptop with 16 GB?** Yes, but count the model as a real cost. Measure resident memory before and after startup.

**Should I use a smaller embedding model?** Check how many tokens your notes actually are first. A model with a short limit can truncate silently.

**Is idle release safe?** It is safe if an in-flight call keeps its own reference to the model and the next call can reload. Test both.
