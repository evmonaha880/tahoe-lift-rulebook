# Data guide: what we have, how far to trust it, and what to use it for

Written 2026-11-08. One page that answers: what is each dataset, what is it assumed to mean, where are the gaps, how accurate is it, and which source to reach for in which situation. The registry behind it is `rules/sources.json` (every source) and `rules/winters.json` (coverage by winter, generated). Labels: **VERIFIED** = tested here with the number given; **UNVERIFIED** = read or assumed, not tested.

## 1. Trust tiers (best to weakest)

| Tier | Meaning | Sources |
|---|---|---|
| **A. Official measurement** | An instrument or an official report, no model in the loop | Resort crest stations (Siberia, Belmont, Roundhouse Btm, Summit, others) hourly and 15-minute; SNOTEL 784; NWS storm reports (peak gusts, snowfall); NWS alerts (IEM VTEC); Truckee airport |
| **B. Operator statement parsed by rules** | The ops account's own words, read by our parser | Ops tweets to lift-day events (post-level accuracy 87.5%, interval 83.4 to 90.7, frozen sample of 320, graded by three models; row-level fully right on about 72% of replayed days) |
| **C. Operator statement read by a model** | The resort's blog read by two model readers, quotes checked | Season and lift calendar (672 facts; both readers agree on 43%; 664 of 672 quotes found word for word in their posts); lift history |
| **D. Derived from text** | A regex or a model reading human text | Blog forecast figures (`regex-v1`): rank correlation 0.72 with Siberia's day max gust over 335 days; 74 forecaster-tweet wind figures (43 usable days); NWS discussion ridge figure: regex 0.43 (not usable), model-read pilot 0.84 on 28 days (promising, small) |
| **E. Modelled estimate** | A reanalysis or regression standing in for a missing measurement | ERA5 and SNOTEL-based Siberia gust for 2015-16, fitted leave-one-winter-out (typical error 7 to 10 mph for the 05:00-09:00 gust, 9 to 12 mph for the day gust; `results/weather_common.json`); Funitel Top gust where the station was off (R2 0.89, error about 4 mph); ERA5 snowfall for 2015-18 (r 0.87 with base depth gain) |
| **F. Narrative** | Human commentary, for spot checks only | Blog posts, forecaster posts, NWS discussions. Never fitted (enforced by `scripts/check_architecture.py`) |

## 2. Every dataset: meaning, assumptions, gaps, use

| Winter | Ops tweets | Parsed | Station wind | Forecast days (blog, by 9am) | Blog ops / weather posts | Scheduled lift-days | Fit-eligible |
|---|---|---|---|---|---|---|---|
| 2015-16 | 729 | yes | none (estimate only) | - | 14 / 0 | 370 | 11-winter view only |
| 2016-17 | 1,052 | yes | hourly | - | 57 / 0 | 679 | 10- and 11-winter views |
| 2017-18 | 518 | yes | hourly, 15min from Feb | - | 12 / 0 | 279 | 10- and 11-winter views |
| 2018-19 | 963 | yes | 15min | - | 4 / 0 | 710 | yes |
| 2019-20 | 537 | yes | 15min | 2 | 6 / 2 | 296 | yes |
| 2020-21 | 743 | yes | 15min | 70 | 9 / 120 | 454 | no |
| 2021-22 | 803 | yes | 15min | 81 | 34 / 136 | 2346 | yes |
| 2022-23 | 1,752 | yes | 15min | 90 | 45 / 155 | 4169 | yes |
| 2023-24 | 984 | yes | 15min | 57 | 47 / 164 | 3609 | yes |
| 2024-25 | 810 | yes | 15min | 43 | 27 / 136 | 687 | yes |
| 2025-26 | 452 | yes | 15min | 34 | 37 / 129 | 128 | yes |

(Generated from `rules/winters.json`. 2015-16 to 2017-18 tweets are parsed and joined to weather in `lift_days_11w.csv` (the headline `lift_days.csv` is the 8 core winters, 2018-19 on); their wind is hourly or estimated, so they appear only in the 10- and 11-winter views (README). 2020-21 ran under COVID operating rules, so it stays in the replay but is out of lift-level fits.)

