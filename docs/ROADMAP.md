# RFD_Blog_Engine - Roadmap

*Drafted 2026-09-22 by laptop Claude at Robert's request ("I trust you to build a strong roadmap").
Awaiting Robert's direction answers (`agentflow direction ask`) and approval.*

## Where it stands (measured 2026-09-22)

- MCP server for generating, storing, approving and publishing posts to WordPress
  (blog.rfditservices.com) and Dev.to. 10 ADRs. Last engine work: calendar tools
  (`get_full_calendar`, atomic `reschedule_post`), idempotent Dev.to sync, metadata validator.
- **Tests: 188 passed** with `uv run --extra dev pytest -q`. Plain `uv run pytest -q` - the house
  command - fails with 13 collection errors, because `pytest` is an optional extra, so `uv run`
  falls through to a system pytest that cannot see the project's packages.
- **The calendar is not recoverable from git.** The post inventory (`data/inventory/*.yaml`) and
  credentials (`.env`) are gitignored. The laptop had neither on 2026-09-22 (the portfolio board
  listed the repo as "remote only"), so nothing could be read or rescheduled.
- The public blog has 56 posts, two to three a week since June, alternating how-to and
  build-in-public. The engine's own audit found **zero tags, zero featured images and no meaningful
  categories** across the whole blog.
- The content has fallen behind the work: nothing yet covers the last ten days (AgentFlow, the
  Studio foundation, the YT Engine going operational). See
  `docs/plans/2026-09-22-content-ladder-proposal.md`.

## Why these milestones, in this order

Robert's work order (AgentFlow `docs/PRIORITIES.md`): fix, then tests, then direction, then roadmap
steps, then docs. So M1 makes the engine run and recover anywhere; M2 is the pacing work Robert
asked for, which needs M1's recovered calendar; M3 fixes the quality gaps the engine itself
measured; M4 turns real shipped work into drafts so the blog stops falling behind; M5 lines the
blog up with the website's SEO/GEO work. Nothing here deletes a post: "Do not remove anything yet."

