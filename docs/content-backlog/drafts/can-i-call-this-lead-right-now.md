---
title: "Can I call this lead right now? How to check TCPA calling hours by state"
excerpt: "A calling-hours check should treat every location signal as a candidate and clear the call only if every candidate allows it. Here is how I built one."
tags: [tcpa, compliance, python, contactcenter, automation]
categories: [How-to]
keyword: tcpa calling hours by state
lane: client
status: draft
source: tcpa-hours library (README, rules data, 52 passing tests, Nov 4 2026)
---

The federal rule is short: telemarketing calls are allowed from 8 a.m. to 9 p.m. at the called person's location. The hard part is "the called person's location". A good calling-hours check treats every location clue you have as a possible place the person could be, and clears the call only when it is allowed in all of them.

I built a small Python library around that idea this week. It answers one question: can I call this lead right now, and if not, when?

> Not legal advice. This is an engineering aid. Have counsel review any rule data before you rely on it.

## The question looks easy

Most dialers and CRMs give you a time zone per lead and a window per campaign. That covers the federal rule on a normal day. It falls apart in four places:

- **The lead's location is a guess.** An area code, a ZIP code and a state field can all point at different places, because numbers move with people.
- **Some states are stricter than federal.** Florida, Massachusetts, Maryland, Oklahoma, Oregon, Washington and Wyoming stop at 8 p.m. Connecticut starts at 9 a.m. Kentucky starts at 10.
- **Some states care about the day.** Alabama, Louisiana, Mississippi, Pennsylvania, Rhode Island and Utah restrict Sundays, and several also restrict holidays.
- **The clock moves twice a year.** Daylight saving time breaks any window math done on wall-clock hours.

## Treat every signal as a candidate

The design choice that made everything else simple: every input becomes a candidate location, and the call is cleared only if every candidate allows it.

- A phone number gives every time zone used anywhere in that area code. A Florida panhandle 850 number has to be inside the window in both Central and Eastern time.
- A ZIP code gives one state and one zone.
- A state alone gives every zone in that state.
- A time zone alone gives every state that uses it, and the strictest one wins.

So a 212 number with a California ZIP has to satisfy New York and California. That sounds overly cautious until you remember what a wrong call costs compared to a call made an hour later.

## What the check returns

```python
from datetime import datetime, timezone
from tcpa_hours import can_call

r = can_call(datetime(2026, 11, 4, 13, 30, tzinfo=timezone.utc), phone="850-555-0100")
r.allowed        # False
r.reasons        # why, in plain words, per candidate
r.next_allowed   # the earliest UTC time every candidate allows the call
r.notes          # things it can't enforce, like Florida's frequency cap
```

`next_allowed` turned out to be the most useful field. A dialer doesn't just need a no. It needs to know when to put the lead back in the queue.

There is also a command line version that exits 0 for allowed and 1 for not allowed, so it can sit in front of a script:

```bash
python -m tcpa_hours --phone 208-555-0100 --zip 83814 --at 2026-11-04T15:30Z
```

## Things it deliberately does not do

I wrote these down as plainly as the features, because a compliance tool that overstates itself is worse than none.

- It does not model exemptions such as prior express consent or an existing business relationship. Every call is treated as a covered solicitation.
- It reports frequency caps (Florida, Maryland, Oklahoma and Oregon cap calls at three per 24 hours) but does not enforce them, because that depends on your call log.
- It does not check Do Not Call lists, consent records or reassigned numbers.
- Debt collection calls follow different rules and are out of scope.
- Toll-free numbers, unknown ZIPs and non-US area codes produce no candidates, and then the call is never cleared.

## Every rule carries its source

Each state rule is a row of plain JSON with the citation, the source link, the date I retrieved it, and whether it came from an official source. Rules I could only confirm from unofficial copies are flagged as unverified and listed in the README, so a lawyer knows exactly where to look first.

Some readings genuinely need a lawyer. Mississippi's statute says "Central Standard Time", so during daylight time the cautious window is 9 a.m. to 8 p.m. local. Louisiana's emergency ban doesn't limit itself to affected parishes in its text. Pennsylvania changed its rule on October 19, 2026. Those go in a "worth a lawyer's look" section instead of being quietly decided in code.

## What I'd tell an operations manager

If your team checks calling hours by campaign and lead time zone only, you are probably fine on most calls and exposed on a few predictable ones: split area codes, leads who moved, Sundays in a handful of states, and the two DST weekends. Those are exactly the cases worth automating, because nobody catches them by hand at 8:55 p.m.

[ROBERT: decide whether to link a public repo here once the library has a license and is published.]
