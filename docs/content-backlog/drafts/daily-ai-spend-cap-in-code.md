---
title: "How to put a daily spending cap on AI API calls in Python"
excerpt: "Log every call's cost to SQLite, sum today's spend per provider, and skip that provider when the cap is reached. The small ledger I used, and the two gaps I'd close."
tags: [python, llm, sqlite, costcontrol, aiagents]
categories: [How-to]
keyword: daily budget cap llm api python
lane: client
status: draft
source: rfd62794/DuggerBot duggerbot/router/ledger.py and router.py (read Nov 4 2026)
---

The simplest reliable spending cap for AI API calls is a ledger: record the cost of every call in a small SQLite table, add up today's spend for a provider before each call, and refuse or reroute when the total would pass your limit. I put one in a personal agent project with a cap of $0.25 a day on the paid model, and the free and local models picked up everything else.

## The table

```sql
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    called_at TEXT NOT NULL,
    date TEXT NOT NULL
);
```

Storing the day as its own column makes "spend today" a cheap query instead of date math on a timestamp.

## The check

```python
async def check_budget(self, provider, daily_cap_usd, estimated_cost):
    today_cost = await self.get_today_cost(provider)
    if today_cost + estimated_cost > daily_cap_usd:
        raise BudgetExceededError(
            f"{provider} daily cap ${daily_cap_usd:.2f} would be exceeded: "
            f"${today_cost:.4f} spent + ${estimated_cost:.4f} estimated"
        )
```

The error message says exactly how much was spent and what was about to be added. When the cap trips, you want the log to explain itself.

## Where the cap lives: in the router

The cap is most useful in the code that chooses a provider. My router walked an ordered chain of providers for each kind of task:

1. skip a provider that's disabled;
2. skip it if its health check fails;
3. skip it if it has a daily cap and the cap is reached;
4. otherwise use it, and report how much budget is left.

If every provider is exhausted, the router raises an error that lists what it tried. So hitting the cap doesn't break anything. Work just moves down the chain to a free or local model.

## Two gaps I'd close

Reading the code again months later, two things stand out.

**The check runs with an estimated cost of zero.** That means the cap is checked against what's already spent, not against the call about to happen. If you're at $0.24 with a $0.25 cap, one more expensive call goes through and lands you over. For a quarter a day that's fine. For a real budget, estimate the call's cost from the prompt size and the model's price before you make it.

**The day comes from the local clock, while the timestamp is UTC.** The `date` column used local date and `called_at` used UTC. That's harmless on one machine, but if the ledger is ever shared between machines in different time zones, "today" means different things. Pick one, and UTC is the safer choice.

## When this is enough

A ledger like this is right for one person or a small team running agents on their own keys. It won't replace provider-side limits, and you should set those too: they're the backstop if your code has a bug. But a cap in your own code is the one that routes work somewhere cheaper instead of just failing.
