# Draft review gate — deterministic anti-slop checks with a review report

## 1. Why this exists

M7.3 of `docs/plans/2026-10-11-real-voice-pipeline.md`. Robert wants draft
review checks built against what readers call AI slop. Research basis (plan
§2): style tells are warnings, not proof — the hard gate is what we can
verify (sourced claims, no placeholders, complete metadata). Adopt the
deslop/SLOPxxx rule taxonomy so the catalog is recognizable; implement in
pure stdlib (regex + statistics), no spaCy dependency.

## 2. Scope

- New `blog_engine/core/draft_review.py`
- `blog_engine/cli.py`: `review <post_id>` command
- `blog_engine/core/publisher.py`: exactly one added refusal — absent or
  `rejected` review file blocks `publish_wordpress` (added BEFORE the
  existing checks; all existing gates unchanged)
- `data/reviews/` (gitignored — add to .gitignore if missing)
- Tests under `tests/`

## 3. The work

1. **Report** — `review_draft(post_id) -> dict` writes
   `data/reviews/{post_id}.json`:
   `{post_id, reviewed_at, verdict, failures[], warnings[], fact_coverage{},
   metadata{}}` as specified in plan §M7.3.
2. **Failure checks (reject):**
   - Everything `content_guard.check()` returns (call it, don't duplicate).
   - Any paragraph in a `fact`-kind section (template known) or any paragraph
     containing a number, date, or proper-noun claim that has neither a
     `[S#]` source ref nor a `[ROBERT:]` placeholder. When no template/pack
     exists yet (pre-M7.2 posts), degrade gracefully: run only content_guard
     + metadata checks and mark `fact_coverage.degraded: true`.
   - Missing category / featured_image / excerpt (the existing publisher
     metadata gate, surfaced here so `review` shows the whole picture).
   - Pack-contradiction check where deterministically possible: a number or
     version string in the draft that appears in the pack with a different
     value attached to the same subject line (simple substring comparison;
     document the heuristic honestly).
3. **Warning checks (never block):**
   - `SLOP001` cliché phrases; `SLOP002` single-word tells (delve, tapestry,
     leverage, multifaceted, furthermore, moreover, "it's worth noting",
     "in today's"); `SLOP020/021` negative parallelism ("it's not X, it's Y",
     "not just X, but Y", "No X. No Y. Just Z."); `SLOP022` formulaic openers
     ("Certainly", "Interestingly"); `SLOP010` em-dash density
     (>3 per 500 words); rule-of-three density (>2 triplet lists per post);
     false ranges ("ranging from X to Y"); section-summary restatement
     ("in conclusion", "in summary" openings); uniform rhythm (sentence-length
     stdev below threshold); `**Header:**` bullet pattern; emoji-led bullets.
   - Curate the lists in a module-level `RULES` structure mapping rule id →
     pattern/description so the catalog is readable and extendable.
4. **Verdict**: `rejected` if failures, `warnings` if warnings only, `clean`
   otherwise. `review <post_id>` prints verdict + counts + every line item.
5. **Publisher hook**: in `publish_wordpress`, after `_check_approved`, load
   `data/reviews/{post_id}.json`; refuse (ValueError, no WP call) if absent
   or `verdict == "rejected"`. Absent-review refusal must name the fix:
   "run `uv run rfd-blog-engine review <post_id>`".

## 4. What NOT to do

- Do NOT make warnings block publishing — Robert decides on warnings; the
  report exists to inform his approval, not replace it.
- Do NOT modify `content_guard.check()` behavior (call it as-is), the
  approval status machine, or `ROBERT_ONLY_PUBLISH` behavior.
- Do NOT add dependencies. Pure stdlib.
- Do NOT run a model for "AI detection" — deterministic only.
- Do NOT commit `data/`; no `.env` reads.

## 5. Verification

```
uv run pytest -q
```

New tests: each warning rule fires on a planted-text fixture and does NOT
fire on a clean fixture; failure on unsourced factual paragraph;
degraded-mode on a pre-pack draft; verdict mapping; publisher refuses on
absent review and on `rejected`, and calls WP normally on `clean`+
`approved` (mocked WP as existing publisher tests do — read them first).

## 6. Rules for this run

- NON-INTERACTIVE. No network/installs/.env. `uv run` only; no `python -c`.
- Branch `directive/<slug>`; commit + push; never main/merge/WordPress.
- Update the Status row on finish or stop.

## 7. Completion criteria

- [ ] `draft_review.py` produces the report file with all three verdicts
- [ ] Failure layer = content_guard + metadata + source-coverage (degrades
      pre-pack)
- [ ] Warning layer covers the SLOP codes listed, in a readable RULES table
- [ ] `review` CLI prints the full report
- [ ] Publisher refuses absent/`rejected` reviews, nothing else changed
- [ ] Tests pass; branch pushed

## 8. Report

Test counts before/after; files changed; the warning-rule list as shipped;
one example verdict report (fabricated fixture).

## Sandbox needs

- Exec(uv run pytest)

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Draft |
| Assigned to | devin |
| Depends on | Blog_Github_Source_Packs_Directive.md (soft — degrades without packs) |

**Status log**
- 2026-10-11 · devin-laptop-repoman · none → Draft — M7.3; failures=verifiable, warnings=advisory per plan research
<!-- queue:end -->
