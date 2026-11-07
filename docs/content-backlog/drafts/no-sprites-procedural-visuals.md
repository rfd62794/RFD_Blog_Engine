---
title: "My game has no sprites. Every item is drawn with math."
excerpt: "Ore, ingots, components and the drone bay in VoidDrift are procedural shapes with fixed seeds, tuned from a config file. Why I chose math over a sprite sheet."
tags: [gamedev, procedural, bevy, rust, design]
categories: [Build in public]
keyword: procedural graphics instead of sprites
lane: dev
status: draft
source: rfd62794/VoidDrift docs/adr/ADR-012-no-sprites-procedural-math-visual-language.md (read Nov 4 2026)
---

VoidDrift doesn't ship a single sprite. Every ore chunk, ingot, component and the drone bay is drawn from math at runtime: polygons, parallelograms, lines and circles, with fixed seeds so they look the same every time.

I didn't start out with a principle about it. I started with a counting problem.

## The counting problem

In May I needed a visual language for the production chain. Four ores, four ingots, four components, plus the drone bay. That's at least a dozen sprites, and every one of them would need a version at each resolution, a place in the build, and an update every time I changed my mind about the look. I'm one person who doesn't draw.

The game's style was already "technical schematic meets sci-fi console". Precise lines, thin strokes, a lot of dark space. That style is basically geometry. So I tried drawing the items with geometry.

## What each thing is made of

- **Ore:** a jagged polygon with a five-pointed vein pattern through it.
- **Ingots:** three-face isometric parallelograms, shaded by which face points where.
- **Components:** schematic shapes built from trapezoids, circles and lines.
- **The drone bay:** a rocket silhouette assembled from simple shapes.
- **World objects:** Bevy meshes with vertex colors for banding.

Every parameter (how jagged, which colors, how big) lives in a `visual.toml` file. I can retune the whole look of the production chain without touching code or rebuilding any assets.

## Why the seeds matter

Procedural art has a trap: if the shape is random every frame, it shimmers, and if it's random every session, players can't learn what things look like. Every item uses a deterministic seed. Iron ore looks like iron ore today and tomorrow. Variation exists between instances, not between frames.

Shapes are generated once when an entity spawns, not every frame, so the cost is small even on a mid-range phone.

## What I gave up

Character. A good pixel artist would give each ore a personality my polygons don't have. There's no texture, no hand-made detail, no happy accident. If the game ever needs a mascot, math won't draw it.

But for this game, the trade was right. It scales from a 720-pixel phone to a desktop monitor without a single extra file. It matches the cold, mechanical place the game is set in. And I spent my evenings on the game instead of on an asset pipeline.

## If you can't draw either

Look at what your game's style actually is before you open an image editor. If the honest answer is lines, shapes and color, you might not need art. You need a config file and a seed.
