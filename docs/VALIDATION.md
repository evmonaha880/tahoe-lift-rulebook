# Parser validation on a frozen sample (2026-11-07)

**What was tested.** 320 held-out posts (40 per winter, 2018-19 to 2025-26) that no earlier check, hand sheet or rule-writing session had seen. The ids were drawn and hashed in `results/validation_sample_ids.json` before the parser work of that evening, and nobody read the posts while writing rules. The parser version graded was **2026.11.07.8**. Each post was graded once; none is re-graded after a parser change (a fix prompted by them needs a new sample).

**Who graded.** Three Claude models (Opus, Sonnet, Haiku), each reading only the tweet, its parse and the project conventions (`PROMPT.txt` in the private analysis folder), not the code. A post is right only if every event is right (type, lift or scope, cause when named) and nothing the tweet clearly says about a lift is missing.

| Result | Value |
|---|---|
| Majority of three (2 of 3 right) | **280 of 320 = 87.5%** (95% interval 83.4 to 90.7) |
| Opus / Sonnet / Haiku alone | 86.9% / 87.5% / 85.6% |
| All three right / all three wrong / split | 267 / 35 / 18 |
| Agreement between graders (Fleiss kappa) | 0.84 |
| By winter (majority right of 40) | 2018-19 34, 2019-20 36, 2020-21 35, 2021-22 35, 2022-23 33, 2023-24 32, 2024-25 37, 2025-26 38 |
| Posts with lift events / without | 86.3% (189 of 219) / 90.1% (91 of 101) |
| Closure posts (parser emitted a closed_day) | 32 of 35 right |
| Posts containing a fallback (P-099) event | 2 of 5 right (too few to judge) |

**What this does and does not show.**
- It supports "about 85 to 90% of posts are read fully right", in line with the two earlier fresh samples (85 to 88%). The interval is about plus or minus 3.5 points.
- The graders are language models and agree with each other (kappa 0.84), not necessarily with the truth. A human check of the 35 closure posts and the 18 split posts is in `04 - Projects/Tahoe Rulebook/Human Check Sheet.md` in the owner's vault; its result will be added here when done.
- Dev and held-out are reported separately: the earlier hand checks (about 90%, then 85 to 88%) are dev-era numbers because fixes were made from them; this 87.5% is the held-out number.
- Not run: Meta Muse and Subquadratic on this sample (they use hackathon credits; pending the owner's decision).
- Counts of the kinds of error were not read from the wrong posts, to keep this sample clean.

## Before and after on the same frozen sample (2026-11-07, night)
How much did the evening's parser work (tag `v2-pre-hardening` against parser 2026.11.07.9) change accuracy on the 320 frozen posts? Only **9 of 320** posts parse differently between the two. The same three Claude graders scored the old parse of those 9: 1 right, 8 wrong; the new parse of the same 9: 3 right, 6 wrong (3 fixed, 1 broken, 5 wrong in both). Net **+2 posts: 278 of 320 (86.9%) before, 280 of 320 (87.5%) after**, well inside the plus or minus 3.5-point interval. The evening's parser work therefore did not move accuracy measurably on this sample; its value is in the guardrails, the checks and the data fixes. The one post that got worse involves the "only lift open / starting the day with" rule (P-014o); it fired once in the sample and was judged wrong, so the rule is suspect and should be checked on a second, fresh sample before more is built on it (the posts were not read, so no fix has been made from them).
