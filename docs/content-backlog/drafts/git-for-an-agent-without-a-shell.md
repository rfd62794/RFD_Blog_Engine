---
title: "I gave my AI agents git without giving them a shell"
excerpt: "An MCP server with 37 named git and GitHub tools, no shell passthrough, no force push, and a confirmation gate on anything that can't be taken back."
tags: [mcp, git, github, aiagents, security]
categories: [Build in public]
keyword: mcp server git tools ai agent
lane: dev
status: draft
source: rfd62794/RFDRepoMan README, ADR-001, repoman/gate.py, docs/SECRETS_SCAN.md (read Nov 4 2026)
---

Coding agents need git. They need to make branches, push them, open pull requests and check CI. The easy way to give them that is a terminal. I didn't want to, so in July I built RFDRepoMan: an MCP server where every git and GitHub action is its own named tool, and nothing broader exists.

## The rule that shaped everything

The first decision record says it in one line: the server will never expose a generic shell, command, script or subprocess tool. No function takes a raw command string. No tool glues caller text into a command.

That sounds limiting, and it is. That's the point. When an agent needs something the server can't do, the answer is a deliberate new tool with typed parameters and tests, not a way to type whatever it wants.

## What's in the box

There are 37 tools in five groups:

- **Local git:** fetch, status, pull, commit, create branch, checkout, push, merge.
- **GitHub:** pull requests (create, merge, close, comment, request reviews), forks, branches, issues, milestones, project items.
- **CI:** workflow runs, latest status for a branch, coverage, branch protection.
- **Verification:** read a repo's state file, verify its test floor, check the working tree is clean, record a manual proof.
- **Setup:** build a GitHub fine-grained token page with the minimum permissions already filled in, and reconcile status across accounts.

What's missing on purpose: force push. It isn't behind a flag. It isn't there.

## The confirmation gate

Six actions are consequential: push, merge, merge a pull request, create a pull request, change a repo's visibility, and delete a remote branch. The gate for them is about as small as code gets:

```python
CONSEQUENTIAL_ACTIONS = frozenset({"push", "merge", "merge_pr", "create_pr",
                                   "set_visibility", "delete_remote_branch"})

def require_confirmation(action, confirmed):
    if action not in CONSEQUENTIAL_ACTIONS:
        raise ValueError("Unknown consequential action")
    if not confirmed:
        return {"refused": f"{action} requires confirmed=True"}
    return None
```

An agent has to pass `confirmed=True` on purpose. It isn't strong security on its own, since the agent can set the flag. What it does is make the dangerous call look different from the safe one in every log, transcript and test, and force a decision at the moment it matters. Paired with a rule in my directives that only I approve merges, it was enough.

## Policy per repo

A repo can declare a small policy in its state file: require CI to pass, a minimum coverage, protected branches. Merges that fail the policy are refused. Overriding it takes `override_policy=True` and a written reason, and the override is recorded as an audit event. I wanted bypassing the rule to be possible and loud.

## Credentials stay out of the conversation

Tokens come from environment variables, one per account. They are never tool arguments and never files in a repo. The GitHub CLI fallback is off unless switched on, and its logs redact anything shaped like a token. Before I made the repo public, I ran a full-history secret scan and committed the raw output to the docs.

## Was it worth it?

The tools are boring to write, and there are a lot of them. But every action is testable: the action, its parameter shape, whether it needs confirmation, and how it interacts with policy. The tests check exactly that. And when something went wrong in a long agent run, the log said "merge_pr refused: requires confirmed=True" instead of a shell transcript I'd have to read line by line.

If you're wiring agents into your repos, start with the smallest set of named actions you actually need. Add tools when an agent hits a wall. You'll end up with fewer than you expect, and every one of them will be one you chose.
