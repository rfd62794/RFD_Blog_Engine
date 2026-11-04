---
title: "My game's text was invisible on one phone, so every screen became egui"
excerpt: "Bevy Text2d rendered as blank or corrupted glyphs on a Mali GPU phone. Moving every HUD element to bevy_egui fixed it. Why I made that a rule for the whole game."
tags: [bevy, rust, gamedev, android, egui]
categories: [Build in public]
keyword: bevy text not showing android
lane: dev
status: draft
source: rfd62794/VoidDrift docs/adr/ADR-003-bevy-egui-hud.md, ADR-004, README technical table (read Nov 4 2026)
---

I build VoidDrift for one phone. A Moto G 2025: 720 by 1604, a Mali-G57 GPU, Android 15. Every architecture choice in the game is made for that device, because it's the one I own and the kind of phone a lot of people actually have.

In April, that phone showed me a HUD with no words on it.

## What went wrong

My first HUD used Bevy's own building blocks: `Text2d` for labels and meshes parented to the camera for panels. On desktop, fine. On the phone, the text rendered as invisible or corrupted glyphs, and the camera-parented panels clipped erratically. My best guess at the time was a transform precision problem on that driver, but I never proved the exact cause. What I could prove was that it happened on the device I was shipping to.

I could have spent weeks chasing a driver issue. Instead I asked a simpler question: is there a way to draw text that doesn't go through the path that's failing?

## The switch

`bevy_egui` draws its own font atlas in its own render pass. It sidesteps the pipeline that was misbehaving. I moved one panel over as a test, the text showed up, and I made the call: all screen-space UI in the game goes through egui. Station panels, map overlays, resource readouts, tabs, the tutorial.

Two settings came with it. UI scale is locked at 3.0 so everything is readable with a thumb on a high-density screen. And Bevy itself is pinned to one version, because an engine upgrade that changes rendering behavior on that one GPU is the last thing I want to discover after a release.

## Why make it a rule

The decision record doesn't say "use egui where it helps". It says all screen-space UI must use egui, and every future screen follows the same pattern. Mixing two UI systems would mean two sets of layout bugs, two ways to handle touch, and one of them known to break on my target device.

Immediate-mode UI also turned out to fit the game. The HUD shows ship state and docking actions that change every frame. Drawing it fresh each frame from the game's state is simpler than keeping a retained UI tree in sync.

## What it cost

The world itself still renders with Bevy meshes. The UI lives in a separate pass, so anything that has to feel like it's in the world, like a label following a drone, takes extra work to line up. And egui's look is recognizable. I've spent time making it feel like a sci-fi console instead of a debug panel.

## What I'd tell another solo dev

Pick one real device and test on it from week one. Emulators and desktop builds tell you the code runs. Only the device tells you what the player sees. And when one part of the engine fights your hardware, it's often cheaper to route around it entirely than to fix it, as long as you write down why so you don't drift back.
