# Federated Blog bridge

## Why this exists

Robert approved a federated Office-Blog-Arcade identity on 2026-10-11. The Blog becomes the readable editorial bridge, sharing ecosystem navigation and exact relationships without becoming visually identical to either sibling.

## Read first

- `docs/DIRECTION.md`, roadmap M6 and `docs/notes/2026-10-11-federated-identity-handoff.md`.
- `docs/notes/2026-09-23-blog-redesign-plan.md`.
- Existing child-theme templates, styles, build tests and crosslink tests.

## Scope

After the site repo commits its phase-1 federation specification, paste the settled navigation/identity contract into this directive before queueing. Then implement the ecosystem switcher, Blog-local navigation, one readable article system, lane accents, byline identity and explicit exact project/game relationships in the WordPress child theme with tests first.

## The work

Keep the Blog's canonical/feed/publishing behavior. Model related destinations explicitly; absence means no CTA. Expose deterministic fixtures or contracts that the site repo can use for offline M13 journey validation.

## Forbidden Actions

- No WordPress writes, post publication, plugin installation, theme deployment or sibling-repo edits.
- Do not infer relationships from titles.
- Do not add scanlines, glass panels or ambient glow to reading surfaces.
- Do not remove content or weaken canonical/SEO/feed behavior.

## Required from User

Robert must approve any live theme deployment or WordPress setting/content change. No owner action is required for local child-theme implementation and tests.

## Verification

Before queueing, run and record the repo's current commands. Expected command family:

```text
uv run --extra dev pytest -q
```

Add focused theme/navigation/link tests and report the real full-suite result. No network-dependent test is allowed.

## Rules for this run

Non-interactive; no installs/downloads; branch commit only; never push, publish or deploy. Stop if the site contract is absent instead of inventing it.

## Completion criteria

- Ecosystem and Blog-local navigation are distinct and accessible.
- Articles share one readable system; lanes use metadata/accent only.
- Explicit relationships resolve to exact Office or Arcade destinations.
- Byline identity routes to Office About.
- Deterministic fixtures support site-side validation.
- Tests pass.

## Report

List templates/data changed, relationship schema, navigation order, exact tests and owner-only follow-ups.

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Draft |
| Assigned to | devin |
| Branch | - |
| Base branch | main |

**Status log**
- 2026-10-11 · devin-laptop-repoman · none → Draft — cross-repo handoff from the approved RFD_IT_Services_Site federation; blocked until the phase-1 contract is committed
<!-- queue:end -->
