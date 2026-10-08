---
title: "How do I transcribe audio files locally with faster-whisper?"
excerpt: "Install faster-whisper, load a model once with INT8, loop over the segments and write an SRT file. No upload and no per-minute fee."
tags: [faster-whisper, transcription, python, whisper, local-ai]
categories: [How-to]
keyword: transcribe audio locally whisper python
status: reviewed
---

Install the `faster-whisper` package, load a Whisper model once with `compute_type="int8"`, call `transcribe()` on your file and loop over the segments it returns. Each segment has a start time, an end time and text, which is everything you need to write an SRT subtitle file. The audio never leaves your machine and there is no per-minute fee.

I use this for video recordings on my own channel. Below is what my wrapper does, the numbers I measured, and what I have not tested.

## What you need

- Python 3.12 (I use uv to manage it).
- The `faster-whisper` package. My project requires version 1.2.1 or newer.
- An audio or video file. FFmpeg is useful if you want to extract the audio first; my repo has a helper that writes a 16-bit PCM WAV.
- Optionally an NVIDIA GPU. On mine, a 4 GB RTX 3050 Ti, I install the CUDA 12.4 build of torch.

## Step 1: Load the model once

```python
from faster_whisper import WhisperModel

model = WhisperModel("medium", device="cuda", compute_type="int8")
```

Loading is the slow, memory-heavy part, so do it once per process. My wrapper keeps a dictionary keyed by model name and device, and a test confirms that three calls load the model only twice when two different keys are used.

## Step 2: Transcribe

```python
segments, info = model.transcribe(
    "recording.mp4",
    vad_filter=True,
    word_timestamps=True,
    language="en",
)
for seg in segments:
    print(seg.start, seg.end, seg.text.strip())
```

I switched on three options on purpose:

- **`vad_filter=True`** skips stretches with no speech. Before I switched backends, a transcript of one recording was full of one-letter fragments, foreign-language scraps and a repeated "Yeah" across near-silent stretches. My check afterwards was a 3 second synthetic tone with no speech in it. The test only asserts that the call finishes and returns a list; the comment beside it says I expect no segments, and I have not recorded the count.
- **`word_timestamps=True`** gives start and end times for each word, which I need for captions.
- **`language="en"`** is hard-coded because everything I record is English. Leave it out and the library detects the language itself (its default is `None`). I have not tried a non-English file.

The library documents `transcribe()` as returning a generator of segments plus an info object, so the real work happens as you loop. Do not be alarmed if the call itself returns instantly.

## Step 3: Write the SRT

An SRT entry is an index, a time range in `HH:MM:SS,mmm` format, the text and a blank line. The only fiddly part is the timestamp:

```python
def srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
```

Write the file as UTF-8. My wrapper emits one entry per word when word timings exist, because I burn captions into Shorts one word at a time. For reading a transcript, use one entry per segment instead; your file will be far smaller. The command in my repo is `transcribe <video>`, which writes the SRT next to the video.

## Which model and how much memory

These are measured numbers, read from `nvidia-smi` on the 4 GB card, with INT8:

| Model | GPU memory used |
|---|---|
| medium | 1001 MB (24%) |
| large-v3 | 1961 MB (48%) |

I had assumed `small` was the biggest model that would fit on this card. That assumption was wrong. The thing that mattered was switching from the reference openai-whisper package to faster-whisper. My notes say the new backend is about four times faster with about half the VRAM, but those figures are the project's claim, not my benchmark. I did not time both backends on the same file, and I have no CPU timings at all.

## Common problems

- **"CUDA requested but not available."** My wrapper raises immediately instead of quietly dropping to the CPU, because I would rather know. Pass `device="cpu"` to run without a GPU. Expect it to be slower, by an amount I have not measured.
- **The package is not installed.** The wrapper imports faster-whisper only when you transcribe, so the rest of the code can be imported and tested without it, and the error says to install it.
- **A missing file.** Check the path first and fail with a plain message before loading a model for nothing.
- **First run is slow.** The library downloads the model from Hugging Face the first time you use a given size. I have not recorded the download sizes.

## FAQ

**Is it really free?** The software is. You pay in your own hardware and electricity, and the first run needs a model download.

**Does my audio get uploaded?** Not by this code. The transcription runs in your own process.

**Can it tell speakers apart?** Not in what I built. I have not used a speaker-separation tool.

**How accurate is it?** I have not scored it against a reference transcript, so I will not give you a number. The medium model has been good enough for my own captions, and I still read them before posting.

**Should I pick medium or large-v3?** Both fit on my 4 GB card. I default to medium and have no accuracy comparison to justify more.

<!-- fact-checked 2026-10-08: 18 claims confirmed, 1 corrected, 1 removed; remaining notes: 4x speed and half VRAM remain the project's own claim, labelled as such; no accuracy or CPU numbers -->
