---
title: "The night a test deleted my repository"
excerpt: "On 2026-09-22 a pre-push hook ran tests that committed to my real repo. I skipped the hook and merged a pull request that deleted 3,823 files."
tags: [git, testing, incident, ai-agents, post-mortem, solo-developer]
categories: [Build in public]
keyword: git hook test deleted repository
status: draft
---

For about eight minutes on the evening of 2026-09-22, the main branch of my game studio repository held one file. It had held 3,823. Nobody hacked anything. A set of tests I had trusted for months did exactly what they were written to do, in the wrong repository, and then I merged the result.

I am writing this down because I am the person who typed the two commands that made it worse, and the lesson is not the one I expected.

## What I was doing

An AI agent had finished a task on its own branch: a small glossary panel for the studio. It was working in a separate git worktree, as all my agents do. At 21:49 it moved its task to Review. I pushed the branch.

The repo has a pre-push hook. The hook runs a check script, which runs the Python and TypeScript tests. I had written that setup myself so nothing red could reach GitHub. That is a normal thing to do.

## What the evidence shows

I reconstructed the timeline from git itself, using the commit timestamps.

- **21:53:20.** A commit named `first` appears on the branch, authored by `Test`. Its stats: 3,824 files changed, 1 insertion, 750,130 deletions. It deletes the whole tree except one file. A second commit named `second` follows one second later.
- **21:55:37.** Another `first` and `second` pair appears. [VERIFY: why a second pair; I assume a second run of the same tests, but I did not confirm.]
- **22:01:16.** I merge pull request #10 into main. The branch tip is the glossary work plus these commits.
- **22:09:01.** A commit named "Restore main: undo test-fixture commits that wiped the tree in PR #10" puts back the 3,824 files: 750,130 insertions. Sixteen minutes after the first bad commit, seven minutes after my merge, the tree is back.

The restore commit is also authored `Test`. That is the second symptom, and it tells you the real cause.

## What actually happened

The tests that create temporary git repositories do a normal thing. They make a folder, run `git init`, make two commits named `first` and `second` to set up a fixture, and compare. Run from a normal shell, that is harmless.

A git hook is not a normal shell. When git runs a hook, it puts variables such as `GIT_DIR` into the environment, telling every child process which repository it is working in. The tests spawned `git` as a child process. It inherited those variables. So `git init` and `git commit`, which should have acted on the temp folder, acted on my real repository. So the fixture's `first` commit, which was meant to build a throwaway repo from scratch, was committed to the live branch instead. [VERIFY: exactly how that commit came to delete every file; I inferred the mechanism from the directive and did not reproduce it.]

The directive I wrote afterwards lists three effects:

1. Fixture commits landed on the branch being pushed, one of which deletes every file.
2. The shared git config got `core.bare = true`, which breaks the main checkout.
3. The config got `user.name = Test` and `user.email = test@test.com`, so later real commits were authored "Test".

The tests were correct. The environment around them was not.

## My two mistakes

I pushed with `--no-verify`, skipping the hook once it started misbehaving. That got the branch, bad commits included, to GitHub. [VERIFY: the `--no-verify` push comes from my own incident note, not from git history.]

Then I merged pull request #10 without listing the commits on the branch first. Had I run `git log origin/main..HEAD` I would have seen commits named `first` and `second` and authored by `Test`. Anything that looks like that is a stop sign. I knew it later. I did not know it at 22:01.

I take no comfort from the fact that the agent did nothing wrong. It was a clean task. The failure was in the shared environment, and in me.

## The fix, and how I know it works

The same night, at 22:21, I queued a task to fix it. It was done by 22:34 and merged at 22:46. The details are in the next post in this series. The short version: every test that runs `git` now gets a scrubbed environment with no `GIT_*` variables, author identity is set by environment instead of by writing git config, and the check script removes all `GIT_*` variables before running the tests. A regression test sets `GIT_DIR` to a second repo and asserts that repo gains no commits.

The first fix was not enough. On 2026-09-23 at 11:39 a commit authored `Test` appeared on main again, a queue-status commit. My notes say the cause was another agent branch based on a version of main from before the fix. Its old tests ran unscrubbed and wrote `Test` into the config. [VERIFY: the root cause is from my notes and a commit author, not something I reproduced.] A fix in the code does not help a branch that does not have it.

## What I do now

1. **List the commits before every push and merge.** `git log origin/main..HEAD`, read the subjects. Do it after the hook, not before.
2. **Treat a `Test` author as an alarm.** It means a test touched a real repository.
3. **Never use `--no-verify` to get past something I do not understand.**
4. **Keep a restore path.** The restore commit is, per its own record, the tree of the glossary branch tip from before the wipe, and git still had it. History does not disappear on a merge.

The real lesson: a safety net can be the thing that does the harm. The hook was there to protect main, and its environment made the tests dangerous. I check what a protection does when it runs, not only whether it ran.
