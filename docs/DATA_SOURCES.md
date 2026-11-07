# Data sources

Status key: **VERIFIED** = tested on 2026-11-07. **UNVERIFIED** = read about, not tested. Credentials live outside the repo. Raw data goes in `data/raw/` (git-ignored).

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
- **Gotchas:** wording and format change across eras (UNVERIFIED for Palisades; observed at another mountain's feed). Raw posts must not be redistributed. Replies (customer questions) may or may not carry cause information: decision pending.

## 2. Weather stations: Western Weather Group public report builder
- **What:** Palisades Tahoe's own weather site. 13 stations, up to 40 fields. **VERIFIED:** no login needed.
- **Site:** `palisadestahoe.westernweathergroup.com`
- **Stations (codes):** BMT Belmont 8000', FNT Funitel Top 7966', KT22 KT Top 8000', OVB Base 6200', RHB Roundhouse Btm 6950', RHT Roundhouse Top 7880', SCB Scott Btm 7075', SCT Scott Top 8120', SHR Sherwood Btm 7115', SIB Siberia 8700', SUM Summit/Ward Mt 8643', TLC Treeline Cirque Mid 7555', YVH Yellow Valve House 7640'.
- **Method (VERIFIED):** `GET /reports/export/csv?data=<base64 of a JSON spec>`. Spec keys: `Stations`, `Groups`, `Fields`, `Deltas`, `Interval`, `Type: "Tabular"`, `DateRange` = `{"$type":"WesternWeatherGroup.CustomReportDateRange, WesternWeatherGroup.Core","Start":"YYYY-MM-DD","End":"YYYY-MM-DD"}`. Helper endpoints (POST): `/reportbuilderapi/stations`, `/intervals`, `/fields`, `/datetypes`. Script: `scripts/pull_wwg.py`.
- **Intervals:** 1440 daily, 60 hourly, 15 fifteen-minute, 1 one-minute. One-minute returned nothing in a test (FNT and KT22, Dec 2023).
- **Fields (40 codes):** wind speed/gust/direction/gust direction; second wind sensors labelled Tower 20, FT-Ridge, FT-284 (**what lift they sit on is UNVERIFIED**); temp, RH, wet bulb, dew point, wind chill, heat index, pressure; precip (latest, daily, 24h, storm); snow (new, depth, hourly, daily, 24h, storm, water equivalent); equipment health (battery, panel temp); fire weather index. Fields available differ by station.
- **Depth (sampled Dec 15-16 each year, VERIFIED but sampling can miss outages):** hourly from Dec 2016 (7 stations); 15-minute from about Dec 2018. Funitel Top appeared from about Dec 2019 and not in the Dec 2025 sample; KT Top and Base appeared only in the 2025 sample. In the first full winter pulled (2016-17, hourly): wind at Siberia, Ward Mt, Roundhouse top and bottom, Scott Top, Sherwood Btm (from Oct 1-6, 2016) and Belmont (from Oct 20, 2016); snow fields mostly empty that winter.
- **Pulled so far:** hourly Oct 2016 to May 2026 (80 monthly files) and 15-minute pull in progress, in `data/raw/wwg/`. **Exact per-station first and last dates are still to be computed from the full pull.**

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

## 5. Sierra Avalanche Center: UNVERIFIED
- Daily forecast for the Central Sierra Nevada published at 7am; an observations archive exists at `archive.sierraavalanchecenter.org`.
- The forecast page needs a browser to render; a plain scrape returned no content. **What fields exist and whether history is downloadable are unknown.** It covers backcountry, not resort control work. Resort control work shows up in lift posts as "patrol".

## 6. Weather-service API (Synoptic): DEAD for history
- **VERIFIED 2026-11-07:** the account's token returned "no access to the requested history" for every history call, including last winter and another mountain. Metadata calls still work. Do not plan on it. Its station metadata was useful once for finding station lists.

## 7. Open-Meteo: backup, UNTESTED in this project
- Free historical and forecast weather API, no key, non-commercial up to 10,000 calls a day, data licensed CC BY 4.0 (from its docs). Modeled data, not ridge-top instruments, so it under-reads gusts on peaks. Use only if station data fails.

## 8. NWS hourly forecast API: for the later "today" module, UNVERIFIED here
- Free, no key. Not needed today.

## Earlier private work: reference only
The earlier private Tahoe Lift Call project left lift-day tables and X post pulls (Palisades 2023-24 and some 2025 slices; Heavenly 2023-24 through 2025-26). They are outside this repo. Observed in them: the 2023-24 pull was incomplete (909 of 1,171 posts). Use only as an independent check on the new parser, never as an input.
