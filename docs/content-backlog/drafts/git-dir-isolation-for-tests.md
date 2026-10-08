---
title: "How to stop tests from touching your real git repo (GIT_DIR under hooks)"
excerpt: "Git hooks export GIT_DIR, so tests that shell out to git hit your real repo. Strip GIT_* variables in a test helper and in the hook runner."
tags: [git, pytest, testing, git-hooks, python, how-to]
categories: [How-to]
keyword: pytest git hook GIT_DIR isolation
status: draft
---

If your tests create a temporary git repository and run `git` inside it, they may be passing in your terminal and quietly dangerous in a git hook. Here is how to find out, and the small fix that stopped it for me.

The short answer: git sets `GIT_DIR` and related variables when it runs a hook. Any child process, including your test's `subprocess.run(["git", ...])`, inherits them and works on the repository git named, not the temp folder you passed as `cwd`. Remove every `GIT_*` variable from the environment before the tests run, and again for each git call the tests make.

## What you need

- Python tests that call `git` through `subprocess` (a fixture repo is the usual reason).
- A `pre-push` or `pre-commit` hook that runs the test suite.
- Ten minutes and a throwaway clone to try it on.

## Why it happens

When git runs a hook it exports variables that tell tools which repository they are in. `GIT_DIR` is the one that matters most. When a process has `GIT_DIR` set, git uses it and ignores the working directory. So this line in a test:

```python
subprocess.run(["git", "commit", "-m", "first"], cwd=tmp_path)
```

commits to the repository the hook is running for. In a plain shell there is no `GIT_DIR`, git discovers the repo from `cwd`, and everything is fine. That is why the tests pass in a normal terminal.

I learned this on 2026-09-22 when a pre-push hook ran a studio project's tests from an agent's worktree. They committed fixture commits named `first` and `second` onto the branch being pushed, one of them removing every tracked file, set `core.bare = true` in the shared git config, and wrote a test author into the repo's config. The incident is in the previous post. This one is the fix.

## Step 1: Write a regression test that fails first

Before changing anything, prove the problem. The directive I wrote said to write the test first and see it fail. The test sets `GIT_DIR` in the environment to a second temporary repo, runs the helper that your tests use to build a fixture, and asserts that the second repo gained **no commits and no config changes**.

If you skip this step you cannot tell whether your fix does anything. In my repo it went red, then green. The commit history has both, with the red commit first.

## Step 2: One helper that builds a clean environment

Put this in a shared test module. My version has these four jobs:

```python
def isolated_git_env(repo_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CEILING_DIRECTORIES"] = Path(repo_path).resolve().parent.as_posix()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@test.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@test.com"
    return env
```

1. **Drop every `GIT_*` variable** you inherited.
2. **Set `GIT_CEILING_DIRECTORIES`** to the temp repo's parent, so git can never walk up and find a real repository above the fixture.
3. **Set `GIT_CONFIG_NOSYSTEM=1`**, so machine-level config does not leak in.
4. **Supply identity through the environment**, not through `git config user.name`.

Then pass `env=isolated_git_env(repo_path)` to every `subprocess` call that runs git.

## Step 3: Never write config from a test

Replace every `git config user.name` and `git config user.email` call in tests with the four author and committer variables above. The test then writes to **no** config file. It was the config writes that kept biting me afterwards, with commits on main authored by `Test`.

Check that you got them all:

```
grep -rn "\"config\", \"user\." --include=test_*.py .
```

My directive's completion criterion was that this finds nothing.

## Step 4: Fix the runner too

The helper protects the tests. The hook's runner should not depend on it. In the script the hook calls, remove the variables before running anything:

```powershell
Get-ChildItem Env:GIT_* | Remove-Item
```

That is my PowerShell version, with a comment pointing at the incident directive. On a shell script, the equivalent is to unset them. I wanted two layers because neither one alone is enough: the runner fix does nothing for a test that spawns git from another entry point, and the helper does nothing for a test that forgot to use it.

## The result

The fix touched six files, 116 added lines and 33 removed. The studio test counts before and after were 4 failed, 101 passed, 9 skipped, then 4 failed, 102 passed, 9 skipped. The only difference was the new regression test. The four failures were already there and unrelated to this problem. It merged the same night, 22:46 on 2026-09-22.

## Common problems

**It may come back.** On 2026-09-23, starting at 11:34, commits authored `Test` showed up on my main again, about twelve hours after this fix merged. I have not established why. My guess is a branch that predates the fix and still runs the old tests, but I have not confirmed that. If you fix the tests, check your long-lived branches and watch the author names on main.

**Tests in other languages.** Anything that spawns `git`, such as a JavaScript test using `execSync`, inherits the same environment. The runner fix covers them. The helper only helps Python.

**Hooks that do not obviously run tests.** A formatter or a doc generator in a hook can call `git` too. Scrub the variables in the script that the hook calls.

## FAQ

**Does this only matter on Windows?** No. The variables are git's, not the operating system's. My incident was on Windows, and I have not tested other platforms.

**Is `GIT_CEILING_DIRECTORIES` needed if I remove `GIT_DIR`?** It is cheap insurance. Without it git may still discover a repository above your temp folder if the temp path sits inside one.

**Can I just not run tests in a hook?** You can. I wanted the net, so I fixed the nets.

<!-- fact-checked 2026-10-08: 14 claims confirmed, 1 corrected, 1 removed; remaining notes: 09-23 recurrence cause unverified; non-Windows behaviour untested -->
