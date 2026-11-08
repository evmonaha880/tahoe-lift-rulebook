# What the operators say in their own words (Operations blog, read 2026-11-07)

**Source.** 75 articles of the Palisades Tahoe Operations blog (https://blog.palisadestahoe.com/category/operations/), chosen for storms, closures, wind, power, ice, avalanche work and season dates, December 2017 to October 2026. The site sits behind a bot wall, so the pages were read through Firecrawl and extracted by model readers (stated facts only, quotes up to 25 words). The 175 stated rules are in `rules/blog_stated_rules.json`. This is evidence for checking and for new hypotheses; none of it feeds the model.

## What it confirmed in our data
| Check | Result |
|---|---|
| Full-resort closure days the blog announces (Dec 26 2021, Mar 10 2023, Mar 14 2023, Mar 1 to 3 2024, Feb 19 2026) | All are closure days in our table, on the right side(s) |
| Feb 17 2026: the blog says all lifts at Palisades and Alpine closed at 12:15 PM | Our table has Palisades only that day: the ops account's posts we pulled show the Palisades closure (11:33 AM) and no Alpine closure post; a gap in the posts, not in the parser |
| Closure days only we have (Dec 30 and 31 2022, afternoon closures) | Plausible: the blog for that storm describes delays and holds, not an all-day closure; we record the afternoon closure from the posts |
| Alpine and Palisades season ends (2021-22 Apr 17 / May 30, 2022-23 Alpine to Jul 4, 2023-24 Alpine Apr 28 / Palisades May 27, 2025-26 Alpine Mar 29 / Palisades May 25) | Match `rules/season_windows.json`; three dates were added or tightened from the blog and moved no lift-day |
| Base to Base Gondola opened Dec 2022 | Our table has no gondola lift-day before 2022-12-17 |
| "Winds over 100 mph are normally not cause for full closure, but compounded weather led to closure" (Mar 13 2023) | Same as our closure table: 20% of days at 100 to 130 mph, 55% above 130, and 35% with 100+ mph and avalanche danger 3+ |
| "Lower mountain lifts open first, then the Funitel, then the upper mountain" after a storm | On 23 recovery days (the day after a Palisades closure): earliest reopen post median 09:20 for the lower-mountain lifts, 10:47 for the Funitel, 10:31 for the upper-mountain lifts (small sample) |

## The wind-hold rule as the operators state it (2017 and 2022)
Five factors: anemometer readings and physical testing (nobody tries a lift at a reading near 120 mph; at 20 to 50 mph they go to the lift, run it and watch), wind speed and direction (a lift and wind vulnerability chart), chair swing against the manufacturer's limits (front-back and side-to-side), gusty versus steady wind (gusty is worse), and the NWS forecast (high and rising: close; marginal and falling: wait on wind hold). The Funitel has an automatic wind sensor that prevents running, and a chair hitting a tower shuts a lift down automatically. Many popular lifts sit on the Sierra crest. "Funitel on wind hold signals serious wind." Olympic Lady cannot run in large wind events.

What this says about our model: speed, direction, gustiness and the morning forecast are all named factors. We have tested speed, hours over a speed, direction and gust factor; the forecast factor is the one we cannot reconstruct from station data (see "Next data layer" below).

## Other stated rules that explain unstated causes
- **Ice (rime):** every grip must be cleared by hand before an upper-mountain lift can run; lifts are spun overnight ("night bump") to prevent it when wind allows. Explains many delayed openings that name no wind.
- **Avalanche control:** no chairlift can open after a large storm without it (examples named: First Venture, Subway, Meadow); up to 49 routes on a full day; needs daylight and visibility; closing the day before lengthens the next day's work.
- **Opening order after a storm:** lower mountain first (Resort Chair, First Venture, Far East, Red Dog, KT-22), then the Funitel if Tower 4 clearance allows, then the upper lifts; Alpine: Subway, Meadow, Treeline mid-station, Sherwood, Roundhouse.
- **Lightning:** all lifts held whenever a strike is detected within 30 miles; all personnel movement stops.
- **Anticipated Weather Impact (AWI):** lifts are scheduled as AWI the afternoon before a storm; on Feb 17 2026 the AWI lifts were targeted for about 11am.
- **When status is published:** next-day lift status at 5:30 pm the day before (2025), after 4 pm (2023), with an update by 7 am. Our "later-day" announcement handling matches this.
- **Power:** an Alpine outage kept two lifts on auxiliary power (Dec 2021); Alpine "will open once power is restored" (Feb 2025).

## Lift history that matters for per-lift rules
Red Dog was replaced by a high-speed six-pack for 2022-23; the hold rate above 80 mph is similar before and after (32% against 25%). The Funitel haul rope was replaced in June 2023 (hold rate above 80 mph 42% before, 46% after). The Base to Base Gondola opened Dec 17 2022. Silverado opens only with enough snow for its access road (open Feb 12 2025). The Aerial Tram was rebuilt in fall 2026.

## Next data layer (free)
The forecast is a named factor and the one input we lack. NOAA's HRRR forecast archive (3 km, hourly, surface gusts, on AWS since 2014, no account needed; `s3://noaa-hrrr-bdp-pds`, readable with the Herbie package) holds what the model forecast each morning for all eight winters. That would give a real as-of morning gust forecast for the crest. Not built: needs an evaluation against our station gusts first. OpenSnow is not needed for this: its history is 15 days and its forecasts have no archive or export.
