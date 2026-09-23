# Content ladder proposal - catching the blog up with the work (2026-09-22)

**Status:** proposal for Robert. Nothing in WordPress or the inventory has been changed.
Robert, 2026-09-22: "The Blog Engine needs some love ... it's behind on ALL aspects, so there are
plenty of opportunities to queue up newer more relevant content on the Ladder. Do not remove
anything yet, simply push it out on the Calendar in favor of better pacing relevant to continued
progress on learning and creating."

## What the public blog shows (read-only, `wp-json/wp/v2/posts`, 2026-09-22)

56 published posts; the latest is 2026-09-20. The cadence has held at roughly two to three a week
since June, alternating between two lanes:

- **How-to (search intent):** Convoso / Telesero / DNC / TCPA / forecasting / Bevy / FFmpeg Shorts.
- **Build-in-public (narrative):** "I stopped watching the dialer...", "The agent told me it was
  done...", "I lost the plot on my own project".

What is missing is the last ten days of actual progress: AgentFlow, the Trinity (Claude, Devin,
Tobor) working as one system, the Studio's arcade and foundation, the YT Engine going
operational. The scheduled queue (not publicly visible) was written before any of that existed.

## Proposed new rungs (newest progress first, alternating lanes)

| # | Lane | Working title | Source of truth |
|---|---|---|---|
| 1 | narrative | One Person, Three Agents, One Queue | AgentFlow directive queue; Trinity notes |
| 2 | how-to | How to Hand Build Work to an AI Agent Without Babysitting It | directive template + "Rules for this run" |
| 3 | narrative | The Night a Test Deleted My Repository | RFDGameStudio PR #10 incident + restore (2026-09-22) |
| 4 | how-to | How to Stop Tests From Touching Your Real Git Repo | `Test_Git_Isolation_Directive` (GIT_DIR leak under hooks) |
| 5 | narrative | Deterministic First: Code Checks Before Any Model Does | AgentFlow review pre-check, Tobor lane |
| 6 | how-to | How to Give Every Game in a Studio Clear Data and Juice for Free | Studio foundation spec + glossary |
| 7 | narrative | Retiring the Assistant That Tried to Do Everything | OpenClaw retirement spec |
| 8 | how-to | How to Make a YouTube Pipeline Set Itself Up | YT Engine `setup` / `doctor` (once merged) |
| 9 | narrative | Priority Without Scores | priority bands spec (once Robert decides) |
| 10 | how-to | How to Run Two Machines' AI Agents Without Collisions | Install routing, remote claim check |

Each rung is written only after its source work has shipped, so every post describes something
real (the house rule: recorded notes are claims, not facts).

## Pacing rule for the calendar

- Keep two to three posts a week, alternating lanes, as today.
- Insert the new rungs at the front of the scheduled queue; **push every existing scheduled post
  later** by the slots the new rungs take, preserving their relative order.
- Nothing is deleted or unpublished. Anything that becomes stale after moving is flagged for
  Robert, not removed.
- Dev.to syndication keeps its `DEVTO_MIN_AGE_DAYS` delay, so moved posts syndicate later too.

## What is needed to execute (blocked on the laptop)

- The laptop had no local checkout (the portfolio board lists this repo as "remote only"); one was
  cloned 2026-09-22.
- The live calendar is `data/inventory/*.yaml` (gitignored) plus WordPress scheduled posts, and the
  credentials are in `.env` (gitignored). Neither exists on the laptop. The Claude Desktop config
  still points at `C:\Github\RFD_Blog_Engine\.venv\...`, so the data most likely lived in the
  pre-cleanup checkout or on the Tower.
- Once `.env` and the inventory are present: read the calendar with `get_full_calendar`, then move
  posts with `reschedule_post(post_id, new_date)` (atomic WordPress + YAML), dry-run first.
