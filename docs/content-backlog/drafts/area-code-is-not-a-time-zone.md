---
title: "An area code is not a time zone"
excerpt: "Looking up an area code's time zone with one default zone misses split area codes. Here is how I map every zone an area code really covers."
tags: [python, timezones, telephony, data, contactcenter]
categories: [How-to]
keyword: area code time zone lookup
lane: client
status: draft
source: tcpa-hours library location.py (_npa_union), checked Nov 4 2026
---

If you look up a phone number's time zone by area code and take the first answer, some of your leads are in a different zone than you think. An area code can span two or three zones, and the default a library returns for the area code can leave out the zone most of its numbers actually use. The safe answer is the full set of zones under that area code.

I ran into this while building a calling-hours checker.

## Where it goes wrong

Phone metadata is usually organized by prefix. The longer the prefix, the more specific the answer. Google's libphonenumber, which most phone tools use underneath, ships a time zone mapping with entries at different lengths: some for a whole area code, many more for an area code plus exchange.

The trap is the short entry. When I compared the area-code-level entry with the exchange-level entries underneath it, some didn't line up. South Dakota's 605 is the example I wrote down: its exchanges map to Central, Mountain, and North Dakota Center time, and an area-code-only lookup can return fewer zones than that.

A few more examples from the same data:

- **850, Florida panhandle:** Central and Eastern.
- **208, Idaho:** Pacific, Mountain and Boise time.
- **605, South Dakota:** Central, Mountain and North Dakota Center.

If your dialer stores one zone per lead and that zone came from a short-prefix lookup, the lead is off by an hour on some fraction of those numbers. For most uses that is a rounding error. For a calling window it is the whole question.

## The fix: union every zone under the area code

The approach I settled on is boring on purpose. Read every prefix entry, group by the first three digits, and keep the union of every zone seen:

```python
def npa_union(phone_table):
    zones, states = {}, {}
    for prefix, (tzs, state) in phone_table.items():
        npa = prefix[:3]
        zones.setdefault(npa, set()).update(tzs)
        if state:
            states.setdefault(npa, state)
    return {npa: (frozenset(z), states.get(npa, "")) for npa, z in zones.items()}
```

Now an area code answers "these are all the places this number could be". A call has to be allowed in every one of them. That is cautious, and it is supposed to be.

There is an opt-in for less caution: narrow by the full six-digit prefix (area code plus exchange) when the data has an entry for it. That is closer to where the number was issued. It is still not where the person lives.

## Why not just ask for the exact zone?

Because there isn't one. A phone number tells you where a number was assigned. It does not tell you where its owner sleeps. People keep their numbers when they move, and that is most of why area codes stopped meaning much.

So every location signal is a candidate, never an answer:

| Signal | What it gives you |
|---|---|
| Area code | Every zone used under it |
| Area code + exchange | Usually one zone, sometimes two |
| ZIP code | One state, one zone, as of when the ZIP data was built |
| State field | Every zone in that state |
| Time zone field | Every state that uses that zone |

When signals disagree, you keep all the candidates. A 212 number with a California ZIP is probably someone who moved west, but "probably" isn't a compliance standard.

## Things to watch in the data itself

- **Non-geographic numbers.** Toll-free and similar area codes have no location at all. Return no candidates, and treat no candidates as "don't call", not "call anytime".
- **Data age.** The ZIP data I used was last updated in October 2021. ZIPs get added and split. Write the data date into your README so nobody assumes it is current.
- **Licenses.** libphonenumber is Apache 2.0 and the ZIP data was MIT. Keep the notices with the bundled files.

## The rule of thumb

If a number can be in more than one place, check every place. Store the set, not the guess.
