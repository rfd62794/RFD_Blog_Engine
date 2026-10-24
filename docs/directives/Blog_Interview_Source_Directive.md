# Interview source — transcripts as source-pack material, CLI + fileable replies

## 1. Why this exists

M7.2b of `docs/plans/2026-10-11-real-voice-pipeline.md`. The anti-slop core:
interviews capture the MOMENT and STRUGGLE only Robert knows — the first-hand
evidence that makes a post unmistakably human (industry-standard SME-interview
pipeline; see plan §2). Robert chose BOTH capture paths: a scheduled ping that
reaches him on Telegram via Tobor, and an on-demand CLI interview.

## 2. Scope

- New `blog_engine/core/interviews.py`
- `blog_engine/cli.py`: `interview ask`, `interview file`, `interview list`
- `data/interviews/` (gitignored — verify .gitignore covers it, add the entry
  if missing; never commit a transcript)
- Tests under `tests/`

## 3. The work

1. **Transcript format** (`data/interviews/{date}-{slug}.md`):
   ```markdown
   ---
   recorded_at: <iso8601>
   source: cli | telegram
   lines:
   ---
   ## Q1 <question>
   <answer text>
   ## Q2 ...
   ```
   `interviews.py` parses this into entries `{ref, kind: "interview", text,
   origin}` where `origin` is `<file>#Q<n>` — compatible with the
   `source_pack.py` schema from the GitHub-packs directive (if that directive
   hasn't landed yet, duplicate the tiny entry-shape locally and mark a
   consolidate-later comment; do not block).
2. **Question selection (deterministic).** `pending_questions(n=3)` scans:
   - open `[ROBERT: ...]` placeholders in `data/drafts/*.json` (the exact
     missing-fact text becomes the question), and
   - inventory posts with status `draft` whose notes lack moment/struggle
     material → a generic "what actually happened / what surprised you" pair.
   Dedupes against questions already asked in existing transcripts.
3. **CLI**:
   - `interview ask [--post-id X]` — prints numbered questions, reads answers
     on stdin, appends a transcript file. `--write-only` prints questions and
     exits (the mode a scheduled job captures).
   - `interview file <transcript_path> --source telegram` — imports a pasted
     Q&A file (the path where Tobor/telegram replies land after Robert
     answers; the transport lives outside this repo).
   - `interview list` — shows open questions and recent transcripts.
4. **Pack bridge**: `pack_entries_for(post_id)` returns interview entries for
   any post whose placeholders/inventory match answered questions, for
   `pack build` to merge (integration lands in the pack-only-generation
   directive; here just provide the function + tests).

## 4. What NOT to do

- Do NOT build the Telegram transport or the AgentFlow scheduled job — that
  config lives in `C:/Github/AgentFlow/agentflow.toml`, a different repo and
  a different directive. This directive delivers only: question selection,
  transcript storage/parsing, the CLI, and `pack_entries_for`.
- Do NOT touch generator/publisher/content_guard/publish tools.
- Do NOT commit `data/interviews/` contents.
- No model calls, no network, no new dependencies.

## 5. Verification

```
uv run pytest -q
```

New tests: transcript write/parse round-trip; `pending_questions` extracts
`[ROBERT:]` placeholders from fixture drafts; dedupe against an existing
transcript; `interview file` import; `pack_entries_for` output shape.

## 6. Rules for this run

- NON-INTERACTIVE. No network/installs/.env. `uv run` only; no `python -c`.
- Branch `directive/<slug>`; commit + push; never main/merge/WordPress.
- Update the Status row on finish or stop.

## 7. Completion criteria

- [ ] `interviews.py` + transcript format under gitignored `data/interviews/`
- [ ] `interview ask|file|list` CLI commands
- [ ] `pending_questions` from placeholders + thin drafts, deduped
- [ ] `pack_entries_for` bridge function
- [ ] Tests pass; branch pushed

## 8. Report

Test counts before/after; files changed; sample transcript (fabricated,
small); note for the follow-up AgentFlow-side directive (what job config it
needs: `command` argv, `skip_if`, cadence).

## Sandbox needs

- Exec(uv run pytest)

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Draft |
| Assigned to | devin |
| Depends on | Blog_Github_Source_Packs_Directive.md (soft — entry shape only) |

**Status log**
- 2026-10-11 · devin-laptop-repoman · none → Draft — M7.2b; Robert approved Telegram+CLI dual capture
<!-- queue:end -->
