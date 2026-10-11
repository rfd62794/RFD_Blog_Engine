# Real-voice pipeline: typed posts, sourced claims, review gates (2026-10-11)

Planned by devin-laptop-repoman with Robert. Approved directions from Robert this
session: six post types at launch; interviews reach him via scheduled Telegram
(Tobor) AND an on-demand CLI command; write this plan, draft all M7 directives,
and queue M7.1 for devin.

## 1. Why

Robert, 2026-10-11: revamp the blog engine's far future — different blog post
type templates, deterministic handling, draft review checks built against what
readers call AI slop, and sourcing drawn from his real work (GitHub activity)
and scheduled interviews with him.

The engine today has exactly one voice: `RFD_CONTENT_FRAME_PROMPT` hardcoded in
`blog_engine/core/generator.py` (MOMENT→SURPRISE→STRUGGLE→LESSON→NEXT, 400-600
words). The 2026-09-27 daily-draft-loop spec already named the biggest gap: no
source-pack step — the model gets a title and notes and improvises. That is
where invented facts and generic prose enter.

## 2. Industry position (researched 2026-10-11)

**Accepted / expected:**
- Google Search Central (updated 2026-10-01): AI assistance is not penalized;
  "it is critical to manually factcheck and review all AI-generated content" —
  explicitly including titles, meta descriptions, structured data, alt text.
  Scaled low-effort content violates spam policy. E-E-A-T rewards first-hand
  experience. Disclosure is encouraged, not required.
- EU AI Act Article 50 (in force Aug 2026): transparency obligations for
  AI-generated publications — labeling machine text is becoming a norm.
- BBC Editorial Guidelines / Impress best-practice note: named accountable
  human, active editorial oversight, mandatory fact-check of AI output, never
  rely on AI alone for research.
- SME-interview pipelines are the industry-standard antidote to generic AI
  content: interview → transcript → voice fingerprint → quote map → draft →
  flattening check. One structured interview feeds multiple posts. Attributed,
  verifiable claims are what AI answer engines cite.

**Ridiculed (the slop tells):**
- Vague attribution ("studies show", "experts agree") — the strongest single
  signal; "confidence without receipts".
- Constructs: "it's not X, it's Y" / "not just X, but Y" / "No X. No Y. Just Z."
- Rule-of-three stuffing, false ranges ("ranging from X to Y"), formulaic
  summaries ("In conclusion", "In summary"), significance inflation
  ("a testament to", "crucial", "pivotal"), hedge stacking
  ("it may be worth considering").
- Lexical tells: delve, tapestry, leverage, multifaceted, robust, furthermore,
  moreover, "in today's fast-paced world", "it's worth noting".
- Typographic: em-dash density, smart-quote/emoji-led bullets, decorative
  unicode in prose, repeated `**Header:**` bullet pattern.
- Structural: uniform sentence rhythm, lists where prose belongs, paragraphs
  whose first sentences alone tell the whole piece.
