# Data sources

Final counts: 7,044 X posts (originals only) across 8 winters, 24,445 parsed events, 15,567 lift-days (10,439 scheduled; 874 more are lifts that normally run on a whole-mountain closure day, now counted as expected; 88 fall outside the season windows; 224 expected lift-days in the 2020-21 COVID winter are left out of lift-level fits).

New columns in `lift_days.csv` (2026-11-07 evening): `closed_all`, `closed_all_time`, `closure_kind`, `closure_conf`, `closure_readers`, `closure_plausible`, `in_season`, `side` (palisades, alpine or link), `tag_*` multi-label cause words, `day_*` counts of cause words in all of that day's posts (avalanche control, power, lightning, ice, visibility, mechanical, flood or road, COVID), `n_posts_day`, `covid_era`, `reopen_posted`, `hold_minutes`, `reopen_assumed_none`, `sib_h40`, `sib_h60`. Inferred causes are in `data/derived/cause_inferred.csv`, never in `lift_days.csv`. Status key: **VERIFIED** = tested on 2026-11-07. **UNVERIFIED** = read about, not tested. Credentials live outside the repo. Raw data goes in `data/raw/` (git-ignored).

## 1. Lift status posts: Palisades ops account on X
- **What:** the resort's operations account posts lift status (holds, reopenings, delays, schedules, and other operational notes). These are the events to explain.
- **Access:** X API, pay per use, **$0.005 per post read**, full-archive search (`from:` queries). Counts endpoint costs $0.01 per request and was used for sizing (about $1 spent). Credit balance and spend are tracked privately. Dedup: re-reading the same post in the same UTC day is free (per X docs).
- **Post counts per winter (VERIFIED by counts endpoint; query was `from:palisadesops`, so includes replies and retweets; originals-only counts not yet sized):**

| Winter | Posts | Cost to pull |
|---|---|---|
| 2016-17 | 1,571 | $7.86 |
| 2017-18 | 659 | $3.29 |
| 2018-19 | 1,250 | $6.25 |
| 2019-20 | 612 | $3.06 |
| 2020-21 | 943 | $4.71 |
| 2021-22 | 1,133 | $5.67 |
| 2022-23 | 2,279 | $11.39 |
| 2023-24 | 1,171 | $5.86 |
| 2024-25 | 826 | $4.13 |
| 2025-26 | 448 | $2.24 |
| **Total** | **10,892** | **about $54.46** |

