---
title: "Opt-in anonymous telemetry for a small game with FastAPI and SQLite"
excerpt: "Ask first, send a random session id and a few events, store them in one SQLite file. How I added privacy-first telemetry to my game without an analytics service."
tags: [telemetry, fastapi, sqlite, privacy, gamedev]
categories: [How-to]
keyword: opt in game telemetry fastapi sqlite
lane: client
status: draft
source: rfd62794/VoidDrift ADR-014, rfd-telemetry/main.py, src/systems/telemetry (read Nov 4 2026)
---

You don't need an analytics platform to learn how people play your game. A consent prompt, a random session id, a handful of event types and a tiny FastAPI server writing to SQLite is enough for a solo developer. That's what I built for VoidDrift, and it runs on both Android and the web build with the same code.

## The rules I set first

Before writing code I wrote the decision down:

- **Opt-in, not opt-out.** The player is asked. Declining is a normal answer, and they can change their mind later.
- **No personal data.** No device ids, no IP addresses stored, nothing that follows a player across installs.
- **Self-hosted.** No third-party SDK, no account with an analytics company.
- **Small.** Session length, platform, game version, and a few milestones like first drone built and first ore refined.

## Consent as three states, not two

In the game, consent is an `Option<bool>`:

```rust
#[derive(Resource, Default, Clone, Copy)]
pub struct TelemetryConsent {
    pub opted_in: Option<bool>,
}
```

`None` means we haven't asked. `Some(false)` means they said no. `Some(true)` means yes. Treating "not asked yet" as its own state is what keeps the game from quietly assuming yes. The answer is saved with the rest of the save file, so it survives restarts.

## A session id that means nothing

Each session gets a fresh random UUID. It ties a session's events together and nothing else. A new session gets a new id.

## The server: one table

```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        session_id TEXT NOT NULL,
        client_version TEXT DEFAULT 'unknown',
        platform TEXT DEFAULT 'unknown',
        meta TEXT DEFAULT '{}',
        received_at TEXT NOT NULL
    )
""")
```

One `POST /v1/event` endpoint validates the payload with a Pydantic model and inserts a row. A `GET /health` endpoint lets me check it's up. SQLite runs in WAL mode so writes don't block reads while I'm looking at the data.

CORS only allows the origins the game is served from: the itch.io page, my own subdomain and localhost for testing. Anything else gets turned away by the browser.

## The most useful event wasn't a milestone

I added a "loop stall" event: if the player goes two minutes without the core loop moving, the game records it once. Milestones tell you what people did. A stall tells you where they got stuck, which is what I actually needed for the tutorial.

## Things I'd watch for

- Don't commit the database file to a public repo. Mine only ever held one test event, but it was there; put it in `.gitignore` before the first real player arrives.
- Version every event with the client version, so a spike can be traced to a build.
- Decide in advance how long you keep the data, and write it in your privacy note.

[ROBERT: confirm the telemetry server is live and which build first shipped the prompt before publishing.]
