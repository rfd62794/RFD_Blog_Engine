---
title: "Bevy add_systems error E0277 with too many systems: the 20-tuple limit"
excerpt: "Bevy registers systems as a tuple, and past about 20 the compiler rejects it with E0277. Split them into groups. How I partitioned my game's Update schedule."
tags: [bevy, rust, gamedev, ecs, compiler]
categories: [How-to]
keyword: bevy add_systems too many systems e0277
lane: client
status: draft
source: rfd62794/VoidDrift docs/adr/ADR-007-system-partitioning.md (read Nov 4 2026)
---

If `app.add_systems(Update, (a, b, c, ...))` suddenly fails with error E0277 once you add one more system, you've hit the tuple size limit. Bevy implements its system traits for tuples up to a fixed size, and my game crossed it at around 20. The fix is to register your systems in more than one group.

## What it looks like

My game VoidDrift registered every Update system in one call in `lib.rs`. It grew past twenty systems: movement, mining, the economy, autopilot, autonomous drones, visuals, narrative, the tutorial, quests, UI, the map. Then one more system broke the build with a trait-bound error that doesn't mention tuple size anywhere obvious. That's what makes it confusing the first time.

## The fix I chose: named partitions

I split the Update schedule into two groups by what the systems are about:

```rust
// Group 1: gameplay and logistics
app.add_systems(Update, (
    ship_movement, mining, economy, autopilot, autonomous_drones, /* ... */
));

// Group 2: station, narrative and UI
app.add_systems(Update, (
    station_visuals, narrative, tutorial, quests, hud, star_map, /* ... */
));
```

Two rules came with it, written into a decision record:

- **Stop at 18 per group.** That leaves room to add a system or chain a few without hitting the limit again mid-feature.
- **Be explicit about order across groups.** Within a tuple you can `.chain()`. Across groups, Bevy schedules freely, so if one system has to run after another in the other group, say so with `.after()` or `.before()`.

## Alternatives I considered

**Nested tuples.** You can put tuples inside tuples, which raises the ceiling. It works, but it hides structure rather than adding any.

**System sets.** Labeling systems with `SystemSet`s and configuring the sets is the more scalable Bevy answer, and it's what I'd use in a bigger project. For one person and two dozen systems, I wanted the simplest thing that made `lib.rs` readable.

**Plugins.** Moving each domain into its own plugin is the natural next step and also solves this, since each plugin registers its own systems. If I outgrow two groups, that's where I'm going.

## The real lesson

The compiler limit forced a decision I should have made earlier: what are the big groups of work in this game? Once the systems were split into "the simulation" and "what the player sees", the file got easier to read and the ordering questions got easier to answer. The error was annoying. The structure it pushed me into was better.
