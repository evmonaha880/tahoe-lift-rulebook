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
