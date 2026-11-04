---
title: "Safe defaults for a self-hosted MCP server: bind to localhost and fail closed"
excerpt: "A home-lab MCP server should listen on localhost by default and refuse every request when no token is set. Two settings I now put in every server I build."
tags: [mcp, security, python, selfhosted, fastapi]
categories: [How-to]
keyword: secure self-hosted mcp server
lane: client
status: draft
source: rfd62794/ClineMCP and rfd62794/OpenAgentMCP READMEs; RFD_Model_Router audit (Sep 23 2026)
---

If you run your own MCP server over the network, give it two defaults: listen only on `127.0.0.1` unless you deliberately set another address, and reject every request when no auth token is configured. Most of my early servers did neither. An audit of one of them is what changed my mind.

## How I found out

In September I had an agent audit a small model router I'd built months earlier. Among the findings: both of its listeners bound to every network interface, there was no authentication, and the default route went to a paid model. Anyone who could reach the port could run calls on my bill. Nothing had gone wrong. Nothing in the code stopped it either.

That's the normal state of a weekend server. You start it on `0.0.0.0` so another machine on your network can reach it, you mean to add auth later, and later never comes.

## Default 1: bind to localhost

A server that listens on `127.0.0.1` can only be reached from the same machine. That's the right default for anything you're running under Claude Desktop or another local client.

```python
import os
host = os.environ.get("MCP_HOST", "127.0.0.1")
port = int(os.environ.get("MCP_PORT", "8003"))
```

When a second machine does need it, set `MCP_HOST` to that machine's specific private address (a LAN or VPN address) rather than `0.0.0.0`. Make the wide-open choice something you type, not something you inherit.

My OpenAgentMCP server now says this in its README right next to the start command: it binds to `127.0.0.1`, and you change it only if remote clients need access.

## Default 2: no token means no access

The second mistake is subtler. Many servers check a bearer token if one is configured, and skip the check if one isn't. That means a missing environment variable silently turns auth off.

Flip it. With no token configured, every request gets a 401. Simplified from my real code:

```python
TOKEN = os.environ.get("CLINEMCP_AUTH_TOKEN")
ALLOW_NO_AUTH = os.environ.get("CLINEMCP_ALLOW_NO_AUTH") == "1"

def authorized(header: str | None) -> bool:
    if not TOKEN:
        return ALLOW_NO_AUTH
    return header == f"Bearer {TOKEN}"
```

For development there's an explicit escape hatch, `CLINEMCP_ALLOW_NO_AUTH=1`. It has to be set on purpose, and it's obvious in any config file that it's on. The server also prints a warning at startup saying auth is off and why, so you can't miss it. That's the pattern in my ClineMCP server, which runs a coding agent's sessions and absolutely should not be reachable by accident.

## A short checklist

1. Default host `127.0.0.1`. Wider access is an explicit setting.
2. No token configured means 401 for every request.
3. An unauthenticated mode exists only behind its own clearly named flag.
4. Tokens come from environment variables or a secret store, never from a committed config file.
5. Log who called what, without logging the token.
6. Paid model routes are not the default route.

None of this is advanced security. It's just making the safe setup the one you get when you forget to configure something, because you will forget.
