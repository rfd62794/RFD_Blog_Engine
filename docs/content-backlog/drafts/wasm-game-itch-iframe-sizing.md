---
title: "How to size a Rust WASM game for an itch.io embed (and make fullscreen work)"
excerpt: "Set the itch.io embed size, constrain the canvas with CSS aspect-ratio, re-inject that CSS after every wasm-pack build, and use the :fullscreen selector, not the event."
tags: [wasm, rust, bevy, itchio, gamedev]
categories: [How-to]
keyword: wasm game itch.io canvas size fullscreen
lane: client
status: draft
source: rfd62794/VoidDrift docs/WASM_ITCH_SIZING.md and ADR-015 (read Nov 4 2026)
---

To make a portrait WASM game fit an itch.io page, set the embed size in the itch.io dashboard, constrain the canvas with CSS (a max width, a max height of `100vh` and an `aspect-ratio`), and make sure your build doesn't overwrite that CSS. For fullscreen, style the canvas with the `:fullscreen` pseudo-class, because the `fullscreenchange` event doesn't reach a game running in itch.io's cross-origin iframe.

These are the values and lessons from getting VoidDrift, a Rust and Bevy game, to behave in a browser.

## Step 1: Pick the embed size on itch.io

My game is portrait, built for a 9:16 phone. I set the itch.io embed manually to 720 by 1280. Don't rely on the default; it assumes landscape.

## Step 2: Constrain the canvas with CSS

```css
canvas {
  max-width: 720px;
  max-height: 100vh;
  aspect-ratio: 9 / 16;
}
canvas:fullscreen {
  max-width: none;
  max-height: none;
}
```

With Bevy, set the window's `fit_canvas_to_parent: true`. Note what "parent" means here: the canvas fits the iframe, not the browser window. That's what you want on itch.io.

## Step 3: Re-inject the CSS after every build

This one cost me an evening. `wasm-pack` regenerates `pkg/index.html` on every build, so any CSS you hand-edit into it disappears next time. My build script now writes the canvas CSS back into the generated page as its last step. If your styles keep vanishing, this is why.

## Step 4: Fullscreen inside an iframe

The game runs in a cross-origin iframe on itch.io. When the player hits fullscreen:

- the `fullscreenchange` event does **not** fire inside the iframe;
- a window `resize` event **does** fire;
- the `:fullscreen` CSS pseudo-class on the canvas is the most reliable way to drop the size constraints.

So I stopped listening for the event and let CSS handle it.

## Step 5: Measure what the UI really gets

My UI is egui. On itch.io, the content area of my bottom drawer reported 162 logical pixels of usable height, measured by logging `ui.available_height()` in the browser console. I'd set the panel to 250, and headers and margins ate the rest. A desktop run reported more, which is how layouts that looked fine locally ended up cramped online.

Two lessons there. Log the real available size in the real embed instead of trusting your constants. And remember that a UI scale setting may apply to world coordinates and not to UI panels, depending on how you set it.

## Quick checklist

1. Set the itch.io embed size to your game's aspect ratio.
2. Canvas CSS: max width, `max-height: 100vh`, `aspect-ratio`.
3. Re-apply that CSS in your build script after wasm-pack runs.
4. Use `canvas:fullscreen`, not the fullscreen event.
5. Log available UI height inside the embed and build layouts from that number.
