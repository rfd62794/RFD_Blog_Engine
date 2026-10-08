---
title: "How do I convert landscape video to vertical 9:16 with FFmpeg?"
excerpt: "Scale the video to 1080 wide and pad it to 1080x1920, or crop or blur-fill instead. Three tested FFmpeg commands and when to use each."
tags: [ffmpeg, vertical-video, youtube-shorts, 9x16, video-automation]
categories: [How-to]
keyword: ffmpeg convert to vertical 9:16
status: draft
---

To turn a 16:9 video into 9:16 with FFmpeg, you choose between three things: pad it with bars, crop the sides off, or fill the empty space with a blurred copy. The padding command is `ffmpeg -i in.mp4 -vf "scale=1080:-1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x131318" -c:a copy out.mp4`. It never cuts anything out of your picture, and it is the one I use.

I make vertical Shorts from screen recordings, where cropping would cut off the part of the screen that matters. The padding filter below comes straight from my code. I wrote the crop and blur versions for this post and ran all three on a synthetic 1920x1080 test clip with FFmpeg 9.0. Each produced a 1080x1920 H.264 file. I did not judge how any of them looks on real footage.

## What you need

- FFmpeg (and ffprobe to check the result).
- A landscape source. Mine are 16:9 recordings.
- Decide where the picture sits. Centered looks natural. At the top leaves room for captions underneath, which is what my caption step does.

## Option 1: Pad (nothing is cut)

```
ffmpeg -i in.mp4 \
  -vf "scale=1080:-1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x131318" \
  -c:a copy out.mp4
```

`scale=1080:-1` makes the video 1080 wide and works out the height. `pad` then places it on a 1080x1920 canvas; `(ow-iw)/2` and `(oh-ih)/2` center it, and `color=` fills the rest. FFmpeg wants colors as `0xRRGGBB` or plain hex, not `#RRGGBB`, so my function strips the `#` and adds `0x`.

To put the picture at the top instead, change the last part of the pad value to `(ow-iw)/2:0`. My caption pipeline does this and fixes the scaled height at 607 pixels (1080 times 9 over 16, rounded down). The exact height is 607.5, so that squeezes the picture by less than a pixel. I never noticed it.

## Option 2: Crop (fills the frame, loses the sides)

```
ffmpeg -i in.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" -c:a copy out.mp4
```

This keeps a 9:16 slice from the middle of the picture and scales it up. For a 1080p source the slice is 607 pixels wide, so you keep roughly a third of the frame and enlarge it by about 1.8 times. That suits a talking head in the middle of the shot. It does not suit a screen recording or a wide game scene.

## Option 3: Blurred background

```
ffmpeg -i in.mp4 -filter_complex \
  "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];\
   [0:v]scale=1080:-2[fg];\
   [bg][fg]overlay=(W-w)/2:(H-h)/2" \
  -c:a copy out.mp4
```

The first branch blows the video up until it covers the canvas and blurs it. The second keeps a sharp full-width copy, and the overlay sits it in the middle. It looks like what many phone apps do. The cost is more processing time. I did not measure it.

## Check the result

```
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 out.mp4
```

You want `1080,1920`. My project has a test that builds a 320x180 test video with FFmpeg's `testsrc`, runs the padding function and asserts exactly that through ffprobe. A second test samples a pixel in the padded area to confirm the background color, and it allows a tolerance of 2 because the color passes through a YUV conversion and does not always come back exact.

## Common problems

- **Odd heights.** When I scaled a 1000x563 test video with `scale=1080:-1`, the height came out as 608 and libx264 accepted it. Some sources give an odd number, which libx264 with `yuv420p` rejects. Use `-2` in place of `-1` to force an even result. [VERIFY: I did not reproduce a rejection.]
- **Audio gets re-encoded.** `-c:a copy` leaves the sound alone. If you also change containers, re-encode instead.
- **A small source looks soft.** Scaling a 640-wide video up to 1080 enlarges every pixel. Cropping makes this worse because it enlarges even more.
- **Line breaks fail in PowerShell.** The trailing backslashes are for a Unix shell. In Windows PowerShell, put the command on one line or use the backtick.

## FAQ

**Which option is best for YouTube Shorts?** I do not have data on which performs better. I pad because my recordings have information at the edges. If your subject is centered, crop.

**What resolution should a Short be?** I use 1080x1920. Check YouTube's current guidance for anything else. [VERIFY]

**How long can a Short be?** My own code disagrees with itself: one function treats anything up to 60 seconds as a Short, a calendar helper uses 180. YouTube changes this rule, so check the current limit before relying on either. [VERIFY]

**Will it work in a script?** Yes. Mine calls FFmpeg through one helper, raises an error on a non-zero exit code and keeps the full command in the error for debugging.
