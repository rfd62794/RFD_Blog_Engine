---
title: "How do I add a doctor command to a Python CLI tool?"
excerpt: "A doctor command runs read-only checks on your tool's setup and prints OK or MISSING with the exact command that fixes each one."
tags: [python, cli, developer-experience, setup, testing]
categories: [How-to]
keyword: python cli doctor command setup check
status: reviewed
---

A doctor command is a subcommand that checks whether your tool is set up correctly and tells you what to run if it is not. Write one small function per setup step that returns True or False, loop over them, print `OK` or `MISSING` plus the fix command for each, and exit with 0 only if every check passed. Nothing in it should change anything.

I added one to my YouTube pipeline after realizing that three one-time setup steps were the only things between me and using the tool every day. Nobody could see which of the three I had skipped, including me.

## What you need

- A Python CLI with subcommands. Mine uses `argparse`, with the logic kept out of the parser file.
- Setup steps you can test without side effects: a file exists, a config has an entry, a database has rows, a credential works.
- A fix command for each step, written out in full.

## Step 1: Turn each setup step into a one-line command

Before the doctor, make each step something you can run in one line. Mine became three:

- `setup desktop` registers the tool as a server in a desktop app's config file.
- `setup auth` signs in to Google once and saves a token.
- `setup sync` runs the first full sync of the channel's video list.

The doctor is only useful if its advice is a command someone can paste.

## Step 2: One check per step, returning a bool

```python
def check_config_registered(path) -> bool:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return False
    return "my-tool" in data.get("mcpServers", {})
```

Notice the broad `except` that returns False. A doctor's job is to report, so a missing file, a bad file and a permission error all just mean "not set up." A test should still catch a crash in the doctor itself.

My three checks are: the config has our entry, the saved token file exists *and* a single read-only API call with it succeeds, and the library table has at least one row.

## Step 3: A table, a loop and an exit code

```python
def run_doctor() -> int:
    checks = [
        ("Config registered", check_config_registered(CONFIG), "mytool setup desktop"),
        ("Token works",       check_token(),                  "mytool setup auth"),
        ("Library has rows",  check_library(),                "mytool setup sync"),
    ]
    all_ok = True
    for name, ok, fix in checks:
        all_ok = all_ok and ok
        print(f"{'OK' if ok else 'MISSING':<7} {name} -- fix: {fix}")
    return 0 if all_ok else 1
```

This is the shape of my real function, shortened. The output is one line per check. Return the number from `main()` so shell scripts can use `mytool doctor && mytool run`. I rewrote this snippet from the repo and did not run this exact shortened version.

## Step 4: Keep it safe

Three rules. The first is my own advice, and the other two are in my code:

1. **Read-only.** The doctor must never repair anything. A tool that fixes problems while claiming to only look is hard to trust.
2. **No secrets in the output.** It prints that a token works, never the token, and never client secrets.
3. **It can never start an interactive flow.** My sign-in check uses a function that only reads the saved token. It can never open a browser, and it cannot quietly succeed on some other credential found on the machine. A later commit added a test for that guard in place of skipping it, because my project has a rule of zero skipped tests.

## Step 5: Test each state with fakes

Never touch the real config, network or account in tests. For the doctor I wrote tests for: all three missing (it prints three fix commands), all three fine (exit code 0), a mix (exit code 1), and each check on its own with a temporary file. The setup test file has 21 tests, and my project notes record the suite going from 395 to 419 passing when the setup tools landed, then 420 after the token-guard test.

## Common problems

- **A slow check makes the doctor feel broken.** Keep each one to a single call. Mine does one API request.
- **Checks that depend on each other.** If the token check needs the config check first, say so in the output instead of guessing.
- **Fix commands that go stale.** I keep the command prefix in one constant so a rename changes it everywhere.
- **Windows paths.** Build the config path from the `APPDATA` environment variable and fall back to the home directory, as mine does.

## FAQ

**Is this the same as `brew doctor` or `flutter doctor`?** The idea is the same: check the environment, print what is wrong. Mine is much smaller because it only knows about one tool.

**Should the doctor fix problems automatically?** I say no. Print the command and let the person run it.

**How many checks should it have?** Mine has three, one per blocking setup step. A fourth check I would add is whether the tool's dependencies are installed. I have not built it.

**Where should the code live?** In its own module. My command-line file only parses arguments and calls it.

<!-- fact-checked 2026-10-08: 20 claims confirmed, 1 corrected, 0 removed; remaining notes: snippet is a shortened rewrite, stated as such -->
