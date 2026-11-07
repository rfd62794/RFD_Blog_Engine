---
title: "Which states ban telemarketing calls on holidays, and what counts as a holiday"
excerpt: "Several states ban sales calls on holidays or Sundays but rarely list the holidays. How I handled it: the 11 federal holidays on both the actual and observed date, plus state extras."
tags: [tcpa, compliance, telemarketing, contactcenter, python]
categories: [How-to]
keyword: telemarketing holiday calling restrictions by state
lane: client
status: draft
source: tcpa-hours library README and states.json (retrieved Nov 4 2026)
---

Alabama, Louisiana, Pennsylvania, Rhode Island and Utah restrict telemarketing calls on holidays, and several states also limit Sunday calls. The catch is that most of these laws don't list which holidays they mean. A safe engineering default is to block the 11 federal holidays on both the actual date and the observed date, and add each state's own holidays on top.

> Not legal advice. Rules change and have exemptions. Have counsel review before relying on any of this.

## Where holidays and Sundays come in

From the rule table in my calling-hours library (each rule has its citation and retrieval date in the source data):

- **Alabama:** no Sundays or holidays; otherwise 8 a.m. to 8 p.m.
- **Louisiana:** no Sundays or state holidays; otherwise 8 a.m. to 8 p.m.
- **Mississippi:** no Sundays; otherwise 8 a.m. to 8 p.m.
- **Pennsylvania:** no Sundays or holidays; 9 a.m. to 7 p.m., since October 19, 2026.
- **Rhode Island:** weekdays 9 to 6, Saturday 10 to 5, no Sundays or holidays.
- **Texas:** Sunday noon to 9 p.m.; other days 9 to 9.
- **Utah:** no Sundays or holidays.
- **Nebraska**, for autodialed calls only: Sundays and holidays 1 p.m. to 9 p.m.

Federal rules allow 8 a.m. to 9 p.m. every day, so the state rule is what bites on these days.

## The "which holiday" problem

A statute that bans calls "on a legal holiday" leaves you to decide what a legal holiday is. Options:

1. **The 11 federal holidays.** Easy to compute, and covered everywhere.
2. **The state's own holiday list.** More accurate, and different in every state. Alabama, for example, has days like Mardi Gras and Confederate Memorial Day that aren't federal.
3. **Both.** The cautious answer.

My library blocks the federal 11 by default and takes an `extra_holidays` list for state-only days, so the state's own calendar can be added without changing code.

## Actual date or observed date?

When a holiday falls on a weekend, it's observed on the nearest weekday. July 4 on a Saturday is observed Friday, July 3. Which day does the ban apply to?

The text usually doesn't say. Blocking both is the safe reading, so that's what the library does. You lose one calling day a few times a year. That's cheap compared to the alternative.

## How to put this into a dialing process

- **Keep holidays as data.** A dated list per state, with a note on where each came from, reviewed once a year.
- **Check the called party's state, not yours.** And when you're not sure where they are, check every state they might be in.
- **Load the year ahead in December.** Observed dates shift every year.
- **Use the called party's date, not your server's.** Servers often run on UTC, where it's already tomorrow by 7 or 8 p.m. Eastern. Compute the holiday check from the local date where the person is.

If you schedule outbound campaigns by hand, this is a good place to add a single automated check. People remember Christmas. They don't remember that a state's own holiday is next Tuesday.
