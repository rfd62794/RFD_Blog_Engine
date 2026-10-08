---
title: "Can a small AI model review code? I measured it and got no answer"
excerpt: "I tried a free model as my code reviewer. The first scorecard says 0 of 9 risky changes slipped through, and that is too few to trust. Here is the data."
tags: [ai-code-review, evals, ai-agents, testing, llm]
categories: [Build in public]
keyword: ai code review small model accuracy
status: draft
---

I want to hand part of my code review to a cheaper model. Before I do, I need one number: how often does it say "safe to merge" about a change that is not? I built a scorecard to get that number. The first run produced a result I can only describe as honest: inconclusive.

## The question that matters

Most review metrics ask whether the reviewer found the bug. That is recall, and it is useful, but it is not the dangerous error. The dangerous error is the reviewer looking at a branch with a real defect and answering plain "merge".

I call that a false-safe. A reviewer that misses a bug and still asks for a fix does little harm, because a human looks again. A reviewer that waves the bug through does real harm.

My review suite already measured recall and false alarms. It did not count false-safes, even though every trial recorded the verdict. So I wrote a directive for a small scorecard module that reads the existing results and counts them.

## The setup

The suite has 10 review cases, each a real change with a known answer. Going by each case's expected verdict, six should come back as merge-after-fix, one should be sent back for rework, and three should be a plain merge. That is seven positives and three negatives.

The scorecard collapses the verdicts into three classes:

- **MERGE**: correct and safe as it stands.
- **FIX**: a concrete defect a small change would fix.
- **HOLD**: the direction is wrong or a human has to decide.

It draws a confusion table of truth against prediction, and computes the false-safe rate with a Wilson 95% confidence interval. I reused the interval code already in the repo instead of writing a new one. No model is called anywhere in the scorecard. It is arithmetic over saved results.

The model under test is `swe-2-high`, one of the free models in my lane. I chose a free one on purpose: the whole point is to see whether the cheap option can take the job.

## The result

This is the card, as committed:

```
swe-2-high: false-safe 0/9 (0%, 95% CI 0%-30%) - 9 graded FIX/HOLD trials, 10 infra-lost
INCONCLUSIVE: fewer than 10 graded FIX/HOLD trials
```

| truth \ predicted | MERGE | FIX | HOLD | none |
|---|---:|---:|---:|---:|
| MERGE | 0 | 1 | 0 | 4 |
| FIX | 0 | 1 | 0 | 7 |
| HOLD | 0 | 0 | 0 | 1 |

Reading it carefully:

- Zero false-safes in 9 graded trials. Good news, and also nearly worthless. With only 9 trials, the true rate could plausibly be as high as 30%.
- The "none" column is the bigger story. Of 14 graded trials, 12 produced no usable verdict at all. Exact-class agreement is 1 of 14, or 7%.
- Recall, meaning the review text hit the known defect, is 3 of 9, or 33%.
- One of five plain-merge cases was wrongly held back. That is a false alarm rate of 20%, with an interval from 4% to 62%.
- Ten trials were lost to infrastructure, not model behaviour, so they are counted separately and not graded.

If I had printed only "0% false-safe", I would have told a flattering lie. The scorecard refuses. When the false-safe denominator is below 10, it prints the word INCONCLUSIVE instead of a confident percentage. I wrote that rule into the directive before any data existed, because I knew a small sample would be tempting to round up.

## What I take from it

First, I cannot hand the review role to this model on this evidence. Not because it did badly, but because I do not yet know. The suite is too small and too many trials were lost.

Second, the model mostly did not answer in the shape the grader wanted. Whether that is a prompt problem, a parsing problem or a capability problem, I cannot say yet. [VERIFY: the cause of the 12 no-verdict trials; I have not read the raw outputs.]

Third, there is a different and encouraging signal from a separate experiment. A binary "pass or flag" second opinion from a free model has been running alongside my real reviews. When I measured it on 2026-10-04 it had made 23 predictions with 19 outcomes known, and the directive that records this reports precision of 1.0. That shows a free model can read a diff and flag trouble. It does not show it can tell "fix this" from "park this", which is why I wrote the three-way scorecard.

## What happens next

A separate piece is already merged: a shadow reviewer that gives a three-way verdict on each real review, then compares it to what actually happened to the branch: merged as is, changed after, or abandoned. It is advisory only, and nothing is merged or blocked because of it. That grows the sample from real work instead of from a ten-case suite. [VERIFY: that it is running and how many verdicts it has recorded.]

The rule I am keeping: a reviewer gets promoted on a number with an interval, not on a feeling. The gate itself is my call, and the scorecard only states the numbers.

## What I have not checked

The card above is the committed file. I did not rerun the suite for this post. [VERIFY: whether a later run replaced these numbers.] The trial total of 24 is my own addition, 14 graded plus 10 lost. [VERIFY: against the raw results file.] And the shadow-reviewer figures come from a directive I wrote, not from a fresh query of the ledger. [VERIFY: current counts.]
