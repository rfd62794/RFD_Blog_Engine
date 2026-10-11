# Post type templates as data — six launch types, fact vs narrative sections

## 1. Why this exists

Robert, 2026-10-11: the engine needs different blog post type templates and
more deterministic handling. Today every post runs through one hardcoded
prompt (`RFD_CONTENT_FRAME_PROMPT` in `blog_engine/core/generator.py`). The
full design is `docs/plans/2026-10-11-real-voice-pipeline.md` (M7.1). This is
the first M7 step: templates become data files other steps build on — source
packs (M7.2) fill a template's required pack keys, and the review gate (M7.3)
reads a template's section kinds to decide which paragraphs need a source.

## 2. Scope

- New directory `blog_engine/templates/` with six YAML files (committed —
  these are code, not data; they do NOT go under gitignored `data/`)
- New module `blog_engine/core/templates.py`
- `blog_engine/core/generator.py` (prompt construction only — routing,
  DraftManager calls, and publish paths unchanged)
- `blog_engine/core/inventory.py` (read an optional `post_type` field only —
  no storage-format change beyond tolerating the key)
- Tests under `tests/`

## 3. The work

1. **Template schema.** Each `blog_engine/templates/<type_id>.yaml` declares:
   ```yaml
   type_id: dev-note
   title: Dev note / build-in-public
   word_envelope: {min: 400, max: 600}
   voice_notes: <free text appended to the prompt>
   required_pack_keys: []        # M7.2 will enforce; define the field now
   sections:
     - id: moment
       kind: narrative           # or: fact
       required: true
       max_words: 90
       prompt_hint: <one line telling the model what this section is>
   ```
   `kind: fact` marks a section that future deterministic assembly fills
   verbatim from a source pack. In THIS directive, fact sections are still
   rendered by the model, but the prompt must state they may only contain
   information from the notes/context provided.
2. **Six launch templates** (type_id → purpose):
   - `dev-note` — build-in-public. Sections = the existing frame
     (moment/surprise/struggle/lesson/next), all `narrative`, 400-600 words.
     It must reproduce the current frame exactly, including the banned-word
     list and the `[ROBERT: ...]`-on-uncertainty instruction.
   - `how-to` — runbook. `fact` sections: `steps`, `code`, `environment`
     (versions/OS). `narrative`: `intro`, `why`, `gotchas`. 500-900 words.
   - `postmortem` — failure story. `fact`: `timeline` (from refs). `narrative`:
     `what-happened`, `root-cause`, `lesson`. 400-700 words.
   - `case-study` — client-facing. `fact`: `problem`, `outcome-metrics`.
     `narrative`: `approach`, `lessons`. 500-800 words.
   - `interview` — Q&A-derived. `fact`: `quotes` (verbatim transcript lines).
     `narrative`: `framing`, `analysis`. 500-800 words.
   - `release-roundup` — digest. `fact`: `items` (version/date/ref list).
     `narrative`: `commentary`, `next`. 300-600 words.
3. **`core/templates.py`.** `load_template(type_id) -> Template` (dataclass or
   TypedDict — match repo style), `list_templates() -> list[str]`,
   `default_type() -> "dev-note"`. Parse with `yaml.safe_load` (pyyaml is
   already a dependency — inventory uses it; verify in `pyproject.toml` first,
   and if it is NOT a dependency stop and note it rather than adding a new
   parser). Raise a clear `ValueError` naming the file on a missing key or
   unknown `kind`. No caching complexity — plain load per call is fine at this
   scale (KISS).
4. **Generator integration.** `PostGenerator.generate` gains
   `post_type: Optional[str] = None`; resolution order: explicit arg →
   inventory `post_type` field → `"dev-note"`. `_build_prompt` renders from
   the loaded template's sections (each section contributes its `prompt_hint`
   + kind label) instead of the literal frame string. Keep
   `RFD_CONTENT_FRAME_PROMPT` in the file but mark it deprecated with a
   one-line comment — it is now `dev-note.yaml`'s source text; the generator
   must not use it for other types. Preserve the `[ROBERT: ...]` instruction
   and banned-word list in every template's rendered prompt (move them to a
   shared `COMMON_RULES` constant appended to all prompts, so a future
   template can't drop them).
5. **Inventory tolerance.** `get_context_for_generation` must not break when a
   post YAML has no `post_type` (default `"dev-note"`) and must pass
   `post_type` through when present. Add `post_type` to `add_post` as an
   optional kwarg defaulting to `"dev-note"`.

## 4. What NOT to do

- Do NOT build source packs, interviews, or the review gate — later M7
  directives. `required_pack_keys` is declared but nothing enforces it yet.
- Do NOT touch `publisher.py`, `content_guard.py`, `draft_manager.py`'s
  approve/publish paths, `source_scan.py`, or anything under
  `blog_engine/tools/publish_tools.py`.
- Do NOT change model routing or add dependencies (no spaCy, no new packages).
- Do NOT add a CLI command in this directive — MCP/generator-level only.
- Do NOT commit anything under `data/`.
- Do NOT read or print `.env` values; mock `route()` in tests the way
  `tests/test_generator.py` does.

## 5. Verification

```
uv run pytest -q
```

Record pass/fail counts before and after. New tests: all six templates load
and validate; a malformed template YAML raises `ValueError` naming the file;
`generate` with each type produces a draft via mocked `route()`; a
`dev-note`-type generation produces a prompt containing the original frame
sections AND the `[ROBERT:]` instruction AND the banned-word list;
`post_type` resolution order works (arg > inventory > default); a post YAML
without `post_type` still generates (no regression — baseline must hold).

## 6. Rules for this run

- NON-INTERACTIVE. No network, no installs, no `.env` reads.
- Python 3.12 via uv; always `uv run`, never bare `python`.
- Never `uv run python -c ...` — write a test instead.
- Work only on your `directive/<slug>` branch; commit and push it. Never
  commit to main, never merge, never deploy, never touch WordPress.
- Update this directive's Status row when you finish or stop partway.
- Create no scratch files outside `.devin-scratch/`.

## 7. Completion criteria

- [ ] `blog_engine/templates/` has six valid YAML templates covering the table
      in `docs/plans/2026-10-11-real-voice-pipeline.md`
- [ ] `core/templates.py` loads/validates them with clear errors
- [ ] `generate(post_type=...)` renders per-template prompts; `dev-note`
      preserves the existing frame byte-for-byte in spirit (same sections,
      same rules)
- [ ] `COMMON_RULES` carries the `[ROBERT:]` instruction + banned words into
      every template's prompt
- [ ] Inventory tolerates missing `post_type`
- [ ] Tests pass; branch pushed

## 8. Report

Test counts before/after; list of every file created/changed; the resolved
section list for one non-dev-note template as rendered into a prompt; any
deviation from the plan doc and why.

## Sandbox needs

- Exec(uv run pytest)

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Queued |
| Assigned to | devin |
| Branch | - |
| Base branch | - |

**Status log**
- 2026-10-11 · devin-laptop-repoman · none → Draft — written alongside docs/plans/2026-10-11-real-voice-pipeline.md (M7.1); approved by Robert in session for Queued
- 2026-10-11 18:54 · devin-overseer (delegated) · Draft → Queued — M7.1 real-voice pipeline; approved by Robert in session 2026-10-11; under delegate.envelope
<!-- queue:end -->
