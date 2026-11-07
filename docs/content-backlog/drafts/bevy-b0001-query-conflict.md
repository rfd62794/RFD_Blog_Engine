---
title: "Bevy B0001 query conflict: why it only crashed on my phone, and the fix"
excerpt: "Two Transform queries in one Bevy system, one mutable, panic with B0001 unless Bevy can prove they never overlap. Without filters fix it. How I made it a rule."
tags: [bevy, rust, gamedev, ecs, android]
categories: [How-to]
keyword: bevy b0001 query conflict
lane: client
status: draft
source: rfd62794/VoidDrift docs/adr/ADR-008-universal-disjointness.md (read Nov 4 2026)
---

Bevy's error B0001 means one system has two queries that could touch the same component on the same entity, and at least one of them is mutable. The usual case is two queries over `Transform`, one with `&mut`. The fix is to add `Without<T>` filters so Bevy can prove the two queries never match the same entity, or to combine them with a `ParamSet`.

In my mining game VoidDrift, this one cost me more time than it should have, because it didn't show up where I was looking.

## The symptom

The game built cleanly. `cargo check` was happy. It ran on desktop. Then on my test phone, a Moto G 2025, it panicked with `B0001: Query conflict`.

The detail that matters: this check happens when the system is set up at runtime, not when the code compiles. A conflict the compiler can't see is still a conflict. If your desktop run doesn't happen to initialize the same system the same way, or you only test one path, the first time you see it can be on a device.

## A system that triggers it

```rust
fn follow_ship(
    ships: Query<&Transform, With<Ship>>,
    mut station: Query<&mut Transform, With<Station>>,
) { /* ... */ }
```

This reads ship transforms and writes the station's. You know a ship is never a station. Bevy doesn't. `With<Ship>` and `With<Station>` don't prove an entity can't have both components.

## The fix: prove they're disjoint

```rust
fn follow_ship(
    ships: Query<&Transform, (With<Ship>, Without<Station>)>,
    mut station: Query<&mut Transform, (With<Station>, Without<Ship>)>,
) { /* ... */ }
```

Now no entity can match both queries, and Bevy accepts it.

## Making it a rule instead of a fix

I fixed it once, then hit it again in another system a week later. So I wrote a decision record that made it a project rule:

- Every system that uses `&mut Transform` must include `Without<T>` filters that prove it's disjoint from every other `Transform` query in that system.
- Standard exclusions for each main entity type are written down. Ships exclude the station, the asteroid field and the mining beam. The station excludes ships and autonomous drones. UI and map labels exclude the main world entities.
- Adding a new main entity type means auditing existing systems for new overlaps.

The nice part of a rule this mechanical is that it's easy to check. A project-wide search for `&mut Transform` shows every place that has to follow it.

## Why not ParamSet?

`ParamSet` is the other standard answer, and it works. You put the conflicting queries in a set and borrow one at a time. I found that it made the system bodies harder to read, with the borrowing dance spread through the logic. Filters keep the conflict-proof in the signature, where you can see it. When the filters get unmanageable, that's my signal to split the system in two.

## The rule of thumb

If a system writes a component that another query in the same system reads, put the proof in the query types. And test on the device you ship to early, not after the build looks done.
