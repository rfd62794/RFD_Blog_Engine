---
title: "How to check a time window across daylight saving time in Python"
excerpt: "Do window math on real instants with zoneinfo, never on wall-clock hours, and the two DST days stop being special cases. Examples from a calling-hours checker."
tags: [python, timezones, zoneinfo, testing, compliance]
categories: [How-to]
keyword: daylight saving time window check python
lane: client
status: draft
source: tcpa-hours library README (DST section) and tests, Nov 4 2026
---

To check whether a moment falls inside a local time window, convert the moment to the place's own time zone with `zoneinfo` and compare local times there. Never add or subtract fixed hour offsets. Done that way, the spring-forward and fall-back days need no special code at all, and Arizona and Hawaii stay on standard time automatically.

I learned this properly while writing a calling-hours checker, where "9 p.m. local" has to be right every day of the year.

## The bug everyone writes first

The first version of most window checks stores an offset per lead, something like "Eastern is UTC-5", and does:

```python
local_hour = (utc_now.hour - 5) % 24
allowed = 8 <= local_hour < 21
```

That is wrong for roughly eight months a year, because Eastern is UTC-4 during daylight time. It is also wrong for anywhere that doesn't observe DST, and it gets the minutes wrong for any zone that isn't on a whole hour.

## Use real instants and a real zone

```python
from datetime import datetime, time
from zoneinfo import ZoneInfo

def in_window(at: datetime, tz: str, start=time(8), end=time(21)) -> bool:
    if at.tzinfo is None:
        raise ValueError("pass a timezone-aware datetime")
    local = at.astimezone(ZoneInfo(tz))
    return start <= local.time() < end
```

Three details matter:

1. **Refuse naive datetimes.** A datetime with no zone is a bug waiting to happen, so raise instead of guessing.
2. **The end is exclusive.** 9:00:00 p.m. is outside an "until 9 p.m." window. Pick one reading and write a test for it.
3. **The zone name carries the rules.** `America/Phoenix` has no DST. `America/Puerto_Rico` has no DST. You don't write those exceptions; the time zone database already has them.

## Finding the next allowed time

The harder question is "when can I call next?". The tempting approach is to compute "tomorrow at 8 a.m." by adding 24 hours. On a DST transition day that lands at 7 or 9.

Build the candidate time in local terms instead, then convert back:

```python
from datetime import datetime, timedelta, timezone

def next_open(at, tz, start=time(8)):
    z = ZoneInfo(tz)
    local = at.astimezone(z)
    day = local.date()
    for _ in range(10):
        candidate = datetime.combine(day, start, tzinfo=z)
        if candidate > local:
            return candidate.astimezone(timezone.utc)
        day += timedelta(days=1)
    return None
```

When a lead has several possible zones, compute this for each and look for the earliest instant that is open in all of them. My library searches up to ten days ahead, which is enough to get past a holiday followed by a Sunday ban.

## When the law names a zone that isn't the local one

Mississippi's statute describes its window in "Central Standard Time". In summer the state is on Central Daylight Time. One reading is "local time". The other is "fixed UTC-6 all year". I check both and require both, which makes the effective summer window 9 a.m. to 8 p.m. local. That is the cautious reading, and the README says so in a section for things a lawyer should look at.

The general lesson: if a rule names a standard-time zone, decide whether it means the clock on the wall or a fixed offset, and write the decision down.

## Test the two days that matter

Whatever you build, write explicit tests for:

- the spring-forward Sunday, at the hour that doesn't exist;
- the fall-back Sunday, at the hour that happens twice;
- a zone with no DST next to a zone with it;
- the exact boundary second at the end of the window.

Those four tests catch almost every mistake I've made with time zones, and they run in milliseconds. On Windows, install the `tzdata` package so `zoneinfo` has a database to read.
