# M1.2: a `doctor` command (read-only health check)

Depends-on: none (M1.1, `uv run pytest -q` working, is already on `origin/main`: baseline below).
Size: M. One new small module, one CLI wiring, one new test file, two small text edits.

## 1. Why this exists

Roadmap M1.2 (`docs/ROADMAP.md`, "A `doctor` command and a complete .env.example"). When the
engine misbehaves on a new machine there is no single place that says what is missing. The YT
Engine solved this with `python -m pipeline.interface doctor` (one line per check, `OK` or
`MISSING`, exit non-zero on failure). This is the same shape for the blog engine. Roadmap M1's
exit criterion is `grep` for `doctor` in `blog_engine/cli.py`.

## 2. Scope

In, in order:

1. New module `blog_engine/core/doctor.py` holding the checks (keeps `cli.py` a thin wiring layer).
2. A `doctor` command in `blog_engine/cli.py` that calls it.
3. New `tests/test_doctor.py`.
4. `.env.example`: add the optional variable names the code reads and `.env.example` lacks
   (see below). `README.md`: one line under "Usage" showing `uv run rfd-blog-engine doctor`.
5. In `docs/ROADMAP.md`, change the `status:` line of step `M1.2` from `pending` to `done`
   (that one line only, after everything else passes).

## 3. The work

Read first, inside this worktree: `blog_engine/cli.py` (click group; commands import lazily
inside the function body), `blog_engine/api/wordpress.py` (`WordPressHandler.get_posts` is a
plain GET), `blog_engine/infra/base_api_handler.py` (`BlogEngineHTTPError` has `.status_code`),
`blog_engine/core/inventory.py` (`INVENTORY_DIR`, per-post `*.yaml`, each with a `post_id` key),
`tests/test_approve_cli.py` (how `CliRunner` and mocks are used here), `tests/test_env.py`.
Facts already verified for you, so do not hunt:

- Credentials the code reads: `WORDPRESS_URL`, `WORDPRESS_USER`, `WORDPRESS_APP_PASSWORD`
  (WordPress) and `DEVTO_API_KEY` (Dev.to). `.env` is loaded from the repo root with
  `load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")` (see `blog_engine/server.py`).
- The WordPress user is a Contributor: it can only create drafts. `get_posts` issues
  `GET {WORDPRESS_URL}/wp-json/wp/v2/posts` with basic auth and params
  (`status`, `per_page`, `page`). It writes nothing.
- `InventoryManager.__init__` CREATES its directory, so doctor must NOT instantiate it. Use
  `INVENTORY_DIR` (a `Path`) directly and only read.
- `data/inventory/*.yaml` is gitignored: in a fresh worktree the directory has no yaml files, so
  tests must build their own temp inventory directory.
- `BaseAPIHandler._make_request` retries 5xx/timeouts up to 4 times with backoff; that is fine
  for doctor, but keep the call to a single request (`per_page=1`).
- Baseline on `origin/main` 3bb606a, measured 2026-10-11 with Python 3.12.12 under `uv run`:
  `uv run pytest -q` gives `281 passed`.

### 3.1 `blog_engine/core/doctor.py`

```python
def run_doctor(
    env: Mapping[str, str],
    inventory_dir: Path,
    wp_client=None,          # object with: async get_posts(status, per_page, page, search) -> list
    out=print,               # callable taking one str; tests capture it
) -> int:                    # 0 when every check is OK, else 1
```

It runs these checks in order and emits ONE line per check through `out`, formatted exactly
`f"{'OK':<8}{name}"` or `f"{'MISSING':<8}{name} - fix: {fix}"`:

1. One check per variable, in this order: `WORDPRESS_URL`, `WORDPRESS_USER`,
   `WORDPRESS_APP_PASSWORD`, `DEVTO_API_KEY`. OK when `env.get(name, "").strip()` is non-empty.
   The line shows the variable NAME only. Fix text: `set NAME in .env (see .env.example)`.
