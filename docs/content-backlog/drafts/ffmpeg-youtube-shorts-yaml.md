---
title: "How do I automate YouTube Shorts with FFmpeg and a YAML file?"
excerpt: "Describe each Short in a YAML file, then let a script cut the clips, pad them to 1080x1920, add captions and mix audio with FFmpeg."
tags: [ffmpeg, youtube-shorts, yaml, python, video-automation]
categories: [How-to]
keyword: ffmpeg automate youtube shorts
status: draft
---

Put each Short in a small YAML file: the source video, a list of clips with start and end times, and one caption line per clip. A script then cuts each clip with FFmpeg, scales it into a 1080x1920 canvas, draws the caption on top, joins the clips and mixes in music or a voice track. You review the file, not the timeline.

This is how I make Shorts for my own YouTube channel, and the code is in a repo I call RFD_YT_Engine. I will only describe what that code does. Where I could not confirm something, it is marked.

## What you need

- Python 3.12, managed with uv.
- FFmpeg and ffprobe on your PATH.
- Pillow for drawing caption images, and PyYAML for reading the file.
- A recording to cut up.

The repo keeps all of this behind one rule: every FFmpeg call goes through a single function, `run_ffmpeg`, which adds `-y` and has a 120 second default timeout. Tests mock that one function, so the pipeline logic can be tested without rendering anything.

## Step 1: Write the beat file

I call each clip a beat. A real file from the repo has these keys:

```yaml
name: af2_01_door_dead_body
source: "C:/path/to/recording.mp4"
music_path: assets/music/lo_fi_chill.mp3
music_volume: 0.20
voice: true
stack_text: true
max_visible_lines: 5
add_outro: true
beats:
  - clip_start: "0:17"
    clip_end: "0:27"
    duration: 10
    line: "The door just opened and closed."
  - clip_start: "17:36"
    clip_end: "17:44"
    duration: 8
    line: "What's this. Staircase. Dead body."
```

One small thing cost me time: use forward slashes in Windows paths. Backslashes inside double-quoted YAML strings are escape characters, and the project notes record that I had to fix the paths in 14 of these files for that reason.

## Step 2: Cut each beat

For every beat the script runs one FFmpeg call with `-ss <start> -to <end> -i <source>`, re-encodes with libx264 and `-pix_fmt yuv420p` at the `fast` preset, and drops the audio with `-an`. Dropping the audio matters: sound is added once, at the end, so the clips stay silent until then.

## Step 3: Make it vertical

Each cut clip is scaled to 1080 pixels wide and padded onto a 1080x1920 canvas with the picture at the top, which leaves the lower part free for captions. The filter is `scale=1080:607,pad=1080:1920:(ow-iw)/2:0`. The 607 is hard-coded in the repo (1080 times 9 over 16, rounded down). I have a separate post on vertical conversion for the other ways to do this.

## Step 4: Draw the captions

I do not use FFmpeg's `drawtext`. The repo renders the caption text to a transparent PNG with Pillow and overlays that image on the clip. The reason written in the code, for the outro card, is that font availability differs between machines and drawing with Pillow avoids it. [VERIFY: the same reason is not written for the caption function; I am inferring it applies there too.]

Two details came from real mistakes. A caption line once ran off the right edge mid-word, so a `wrap_line` function now wraps at word boundaries and stops at a maximum number of lines. And `stack_text: true` keeps a sliding window of the last five lines on screen instead of replacing the caption each beat.

## Step 5: Join and mix audio

The processed clips are joined, and then audio is mixed with an `amix` filter: music at volume 0.20, a voice track at 0.50, with the voice delayed 0.3 seconds. Those are the defaults in the code. If the music file is missing, the script logs a warning and renders without music instead of failing.

The voice track is text-to-speech from the same `line` values, switchable between Windows voices and Edge TTS with one config value. It speaks the original lines, not the stacked caption text, so nothing is read twice.

## Step 6: Run it, then publish separately

```
uv run python -m pipeline.interface produce-short shorts/<name>.yaml
```

The output lands in `output/shorts/<name>.mp4`. Uploading is a different command with a second YAML file next to the first (`<name>.meta.yaml`: title, description, tags, privacy). It prints the metadata and the API request body and sends nothing unless I add `--upload`.

The first unmocked run of this path was two beats plus an auto-added outro. The notes record an 8.0 second, 21 MB MP4 that I checked with ffprobe. I have not timed how long the render took. [VERIFY: render time on a typical Short]

## Common problems

- **Silent gaps in a joined video.** In my speed-ramp path (a different one from the beat files), a cut past about 30 to 45 seconds into a source silently produced a valid but empty file, and the concat step accepted it. Now every rendered segment is checked with ffprobe and an error is raised for zero frames or zero duration.
- **`setpts` without `fps`.** Changing playback speed with `setpts` alone left the frame count wrong and caused "Non-monotonic DTS" warnings later. The code always writes `setpts=PTS/N,fps=30` together, and a test enforces it.
- **`unknown keyword` from the concat list.** PowerShell's UTF-8 option writes a byte order mark that FFmpeg reads as part of the word `file`. Write the list from Python and it is gone. A test checks the first three bytes.

## FAQ

**Do I need a GPU?** Not for this part. The FFmpeg steps here are software encodes. A GPU only comes into my pipeline for transcription.

**Can I do this without Python?** Yes, with shell scripts, but the caption wrapping and the checks above are where Python earned its place for me.

**How many Shorts have I made this way?** The repo tracks 142 metadata files and 159 Short definitions. I do not know how many were uploaded. [VERIFY]

**Is the render deterministic?** The inputs are, but I have not compared two renders byte for byte.