### Outcomes
| Dataset | What a row means | Assumptions built in | Gaps and errors | Use it for |
|---|---|---|---|---|
| Ops tweets, parsed events (`*_events.json`) | A status statement about a lift, side or the whole resort, with a start time and cause | Hedged wording ("expect delays") is a warning, not a hold (decision 23). Squaw One = Wa She Shu, Squaw Creek = Resort Chair. A roster announced for tomorrow belongs to tomorrow. Time is America/Los_Angeles | A hold nobody posted is invisible. Post-level 87.5%. About 40% of side-days in 2018-21 and 2024-26 give a lift count, not names. 2015-18 not parsed. Squaw-era wording not handled | What happened, when, and the stated cause. Not for lifts that never got a post |
| Lift-day table (`lift_days.csv`) | One lift on one local day: scheduled or not, held or not, cause, reopening | **Scheduled** = named in that day's roster, or began the day on hold (decision 58). **No reopening post means it did not reopen** (decision 36). Whole-side closure expands to every lift in the winter's typical roster (decision 28), which **counts lifts that had not yet opened or had already closed** (283 of 787 such rows are after a lift's last scheduled day; 29 before its first). A day is a Pacific calendar day; a winter is Oct 1 to May 31 | Per-lift rules rest mainly on 2021-22 to 2023-24. `late_open_implied` (180 rows) is flagged, not counted | The model's labels. Treat closure rows with the staged-opening caveat until the per-lift calendar lands |
| Season windows (`season_windows.json`, effective windows) | Open and close day per side | Union of web date and first and last roster day (decision 29) | Several nulls; two 2025-26 Palisades dates differ from the blog | Superseded by the blog calendar once wired in |

### Calendar and history
| Dataset | Meaning | Assumptions | Gaps | Use it for |
|---|---|---|---|---|
| Season calendar (`season_calendar_resolved.json`, `season_calendar.json`) | Opening and closing days, staged lift openings, closure days, per side | Dates are what the blog **announced**, not proof it happened. Latest non-cancelled statement wins. Before Sept 2021, "Palisades Tahoe" in a blog post means the Squaw side. Blog is the source of truth for edges (decision 62) | 2018-19 and 2019-20 have almost no operations posts; three dates to confirm (Palisades 2025-26 open and close, 2016-17 close) | Season edges, staged openings, closure causes. Check actual last day against tweets |
| Lift history (`lift_history.json`) | Construction and replacement that change what a name means | Hobbyist lift database used for machine types (UNVERIFIED) beside blog posts | No source says any lift now runs in higher wind, except Treeline Cirque's location | Splitting a lift's fit by era (Red Dog, Treeline Cirque, Base to Base Gondola, Siberia) |

### Weather features
| Dataset | Meaning | Assumptions | Gaps | Use it for |
|---|---|---|---|---|
| Resort stations hourly and 15-minute | Gust, speed, direction, temperature, pressure, snow depth at named stations | Files run on local time (two checks support it; the vendor does not label it). Day window 06:00 to 16:00, early window 05:00 to 09:00 | Fields grow from 11 to 36 over the years. Only Siberia, Belmont, Roundhouse Btm cover 2016-17 to 2025-26. Funitel Top missing or off in 7 of 10 winters (estimated, flagged). 171 dropout station-days. 15-minute starts Feb 2018. One data point suggests peak gusts read low (blog 195 vs feed 173, 2024-03-02) | Crest wind features, from 2016-17 |
| SNOTEL 784 | Snow water, depth, precipitation, temperature, wind at 8,010 ft | Standard-time clock (UNVERIFIED) | Depth spikes (the old new-snow figure reached 121 in) | Snow water, long history, stand-in wind for 2015-16 |
| New snow 24 h (`new_snow24`) | Depth gain at the Alpine base station | Dropout-filtered | None before 2018-19 | Snow loading from 2018 |
| Avalanche danger (SAC) | Backcountry danger rating, one zone | Used as a signal for patrol holds | Coverage 0 to 88% before 2021; mid-April stop | Patrol and late-open signal |
| NWS alerts | Watches and warnings in force | `nws_pre_*` = in force at 06:00 | Wind alerts add nothing beyond measured gusts | Storm context |
| Truckee airport | Labelled-clock observations | Valley site | Correlation 0.62 with Siberia | Clock checks only |
| ERA5 and SNOTEL combined | Estimated Siberia gust and snowfall | Flagged `estimate` in `gust_src_early` when used | Typical error 7 to 10 mph (early gust), 9 to 12 (day gust); compresses high gusts | 2015-16 only; 2016-17 and early 2017-18 use hourly station values (`station_hourly`); the 10-winter view leaves 2015-16 out |

### Forecast
| Dataset | Meaning | Assumptions | Gaps | Use it for |
|---|---|---|---|---|
| Blog forecast (`blog_forecast.csv`) | The forecaster's ridge gust figure for the day, read by regex | Usable as a morning input only if posted by 09:00 (804 of 849 were). "60-70+" stored as 70 with a lower-bound flag | 2020-21 on; 377 days with a gust figure; text rules can miss figures | Morning forecast feature; adds about +0.01 where a figure exists and +0.05 over all days (day level, six winters) |
| Forecaster tweets, NWS discussions | Narrative forecast | Not parsed into a feature | Tweets: no wind numbers before 2017-18. NWS discussion figure covers whole multi-day text | Spot checks only |

## 3. Which source for which question

| Question | Reach for | Then check with | Do not use |
|---|---|---|---|
| Did a lift hold today, when, why? | Parsed ops tweets | `scripts/commentary.py DATE` (blog, NWS) | Blog alone (too few days) |
| When did the season really open or close, by side? | Blog calendar (announced), then tweet rosters (actual last day) | Commentary for the post | Third-party date sites (wrong) |
| In what order do lifts open? | Tweet rosters (first scheduled day) plus blog first-run facts | Opening Progression note | Whole-side closure expansion |
| How windy was it at the crest? | Siberia and Belmont hourly or 15-minute | NWS storm reports (peak); blog quotes | Airport wind; ERA5 unless nothing else |
| 2015-16 wind | SNOTEL plus ERA5 estimate, flagged | Blog and NWS text | Treating it as measured |
| Morning forecast | Blog forecast figure, 2020-21 on. NWS discussion read by a model is the candidate for 2015-16 to 2019-20 (pilot only) | Commentary | The NWS discussion regex figure (rank 0.43) |
| New snow | Alpine base depth gain (2018+), SNOTEL snow water | NWS snowfall lines, Snow Lab | SNOTEL depth sum alone |
| Is a number or parse odd? | `scripts/commentary.py` | The raw post (`scripts/replay_day.py`) | Letting commentary change a rule without a held-out test |
| Which clock do the weather files use? | Truckee airport lag test (supports local time) | Vendor, if asked | Assuming |
| What does a lift name mean in year X? | `lift_history.json`, `lift_groups.json` | Blog | A single rule across a rebuild |

## 4. Assumption register (the ones that move numbers)

1. **Removed (decision 63).** No reopening post now means the end of the hold is unknown. Only 1,240 of 4,311 held lift-days have an observed reopening. For wind holds the old assumption was usually right (94% of those days stayed windy through the afternoon); for mechanical, weather, patrol and unstated causes it was not safe.
2. A lift on hold before 09:00 is a lift on hold and was meant to run (decision 58, confirmed by Evan 2026-11-08; the posts say "will begin the day on wind hold"). It added 1,741 lift-days, mostly holds, so pooled F1 rose by about 0.08: that rise is the definition, not a better model.
3. Whole-side closure expands only to lifts that had opened and not yet closed for the season (decision 65, replacing the winter-wide roster of decision 28): 272 of 788 expansion rows removed. Windows come from tweet evidence; sides with fewer than 20 named-roster days in a winter keep the old expansion and are flagged (`closed_all_basis`).
4. Hedged language is a warning (decisions 23, 35). Models graded it differently.
5. Winter 2020-21 is excluded from lift-level fits (decision 38).
6. Lift-level rules are fitted on side-days whose schedule post names the lifts (82%).
7. The ops account posts what operators decided; undecided or unposted holds are not in the data.
8. Weather files run on local time; day and early windows are fixed clock windows.
9. Calendar dates are announcements, not outcomes.
10. Estimated values (Funitel gust, 2015-16 wind, ERA5 snow) are always flagged and scored apart.

## 5. Gap register

| Gap | Size | Mitigation | Status |
|---|---|---|---|
| 2015-18 tweets unparsed | 3 winters, 2,299 posts | Parse on training posts only; samples frozen | open |
| Staged openings | 272 closure rows for lifts not open that day removed | Per-lift windows from tweet evidence (decision 65); blog first-run dates as a cross-check; walk-through with Evan per season | done for closures; walk-through open |
| No station wind in 2015-16 | 1 winter | SNOTEL plus ERA5 estimate | designed, not built |
| Weather inputs differ by winter | all | Common set from Siberia, Belmont, SNOTEL | designed, not built |
| Forecast column only 2020-21 on (blog) | 6 winters | **NWS Reno forecast discussions cover all 11 winters** (a pre-9am issuance on every day, 2,673). A blind model-read pilot of 132 days: when the text gives a ridge figure (28 of 116 days with a station reading) rank correlation with Siberia is **0.84**, against 0.43 for the first regex; days where the reader found no ridge wind in the text had 20% windy days (55+ mph), days called calm 6%, days with a figure 68%. Tiny sample; wind-hold prediction not yet tested | pilot positive; full run on about 1,450 days with ridge wording needs a decision |
| Lift eras and gondola mode not in the table | 4 lifts | `lift_era`, `operating_mode` columns | open |
| Peak-gust under-read | 1 data point | Compare feed with NWS peak reports by storm | open |
| No independent truth for holds | all | Spot checks, hand check of 52 posts still with Evan | open |
| Blog edges for 2018-19, 2019-20 | 2 winters | Tweets | open |
| Snow depth before 2018 | 3 winters | ERA5 snowfall, flagged | designed, not built |

## 6. How to keep this true
`scripts/build_winters.py` regenerates the coverage table; `scripts/check_architecture.py` fails the build if the registry, raw hashes, frozen samples or the commentary rule drift; this file is hand-written and should be updated when a source changes tier or an assumption changes (add it to the same commit).
