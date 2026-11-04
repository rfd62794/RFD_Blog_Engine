---
title: "How to get JSON logs in Python with no dependencies"
excerpt: "One JSON object per line, UTC timestamps, a service name and rotation, using only the standard library. The small logging package I published to PyPI."
tags: [python, logging, json, pypi, observability]
categories: [How-to]
keyword: python json logging no dependencies
lane: client
status: draft
source: rfd62794/RFD_Logging README and package source (v0.1.3, read Nov 4 2026)
---

You can get structured JSON logs in Python with nothing but the standard library: a custom `logging.Formatter` that writes one JSON object per line, a rotating file handler, and a stream handler for stdout. I packaged mine as `rfd-logging` on PyPI so every one of my small services logs the same way.

## Why bother

I had half a dozen services, each logging differently. Some printed. Some used plain `logging` text. When something broke at 2 a.m. on a machine running scheduled jobs, I was grepping different formats across different folders.

JSON lines fix that. Every line is one event. Every event has the same fields. Any tool, or a ten-line Python script, can read them.

## What one line looks like

```json
{"timestamp": "2026-06-21T20:38:33.105Z", "level": "ERROR", "service": "rfd-collectors", "message": "Database unreachable", "extra": {"host": "db.local"}, "request_id": null, "error": "Connection refused"}
```

The fields are fixed: `timestamp` (UTC with milliseconds), `level`, `service`, `message`, `extra`, `request_id`. `error` and `traceback` appear only when there's something to put in them.

## Using it

```python
from rfd_logging import get_logger

logger = get_logger("my-service", log_dir="logs")
logger.info("Request received", extra={"endpoint": "/api/data", "request_id": "req-abc123"})

try:
    1 / 0
except ZeroDivisionError:
    logger.exception("Unhandled error during processing")
```

## The details that took longer than the formatter

**Idempotent setup.** Calling `get_logger` twice with the same name must not add a second set of handlers, or every line gets written twice. The function returns the cached logger on repeat calls.

**Rotation.** Each service writes to its own file, rotated at 10 MB with five backups. Without rotation, a chatty service will eventually fill a disk.

**Stdout too.** Every line also goes to stdout, because on Windows I run services under NSSM, which captures stdout to its own log. Both are useful.

**Level from the environment.** `RFD_LOG_LEVEL=DEBUG` turns on debug output without a code change. It's read when the logger is first created, not at import time, so setting it in a service wrapper works.

**Redaction.** There's a small redaction module so that token-shaped values don't end up in a log file. Logs get copied, pasted into chats and attached to bug reports. Assume yours will be.

The whole package is about 400 lines including timing and test helpers, and it imports only `logging`, `json`, `datetime`, `pathlib` and `os`.

## Should you publish yours?

Probably not, unless you have several projects of your own that need it. The value isn't the code, which is small. It's that every service I write now starts with the same two lines, and every log I read looks the same.

```bash
pip install rfd-logging
```
