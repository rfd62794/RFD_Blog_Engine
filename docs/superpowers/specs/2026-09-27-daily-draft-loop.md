# Daily draft loop: write -> fact-check -> Robert approves -> publish (2026-09-27)

## 1. Why this exists

Robert, 2026-09-27: "I approve blog publishing, but first we need a daily loop to write drafts for
me to approve." Flow: every day, drafts get written automatically -> Claude fact-checks/rewrites
them -> Robert approves each post -> only then it publishes. Robert's per-post approval is the
**only** publish trigger; nothing publishes without it.

Past failure this must not repeat: AI drafts invented scenes/stats and called themselves
"verified" (`docs/directives/Robert_Only_Publish_Directive.md` background, and the RFD Content
Frame's `[ROBERT: ...]` placeholder convention exists because of it).

## 2. What already exists (verified against code, not docs, 2026-09-27)

**Draft state machine** (`blog_engine/core/draft_manager.py`)
- `VALID_STATUSES = {"draft", "approved", "published"}` but nothing in the codebase ever sets
  `"published"` — `Publisher._update_draft_publish_fields` only sets `published_at` once both
  `wp_url` and `devto_url` exist. The draft JSON's own status field stops at `"approved"`; "is it
  live" lives in WordPress, not in the draft file.
- `create_draft`, `update_draft(post_id, content, title=None, saved_by="human")`,
  `approve_draft(post_id, approved_by="human")` — `approve_draft` raises `ValueError` unless
  current status is `"draft"`. `update_draft` always snapshots the prior content as a revision
  first (`save_revision`), so a fact-check rewrite is non-destructive by construction.
- Drafts are JSON files at `data/drafts/{post_id}.json` (gitignored), one per post.

**Publish gate** (`blog_engine/core/publisher.py`, enforced by
`docs/directives/Robert_Only_Publish_Directive.md`, done 2026-09-23)
- `publish_wordpress(post_id, publish=False, scheduled_date=None)`: refuses immediately
  (`ROBERT_ONLY_PUBLISH_MESSAGE`, no WP call) if `publish=True` or `scheduled_date` is set. Then
  `_check_approved` requires `draft["status"] == "approved"`. Then `content_guard.check(draft)`
  must return `[]`. Then a hard metadata gate (featured image, category, >=3 tags). Only then does
  it call WordPress, and even then with `status="pending"` — never `"publish"`.
- **This means the "publish" WordPress ever does is entirely manual**: the WP user is meant to be
  Contributor (can submit for review, cannot publish), and the engine never sends `"publish"` or
  `"future"` as a WP status anywhere (that's what the Robert-Only-Publish directive tests assert).
  The per-post approval gate this task asks for already exists at two layers (draft status +
  WordPress role) — what's missing is everything upstream of it: automatic generation, fact-check
  recording, and a small approval surface that isn't "call an MCP tool by hand."
- `content_guard.check()` (new 2026-09-23) flags `[ROBERT: ...]` placeholders, `TODO`/`TBD`/
  `lorem ipsum`, empty excerpt, missing categories — but it only catches *unresolved* placeholders.
  It does not verify that a claim left in the draft has a source. That's the fact-check stage's job.

**Generation** (`blog_engine/core/generator.py`)
- `PostGenerator.generate(post_id, model=None, override_frame=False)` requires the post to already
  exist in `data/inventory/{post_id}.yaml` (`InventoryManager`). There is **no topic-sourcing step**
  today — nothing scans git logs, the directive queue, or portfolio activity to decide what to
  write about or to call `register_post`. Roadmap M4.1 (`docs/ROADMAP.md`) names this gap directly:
  "Source packs from real work... A `draft from-source <folder>` command that turns a checked
  facts file... into a draft... Uses only facts in the pack; the draft lists every fact's source
  line." That command does not exist yet, and `docs/sources/` (the folder M4.1 assumes) does not
  exist in this repo. **This is the biggest missing piece** and where invented facts would sneak
  back in if built carelessly.
- `RFD_CONTENT_FRAME_PROMPT` already encodes MOMENT -> SURPRISE -> STRUGGLE -> LESSON -> NEXT and
  400-600 words, matching the `rfd-content-frame` skill. It does not currently instruct the model to
  emit `[ROBERT: ...]` for anything it can't source, or to cite where each claim came from.
- `blog_engine/infra/model_router.py` `route("generation", prompt)` tries Groq -> Gemini ->
  OpenRouter -> Ollama, in that order, first success wins. **Finding:** the `generation` role's
  OpenRouter fallback is `anthropic/claude-3-haiku` — a **paid** model, not free-tier. This
  contradicts the free-lane-only rule for generation and must be fixed before the daily loop uses
  this router unattended (Directive 1, below).

**CLI** (`blog_engine/cli.py`): only `serve`, `version`, `backfill`. Draft/generate/approve/publish
are MCP tools only (`blog_engine/tools/{draft,generate,publish}_tools.py`), reachable today only
through an MCP client (Claude Desktop) or by importing the classes directly. There is no
`uv run rfd-blog-engine approve <post_id>` command — that's the smallest missing approval surface.

**Scheduling hook to reuse** (`C:\Github\AgentFlow\agentflow.example.toml`, `[specialists.jobs.<name>]`
section, spec T4 referenced there): AgentFlow already has a first-class "run this command once a
day, at `daily_at`, and do something with its stdout" primitive —
```
[specialists.jobs.<name>]
daily_at     = "07:30"
command      = ["python", "C:/path/to/job.py"]   # argv list, never a shell string
timeout_s    = 300
kind         = "research"
skip_if      = "NO_CANDIDATES"   # exact stdout meaning "nothing to do" - no ask at all
silent_reply = "NO_REPLY"
prompt       = "Judge this output:\n\n{output}"
```
This is the existing daily-beat pattern to hook into rather than inventing a new Windows Scheduled
Task. The `command` is the deterministic part (source scan + generation call); the specialist
model step is advisory/read-only by design ("notes only, never queue writes or code") — it is
therefore the wrong place to *do* the Claude fact-check rewrite, only a reasonable place to post a
"N drafts ready for fact-check" notice. The fact-check rewrite itself stays a Claude Code session
task (per Robert's stated flow: "Claude fact-checks/rewrites them"), not something the specialist
lane does unattended.

## 3. Design: the four stages

### Stage A — daily generation (deterministic, free-lane only, 1-2 drafts/day max)

New `blog_engine/core/source_scan.py`:
- `scan_recent_activity(repos: list[Path], since_days: int = 2) -> list[dict]` — reads
  `git log --since=... --oneline` (and, where present, closed/Done rows from the directive queue's
  own log, e.g. `mcp__directive-queue__runs` or the queue markdown files' Status logs) across a
  configured allow-list of repos, and turns each real shipped item into a topic candidate:
  `{post_id, title, notes, category, tags, source_repo, source_ref}` where `source_ref` is a real
  commit sha or directive filename — never a generated string. No repo is scanned unless it's on
  the allow-list (config, not a hardcoded scan-everything).
- `register_post` (existing `InventoryManager.add_post`) is called for at most 2 candidates/day,
  oldest real work first, skipping anything already registered (`post_id` collision) or already
  drafted.
- If zero eligible candidates exist that day (no new shipped work), the command prints
  `NO_CANDIDATES` and exits 0 — this is the `skip_if` value the AgentFlow job config uses, so an
  ordinary quiet day produces no draft and no noise, rather than a manufactured one.
- Then, for each newly registered candidate, call the **existing**
  `PostGenerator.generate(post_id)` (unchanged) to produce the draft via the free-lane router.
- **Fix required first:** `model_router.py`'s `generation` role OpenRouter entry
  (`anthropic/claude-3-haiku`) must become a real free-tier slug (e.g. an
  `openrouter/*:free` model per `docs/superpowers/specs/2026-09-24-free-lane.md`'s convention) —
  Directive 1.
- **Prompt change** (Directive 1): `RFD_CONTENT_FRAME_PROMPT` gets one added instruction: *"For any
  number, date, name, or quote you cannot find in the source material given to you, write
  `[ROBERT: fill in — <what's missing>]` instead of inventing it. Never state a fact you were not
  given."* This is the same placeholder convention `content_guard.py` already enforces on the way
  out — the prompt should stop the invented-stat problem at the source, and the guard stays as the
  backstop.

### Stage B — fact-check (Claude review, records sources per claim)

New per-draft sidecar, `data/fact_checks/{post_id}.json` (gitignored, same pattern as
`data/drafts/`):
```json
{
  "post_id": "dev-034",
  "reviewed_at": "2026-09-27T14:00:00Z",
  "reviewed_by": "claude",
  "claims": [
    {"text": "the queue merged PR #7 on 2026-09-23", "source": "git:0dad6e0", "status": "verified"},
    {"text": "<placeholder left for Robert>", "source": null, "status": "unsourced"}
  ],
  "verdict": "clean" | "needs_robert" | "rewritten"
}
```
This is a session task, not a script: a Claude Code session (interactive or a scheduled `/loop`
beat) reads the draft, checks every factual claim against real sources (git log, the directive
queue, RFD Memory — never invents a source), calls `update_draft(post_id, content, saved_by="claude")`
if it rewrites anything (this already snapshots the prior revision), and writes the sidecar. A
draft the fact-check can't fully source stays in `status: "draft"` with `[ROBERT: ...]` markers
still in it — `content_guard` already refuses to push those to WordPress, so this is enforcement,
not just hygiene.

### Stage C — Robert approval surface (smallest option: a CLI command)

Add to `blog_engine/cli.py`:
```
@cli.command()
@click.argument("post_id")
def approve(post_id):
    """Approve a draft (post_id) — the only step that lets it reach WordPress as pending."""
```
wraps the existing `DraftManager.approve_draft(post_id, approved_by="robert")` (unchanged) and
prints the resulting status. This is deliberately the smallest surface: no new mailbox message
type, no TUI panel — Robert already has a terminal in the loop. `list_inventory`/`get_draft`
(existing MCP tools) already let him see what's pending; a `uv run rfd-blog-engine list-drafts`
read-only companion command is optional nice-to-have, not required for this loop.

### Stage D — publish-on-approval (already gated in code; add the loop-specific proof)

No change needed to `Publisher.publish_wordpress` — `_check_approved` already refuses anything
whose `status != "approved"`, before any WordPress call, before `content_guard`, before the
metadata gate. What Directive 2 adds is a test that exercises the **whole daily-loop path**
end-to-end: source-scan registers a post -> generate produces a `"draft"` -> (no approval) ->
`publish_wordpress` is called -> asserts `ValueError` naming the post_id and current status, and
asserts the mocked WordPress handler's `create_post` was **never called** (not just that it
raised). This closes the gap between "the unit test for `_check_approved` passes" and "the actual
new daily-loop code path can't accidentally call approve for you."

## 4. Scope for this loop (solo-sized)

- 1-2 drafts per day, hard cap, oldest real work first.
- Only repos on an explicit allow-list are scanned (starts with just `RFD_Blog_Engine` and
  `AgentFlow`; Robert adds more later — do not default to scanning everything under `C:\Github`).
- No new database tables; the sidecar JSON pattern matches `data/drafts/` exactly.
- No mailbox/TUI work in this pass — CLI `approve` only. If Robert later wants Telegram/mailbox
  approval, that's a follow-up directive, not part of this one.
- Nothing here touches WordPress credentials, publishes, or reads `.env` values.

## 5. Open questions for Robert (max 2)

1. **Which repos feed the daily scan, and what counts as "real activity"?** Just commits to
   `RFD_Blog_Engine`/`AgentFlow` main, or also directive queue Done rows across all repos, or the
   Portfolio board's active-project list? The spec assumes a short explicit allow-list to start;
   confirm the list.
2. **Where does the fact-check stage run day to day** — an interactive Claude Code session Robert
   opens each morning, or a scheduled `/loop` beat that drafts but leaves everything at
   `status: "draft"` for Robert to review in the CLI regardless? Either works with the gate as
   designed; it changes whether Directive work needs a `/loop`-flavored entry point.

## 6. Directives (this pass writes 2; more listed as "to write")

- `docs/directives/Blog_Daily_Draft_Source_Directive.md` — Stage A: fix the paid-model leak in
  `model_router.py`'s `generation` role, add the `[ROBERT: ...]`-on-uncertainty prompt instruction,
  build `source_scan.py` against the two-repo allow-list, wire the 1-2/day cap and `NO_CANDIDATES`
  exit. **Written.**
- `docs/directives/Blog_Approve_CLI_And_Publish_Gate_Test_Directive.md` — Stage C + D: the
  `approve` CLI command, and the end-to-end "unapproved draft cannot publish" test described above.
  **Written.**
- *To write next pass:* a fact-check sidecar schema directive (Stage B's `data/fact_checks/`
  writer + reader helpers, so Claude's review has a place to land instead of being pure session
  memory) — not written this pass, time-boxed by the 2026-09-27 09:45 wind-down.
- *To write next pass:* the AgentFlow-side `[specialists.jobs.blog_daily_draft]` config entry and
  its `command` script (`C:\Github\AgentFlow\agentflow.toml` lives in a different repo — needs its
  own directive/PR there, not this one).
