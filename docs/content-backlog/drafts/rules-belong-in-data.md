---
title: "I put 52 jurisdictions' calling rules in a JSON file instead of code"
excerpt: "Keeping state rules as data, each row with a citation, a retrieval date and a verified flag, made a compliance library reviewable by someone who can't read Python."
tags: [python, compliance, data, design, buildinpublic]
categories: [Build in public]
keyword: rules as data compliance
lane: dev
status: draft
source: tcpa-hours library data/rules/states.json and SOURCES.md, Nov 4 2026
---

The first time I sketched my calling-hours library, every state was an `if` statement. Florida stops at 8. Connecticut starts at 9. Texas has a Sunday window. It would have worked, and nobody but me could ever have checked it.

So I moved every rule into one JSON file, and the code became a small engine that reads it.

## What a row looks like

Each of the 50 states, plus DC and Puerto Rico, is one object. The fields that matter:

- `jurisdiction` and `name`
- `windows`: the allowed hours, by day type, or nothing if the state adds no hours of its own
- `holidays_banned`, `emergency_banned`, and a `frequency_cap` if there is one
- `citation`: the statute section
- `source_url`: where I read it
- `retrieved`: the date I read it
- `source_type`: official or secondary
- `verified`: true only if I read the official text
- `notes`: anything odd, in plain English

The Alaska row is a good example of why the boring fields matter. Alaska has no calling-hours rule beyond the federal one. The row says that, names the two statute sections I checked, says I read them from an unofficial copy because the official site wouldn't load for me, and marks the row unverified.

"No rule" is a claim too. It deserves a source as much as "8 a.m. to 8 p.m." does.

## Why this was worth the extra effort

**A lawyer can review it.** Nobody should trust a compliance tool written by one person in a week. The useful thing I can do is make it cheap to check. A generated table lists every rule with its citation and link, and a reviewer can work down it without opening a single `.py` file.

**Unverified rules are visible.** Nine rows came from unofficial copies or were "no rule found" results I couldn't confirm. They are applied by default because skipping them would be less safe, but there is a switch to exclude them, and the result tells you when it did.

**Changes are diffs.** Pennsylvania changed its rule on October 19, 2026. That was a change to one row, and the commit shows exactly what moved. In code it would have been buried in a function.

**The engine stays small.** It knows about windows, days, holidays and candidates. It doesn't know about Kentucky.

## What the data can't say

Some rules don't fit a schema. Michigan's 9 a.m. start lives in a statute about harassing calls. New York's emergency ban applies by county or town. Mississippi names "Central Standard Time". Those got a `notes` field and a "readings worth a lawyer's look" section in the README, rather than a clever field that pretends the ambiguity isn't there.

There is also one honest gap: the rules aren't versioned by date yet. Pennsylvania's new rule applies even if you ask about a date before October 19. I wrote that in the README's "what it does not do" list.

## The pattern I'm keeping

This is the same lesson I keep relearning in my other projects: when something is going to be argued about, store it as data with its receipt attached. Code is for the part that doesn't change when the law does.

If I were starting again I'd write the schema first and the engine second.
