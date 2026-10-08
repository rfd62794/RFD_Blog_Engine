---
title: "How do I add my own MCP server to Claude Desktop?"
excerpt: "Add one entry under mcpServers in Claude Desktop's config file, back the file up first, then restart the app. Here is the entry and a script for it."
tags: [mcp, claude-desktop, python, configuration, automation]
categories: [How-to]
keyword: add mcp server claude desktop
status: draft
---

Open Claude Desktop's config file, add an entry for your server under `mcpServers` with the command that starts it, save, and restart the app. The risky part is the file itself, which holds every server you already have, so copy it before you touch it and merge your entry in rather than replacing the file.

I run at least two MCP servers of my own, a YouTube one and a blog one, and I got tired of hand-editing this file. So I had a command built, by an AI agent under my direction, that does the edit safely. This post is the manual steps plus what that command does. Everything is on Windows.

## What you need

- Claude Desktop installed and run at least once.
- An MCP server you can start from a command line. Mine speaks over stdio, which is the way Claude Desktop launches servers.
- A command that works from any folder: an absolute path or a tool that accepts one.

## Step 1: Find the config file

On Windows it is `%APPDATA%\Claude\claude_desktop_config.json`. My code builds that path from the `APPDATA` variable and falls back to the home directory plus `AppData\Roaming` if the variable is missing. [VERIFY: the path on macOS and for the Store version of the app; I only use the Windows file.]

## Step 2: Back it up

Copy the file with a timestamp before any edit:

```
claude_desktop_config.json.bak-20261007-141500
```

My command does this automatically in the same folder and prints the backup path. It only backs up when the file exists, and it skips the backup on a dry run.

## Step 3: Add the entry

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "--no-sync", "--directory", "C:\path\to\project",
               "python", "-m", "mypackage.mcp_server"]
    }
  }
}
```

The key (`my-server`) is the name the app shows. If the file already has other servers, keep them and add yours beside them. Valid JSON matters: a stray trailing comma will break every server at once.

I use `uv run --directory <repo>` because it works no matter what folder the app starts in, and it uses the project's own Python. The older example inside my server's docstring points at a hard-coded Python 3.14 executable, which bypasses the project's own uv-managed environment. I have left that docstring as it is and the script now writes the `uv` form. [VERIFY: fix the stale docstring before anyone copies it]

## Step 4: Restart Claude Desktop

Closing the window may not be enough, so quit the app fully and reopen it. My command prints "Restart Claude Desktop to load the server." because I kept forgetting. [VERIFY: whether closing to the tray is enough on your version.]

## What my script does that a text editor does not

The brief for that command asked for the tests first. They describe the behavior well:

- With another server already present, it adds ours and leaves the other one unchanged.
- With no file at all, it creates one containing only our entry.
- With invalid JSON, it prints "File left untouched" and exits with code 1 rather than guess.
- With `--dry-run`, it prints the entry it would write and changes nothing.
- Running it twice leaves exactly one entry.

That last one is the behavior to copy if you script this. Use the server's name as a dictionary key and assigning twice is harmless.

## The server side, briefly

Mine uses the low-level `Server` class from the `mcp` Python package, with a list-tools handler, a call-tool handler and `stdio_server()`. The project pins `mcp>=1.29.0,<2` so a major release cannot arrive unannounced. A server like this talks to the app through standard input and output, so do not print debug text to stdout. Use logging. [VERIFY: confirm that nothing in my server writes to stdout.]

## Common problems

- **The server does not appear.** The usual causes are invalid JSON, the app was not fully restarted, or the command is not found. Run the exact command from a terminal first.
- **It appears but the tools fail.** Check that the working directory is right. This is why I pass `--directory`.
- **Another tool was overwritten.** This is the reason for the backup. Restore it by copying the `.bak` file over the original.
- **A docstring says one thing and the code another.** Mine claims 24 tools. A count of `Tool(` entries in the file gives 27. [VERIFY: count the registered tools at runtime.]

## FAQ

**Can I have several servers?** Yes, one entry each, with different keys. I run two.

**Do I need uv?** No. You can point `command` at your project's Python executable and set `cwd`, as my blog server's example config does.

**Is it safe to let Claude edit this file?** I would not without a backup and a dry run. My command refuses to touch a file it cannot parse.

**How do I know it is set up?** My project has a `doctor` command that checks whether our entry is present in the file and prints the fix if it is missing.
