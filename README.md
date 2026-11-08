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
| Evidence | 7,044 posts from the ops account, 8 winters (2018-19 to 2025-26), parsed into 23,966 events by a rule-based parser |
| Parser tests | 191 regression cases, all passing; 2.1% of posts (150) match no rule |
| Parser accuracy | Original hand check (240 held-out posts, before the closure rule): about 90% of posts fully right, plus or minus 5 points. Re-check on the evening of 2026-11-07 by an independent model reader (it saw only the post text and the event definitions, not the parser code): 120 random held-out posts, 109 fully right (91%); 54 held-out posts about closures, 35 fully right (65%); 174 posts overall, 144 right (83%). One reader, not a human, and strict: a post is right only if every event is right and nothing stated is missed. Closure and roster posts are the weak spots. The hedged-warning rule (P-012h) was added after this re-check, from train posts only. |
| Independent readers | Subquadratic and Meta Muse each labeled posts blind, without seeing the parser: Subquadratic all 7,044, Meta Muse 7,040 (4 calls failed). The parser agrees with them 93.1% and 97.2% of the time; they agree with each other 94.6%. Agreement is not truth. |
| Rulebook | Hold rules for 39 lifts, each tagged *inferred* (from weather) with the *observed* counts kept beside it |

**What the rules show** (leave-one-winter-out; details and every number in [docs/RESULTS.md](docs/RESULTS.md)):
- A wind line of about 60 mph gusts at the crest predicts which days see a wind hold. It is stable across winters and beats a 25 mph rule in all 8 (day-level F1 0.70 to 0.88 against 0.38 to 0.72).
- Which lift holds is harder. On expected lift-days (scheduled, plus lifts under a whole-mountain closure), one learned wind line does about as well as separate per-lift rules (pooled F1 0.57 each); the 25 mph rule has high recall and very low precision.
- **"All lifts closed" is an event, and it is predictable** (what counts as a closure, by kind and conditions: [docs/CLOSURES.md](docs/CLOSURES.md)). 47 whole-mountain closure days are counted from the posts (44 graded high confidence, 3 medium). Closures were rare below 100 mph gusts (3 to 4% of days), 22% of days at 100 to 130 mph and 55% at 130 and above. Avalanche danger 4 closed the mountain on 45% of days.
- **Storm days start late.** With wind under 60 mph, 25% of lifts were held or closed on days with 2+ in of new snow, 1+ in of snow water or avalanche danger 3+, against 6% on other days (54 such days).
- **Hours beat the peak gust.** With a 60 to 100 mph peak, a Tram or Funitel hold came on 17% of days with 2 hours or less at 60 mph or more, and 61% with more than 5 hours. Wind direction adds nothing once duration is counted; south-west storms simply last longer.
- When a gateway (Tram or Funitel) holds, 66% of upper-mountain lift-days hold with it, 49% on days without a whole-mountain closure; when neither holds, 7%.
- Mechanical and lightning holds are only weakly predictable from these weather files.
- **Holds with no named cause (1,376 of 5,412) get an inferred cause.** A model fitted on the holds whose post names one cause, using weather, the date and the cause words in the day's other posts (avalanche control, power, lightning, ice), recovers the named cause 80% of the time on winters it never saw (67% by always guessing wind). It is confident on 56% of the unstated holds. Inferred causes are kept apart from observed ones: [docs/CAUSES.md](docs/CAUSES.md).
- **After a hold, no reopening post that day is read as "did not reopen"** (an assumption, stored separately from the observed reopenings). A reopening is posted for 40% of holds under 40 mph and 13% at 100 mph and above; the median posted hold is about 50 to 110 minutes.

**COVID.** 2019-20 ends on 2020-03-14 (the resort suspended operations on 2020-03-15; no COVID wording appears in the posts). Winter 2020-21 ran under operating rules (reservations, capacity limits): lifts held on 30% of calm days (under 40 mph) against 9% in other winters and on 22% of days with 100+ mph gusts against 76%, so it stays in the replay and the day-level wind line but is left out of the lift-level fits (214 expected lift-days).

**Limits.** Outcomes are what the ops account posted; unposted holds are invisible. In the core season (January to April) every day has posts; silence at the season edges means the mountain was not operating. The 12 silent days 2025-12-07 to 2025-12-18 (gusts to 105 mph) are real: X's own counts show the ops account posted nothing in that window, and the daily originals counts match the pulled files exactly in all eight winters (checked 2026-11-07). Replies are left out on purpose; a sample of 28 replies was customer questions, not status updates. Per-lift results rest mainly on three winters (2021-22 to 2023-24) that name lifts on most days. The Funitel-top wind is partly an estimate. No result here is a forecast of tomorrow.

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
