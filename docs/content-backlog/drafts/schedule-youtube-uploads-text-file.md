---
title: "How do I schedule YouTube uploads from a text file?"
excerpt: "Put a schedule time in each video's YAML file, upload as private with publishAt, and preview every date before anything is sent to YouTube."
tags: [youtube-api, scheduling, python, yaml, automation]
categories: [How-to]
keyword: schedule youtube uploads api python
status: reviewed
---

Write the publish time into a small text file next to each video, upload the video as private with the `publishAt` field set, and let YouTube make it public at that time. YouTube's documentation says `publishAt` can be set only when the video's privacy status is private. Before anything is sent, print the title and the exact request body so you can check every date.

I should be honest about the title. I do not use one calendar file. Each of my Shorts has its own YAML file with a `schedule` line, plus a planning step that works out dates for a whole batch. Both are described here, and both come from my RFD_YT_Engine repo.

## What you need

- A YouTube Data API project with OAuth credentials, and a saved token.
- Python, with Google's API client library.
- A metadata file per video.

## Step 1: Put the schedule in the metadata file

```yaml
title: "A title under 100 characters"
description: |
  Description here.
tags: [one, two, three]
privacy: "private"
category_id: "20"
made_for_kids: false
schedule: "2026-07-26T22:00:00-04:00"
```

My repo has 142 of these. Always include the UTC offset, as the scheduled files in my repo do (six others leave `schedule` empty). My parser also accepts times with no offset (`2026-07-26 22:00`), but I do not know how YouTube would interpret them.

## Step 2: Turn it into an API request

When a schedule is present, the code ignores the `privacy` value, sends `privacyStatus: private` and sets `status.publishAt` to the time in RFC 3339 form. A video with no schedule goes up with whatever privacy the file says. A value that matches none of the accepted formats raises an error instead of being guessed.

## Step 3: Validate before sending

The checks are the limits as I have them in my code: a title that is not empty and not over 100 characters, a description of at most 5,000 characters, tags totalling at most 500 characters, and a privacy value of public, unlisted or private. I have not checked each one against YouTube's current documentation.

## Step 4: Dry run by default

My upload commands send nothing unless I add `--upload`. The default prints the resolved metadata and the request body, then says "DRY RUN: nothing sent to YouTube." A confirmation prompt follows a real upload unless I pass `--yes`.

## Step 5: Plan a whole batch

For a pile of private videos, hand-picking dates does not scale. My planning function is pure: it takes a list of videos and returns a plan, calling no API and writing nothing. The rules:

- Only private videos of 60 seconds or less are considered.
- Titles are matched to a game by their starting words. If any title matches none, the whole plan stops with the list of unknown titles.
- Videos are dealt out one per day in a round-robin across the games, so the same game does not run for days.
- Every slot is at 22:00.

Previewing prints a table with the old date, new date and exact UTC time for every video. Only `--apply` writes. The apply step refuses to run if any new date is already in the past, and it reports "N rescheduled, M failed" at the end rather than aborting on the first failure.

## A trap in my own plan

The time zone is a fixed offset of UTC-4, not a named zone. The docstring says so: in winter, a 22:00 slot lands at 21:00 Eastern Standard Time (02:00 UTC). If you want a time that stays put on the wall clock across daylight saving, use a named zone such as America/New_York. I ported this rule from an older tool so that dates would match, and I left it. If clocks matter to you, do not copy it.

## Spotting clashes

A second helper looks at a date range and flags runs where one game appears more than twice in a row (the limit is a parameter, default 2). It also separates two videos at the exact same moment, a real conflict, from two videos on the same date at different times, which I do on purpose. Its docstring says it would have flagged a seven-day run of one game on my calendar.

## Common problems

- **The video went public at once.** It was probably uploaded with no schedule, or the field name was wrong.
- **A scheduled video stays private.** Check `publishAt` is in the future and ends in a valid offset or `Z`.
- **Uploads are locked to private.** YouTube's documentation says videos uploaded through `videos.insert` from unverified API projects created after 28 July 2020 are restricted to private viewing until the project passes an audit.
- **Quota.** An upload costs far more quota than a read. YouTube's quota pages are not consistent with each other on the exact figure, so check the current cost and your project's limit before planning a big batch.

## FAQ

**Can I move a scheduled video later?** Yes. I have a batch reschedule function that processes videos one at a time and records success or failure for each.

**Do I need a database?** My version keeps a local copy of the channel's video list so calendar checks cost no API calls. You could do without.

**Can I do this with a spreadsheet?** I have not tried. A CSV would be an equally good source for the same plan.

<!-- fact-checked 2026-10-08: 22 claims confirmed, 2 corrected, 1 removed; remaining notes: offset-less schedule behaviour and exact quota cost left as reader checks -->