2. `WordPress reachable (read-only GET)`:
   - If any of the three `WORDPRESS_*` checks failed, report MISSING with fix
     `set the WORDPRESS_* variables first` and make NO network call.
   - Otherwise do exactly one `await wp_client.get_posts(status="publish", per_page=1, page=1)`
     (run it with `asyncio.run`). When `wp_client` is None, build
     `WordPressHandler(None, env["WORDPRESS_URL"], env["WORDPRESS_USER"], env["WORDPRESS_APP_PASSWORD"])`
     (`get_posts` never touches the DB, so pass `None`; do not create a `DBManager`).
   - Success (any list result, including empty) is OK. On any exception report MISSING with a fix
     built ONLY from the exception class name and, for `BlogEngineHTTPError`, its `status_code`,
     e.g. `check WORDPRESS_URL and credentials (BlogEngineHTTPError 401)`. Never include the
     exception message or text: it can echo URLs or response bodies.
3. `Inventory present and non-empty`: OK when `inventory_dir` is an existing directory holding
   at least one `*.yaml` file whose parsed content is a mapping with a `post_id` key. Otherwise
   MISSING with fix `restore data/inventory/*.yaml (rebuild-from-WordPress is roadmap M1.3)`.
   Read only: never create the directory or any file; a yaml that fails to parse is simply not
   counted.

Return 0 only if all checks are OK; any MISSING gives 1. Secret VALUES (any env value) must never
appear in any emitted line, in any branch.

### 3.2 `blog_engine/cli.py`

Add `@cli.command() def doctor():` with a one-line docstring. Inside: lazy-import `os`, `Path`,
`load_dotenv`, `INVENTORY_DIR` and `run_doctor`; call
`load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")` (the same path `server.py` uses),
then `raise SystemExit(run_doctor(os.environ, INVENTORY_DIR, out=click.echo))`. Keep the command to
those few lines. The word `doctor` must appear in the file (roadmap exit grep).

### 3.3 Tests, `tests/test_doctor.py` (no network, no real `.env`, no real inventory)

Call `run_doctor` directly with an explicit `env` dict, a `tmp_path` inventory directory and a fake
`wp_client` (a small class with `async def get_posts(...)` that records calls). Also one
`CliRunner` test of the `doctor` command with `blog_engine.cli`'s collaborators patched so no
`.env`, network or real inventory is touched (patch `run_doctor` at its import location, or patch
`load_dotenv` and pass env through `monkeypatch.setenv`/`delenv`; keep it simple). Cover:

1. All present, inventory has one valid yaml, fake WP returns `[]`: returns 0, every line starts
   `OK`, and the fake recorded exactly one `get_posts` call with `status="publish"`, `per_page=1`.
2. A missing or blank `WORDPRESS_URL`: returns 1, that line is MISSING, the WordPress check is
   MISSING, and the fake recorded ZERO calls.
3. Missing `DEVTO_API_KEY` alone: returns 1, the other lines OK.
4. WordPress failure: the fake raises `BlogEngineHTTPError(401, "secret-body-text")`: returns 1,
   the line contains `401` and does NOT contain `secret-body-text`.
5. Inventory directory missing: returns 1 and the directory still does not exist afterwards.
   Inventory directory exists but empty, or only a yaml without `post_id`: returns 1.
6. Secrets never printed: set the three secret variables to the sentinels `SENTINEL_PW_123`,
   `SENTINEL_KEY_456`, `SENTINEL_USER_789`; for the all-OK run and the failure run, assert none of
   the sentinels appears in the captured output.
7. Read-only proof: the fake WP client exposes ONLY `get_posts`; use a class with no other
   methods so any call to `create_post`, `update_post` or `upload_media` would raise
   `AttributeError` and fail the test.
8. CLI: `doctor` is registered (`--help` lists it) and its exit code equals `run_doctor`'s return.

### 3.4 `.env.example` and README

Append to `.env.example`, as commented-out lines so the existing `tests/test_env.py` still passes
(names only, no values, no secrets):

```
# Optional
# SOURCE_SCAN_REPOS=
# DEVTO_SYNC_START_DATE=
# DEVTO_MIN_AGE_DAYS=
```

(`SOURCE_SCAN_REPOS` is read in `blog_engine/core/source_scan.py`; the other two names are the
values of `DEVTO_SYNC_START_DATE_ENV` and `DEVTO_MIN_AGE_DAYS_ENV` in `blog_engine/devto_sync.py`.)
Add one line to README "Usage" showing `uv run rfd-blog-engine doctor` and what its exit code means.