- **Plan:** one winter at a time, starting 2023-24, then 2024-25, 2025-26, then older. See `PARSING_RULES.md`.
- **Gotchas:** wording and format change across eras (UNVERIFIED for Palisades; observed at another mountain's feed). The raw pull files are kept out of git; the app shows the text of public posts beside the events parsed from them. Replies (customer questions) may or may not carry cause information: decision pending.

## 2. Weather stations: Western Weather Group public report builder
- **What:** Palisades Tahoe's own weather site. 13 stations, up to 40 fields. **VERIFIED:** no login needed.
- **Site:** `palisadestahoe.westernweathergroup.com`
- **Stations (codes):** BMT Belmont 8000', FNT Funitel Top 7966', KT22 KT Top 8000', OVB Base 6200', RHB Roundhouse Btm 6950', RHT Roundhouse Top 7880', SCB Scott Btm 7075', SCT Scott Top 8120', SHR Sherwood Btm 7115', SIB Siberia 8700', SUM Summit/Ward Mt 8643', TLC Treeline Cirque Mid 7555', YVH Yellow Valve House 7640'.
- **Method (VERIFIED):** `GET /reports/export/csv?data=<base64 of a JSON spec>`. Spec keys: `Stations`, `Groups`, `Fields`, `Deltas`, `Interval`, `Type: "Tabular"`, `DateRange` = `{"$type":"WesternWeatherGroup.CustomReportDateRange, WesternWeatherGroup.Core","Start":"YYYY-MM-DD","End":"YYYY-MM-DD"}`. Helper endpoints (POST): `/reportbuilderapi/stations`, `/intervals`, `/fields`, `/datetypes`. Script: `scripts/pull_wwg.py`.
- **Intervals:** 1440 daily, 60 hourly, 15 fifteen-minute, 1 one-minute. One-minute returned nothing in a test (FNT and KT22, Dec 2023).
- **Fields (40 codes):** wind speed/gust/direction/gust direction; second wind sensors labelled Tower 20, FT-Ridge, FT-284 (**what lift they sit on is UNVERIFIED**); temp, RH, wet bulb, dew point, wind chill, heat index, pressure; precip (latest, daily, 24h, storm); snow (new, depth, hourly, daily, 24h, storm, water equivalent); equipment health (battery, panel temp); fire weather index. Fields available differ by station.
- **Pulled (VERIFIED, 2026-11-07):** all 10 winters, Oct 1 to May 31 each. Hourly: 80 monthly files. 15-minute: 80 monthly files, but 15-minute data only starts in Feb 2018. About 240 MB total in `data/raw/wwg/` (git-ignored). No failed requests.
- **Wind coverage per station, from the full pull** (first day with wind speed; share of each winter's Oct-May hours with data, 15-minute from 2018-19, hourly for 2016-17 and 2017-18):

| Station | First data | Full winters | Gaps and notes |
|---|---|---|---|
| Siberia 8700' (SIB) | 2016-10-01 | all 10 | 87 to 99% |
| Belmont 8000' (BMT) | 2016-10-20 | all 10 | 88% in 2016-17 (late start), then 97 to 100% |
| Roundhouse Btm 6950' (RHB) | 2016-10-01 | all 10 | 88 to 100% |
| Roundhouse Top 7880' (RHT) | 2016-10-01 | all 10 | 15-minute has it for 2018 onward; hourly shows 0% after 2017-18 |
| Summit / Ward Mt 8643' (SUM) | 2016-10-01 | 2016-17 to 2025-26 | 15-minute 83 to 100% from 2018-19; hourly misses 2018-19 to 2021-22 |
| Scott Top 8120' (SCT) | 2016-10-02 | all 10 | 64 to 99% |
| Sherwood Btm 7115' (SHR) | 2016-10-06 | partial | 0% in 2019-20 to 2022-23, 18% in 2023-24 |
| **Funitel Top 7966' (FNT)** | **2019-04-05** | 2019-20 to 2022-23, 2024-25 | **23%, 46% and 45% in 2018-19, 2023-24 and 2025-26** |
| Treeline Cirque 7555' (TLC) | 2022-12-27 | 2023-24 on | 64% in 2022-23 |
| Base 6200' (OVB) | 2025-02-06 | 2025-26 only | 47% in 2024-25, 91% in 2025-26 |
| **KT Top 8000' (KT22)** | **2025-10-23** | **none** | **2025-26 only, 90%** |

- **Data-quality rules learned:** (1) The hourly export is incomplete for some stations that the 15-minute export has (Summit, Roundhouse Top), so use 15-minute from 2018-19 on and hourly only for 2016-17 and 2017-18. (2) Hourly 2017-18 has more than one row per hour at some stations (up to 127% of expected): de-duplicate before use. (3) Scott Btm and Yellow Valve have temp and humidity only, no wind.
- **Second wind sensors:** FT-Ridge and FT-284 wind speed appear only at Ward Mt summit and only in 2025-26. Tower 20 has no data in any month pulled. They are not usable as historical features.
- **Snow depth at the stations** exists only at Roundhouse Btm (from 2018-04-27), Belmont (from 2018-05-31) and Base (from 2025-02-06). SNOTEL (section 3) is the long snow record.
- **Consequence for lift-specific wind:** only Funitel has a multi-winter lift-top record, with gaps. KT Top has one winter. Other lifts must be matched to the nearest ridge station. Lift-to-station mapping is a modeling decision, not data.

## 3. SNOTEL site 784, Palisades Tahoe (NRCS)
- **What:** snow sensor at 8,010 ft, 39°11'N 120°16'W, Placer County, near the Siberia station. **VERIFIED.**
- **Depth:** reporting since 1979-10-01; snow depth since 1998-06-17; wind since 2008-08-11.
- **Access (VERIFIED, free, no key):** NRCS report generator CSV. Pattern: `https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customSingleStationReport/hourly/784:CA:SNTL%7Cid=%22%22%7Cname/START,END/WTEQ::value,SNWD::value,PREC::value,TOBS::value,WSPDV::value,WSPDX::value,WDIRV::value` (dates as YYYY-MM-DD). Script: `scripts/pull_free.py`.
- **Pulled:** hourly Oct 1 to May 31 for 18 winters (2008-09 to 2025-26), about 5,800 rows each. Wind present nearly everywhere; 2017-18 about 19% blank.
- **Columns:** snow water equivalent, snow depth, accumulated precipitation, air temperature, wind speed average and maximum, wind direction.

## 4. El Niño indices: NOAA CPC
- **ONI:** `https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt`. **RONI:** `https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt`. **VERIFIED:** 1950 to ASO 2026 (ASO 2026: ONI 2.46, RONI 1.97). Free. Pulled by `scripts/pull_free.py`.
- NOAA's current monitor is RONI; keep both.
- Context: CPC El Niño Advisory, next discussion scheduled Nov 12, 2026.
- **Winter labels (VERIFIED from the files; Dec-Jan-Feb value; ONI / RONI):**

| Winter | ONI | RONI | Label (by ONI) |
|---|---|---|---|
| 2009-10 | +1.47 | +1.44 | moderate El Niño |
| 2014-15 | +0.73 | +0.54 | weak El Niño |
| 2015-16 | +2.50 | +2.14 | very strong El Niño |
| 2016-17 | -0.08 | -0.60 | neutral (La Niña by RONI) |
| 2017-18 | -0.71 | -1.08 | La Niña |
| 2018-19 | +0.99 | +0.68 | weak El Niño |
| 2019-20 | +0.71 | +0.14 | weak El Niño (neutral by RONI) |
| 2020-21 | -0.99 | -1.32 | La Niña |
| 2021-22 | -0.76 | -1.18 | La Niña |
| 2022-23 | -0.55 | -0.86 | La Niña |
| 2023-24 | +1.84 | +1.13 | strong by ONI, moderate by RONI |
| 2024-25 | -0.46 | -1.10 | neutral by ONI, La Niña by RONI |
| 2025-26 | -0.39 | -0.91 | neutral by ONI, La Niña by RONI |

- **Consequence:** only three winters with lift posts and stations are El Niño winters (2018-19 weak, 2019-20 weak, 2023-24 strong or moderate depending on the index). All are weaker than the very strong event forecast for 2026-27. The best strong analog, 2015-16, predates the station records; whether the ops account posted lift status that winter is **not checked**. El Niño findings from this data are an extrapolation and must be labelled as such.

## 5. Sierra Avalanche Center: public API, VERIFIED and PULLED 2026-11-07
- **Access:** `https://api.avalanche.org/v2/public/products?avalanche_center_id=SAC` returns JSON with no key. One call returned 3,033 products (3 MB). The `date` parameter did not filter, so the whole archive comes back at once. Zone list: `.../products/map-layer/SAC` (one zone: Central Sierra Nevada).
- **Depth:** 2013-04-09 to 2026-11-07. Counts by type: 2,125 forecasts, 849 weather products, 59 summaries. About 150 products a year in 2014-2019, about 300 a year from 2020 (daily in season).
- **Fields on a forecast:** danger rating per elevation band (lower, middle, upper) for today and tomorrow, `bottom_line` text, `danger_level_text`, `json_data` (probably avalanche problems; **not yet inspected**), publish and expiry times. `weather_data` was empty on every record.
- **Limits:** one zone for the whole region. **Not verified that Palisades lies inside the zone.** It is a backcountry forecast, not resort control work; control work shows up in lift posts as "patrol". Likely use: daily danger rating as one signal for patrol-related holds and late openings.

## 6. Weather-service API (Synoptic): DEAD for history
- **VERIFIED 2026-11-07:** the account's token returned "no access to the requested history" for every history call, including last winter and another mountain. Metadata calls still work. Do not plan on it. Its station metadata was useful once for finding station lists.

## 7. Open-Meteo: backup, UNTESTED in this project
- Free historical and forecast weather API, no key, non-commercial up to 10,000 calls a day, data licensed CC BY 4.0 (from its docs). Modeled data, not ridge-top instruments, so it under-reads gusts on peaks. Use only if station data fails.

## 8. NWS hourly forecast API: for the later "today" module, UNVERIFIED here
- Free, no key. Not needed today.

## Earlier private work: reference only
The earlier private Tahoe Lift Call project left lift-day tables and X post pulls (Palisades 2023-24 and some 2025 slices; Heavenly 2023-24 through 2025-26). They are outside this repo. Observed in them: the 2023-24 pull was incomplete (909 of 1,171 posts). Use only as an independent check on the new parser, never as an input.

## 9. Data-quality fixes, 2026-11-07 (audit)
- **Avalanche danger:** forecasts before 2020 carry only the top-level `danger_rating`, not the per-band list. It equals the max of the bands in all 2,685 products where both exist, so it is used as the fallback. Coverage of lift-days: 2018-19 0 to 79%, 2019-20 0 to 87%, 2020-21 69 to 88%. Days after the center stops forecasting (mid-April) stay blank.
- **New snow in 24 hours:** the old figure (sum of SNOTEL depth increases) reached 121 inches because of sensor spikes. Replaced by the depth gain at the Alpine Roundhouse base station (15-minute depth, dropout-filtered), 97 to 100% coverage in every winter, correlation 0.55 to 0.87 with the SNOTEL water gain, maximum 36 inches. The old figure is kept as `new_snow24_snotel`.
- **Funitel-top wind:** the station returns no rows before Apr 2019, Feb to May 2024 and Nov 2025 to Feb 2026 (checked with direct single-station requests against the same source). Where missing, the daily max gust is ESTIMATED as 2.16 + 0.13 x Siberia + 0.72 x Belmont (R2 0.89 on 1,006 measured days, error about 4 mph). The column `fnt_src` says `measured` or `estimated`; the raw reading is kept in `fnt_measured`. 2025-26 readings are a different regime (R2 -0.26 against the earlier fit), so that whole winter uses the estimate.
- **Known limits:** estimates are not measurements; the Funitel estimate misses about 1 in 5 days at or above 40 mph. SNOTEL timestamps appear to be fixed standard time, which could shift the 9am snow reading by an hour in spring (unverified).

## 10. NWS watches, warnings and advisories: Iowa Environmental Mesonet archive. VERIFIED 2026-11-07
- **What:** National Weather Service Reno office events for the Greater Lake Tahoe Area zone (CAZ073: the zone choice is UNVERIFIED, read from the zone name, but it passes a spot check: Blizzard Warnings on 2023-02-28 and 2024-03-01 to 03, a Winter Storm Warning and flood alerts on 2023-03-14, a Winter Storm Warning on 2026-02-17).
- **Access:** free, no key: `https://mesonet.agron.iastate.edu/json/vtec_events_bywfo.py?wfo=REV&year=<year>` (`scripts/pull_nws.py`). 446 events for 2018 to 2026; raw files in `data/raw/nws/`, events in `data/derived/nws_alerts.csv`.
- **Columns in `lift_days.csv`:** `nws_hw_w` (High Wind Warning), `nws_hw_a` (watch), `nws_wi` (Wind Advisory), `nws_ws_w` / `nws_ws_a` (Winter Storm Warning / Watch), `nws_ww` (Winter Weather Advisory), `nws_bz` (Blizzard Warning), `nws_flood`, `nws_wind_any`, `nws_storm_any` (in force at any point 6am to 4pm Pacific) and `nws_pre_wind`, `nws_pre_storm` (already in force at 6am, what a morning-of forecast could have known).
- **What it adds:** Winter Storm and Blizzard alerts add a little for closures and lost lift-days beyond measured wind (closure AUC +0.024, lift-day log-loss -0.005); wind alerts add nothing beyond the measured gust; avalanche danger adds far more (closure AUC +0.082).

## 11. Wind at the hour of the call, and the nearest station to each lift
- **`gust_at_event`, `gust_prior3h`, `spd_at_event`:** Siberia crest gust and speed in the hour of the first post about the lift, and the strongest gust in the three hours before it.
- **`local_gust`, `local_station`:** the daily 6am to 4pm gust at the station judged nearest to each lift (`rules/lift_stations.json`, UNVERIFIED: no coordinates were used). Against the crest gust it raises the hold AUC by 0.01 to 0.04 for Shirley Lake, Big Blue, Headwall, Solitude, Silverado and the Tram, and lowers it for the Alpine lifts (mean change -0.02 over 25 lifts), so the rules still use the crest gust.

## 12. Hiking, runs and the season edges
Posts mentioning hiking or uphill travel by month: January 4, February 3, March 6, April 3, May 3, October 2 (of only 19 October posts), November 0, December 5. Run or trail closure wording: December 15, January 17, February 17, March 10, April 5, May 2, November 5. Neither is concentrated in the warm months; October is the one month where a large share of posts (2 of 19) is about hiking. Hike-only access is now a partial operation and runs such as Mountain Run are not lifts.


## 13. Time conventions and the daylight-saving check (2026-11-07)
- **Posts:** `created_at` is UTC; every event is stamped in America/Los_Angeles (offset in the string). A day is a Pacific calendar day.
- **Weather files (`data/raw/wwg/15min`)** carry a `Date` and `Time` (HHMM) that the vendor does not label with a time zone. Windows used: early 05:00 to 09:00, day 06:00 to 16:00 on that clock; Siberia hours are counted from 15-minute readings divided by 4.
- **Check, unverified against the vendor:** on 31 wind-hold events posted on daylight-saving dates, the Siberia gust profile around the post time peaks at the same offset as on 103 standard-time dates (one hour after the post-hour window), which fits a clock that follows local time. If the files were fixed to standard time the profile on daylight-saving dates would be shifted by one hour. The sample is small.
- **Sensitivity:** moving every window one hour earlier on daylight-saving dates (the case where the files are fixed to standard time) changes the pooled day-level F1 from 0.81 to 0.83 and the morning-only F1 from 0.76 to 0.76, and narrows the morning line from 47 to 55 mph to 48 to 51 mph. So the time convention is a known uncertainty worth about 0.01 to 0.02 of F1. Ask the vendor or find a second source with a stated time zone before calling it settled.
- **Daylight-saving days** have 23 or 25 hours; no feature uses a count of hours in a day, only fixed clock windows, so they need no special handling. Snow features read the SNOTEL hourly file at 09:00 on the file's own clock (`build_dataset.py snow_feats`); the clock convention of that file has not been verified.
