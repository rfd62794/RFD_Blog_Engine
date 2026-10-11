# Direction: RFD_Blog_Engine

## Cross-site federation (approved 2026-10-11)

The Blog is the editorial bridge in the Robert Floyd Dugger ecosystem: Office
(`rfditservices.com`) establishes professional proof, Blog (`blog.rfditservices.com`)
provides readable technical depth, and Arcade (`games.rfditservices.com`) provides play and
studio history. The three properties share identity, navigation behavior, accessibility and
exact cross-links without sharing one visual treatment.

For the Blog, long-form readability comes first. Automation and Game Building are lanes expressed
through metadata and restrained accents, not separate reading systems. The ecosystem switcher is
always Office · Blog · Arcade; Blog-local navigation is Latest · Automation · Game Building ·
About Robert. Automation posts should link to the exact Office project or case study, and game
posts to the exact Arcade game or Studio story, when an explicit verified relationship exists.
The author's identity routes to the Office About page. Publishing controls remain unchanged:
Robert approves every post and theme deployment.

Implementation handoff and dependencies are in
`docs/notes/2026-10-11-federated-identity-handoff.md`, roadmap M6 and
`docs/directives/Federated_Blog_Bridge_Directive.md`.

```yaml direction
version: 1
answered: 2026-09-23 robert-claude
purpose: Keep a public record of learning and building - how-to posts and build-in-public stories - that brings in contact-center and automation work and keeps pace with the real projects.
done_when:
- The calendar is recovered and paced from real shipped work, every post has a category, tags, a featured image and a meta description, and new work reaches a draft within a week of shipping.
do_not:
- Never delete or unpublish a post without Robert
- never invent facts, numbers, clients or quotes
- never publish a draft Robert has not approved.
audience: clients
hours_per_week: <1
stakes: medium
```