## 4. What NOT to do

- Never publish, create, update, schedule, delete or upload anything in WordPress or Dev.to. The
  only network call allowed anywhere in this change is the single `GET` described above, and it is
  made only by the real command, never by a test.
- Do not add a Dev.to validity check (no GET exists in `DevToHandler`; presence of the key name is
  all doctor checks; real validation is a possible later step).
- Never print, log, echo or write any secret value, any `.env` content, or any exception message
  from the WordPress call. Do not read or print `.env`.
- Do not instantiate `InventoryManager` or `DBManager`, and do not create `data/inventory`.
- Do not edit any other roadmap line, `tests/test_env.py`, or existing tests. No new dependencies.
- Do not read outside this working directory. Do not search, glob or hunt: if a file named above
  is missing, stop and say so in the Status row.

## 5. Verification

Run each from the worktree root; the expected result follows each fence.

```bash
uv run pytest -q tests/test_doctor.py
```
Expected: all pass, at least 8 tests.

```bash
uv run pytest -q
```
Expected: no failures. Baseline is `281 passed`, so expect `281 + <your new test count> passed`.

```bash
grep -n "doctor" blog_engine/cli.py
```
Expected: at least one match (the roadmap M1 exit grep).

```bash
grep -n "get_posts" blog_engine/core/doctor.py
```
Expected: exactly one call site.

```bash
grep -n "create_post\|update_post\|upload_media\|InventoryManager\|DBManager\|mkdir" blog_engine/core/doctor.py
```
Expected: no output.

```bash
grep -n "doctor" docs/ROADMAP.md
```
Expected: the M1.2 entry present; then `grep -n "id: M1.2" -A8 docs/ROADMAP.md` shows `status: done`.

```bash
git diff --stat origin/main
```
Expected: only `blog_engine/core/doctor.py` (new), `blog_engine/cli.py`, `tests/test_doctor.py`
(new), `.env.example`, `README.md`, `docs/ROADMAP.md` (1 line).

## 6. Rules for this run

- This run is **NON-INTERACTIVE**. Any tool call needing confirmation is rejected and the run
  ends mid-task. Do not install, download or fetch anything. Do not read outside this working
  directory, and do not use a search, memory or web tool.
- The test command is exactly `uv run pytest -q <file>` or `uv run pytest -q` (never bare
  `python`). Never run the real `doctor` command: it would load `.env` and call WordPress.
- Never use `git -C` or `git -c`; run git from the worktree.
- Create no scratch or debug files. If one is unavoidable it goes under `.devin-scratch/`.
- Work only on your `directive/<slug>` branch. **Never commit to main, never push, never deploy.**
- Set this directive's Status row to `Review` when finished, or write the blocker in it if you stop
  partway. Do not mark it Done.
- If a tool call is genuinely blocked, stop and write why in the Status row instead of trying
  another way around it.

## 7. Completion criteria

- [ ] `doctor` command exists, backed by `blog_engine/core/doctor.py`, exits 0 only when all checks OK.
- [ ] Checks: four env names (names only), WordPress reachable via one read-only GET, inventory
      present and non-empty. No secret value is ever printed.
- [ ] `tests/test_doctor.py` passes with the network mocked; `uv run pytest -q` is `281 + N passed`.
- [ ] `.env.example` lists every variable name the code reads; README has the usage line.
- [ ] M1.2 `status: done` in `docs/ROADMAP.md`; no other roadmap line changed.
- [ ] `git diff --stat origin/main` shows only the six files listed above.

## 8. Report

Commit hash, before/after test counts, the exact line format of a passing and a failing run (from
the tests, never from a real run), and anything in 3.1 you had to interpret.

<!-- queue:start -->
## Queue

| Field | Value |
|---|---|
| Status | Draft |
| Assigned to | devin |
| Branch | - |
| Base branch | - |

**Status log**
- 2026-10-11 · robert-claude (authoring subagent) · none → Draft — authored on directive-authoring branch, not yet queued
<!-- queue:end -->