```yaml roadmap
status: draft
approved: ''
reviewed: '2026-09-22'
replan_after_days: 14
stop_if: Robert retires the blog or folds the engine into a successor (the README's PrivyBot note).
milestones:
- id: M1
  title: The engine runs and recovers on any machine
  status: pending
  exit:
  - test: uv run pytest -q
  - grep:
      path: blog_engine/cli.py
      pattern: doctor
  steps:
  - id: M1.1
    title: Make `uv run pytest -q` work (dev tools as a dependency group)
    kind: fix
    size: S
    value: 5
    status: pending
    directive: ''
    detail: Move pytest, pytest-asyncio, pytest-cov and ruff from [project.optional-dependencies] dev to [dependency-groups] dev so a plain `uv run pytest -q` uses the project venv. Baseline 188 passed must hold; update README's test command.
    accept:
    - test: uv run pytest -q
  - id: M1.2
    title: A `doctor` command and a complete .env.example
    kind: feature
    size: M
    value: 4
    status: pending
    directive: ''
    detail: Same shape as the YT Engine's doctor - one line per check, OK or MISSING with the fixing command - for .env keys present, WordPress reachable (read-only call), Dev.to key valid (read-only), inventory present and non-empty. Never print secret values. .env.example lists every key the code reads.
    accept:
    - grep:
        path: blog_engine/cli.py
        pattern: doctor
  - id: M1.3
    title: Rebuild the inventory from WordPress
    kind: feature
    size: M
    value: 5
    status: pending
    directive: ''
    detail: Losing data/inventory must never again mean losing the calendar. Using the existing reconcile/wp_sync tools, add `inventory rebuild --from-wordpress [--dry-run]` that reads every published, scheduled and draft post over the WP API and writes inventory YAML, never overwriting an existing file without --force. Tests use a fake WP client.
    accept:
    - test: uv run pytest -q tests/test_reconcile.py
- id: M2
  title: The calendar paces itself to the work
  status: pending
  exit:
  - test: uv run pytest -q
  - file: docs/pacing.md
  steps:
  - id: M2.1
    title: A pacing planner that only ever moves posts later
    kind: feature
    size: M
    value: 5
    needs: [M1.3]
    status: pending
    directive: ''
    detail: '`calendar plan --insert N [--cadence 2-3/week]` computes a move list: N new slots at the front, every existing scheduled post pushed later in the same order, lanes kept alternating (how-to / build-in-public). Dry run by default; `--apply` calls reschedule_post per move. It can never delete or unpublish, enforced by a test.'
    accept:
    - test: uv run pytest -q tests/test_calendar.py
  - id: M2.2
    title: Stale-after-move report
    kind: feature
    size: S
    value: 3
    needs: [M2.1]
    status: pending
    directive: ''
    detail: After a plan, list posts whose content references dates, versions or counts that the move makes stale, for Robert to review. Flags only - never edits or removes.
  - id: M2.3
    title: Write docs/pacing.md
    kind: docs
    size: S
    value: 2
    needs: [M2.1]
    status: pending
    directive: ''
    detail: The cadence rule, the lanes, the never-delete rule and how to run a plan.
    accept:
    - file: docs/pacing.md
- id: M3
  title: Every post has categories, tags, a featured image and a meta description
  status: pending
  exit:
  - test: uv run pytest -q
  steps:
  - id: M3.1
    title: Apply taxonomy across all posts
    kind: feature
    size: M
    value: 4
    needs: [M1.2]
    status: pending
    directive: ''
    detail: set_post_taxonomy exists but was never applied live. Propose a small category set (the two lanes plus topic) and tags per post from content, write the proposal to a file for review, then apply with a dry run first.
  - id: M3.2
    title: Featured-image upload support
    kind: feature
    size: M
    value: 3
    status: pending
    directive: ''
    detail: The state file's own next step. Upload an image to the WP media library and attach it; tests fake the API. Image creation itself is out of scope here.
  - id: M3.3
    title: The validator enforces the fundamentals
    kind: tests
    size: S
    value: 3
    needs: [M3.1, M3.2]
    status: pending
    directive: ''
    detail: validate_metadata fails a post without a meaningful category, at least one tag, a featured image and a meta description.
- id: M4
  title: Shipped work becomes draft posts
  status: pending
  exit:
  - test: uv run pytest -q
  steps:
  - id: M4.1
    title: Source packs from real work
    kind: feature
    size: M
    value: 4
    status: pending
    directive: ''
    detail: A `draft from-source <folder>` command that turns a checked facts file (like the website's docs/sources/*/facts.md) into a draft in the inventory, status draft, never published without approval. Uses only facts in the pack; the draft lists every fact's source line.
  - id: M4.2
    title: Draft the ten ladder posts
    kind: feature
    size: M
    value: 4
    needs: [M4.1, M2.1]
    status: pending
    directive: ''
    detail: One draft per rung in docs/plans/2026-09-22-content-ladder-proposal.md whose source work has shipped; slotted by the M2 planner.
- id: M5
  title: The blog and the website reinforce each other
  status: pending
  exit:
  - test: uv run pytest -q
  steps:
  - id: M5.1
    title: Case studies and posts link both ways
    kind: feature
    size: S
    value: 3
    status: pending
    directive: ''
    detail: A post generated from a source pack links the matching rfditservices.com case study; the site's case study lists related posts (site-side change lives in RFD_IT_Services_Site).
  - id: M5.2
    title: Dev.to canonical and GEO summary checks
    kind: tests
    size: S
    value: 2
    status: pending
    directive: ''
    detail: Every syndicated post carries the blog canonical URL; every post opens with a one-paragraph factual summary an answer engine can quote. Checked by the validator.
```

## Direction questions for Robert

Run `agentflow direction ask` in this repo (or answer in chat): purpose, done_when, do_not,
audience, hours_per_week, stakes. The draft assumes: purpose = keep a public record of learning and
building that brings in contact-center and automation work; do_not = delete or unpublish posts
without Robert, invent facts; audience = clients; stakes = medium (public but recoverable).
