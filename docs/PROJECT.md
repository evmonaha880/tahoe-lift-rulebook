# Project: Palisades lift-hold rulebook

## Goal
Recover the unpublished rules that decide when Palisades Tahoe / Alpine Meadows lifts hold, open late, or close, then prove the rules on winters they were not built from. The learning goal (software archaeology as a skill) matters more than winning.

## Why it counts as software archaeology
The "system" is the operators' decision process. The evidence is partial and indirect (posts, weather readings). The method matches the problem statement: recover from traces, separate observed from inferred, and prove behavioral equivalence by predicting held-out days.

## Scope
| | Today (hackathon) | Later |
|---|---|---|
| Mountains | Palisades Tahoe + Alpine Meadows | Heavenly, Northstar, Kirkwood, Mt Rose |
| Product | Rulebook + replay (A) | "What to do this morning" module reading the same rulebook plus live feeds |
| Winters | All 8 pulled and parsed (2018-19 to 2025-26) | All available |

## Not wind-only
The first hypothesis (wind explains holds) was rejected as too narrow. Candidate causes:
| Cause family | Evidence fields |
|---|---|
| Wind | speed, gust, direction; lift-top sensors where they exist |
| Snow loading and avalanche control | snow per hour, 24-hour and storm snow, depth, snow water, precipitation |
| Rain vs snow, icing | temperature, wet bulb, humidity, dew point |
| Storm approach | pressure |
| Not in any weather file | mechanical, staffing, scheduled opening, calendar. These stay in an "unexplained" bucket, labelled as such. |

## Definitions (working, to be refined as parsing proceeds)
- **Hold:** a lift that was scheduled to run is stopped or not started, with or without a stated cause.
- **Delay / late open:** opens later than scheduled.
- **Partial:** limited operation (for example mid-station only, sightseeing only, shortened hours).
- **Closed day:** not operating for the day.
- **Winter:** Oct 1 to May 31, labelled by its start year (2023-24).
- **Observed vs inferred:** observed = stated in a post; inferred = estimated from weather when the post gives no cause. Never merged.

## Event schema (target)
`mountain, lift, event_type, start, end, cause, cause_source (observed|inferred), source_post_id, parse_rule_id, confidence`

Event types: scheduled_opening, hold_start, reopen, delay, partial, closed_day, parking, other (filtered).

## Output options
- **A (base): Rulebook + replay.** A page showing the recovered rules per lift (each tagged observed or inferred, with evidence counts) and a replay of a past morning: predict from early weather, then reveal what happened. Plus a scoreboard on unseen winters against a simple baseline. Static page, desktop only.
- **B (stretch): What-if sliders.** Pick wind, gusts, snow, temperature and time; see per-lift hold chance, expected reopening and which rule fired. Probabilities are honest counts ("held 87% of the time, 41 cases").
- The product is the rulebook and replay, not a chat agent and not a dashboard. The static app lives in `docs/app/` (live at https://evmonaha880.github.io/tahoe-lift-rulebook/app/). No what-if sliders and no chat agent were built.

## Final status (2026-11-07)
7,044 posts, 24,445 events, 153 posts (2.2%) matching no rule, 244 parser tests, about 90% of posts fully right on a 240-post hand check (plus or minus 5) before the evening's fixes, and 85 to 88% by five-model majority on two later sets of 120 never-seen posts. Two independent blind readers (Subquadratic, Meta Muse) labeled the posts; the parser agrees with them 93.1% and 97.3%. Results, with the simple rules shown where they win: [RESULTS.md](RESULTS.md). Limits: unposted holds are invisible; per-lift results rest mainly on three winters that name lifts; crest wind sensors dominate; Funitel-top wind is partly estimated; nothing here forecasts tomorrow.

## Testing
- Leave-one-winter-out: build rules on all winters but one, test on the one left out, rotate.
- Baseline to beat: a simple "wind over 25 mph" rule (to be confirmed).
- Show failures: rules that were rolled back, and where predictions miss.
- Likely judge question: "how do you know it isn't noise?" Answer: held-out winters, baseline, rule stability across winters.

## El Niño plan
- **Verified:** NOAA CPC (Oct 8, 2026) reports an El Niño Advisory with a strong-to-very-strong event likely through Jan-Mar 2027. NOAA says impacts are not guaranteed in any one place.
- **Verified (news analysis, Oct 17):** three seasonal models average about 17% less snow than normal near Tahoe in Nov-Dec and about 28% more in Jan-Mar, with the models disagreeing. Warm storms can rain at the 6,200 ft base while snowing on the upper mountain.
- Label every winter with ONI/RONI phase (El Niño, neutral, La Niña) from the index files, then compare hold behavior across phases.
- Archetype days defined from station data (for example warm rain-on-snow storm, windy cold front, east-wind day, calm cold day, heavy-snow patrol day). To be derived from the data, not assumed.
- Replay of winter 2023-24. That it was a strong El Niño winter is from memory and **unverified**; confirm from the index file.
- Not supported by the data: a synthetic whole-winter simulator. Offer archetype scenarios, framed as "what these days tend to look like", not a forecast.

## Hackathon facts (from the participant guide)
- New work only; the demo may show only what was built at the event. Public repo, up to 4 per team, start from an empty repo, commit often.
- Round 1: about 3 minutes live demo plus 1-2 minutes Q&A. Weights: working demo 35%, implementation difficulty 30%, impact 20%, creativity 15%. Top 6 go to a second round.
- Submission: 1-minute demo video, public repo, demo link, all teammates added. Due 5:00pm PT.
- Banned: AI mental health, basic RAG, Streamlit, image analyzers, AI-for-education chatbots, job-application screeners, nutrition coaches, personality analyzers, medical advice, any project where a dashboard is the main feature, sports analyzers or coaches.
- Whether data collected before the event, and tables derived from it, are acceptable to the organizers is **unconfirmed**. The code in this repo was all written at the event.
