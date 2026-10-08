---
title: "Writing an AGENTS.md that matches the real tree"
excerpt: "I ran every command in my AGENTS.md files and diffed the claims against the repo. Wrong Python versions, a missing README and a test command that fails."
tags: [agents-md, ai-agents, documentation, onboarding, python, developer-experience]
categories: [How-to]
keyword: agents.md file best practices
status: draft
---

An AGENTS.md file is the first thing a coding agent reads in a repo. If it is wrong, the agent starts the job with a wrong map and does not know it. A human new hire notices the README is off and asks someone. An unattended agent just follows it.

In late September 2026 I had agents write or harden this file in three of my repos, with one rule: run every command, and check every claim against the tree. This is what that turned up, and what I now put in the file.

## The rule: write only what you just checked

The three passes happened on 2026-09-24 (two repos) and 2026-09-27 (one). The tasks were small commits: the file changed by 113 lines in one repo, and was new at 99 and 108 lines in the others. What mattered was the method. For each statement the agent had to find the file or run the command that proves it.

Every repo failed that test at least once. Here are the failures.

## What was wrong

**A README that did not exist.** In my memory server's AGENTS.md, the documentation list included `README.md`. The repo has no README. The hardened version says so in a note: "No `README.md` exists — an earlier version of this file referenced one in error." An agent trying to open it would have lost a tool call and maybe a run.

**A setup step that configured nothing.** The same file said to copy `.env.example` to `.env`. Nothing in the package loads a `.env` file. The four variables the example documents (ports, database path, log file) are read nowhere. Real config lives in a YAML file, and the only environment variables the code reads are a handful of named ones. An agent following the old instructions would have changed nothing while believing it had configured the service. The audit wrote a directive to fix `.env.example`, and listed the trap in the file's "common pitfalls" so the next agent does not fall in.

**A Python version.** My video pipeline's README said "Python 3.12 via uv". The `.python-version` file says 3.11, and the virtualenv's config reports CPython 3.11.9. I mention this one because it is boring: it is the kind of drift nobody notices until a lockfile resolves differently.

**A roadmap that still said pending.** Two roadmap steps said `status: pending`. Both directives were Done and merged, with commit hashes in the queue blocks. The same repo's direction document also claimed that no AGENTS.md existed yet, which stopped being true the day the file was written.

**A test command that fails.** This was the most useful find. In a research repo of mine, the documented command for the paper-only tests was `uv run pytest -c tests/paper/pytest.ini -q`. The agent ran it live. It failed: with no path argument pytest fell back to a scan of the whole repo, and reported 54 collection errors, including from plain text files in an artifacts folder. Two forms work, and both passed 87 tests: `uv run pytest tests/paper -q`, and the `-c` form with the path added. The broken form had been copied into three docs and seven places in the roadmap.

**Documents that describe a repo that is gone.** Several old docs in that repo name paths that no longer exist, or describe the project by an earlier name with command flags that were removed. The fix I chose is deliberately small: put a one-sentence "superseded" banner at the top of each stale doc pointing at AGENTS.md, and leave the body alone. The goal is not to modernise history. It is to stop an agent trusting it.

## What the good version has in it

After three of these I now expect the same sections.

1. **What this is, in two sentences, and what it is not for.** My memory server's file says it is a stopgap until my main project owns memory, "keep it running and correct, don't grow it". That one line prevents a whole class of well-meaning scope creep.
2. **The tree, as it is.** Each file with one phrase. Mark what is gitignored and absent from a fresh clone, such as the database and the logs, so absence is not read as data loss.
3. **The commands, each tested, with a date.** "Verified 2026-09-24 (fresh `.venv`, Python 3.12.12): `126 passed, 1 failed in 113.68s`" beats "run the tests".
4. **A boundaries section.** What not to touch: the live service, the live checkout, a production database. Say why, and say what has gone wrong before.
5. **Pitfalls found the hard way.** The `.env.example` trap and "do not report the suite as broken over the one known failure" both earned their places.
6. **A link to the current-state file.** I keep a short `docs/state/current.md` for verified facts that change often. AGENTS.md is the stable map, not the daily log.

Some of those fixes were still drafts when I looked. [VERIFY: whether the freshness and stale-docs directives have since merged.]

## Keep it from rotting

A file that was right in September is wrong by Christmas. Two things help:

- **Evidence beside every claim.** A date and a command output. When a reader sees a three-month-old date, they know to re-verify.
- **A cheap freshness directive.** The pass that finds a wrong claim also writes the small fix as its own task, with a rule to verify the claim again before editing. Mine says: "the evidence above was true on 2026-09-24 but re-check before trusting it."

## A short checklist

Take any AGENTS.md, yours included, and:

1. Run every command in it from a fresh clone.
2. Check every file path with `ls`.
3. Check every version number against the lockfile or version file.
4. Read the roadmap's statuses against the git log.
5. Search for words like "yet", "not merged" and "queued", which go stale first.

Where I skipped these steps, my agents inherited my mistakes.
