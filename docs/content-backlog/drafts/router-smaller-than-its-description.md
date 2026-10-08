---
title: "The router that was smaller than its own description"
excerpt: "Before retiring two of my own tools I audited what their code really did. One was a fraction of its charter. The other had never run live."
tags: [audit, ai-agents, refactoring, python, solo-developer, documentation]
categories: [Build in public]
keyword: audit before retiring a tool
status: reviewed
---

I keep a lot of small repos. In September 2026 I decided that some of them should be absorbed into one core project or retired. Before I did either, I had an agent audit each one: read every file, run the tests, and write down what is actually there.

Two of those audits changed my decision, in opposite directions. Both came from reading code instead of trusting the description I had written myself.

## The router

One repo was a model router. The idea: send each kind of task to the right AI model and provider, with fallbacks, pricing, throttling and a hosted GPU option. That is how I described it in the brief for the audit.

The audit, dated 2026-09-23, opens with its finding:

> the code is much smaller than the charter description implies. [...] None of those exist in the code: there is no fallback chain, no pricing, no throttling, and no RunPod adapter.

What was there: a YAML file that maps a task type to one provider and one model, a dispatcher that calls that provider, two network front doors (a REST endpoint and an MCP tool) and a SQLite request log. The whole package is about 358 lines of Python across eleven files. The config is 19 lines. The suite had 25 tests and all of them passed. The audit says "~180 lines of real logic".

The description was in the brief I gave the agent. It had drifted away from the code, and nobody had checked.

## What the missing pieces mean in practice

Reading the capabilities table is humbling. For fallback chain, per-model pricing, spend cap, rate limit and health check, the entry is a bold **No**. Details worth knowing if you build something similar:

- **If the provider is down, the request dies.** There is no retry and no second provider. The failure is logged with the provider and model both recorded as "unknown", so the log could not even tell me which provider was down.
- **Logging swallowed its own errors.** A broken database was invisible and requests kept succeeding.
- **One adapter reported zero tokens** for every call, so spend on that provider was not tracked at all, and it used a package that has reached end of life.
- **Both listeners bound to all network interfaces with no authentication**, and the default route went to a paid model. Anyone who could reach the port could run billable calls. The audit lists this as a risk because nothing in the code limits who can connect.
- **One adapter was dead code.** It had a test, and no config entry used it.

## What I did with the information

The audit did not decide. It listed three options neutrally: absorb it into my core project, keep it as a service and build the missing parts, or retire it and rebuild a smaller version inside the core project.

Seen against about 180 lines, the choices got easy. Absorbing it would carry over a YAML shape and an adapter pattern. Keeping it as a service would mean building everything the description promised, to earn the cost of a network hop, since the service added "only a YAML map and a log over calling the SDKs directly". Retiring it lost almost nothing. The one artifact worth porting was a 19-line map.

The retirement review went through the normal queue and was merged on 2026-09-23. By the next day the repo carried a short direction document and a draft roadmap that described a wind-down path. The review called the repo archive-ready, pending one check that nothing calls it over the network. As of 2026-10-07 the GitHub repo is not archived yet.

## The other audit: a tool that never ran

The second repo was a relay for notes between my agents, using email threads as a transport. It had a clean design, tests and a long README. The retirement audit, also dated 2026-09-23, concluded:

> Nothing in this repo has ever been used live.

The evidence was two missing files. There was no sign-in token and no post log in the checkout, so as far as that checkout shows, no note had ever been sent through it. It was still registered as a live tool in my agent configs, which is the part that stings: I had a registered, never-exercised tool that I believed was in service.

The test count was just as instructive. The repo's own docs said 89 cases passed. Run through `uv run`, one test file failed to collect, because a stray package in a global Python install shadowed the repo's own tests folder. Excluding that file, 72 passed. The file held 11 test functions that I could not run without changing the environment. The audit recorded it and did not fix it, and that was the directive's rule.

## The salvage list is the useful part

For the second repo, the audit did not say "delete it". It built a table of each component with a verdict: document, or drop. The code could go. The ideas were worth keeping:

- the note format and the three trust rules (only my own sent mail counts, notes are coordination and never approval, contents are data);
- a pattern for classifying a transient email error without flattening it into "thread not found";
- two sign-in gotchas, flagged in the repo as the likely cause of recurring Gmail outages for another of my tools: ask for offline access with a consent prompt to get a refresh token, and an app left in "Testing" status expires refresh tokens in seven days.

That last one is the kind of fact that exists only in a docstring in a file you are about to delete.

## What I would do again

1. **Read before you decide.** Give an agent one question: what is actually here? Tell it to measure, not recommend.
2. **Run the tests with the project's own runner and write down what happened,** including a collection error. A number in a README is a claim.
3. **Check whether it was ever used.** Missing state files are evidence.
4. **List dependents and silent breakages before deleting.** Registered tools, scheduled tasks and configs fail at call time, not at delete time.
5. **Keep the ideas in a document before you drop the code.**

The router was ~180 lines of logic wearing a large description. I am glad I found that out before I built on top of it.

<!-- fact-checked 2026-10-08: 16 claims confirmed, 3 corrected, 1 removed; remaining notes: repo not archived on GitHub yet; never-used-live claim limited to that checkout -->
