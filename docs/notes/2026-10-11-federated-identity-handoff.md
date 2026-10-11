# Federated identity handoff — Blog

**Date:** 2026-10-11  
**Source of decision:** `RFD_IT_Services_Site/docs/DIRECTION.md`, approved by Robert.

## System role

The unified system has three purpose-fit properties:

- **Office** (`rfditservices.com`): professional proof, hiring, selective consulting, résumé and contact.
- **Blog** (`blog.rfditservices.com`): readable technical depth and the bridge between professional work and game building.
- **Arcade** (`games.rfditservices.com`): play, experimentation and Studio history.

This is a federated identity, not one identical theme. Shared identity comes from navigation semantics, Robert's name/title, spacing and type roles, accessibility, metadata order, footer/header anatomy and exact related destinations.

## Blog contract

- Ecosystem switcher: **Office · Blog · Arcade**, with Blog active.
- Blog-local navigation: **Latest · Automation · Game Building · About Robert**.
- Long-form readability comes first: one article system and a roughly 720px reading column.
- Automation and Game Building are metadata lanes with restrained accents, not separate article templates.
- Robert's byline routes to `https://rfditservices.com/about/`.
- Automation posts may link to an exact Office project/case study; game posts may link to an exact Arcade game/Studio story. Relationships must be explicit data. Never infer them from similar titles.
- Preserve canonical URLs, feeds, SEO behavior, WordPress publishing controls and the rule that Robert approves every post.

## Dependencies and ownership

The site repo owns the federation specification and final cross-site validation. This repo owns WordPress child-theme implementation and deterministic fixtures/contracts for Blog links. No worker should edit both repos from one directive. Copy settled requirements into the target repo's directive because dispatched worktrees cannot read siblings.

Relevant site milestones: M8 contract, M9 navigation, M10 Office journeys, M11 Blog bridge, M13 validation. This repo tracks the implementation as roadmap M6 and `docs/directives/Federated_Blog_Bridge_Directive.md`.

## Coordination warning

The earlier redesign note at `docs/notes/2026-09-23-blog-redesign-plan.md` said no Sora, glass, scanlines or glow and that the Blog moves toward the Office. That remains compatible with this direction. Where old shared-nav instructions require one flattened row, the 2026-10-11 federation contract supersedes them once the site repo's phase-1 specification is committed.
