# Palisades lift-hold rulebook

Software archaeology on a system nobody wrote down: **when and why do Palisades Tahoe lifts hold, open late, or close?**

The lift operators follow rules that are not published. The only evidence is what they posted and what the weather was doing. This project recovers those rules from that evidence, keeps what was *observed* separate from what was *inferred*, and tests each rule on winters it never saw.

Built from an empty repo on 2026-11-07 at the AIE Code Summit Hackathon (problem statement: Software Archaeology). All code here was written during the event. Data is pulled from public sources.

**Demo video (1 minute): https://youtu.be/Y7q8n83wd7w**

**Live demo: https://evmonaha880.github.io/tahoe-lift-rulebook/app/** (source in [docs/app/](docs/app/index.html)). Replay a real morning from a winter the rules never saw, set your own conditions, and see the evidence.

Hook photo: r/palisadestahoe.

## Status (final, 2026-11-07)

| | |
|---|---|
| Evidence | 7,044 posts from the ops account, 8 winters (2018-19 to 2025-26), parsed into 23,907 events by a rule-based parser |
| Parser tests | 186 regression cases, all passing; 2.1% of posts (150) match no rule |
| Parser accuracy | About 90% of posts fully right on a 240-post hand check of held-out posts (plus or minus 5 points). The check was done before the whole-mountain-closure rule (P-022, added the evening of 2026-11-07 from train posts only); closure posts have not been hand-graded. |
| Independent readers | Subquadratic and Meta Muse each labeled posts blind, without seeing the parser: Subquadratic all 7,044, Meta Muse 7,040 (4 calls failed). The parser agrees with them 93.1% and 97.2% of the time; they agree with each other 94.6%. Agreement is not truth. |
| Rulebook | Hold rules for 39 lifts, each tagged *inferred* (from weather) with the *observed* counts kept beside it |

**What the rules show** (leave-one-winter-out; details and every number in [docs/RESULTS.md](docs/RESULTS.md)):
- A wind line of about 60 mph gusts at the crest predicts which days see a wind hold. It is stable across winters and beats a 25 mph rule in all 8 (day-level F1 0.70 to 0.88 against 0.38 to 0.72).
- Which lift holds is harder. On expected lift-days (scheduled, plus lifts under a whole-mountain closure), one learned wind line does about as well as separate per-lift rules (pooled F1 0.57 each); the 25 mph rule has high recall and very low precision.
- **"All lifts closed" is an event, and it is predictable.** 48 whole-mountain closure days are counted from the posts. Closures were rare below 100 mph gusts (4% of days), 21% of days at 100 to 130 mph and 50% at 130 and above. Avalanche danger 4 closed the mountain on 44% of days.
- **Storm days start late.** With wind under 60 mph, 24% of lifts were held or closed on days with 2+ in of new snow, 1+ in of snow water or avalanche danger 3+, against 6% on other days (61 such days).
- **Hours beat the peak gust.** With a 60 to 100 mph peak, a Tram or Funitel hold came on 18% of days with 2 hours or less at 60 mph or more, and 61% with more than 5 hours. Wind direction adds nothing once duration is counted; south-west storms simply last longer.
- When a gateway (Tram or Funitel) holds, 66% of upper-mountain lift-days hold with it, 49% on days without a whole-mountain closure; when neither holds, 7%.
- Mechanical and lightning holds are only weakly predictable from these weather files.

**Limits.** Outcomes are what the ops account posted; unposted holds are invisible. In the core season (January to April) every day has posts; silence at the season edges means the mountain was not operating. One unexplained gap remains, 2025-12-07 to 2025-12-18 (12 silent days, gusts to 105 mph), which needs a targeted re-pull to separate a pull gap from a closure. Per-lift results rest mainly on three winters (2021-22 to 2023-24) that name lifts on most days. The Funitel-top wind is partly an estimate. No result here is a forecast of tomorrow.

## Data sources

| Source | What | How it is pulled |
|---|---|---|
| Palisades Tahoe / Alpine Meadows weather stations (Western Weather Group public report builder) | Wind, gust, direction, temp, humidity, pressure, snow and precipitation, 13 stations, hourly from Oct 2016 and 15-minute from about 2018 | `scripts/pull_wwg.py` |
| NRCS SNOTEL site 784, Palisades Tahoe | Hourly snow water, snow depth, temperature, wind, 2008 onward | `scripts/pull_free.py` |
| NOAA CPC ONI and RONI indices | El Nino / La Nina phase by season, 1950 onward | `scripts/pull_free.py` |
| Palisades mountain operations account on X | Lift status posts (the events to explain) | X API, pay per use. The raw pull files stay out of git; the app shows the text of public posts next to the events parsed from them. |
| Sierra Avalanche Center public API | Daily danger rating, 2013 onward | `https://api.avalanche.org/v2/public/products?avalanche_center_id=SAC` (no key) |

`scripts/pull_probe*.py`, `scripts/wwg_*.py` are the exploration scripts used to find each source's depth and request format.

## Re-running

In order: `scripts/parse_posts.py <year> <train|heldout>` for each winter, `scripts/build_dataset.py 2018 ... 2025`, `scripts/recover_rules.py`, `scripts/baselines.py`, then `scripts/build_app_model.py` (writes the app's only data file) and `scripts/check_app_model.py` (fails if the app's numbers differ from the results); tests with `python3 -I tests/golden.py`.

Raw data goes in `data/raw/` (git-ignored). Scripts read API credentials from files kept outside the repo, never from the repo itself.
