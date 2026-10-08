# Blog content backlog (2026-10-08)

Built for Robert Dugger, RFD IT Services. Mined read-only from the git logs and docs of AgentFlow, RFDGameStudio, RFD_YT_Engine, RFD_Memory_MCP, RFD_Model_Router, SyncBusMCP, Portfolio and PhantomArbiter, plus this repo's ROADMAP, DIRECTION, content-ladder proposal and daily-draft-loop spec. Nothing here is published; every item is `idea` until Robert approves a draft.

## How to read this

- **Lane.** `dev` = dev-identity (build-in-public, RFD Content Frame). `client` = client search-intent (how-to, answers a query an operations manager or small-business owner types). The two lanes have opposite structures; do not mix them in one post.
- **Evidence.** A commit hash or doc path inside the named repo. If the cell says `none in repos`, the post needs Robert's own experience and cannot be drafted from the repos.
- **Difficulty.** S = one sitting from the cited evidence. M = needs a re-check of live state. L = needs Robert's input or a new measurement.
- **Guardrails for every post.** No employer, client or employer-tool names. Run the NCA boundary check before any client-lane post that touches contact-center operations. No personal finances, keys, IPs or credentials. Claims trace to evidence or carry `[VERIFY]`.
- **Drafted already:** items 1, 2, 3 and 5 have full first drafts in `drafts/` (see the end).

## Series: How I use AI to be maximally productive (8 posts)

| # | Working title | Lane | Target keyword | Search intent | Source repo / evidence | Diff | Status |
|---|---|---|---|---|---|---|---|
| 1 | How I run AI coding agents through a directive queue | dev | ai coding agent task queue | Informational: how do people organise several agents without babysitting them | AgentFlow `docs/QUEUE.md`, `Portfolio/STATUS.md` (2026-10-06 board), RFD_Memory_MCP queue log 2026-10-03 (`11a0ca7` to `c599fb4`) | S | idea |
| 2 | Free models first: how I route AI work by cost | dev | ai model routing by cost | Informational: how to cut LLM spend without losing quality | AgentFlow `docs/LANES.md`, `docs/free-agent.md`, commit `c69f15ba8`; RFD_Model_Router `docs/AUDIT.md` | S | idea |
| 3 | Letting a bot play my game before I do | dev | automated playtesting browser game | How-to: test a web game without a QA team | RFDGameStudio `docs/superpowers/specs/2026-10-04-automated-playtesting.md`, commits `99b15571`, `52d0ec40`, `686d6c6f` | M | idea |
| 4 | How I edit YouTube Shorts with FFmpeg and a YAML file | dev | ffmpeg automate youtube shorts | How-to: scripted vertical video assembly | RFD_YT_Engine `infra/ffmpeg.py`, `pipeline/production/ffmpeg_ops.py` (`pad_to_vertical`, `render_segment`), `docs/adr/ADR-004.md`, commit `58156c5` | M | idea |
| 5 | Giving AI agents a memory without eating 867 MB of RAM | dev | mcp memory server sqlite embeddings | How-to/diagnosis: shared agent memory that stays small | RFD_Memory_MCP `docs/directives/RFD_Memory_MCP_Server_RAM_Directive.md`, commit `1c6f303`, `docs/HYBRID_RECALL.md` | S | idea |
| 6 | How my agents leave each other notes: a mailbox with a git relay | dev | multi agent handoff mailbox | Informational: agent-to-agent handoff that survives restarts | AgentFlow `docs/MAILBOX.md`, commit `1cb4a9b4c` (mail digest fold) | M | idea |
| 7 | Can a small model review code? I measured it | dev | ai code review small model accuracy | Informational: do cheap models catch bugs | AgentFlow `docs/evals/reviewer_scorecard.md`, commit `bb5d285b6` (result is INCONCLUSIVE, say so) | M | idea |
| 8 | Designing a game with AI as the builder and me as the captain: Shoal's two modes | dev | ai assisted game design process | Informational: what the human decides vs the agent builds | RFDGameStudio branch `docs/shoal-direction` (`docs/demos/shoal/DIRECTION.md`), commits `59792ee9`, `d84e3bac` | M | idea |

## Dev-identity, other (12 posts)

