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
| Evidence | 7,044 posts from the ops account, 8 winters (2018-19 to 2025-26), parsed into 24,978 events by a rule-based parser |
| Parser tests | 266 regression cases, all passing; 2.0% of posts (143) match no rule |
| Parser accuracy | **Frozen sample, graded once on 2026-11-07 (parser 2026.11.07.8): 280 of 320 never-seen held-out posts fully right by three-model majority = 87.5%, 95% interval 83 to 91 (docs/VALIDATION.md).** Earlier dev-era checks: original hand check (240 held-out posts, before the closure rule): about 90% of posts fully right, plus or minus 5 points. Re-check on the evening of 2026-11-07 by an independent model reader (it saw only the post text and the event definitions, not the parser code): 120 random held-out posts, 109 fully right (91%); 54 held-out posts about closures, 35 fully right (65%); 174 posts overall, 144 right (83%). One reader, not a human, and strict: a post is right only if every event is right and nothing stated is missed. Closure and roster posts are the weak spots. The hedged-warning rule (P-012h) was added after this re-check, from train posts only. Third check (evening of 2026-11-07, after the scope, later-day, exception, hike and run fixes): three different Claude models (Opus, Sonnet, Haiku) graded the same 174 posts independently. On 120 fresh random held-out posts: 88%, 92% and 88% fully right (majority vote 88%). On the 54 closure posts, which were seen while fixing and so are no longer blind: 78%, 76% and 70% (majority 76%, up from 65%). The three agree with each other 93 to 96% of the time (Fleiss kappa 0.78). The two hackathon models then graded the same sheet: Meta Muse (muse-spark-1.3) 86% fresh and 69% closure posts, Subquadratic (subq-snap-1.1) 84% and 63%, once given the project's lift aliases and cause conventions (without them 82% / 80% on fresh posts, 59% / 59% on closure posts, because they do not know that Squaw One is Wa She Shu or that a power outage counts as mechanical). Five-model majority: 88% on the fresh posts, 70% on the closure posts (kappa 0.73); 17 of 174 posts were wrong for all five. Fourth check, on 120 never-seen held-out posts after the five-pattern fixes (named groups, closure scope and weekdays, closed-versus-limited, runs and parks, schedule swaps and exclusions): Opus 88%, Sonnet 87%, Haiku 88%, Meta Muse 85%, Subquadratic 85%; five-model majority 88% (105 of 120), pairwise agreement 96%, kappa 0.84; 12 posts wrong for all five. Random-post accuracy did not move because the fixed patterns are rare; the remaining errors are roster typos and short names ("Red Dod", "Sibo", "Gld Coast"), events in a second casual sentence, and wrong event type on plans. Fifth check (after the remainder pass: lift-name typos and short forms, a hold stated in a second sentence, electrical trouble, plans read as reopenings, count-only posts, "all chairlifts closed", download-only runs), on another 120 never-seen held-out posts: Opus 87%, Sonnet 86%, Haiku 86%, Meta Muse 85%, Subquadratic 82%; majority 85% (102 of 120); kappa 0.84. Across the two fresh samples after the fixes accuracy sits at 85 to 88%: what is left is a long tail (hedged wording, rosters that drop lifts after a time line, "expected for 9am", "removed from the schedule", cause labels for de-icing and mechanical trouble), each worth a few posts. They are models, not people. |
| Independent readers | Subquadratic and Meta Muse each labeled posts blind, without seeing the parser: Subquadratic all 7,044, Meta Muse 7,040 (4 calls failed). The parser agrees with them 93.1% and 97.3% of the time; they agree with each other 94.6%. Agreement is not truth. |
| Rulebook | Hold rules for 41 lifts, each tagged *inferred* (from weather) with the *observed* counts kept beside it |

