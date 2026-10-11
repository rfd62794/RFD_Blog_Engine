# GitHub source packs — deterministic collector via gh CLI with git fallback

## 1. Why this exists

M7.2a of `docs/plans/2026-10-11-real-voice-pipeline.md`. Generation must
become pack-only: every post gets its facts from a `data/source_packs/
{post_id}.yaml` file built deterministically from real work, so the model can
never state a fact it wasn't given. `source_scan.py` already produces
candidates from local `git log`; this collector produces the richer pack —
PR bodies, issue context, release notes, diff stats — the material that makes
a post specific instead of generic.

## 2. Scope

- New `blog_engine/core/source_github.py`
- New `blog_engine/core/source_pack.py` (pack schema + writer/reader — shared
  with the later interview collector)
- `blog_engine/cli.py`: `pack build <post_id>` command
- Tests under `tests/`

## 3. The work

1. **Pack schema** (`source_pack.py`):
   ```yaml
   post_id: src-abc1234
   built_at: <iso8601>
   post_type: dev-note        # copied from inventory if present
   sources:
     - ref: S1
       kind: commit           # commit | pull_request | issue | release | diffstat
       text: <human-readable fact line>
       origin: <real locator: full sha, PR url, issue url>
   ```
   `write_pack(post_id, entries, path=data/source_packs)` and
   `read_pack(post_id) -> dict | None`. Refs are assigned `S1..Sn` in order;
   `origin` must be a real locator, never a generated string — assert in the
   writer that `origin` matches a sha/url/transcript-line pattern.
   Never overwrite an existing pack unless `--force`.
2. **GitHub collector** (`source_github.py`): given a repo path on the
   existing `ALLOWED_REPOS` list (reuse `source_scan._allowed_repos`) and a
   ref or `--since-days`, emit pack entries:
   - Commits: `git log` argv-list calls like `source_scan` (same sandbox
     pattern), including `--stat` diff summary per commit.
   - PRs/issues/releases: try `gh` via argv list
     `["gh", "pr", "view", <n>, "--json", "title,body,mergedAt,url"]` etc.
     Detect `gh` absence or failure and fall back to git-only entries with a
     `pack_warnings` note — never fail the whole build because `gh` is missing
     or unauthenticated.
   - Skip bookkeeping subjects (`Merge `, `Queue: `) exactly as source_scan.
3. **CLI**: `pack build <post_id> [--repo PATH] [--since-days N] [--force]` —
   requires the post to exist in inventory (resolve its `source_repo`/
   `source_ref` when the post came from `source_scan`; else require `--repo`).
   Prints `pack: data/source_packs/<post_id>.yaml (N sources)` or
   `NO_SOURCES` when nothing qualifies.

## 4. What NOT to do

- Do NOT call `gh api` or the network in tests — mock `subprocess.run` at the
  boundary (tests may use a real `tmp_path` git repo for the git-log parts,
  the same pattern as `tests/test_source_scan.py`).
- Do NOT change `generator.py`, `publisher.py`, `content_guard.py`,
  `source_scan.py`'s existing functions, or any publish path.
- Do NOT widen `ALLOWED_REPOS`.
- Do NOT commit anything under `data/`; do NOT read `.env`.
- No new dependencies.

## 5. Verification

```
uv run pytest -q
```

New tests: pack write/read round-trip; writer refuses bad `origin`; overwrite
refusal without `--force`; git-only fallback when `gh` fails (mocked);
entries carry real shas from a `tmp_path` fixture repo; `NO_SOURCES` output.

## 6. Rules for this run

- NON-INTERACTIVE. No network, no installs, no `.env` reads.
- `uv run` only; no `python -c`. Branch `directive/<slug>`; commit + push;
  never main, never merge, never touch WordPress.
- Update the Status row on finish or stop.

## 7. Completion criteria

- [ ] `source_pack.py` schema + writer/reader with ref/origin validation
- [ ] `source_github.py` emits commit/diffstat entries from git and
      PR/issue/release entries via `gh` argv calls, degrading to git-only
- [ ] `pack build` CLI works against an inventory post
- [ ] Tests pass; branch pushed

## 8. Report

Test counts before/after; files changed; a sample generated pack (verbatim,
small); how `gh` absence is detected and reported.

## Sandbox needs

- Exec(uv run pytest)
- Exec(git -C)

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Draft |
| Assigned to | devin |
| Depends on | Blog_Post_Templates_Directive.md |

**Status log**
- 2026-10-11 · devin-laptop-repoman · none → Draft — M7.2a; queue after M7.1 merges (pack schema copies post_type)
<!-- queue:end -->