| # | Working title | Lane | Target keyword | Search intent | Source repo / evidence | Diff | Status |
|---|---|---|---|---|---|---|---|
| 9 | Cutting a game down to its first session: parking features behind a flag | dev | scope cutting game prototype feature flag | Informational: how to trim a game without deleting work | RFDGameStudio commit `4c55844d` (Succession M0 parkedFeatures.ts, ablation tests) | S | idea |
| 10 | How long does my game take to finish? A headless AI-vs-AI soak test | dev | game balance simulation soak test | How-to: measure game length without playing | RFDGameStudio commit `728cbe3d` (`headlessCampaign.ts`, `test_planetofgreed_soak.ts`) | M | idea |
| 11 | A ten-point nudge swung my game from 52.8% to 1.2% | dev | game balance tuning sweep | How-to: tune numbers from evidence | RFDGameStudio `docs/superpowers/specs/2026-10-04-tuning-tools.md`, commit `686d6c6f` | S | idea |
| 12 | A baseline file that only lets the count go down: guarding seeded randomness | dev | deterministic simulation seeded random testing | How-to: ratchet a code-quality count | RFDGameStudio commit `fdc184c2`, `ts/tests/seeded_sim_guard.baseline.json` | S | idea |
| 13 | When a coding agent's run dies without a word | dev | ai agent process died diagnosis | Diagnosis: why unattended runs vanish | AgentFlow `docs/notes/2026-10-03-process-died-analysis.md` | M | idea |
| 14 | The rule my agents follow before they merge: when unsure, defer | dev | ai agent merge rules human approval | Informational: safe delegation of merges | AgentFlow `docs/directives/Devin_Merge_Rule_Directive.md` (2026-10-06) | M | idea |
| 15 | Zero failing, zero skipped: a test floor for a solo developer | dev | zero skipped tests policy | Opinion/how-to: a test floor that agents can enforce | AgentFlow `docs/PRIORITIES.md` ("The floor") | S | idea |
| 16 | The router that was smaller than its own description | dev | audit before retiring a tool | Informational: check what code really does before keeping or retiring it | RFD_Model_Router `docs/AUDIT.md` (commit `0623caa`), SyncBusMCP retirement audit (`f3781b6`) | S | idea |
| 17 | Writing an AGENTS.md that matches the real tree | dev | agents.md file best practices | How-to: onboarding file for coding agents | RFD_YT_Engine commit `6b01ee0`, RFD_Memory_MCP `53e8020`, PhantomArbiter `c269b9fa` | S | idea |
| 18 | The night a test deleted my repository | dev | git hook test deleted repository | Narrative + diagnosis | `docs/plans/2026-09-22-content-ladder-proposal.md` rung 3 (RFDGameStudio PR #10 incident) | L | idea |
| 19 | How to stop tests from touching your real git repo (GIT_DIR under hooks) | dev | pytest git hook GIT_DIR isolation | How-to | Ladder proposal rung 4 (`Test_Git_Isolation_Directive`) | L | idea |
| 20 | Deterministic first: code checks before any model reads the diff | dev | pre-check before ai code review | Informational | Ladder proposal rung 5; AgentFlow `docs/PRIORITIES.md` ("review pre-check") | M | idea |

## Client search-intent (10 posts)

These need Robert's own practical experience. Repo evidence only supports the technique, not claims about a client's operation.

| # | Working title | Lane | Target keyword | Search intent | Source repo / evidence | Diff | Status |
|---|---|---|---|---|---|---|---|
| 21 | How to transcribe audio files locally with faster-whisper | client | transcribe audio locally whisper python | How-to, no per-minute fees | RFD_YT_Engine `pipeline/ingest/` (faster-whisper in README) | M | idea |
| 22 | How to convert landscape video to vertical 9:16 with FFmpeg | client | ffmpeg convert to vertical 9:16 | How-to | RFD_YT_Engine `pipeline/production/ffmpeg_ops.py` `pad_to_vertical` | S | idea |
| 23 | How to add a doctor command to a Python tool so setup problems explain themselves | client | python cli doctor command setup check | How-to | RFD_YT_Engine commit `c9fd5eb`; this repo ROADMAP M1.2 | S | idea |
| 24 | How to connect your own tool to Claude Desktop as an MCP server (with a config backup first) | client | add mcp server claude desktop | How-to | RFD_YT_Engine README "First-time setup" (`setup desktop`) | S | idea |
| 25 | How to keep an automation from publishing by accident: WordPress Contributor role | client | wordpress contributor role automation | How-to / risk | This repo README "Publishing", `docs/superpowers/specs/2026-09-27-daily-draft-loop.md` | S | idea |
| 26 | How to schedule YouTube uploads from a plain-text calendar | client | schedule youtube uploads api python | How-to | RFD_YT_Engine `pipeline/scheduling/`, commit `715a64b` | M | idea |
| 27 | How to automate a weekly operations report from Google Sheets with Python | client | automate weekly report google sheets python | How-to for ops managers | none in repos; needs Robert's own example | L | idea |
| 28 | How to clean and dedupe a call or lead list in Python before you load it | client | dedupe lead list python csv | How-to for ops managers | none in repos; NCA check first | L | idea |
| 29 | How to add meta descriptions, tags and categories to every WordPress post by script | client | wordpress bulk update meta description tags | How-to | This repo `blog_engine/core/backfill.py`, `tools/taxonomy.py`; ROADMAP M3 | M | idea |
| 30 | Build or buy: a plain checklist for small-team automation | client | build vs buy automation small business | Decision guide | none in repos; Robert's judgment; NCA check first | L | idea |

## Series order suggestion

Lead with 1, then 5, 2, 3, 7, 4, 6, 8. Posts 1 and 5 are the strongest because the evidence is a complete, dated trail in git. Post 7 must report the inconclusive result as it is.

## Drafted

| # | File | Status |
|---|---|---|
| 1 | `drafts/directive-queue-ai-agents.md` | draft, needs Robert's approval and a fact-check pass |
| 2 | `drafts/free-model-lanes-cost-routing.md` | draft |
| 5 | `drafts/memory-server-867mb-fix.md` | draft |
| 3 | `drafts/bot-playtest-web-game.md` | draft |
| 6 | `drafts/agent-mailbox-git-relay.md` | draft, fact-checked 2026-10-08 (0 [VERIFY] left); restart survival and relay delivery time untested, so still draft |
| 7 | `drafts/small-model-code-review-measured.md` | reviewed 2026-10-08 (fact-checked; shadow-reviewer numbers updated, reports INCONCLUSIVE as it is) |
| 8 | `drafts/shoal-two-modes-ai-builder.md` | reviewed 2026-10-08 (fact-checked) |
| 9 | `drafts/parking-features-behind-flag.md` | reviewed 2026-10-08 (fact-checked; ablation rerun, panel line count corrected) |
| 10 | `drafts/headless-ai-soak-test-game-length.md` | reviewed 2026-10-08 (fact-checked; soak test rerun, matches) |
| 11 | `drafts/ten-point-nudge-game-balance.md` | reviewed 2026-10-08 (fact-checked; headline corrected to 14.8%, probe rerun) |
| 12 | `drafts/seeded-randomness-ratchet-baseline.md` | reviewed 2026-10-08 (fact-checked; 199/236 totals replaced by recount) |
| 4 | `drafts/ffmpeg-youtube-shorts-yaml.md` | reviewed (fact-checked 2026-10-08), ready for Robert's read |
| 21 | `drafts/transcribe-audio-locally-faster-whisper.md` | reviewed (fact-checked 2026-10-08), ready for Robert's read |
| 22 | `drafts/ffmpeg-landscape-to-vertical-9x16.md` | reviewed (fact-checked 2026-10-08), commands rerun on a synthetic clip |
| 23 | `drafts/python-cli-doctor-command.md` | reviewed (fact-checked 2026-10-08), ready for Robert's read |
| 24 | `drafts/add-mcp-server-claude-desktop.md` | reviewed (fact-checked 2026-10-08), note the stdout-logger caveat |
| 25 | `drafts/wordpress-contributor-role-automation.md` | draft (fact-checked 2026-10-08), confirm live role first |
| 26 | `drafts/schedule-youtube-uploads-text-file.md` | reviewed (fact-checked 2026-10-08), ready for Robert's read |
| 29 | `drafts/wordpress-bulk-update-meta-tags-categories.md` | draft (fact-checked 2026-10-08), live apply unconfirmed |