**What the rules show** (leave-one-winter-out; details and every number in [docs/RESULTS.md](docs/RESULTS.md)):
- A wind line of about 60 mph gusts at the crest predicts which days see a wind hold. It is stable across winters and beats a 25 mph rule in all 8 (day-level F1 0.73 to 0.88 against 0.37 to 0.71).
- Which lift holds is harder. On expected lift-days (scheduled, plus lifts under a whole-mountain closure), separate per-lift rules do slightly better than one learned wind line (pooled F1 0.66 against 0.63); the 25 mph rule has high recall and very low precision (F1 0.48).
- **"All lifts closed" is an event, and it is predictable** (what counts as a closure, by kind and conditions: [docs/CLOSURES.md](docs/CLOSURES.md)). 51 whole-mountain closure days are counted from the posts (46 graded high confidence, 5 medium). Closures were rare below 100 mph gusts (3 to 6% of days), 20% of days at 100 to 130 mph and 55% at 130 and above. Avalanche danger 4 closed the mountain on 46% of days. National Weather Service Winter Storm and Blizzard Warnings add a little (7 of the 8 days under a Blizzard Warning were closure days), but avalanche danger adds far more beyond wind (see [docs/CLOSURES.md](docs/CLOSURES.md)).
- **Storm days start late.** With wind under 60 mph, 27% of lifts were held or closed on days with 2+ in of new snow, 1+ in of snow water or avalanche danger 3+, against 7% on other days (55 such days).
- **Hours beat the peak gust.** With a 60 to 100 mph peak, a Tram or Funitel hold came on 17% of days with 2 hours or less at 60 mph or more, and 62% with more than 5 hours. Wind direction adds nothing once duration is counted; south-west storms simply last longer.
- When a gateway (Tram or Funitel) holds, 77% of upper-mountain lift-days hold with it, 70% on days without a whole-mountain closure; when neither holds, 14%.
- Mechanical and lightning holds are only weakly predictable from these weather files.
- **Wind at the moment of the call.** In the three hours before the post, the Siberia crest gust had already reached a median of 77 mph before a Tram wind hold, 98 before a Funitel hold, 78 before an upper-mountain lift, 91 for Alpine lifts and 107 for lower lifts; 88 to 97% of wind holds followed an hour with gusts of 60 mph or more. A third of wind holds were called before the day's peak.
- **Holds with no named cause (1,446 of 5,413) get an inferred cause.** A model fitted on the holds whose post names one cause, using weather, the date and the cause words in the day's other posts (avalanche control, power, lightning, ice), recovers the named cause 80% of the time on winters it never saw (69% by always guessing wind). It is confident on 60% of the unstated holds. Inferred causes are kept apart from observed ones: [docs/CAUSES.md](docs/CAUSES.md).
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
| National Weather Service Reno office alerts (Iowa Environmental Mesonet archive) | Winter Storm, Blizzard, High Wind and flood alerts for the Greater Lake Tahoe Area zone, 2018 onward | `scripts/pull_nws.py` (free, no key) |
| Season dates found on the web | Opening and closing days per side and winter | `rules/season_windows.json` (evidence file, with confirmed and unconfirmed marked) |

The scripts used once to find each source's depth and request format (probe scripts for the X and weather APIs) were removed on 2026-11-09 after their findings were written into this file; they remain in the git history.

## Data architecture

Start with `docs/DATA_GUIDE.md`: every dataset, how far to trust it, its assumptions and gaps, and which source to use for which question.


| Layer | Where | Rule |
|---|---|---|
| Raw | `data/raw/` (git-ignored; counts and hashes in `docs/RAW_INVENTORY.md`) | Never edited. Posts, 15-minute station files, SNOTEL, avalanche forecasts, NWS alerts |
| Parsed events | `data/derived/*_events.json` | One row per status event, stamped with `parser_version`. Observed `cause` and post-level `cause_tags` |
| Lift-day table | `data/derived/lift_days.csv` | One row per lift per local day. Outcomes come only from posts; features only from weather. Every column is described in `rules/features.json` (role, when it is known, unit, source) |
| Inferred | `data/derived/cause_inferred.csv` | Modelled causes for holds whose post names none. Never mixed into the observed columns |
| Results | `results/`, `docs/RESULTS.md`, `docs/numbers.json` | Scores are leave-one-winter-out; the quoted numbers are checked against the data |
| App | `docs/app/model.js` | A pure view of the results; the page recomputes nothing |
| Source registry | `rules/sources.json`, `rules/winters.json` | Every source with its role, pull script, winters, as-of, clock, cost and redistribution; per-winter coverage generated from the files |
| Commentary | `data/derived/blog_posts.csv`, `blog_text.jsonl`, raw forecaster and NWS text | Human narrative for spot checks (`scripts/commentary.py <date>`); never fitted, enforced by `scripts/check_architecture.py` |

How a change is made safe: the parser carries a version and a golden test per behaviour; `scripts/diff_events.py` shows which posts a change touched; `scripts/check_data.py` checks the output (values, order, quality flags, column registry); `scripts/check_numbers.py` finds stale copies of headline numbers; `scripts/check_architecture.py` checks the source registry, raw hashes, frozen samples, clocks and that commentary is never fitted; `scripts/run_all.sh` rebuilds everything in about a minute; `scripts/manifest.py` records what produced the build. When a number describes a day (full-day gust) it is labelled as hindsight; only morning (as-of) features are presented as a prediction. A validation sample of 320 held-out posts is frozen in `results/validation_sample_ids.json` and graded once.

## Re-running

In order: `scripts/parse_posts.py <year> <train|heldout>` for each winter, `scripts/pull_nws.py`, `scripts/build_dataset.py 2018 ... 2025`, `scripts/recover_rules.py`, `scripts/baselines.py`, `scripts/infer_causes.py` and `scripts/closure_conditions.py` (they write docs/CAUSES.md and docs/CLOSURES.md; numpy needed), then `scripts/build_app_model.py` (writes the app's only data file) and `scripts/check_app_model.py` (fails if the app's numbers differ from the results); tests with `python3 -I tests/golden.py`.

Raw data goes in `data/raw/` (git-ignored). Scripts read API credentials from files kept outside the repo, never from the repo itself.