- Existing open-source linters to adopt rather than reinvent: `deslop`
  (SLOP001-032 rule codes, spaCy+regex, drawn from Wikipedia's "Signs of AI
  writing" and the Max Planck 2024 word-frequency study), `slop-lint`
  (em-dash as hard fail, everything else as warning), sloptells.com's measured
  frequency list.

**Standing caveat from the same sources:** no detector is decisive — humans
trip these too (Mark Twain beats GPT-4.1 on em dashes per 1k words). So style
checks produce **warnings in a review report**; the hard gate is what we can
actually prove: sourced claims, no placeholders, complete metadata. The blog's
defense is receipts, not passing a vibe check.

## 3. Design: milestone M7

### M7.1 — Post types as data (templates)

New `blog_engine/templates/*.yaml`, one file per post type, loaded by a new
`blog_engine/core/templates.py`. Six launch types:

| type id | use | deterministic sections | model sections |
|---|---|---|---|
| `dev-note` | build-in-public (replaces today's frame) | moment/struggle facts from pack | narrative prose |
| `how-to` | runbook/tutorial | steps, code blocks, commands, versions verbatim | intro, why-it-works, gotchas |
| `postmortem` | failure story | timeline from git/issue refs | analysis, lesson |
| `case-study` | client-facing, links Office site | problem/outcome facts, metrics from pack | narrative |
| `interview` | Q&A-derived piece | quotes verbatim from transcript | framing, connective prose |
| `release-roundup` | shipped-work digest | version/date/PR list verbatim | commentary per item |

Each template YAML declares: `sections` (id, kind: `fact` | `narrative`,
required bool, max_words), `word_envelope` (min/max), `voice_notes`,
`required_pack_keys` (what the source pack must contain before generation may
run), `review_rules` (per-type rule overrides). The existing
MOMENT→SURPRISE→STRUGGLE→LESSON→NEXT frame becomes `dev-note`'s definition —
no behavior change for existing inventory until other types land.

Deterministic win: `fact` sections are assembled by code from the source pack
and inserted verbatim into the generated document; the model never sees them
as generation targets. The prompt only covers `narrative` sections and is told
the fact sections are fixed.

### M7.2 — Source packs (deterministic collectors)

A post may not be generated without a source pack at
`data/source_packs/{post_id}.yaml` (gitignored, same pattern as `data/drafts/`).
Pack schema: `sources: [{ref, kind, text, origin}]` where `ref` is a short id
(`S1`, `S2`, …) the model cites inline, `origin` is a real locator (commit sha,
PR url, transcript line, issue url) — never a generated string.

- **M7.2a github**: `blog_engine/core/source_github.py` — extends
  `source_scan`'s allow-list. Pulls merged PRs, closed issues, releases,
  commit log + diff stats via `gh` CLI (argv list, never shell) with a
  local-git fallback when `gh` is absent. Emits pack entries.
- **M7.2b interviews**: `blog_engine/core/interviews.py` —
  `data/interviews/{date}.md` transcripts, two capture paths:
  1. CLI `interview ask` — prints 2-3 questions, reads answers into the file.
  2. AgentFlow `[specialists.jobs.blog_interview]` scheduled beat that pings
     Robert via Tobor/Telegram; replies get filed by a CLI `interview file`
     command. (The AgentFlow-side config lives in that repo — separate
     directive there; this repo provides the file format + CLI.)
  Interview questions are generated deterministically from open
  `[ROBERT: ...]` placeholders in existing drafts and from recent shipped work
  lacking a moment/struggle.

Generation becomes **pack-only**: the prompt receives the pack with its refs
and is instructed: every factual claim carries `[S#]`; anything unsourceable
becomes `[ROBERT: ...]`. A post-render pass rewrites `[S#]` citations out of
the published text but records them in the pack's claim ledger.

### M7.3 — Draft review gate

`blog_engine/core/draft_review.py` (new; `content_guard` stays as-is and is
called by it) produces `data/reviews/{post_id}.json`:

```json
{
  "post_id": "dev-034",
  "reviewed_at": "...",
  "verdict": "clean | warnings | rejected",
  "failures": ["unresolved placeholder [ROBERT: ...] at ¶3", "claim ¶5 has no source_ref"],
  "warnings": ["SLOP020 negative parallelism ¶4: 'it's not X, it's Y'", "SLOP001 'delve' ¶2"],
  "fact_coverage": {"paragraphs": 12, "sourced": 9, "placeholder": 2, "unsourced": 1},
  "metadata": {"category": true, "tags": 4, "featured_image": true, "excerpt": true}
}
```

Rule taxonomy adopts deslop's SLOPxxx codes so future contributors recognize
the catalog. Checks, split by severity:

- **Failures (reject):** unresolved `[ROBERT:]`/`TODO`/`TBD`, any factual
  paragraph (non-narrative-slot) without a source_ref or placeholder, missing
  category/featured image/excerpt, empty excerpt, claims contradicting pack
  data (checked by deterministic string/number compare where possible).
- **Warnings (flagged, publishable after Robert sees them):** SLOP lexicon,
  negative parallelism, rule-of-three density, em-dash density over threshold,
  uniform sentence-length variance, formulaic openers/closers.
- **Verdict:** `rejected` if any failure; `warnings` if warnings only;
  `clean` otherwise. `Publisher.publish_wordpress` gains one line: refuse when
  the review file is absent or `verdict == "rejected"`. Warnings are surfaced
  in the review report Robert sees before approving — his call, as always.

Stage B fact-check from the 2026-09-27 spec writes into this same review file
(adds a `claims` array); the sidecar schema is unified rather than a second
file.

### M7.4 — Wiring

- `generate` gains `post_type` (from inventory YAML or template default).
- `generate-daily` grows `--type` inference later; initial candidates stay
  `dev-note`.
- The CLI gets `review <post_id>` (runs the gate, prints the report) and
  `interview ask|file`.
- The AgentFlow scheduled jobs (daily draft, weekly interview ping) are
  configured in AgentFlow's `agentflow.toml` — separate repo, separate
  directive; this repo only documents the commands those jobs call.

## 4. Guardrails (unchanged)

- Robert-only publish stays exactly as is; every new gate adds checks before
  the existing approval check, never instead of it.
- Nothing here deletes or unpublishes a post.
- Free-lane models only for generation; the review gate is pure stdlib Python
  (no model call, no spaCy dependency — regex + stdlib; deslop is a reference,
  not a dependency).
- `data/` stays gitignored; templates live in `blog_engine/templates/` and are
  committed.

## 5. Directives

| directive | step | status |
|---|---|---|
| `Blog_Post_Templates_Directive.md` | M7.1 | Queued → devin |
| `Blog_Github_Source_Packs_Directive.md` | M7.2a | Draft |
| `Blog_Interview_Source_Directive.md` | M7.2b | Draft |
| `Blog_Draft_Review_Gate_Directive.md` | M7.3 | Draft |
| `Blog_Pack_Only_Generation_Directive.md` | M7.4 wiring (needs M7.1+M7.2a) | Draft |

Order rationale: templates first (they define what a pack must supply), then
collectors, then the gate — the gate's fact-coverage check is meaningless
until packs exist.
