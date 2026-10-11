# Pack-only generation — every claim traced to a source ref

## 1. Why this exists

M7.4 wiring in `docs/plans/2026-10-11-real-voice-pipeline.md`. Once templates
(M7.1) and source packs (M7.2a) exist, generation becomes pack-only: the
prompt carries the pack's numbered sources, the model must cite `[S#]` per
factual claim or emit `[ROBERT: ...]`, and a post-render pass strips
citations from the publishable text while recording them in a claim ledger.
This is the step that makes "never state a fact you were not given"
enforceable instead of advisory.

## 2. Scope

- `blog_engine/core/generator.py` (prompt construction + post-render pass)
- `blog_engine/core/source_pack.py` (claim-ledger field + merge of
  `pack_entries_for` interview entries at build time)
- `blog_engine/cli.py`: `generate` command exposing post_type (draft-only —
  it creates a draft, it does NOT publish)
- Tests under `tests/`

## 3. The work

1. **Pack requirement**: `generate(post_id)` refuses (ValueError naming the
   fix — "run `pack build` first") when the post's template has non-empty
   `required_pack_keys` and no pack exists, or when the pack exists but lacks
   a required key. `dev-note` with empty `required_pack_keys` keeps today's
   notes-based behavior (backward compatible — no forced migration of
   existing inventory).
2. **Prompt**: render the pack as a numbered source list; add the standing
   instruction (extend `COMMON_RULES`): *"Every number, date, name, quote,
   or factual claim must end with the source ref it came from, written
   `[S#]`. If a needed fact is not in the sources, write `[ROBERT: fill in —
   <what's missing>]`. Never state a fact you were not given."* Fact-kind
   sections are described as "use only the sources verbatim; you are
   organizing, not creating."
3. **Post-render pass** (`_strip_citations(content) -> (clean_content,
   claim_ledger)`): remove `[S#]` markers from the draft text; record
   `{paragraph_index, claim_excerpt, refs: [S#]}` into the pack file's
   `claim_ledger` array (the review gate reads it for fact_coverage). Any
   `[S#]` citing a ref not in the pack → log warning + leave
   `[ROBERT: verify — invented citation]` in the text (content_guard then
   blocks it — fail closed).
4. **Interview merge**: when `pack build` runs and `pack_entries_for(post_id)`
   returns entries, append them with fresh refs before writing (idempotent —
   skip refs already present).
5. **CLI**: `generate <post_id> [--type T]` — thin wrapper over
   `PostGenerator.generate`, prints `draft: <post_id>`; creates drafts only,
   never approves/publishes.

## 4. What NOT to do

- Do NOT weaken the existing `[ROBERT:]` content_guard path — invented-citation
  handling relies on it.
- Do NOT touch publisher/approval/publish tools.
- Do NOT require packs for post types whose template declares none — dev-note
  backward compatibility is deliberate.
- No new deps, no network, no `.env`, no `data/` commits.

## 5. Verification

```
uv run pytest -q
```

New tests: refusal without required pack; prompt contains numbered sources +
citation instruction; `[S#]` stripped from output and ledger written; bogus
ref becomes the verify-placeholder (which content_guard then flags — assert
it); interview entries merge idempotently; dev-note without pack still
generates.

## 6. Rules for this run

- NON-INTERACTIVE. No network/installs/.env. `uv run` only; no `python -c`.
- Branch `directive/<slug>`; commit + push; never main/merge/WordPress.
- Update the Status row on finish or stop.

## 7. Completion criteria

- [ ] Generation requires a pack when the template says so; refuses with the
      fix named
- [ ] `[S#]` citations stripped into a claim ledger; bogus refs fail closed
      via `[ROBERT: verify]` + content_guard
- [ ] Interview entries merge into packs
- [ ] `generate` CLI exists (draft-only)
- [ ] Tests pass; branch pushed

## 8. Report

Test counts before/after; files changed; one end-to-end fixture trace (pack →
prompt → cited draft → clean draft + ledger).

## Sandbox needs

- Exec(uv run pytest)

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Draft |
| Assigned to | devin |
| Depends on | Blog_Post_Templates_Directive.md, Blog_Github_Source_Packs_Directive.md |

**Status log**
- 2026-10-11 · devin-laptop-repoman · none → Draft — M7.4; hard dependency on templates + pack schema
<!-- queue:end -->
