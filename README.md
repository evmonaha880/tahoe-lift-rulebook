# Palisades lift-hold rulebook

Software archaeology on a system nobody wrote down: **when and why do Palisades Tahoe lifts hold, open late, or close?**

The lift operators follow rules that are not published. The only evidence is what they posted and what the weather was doing. This project recovers those rules from that evidence, keeps what was *observed* separate from what was *inferred*, and tests each rule on winters it never saw.

Built from an empty repo on 2026-11-07 at the AIE Code Summit Hackathon (problem statement: Software Archaeology). All code here was written during the event. Data is pulled from public sources.

## Status

Work in progress. Data collection scripts first, analysis next. Nothing here claims results yet.

## Data sources

| Source | What | How it is pulled |
|---|---|---|
| Palisades Tahoe / Alpine Meadows weather stations (Western Weather Group public report builder) | Wind, gust, direction, temp, humidity, pressure, snow and precipitation, 13 stations, hourly from Oct 2016 and 15-minute from about 2018 | `scripts/pull_wwg.py` |
| NRCS SNOTEL site 784, Palisades Tahoe | Hourly snow water, snow depth, temperature, wind, 2008 onward | `scripts/pull_free.py` |
| NOAA CPC ONI and RONI indices | El Nino / La Nina phase by season, 1950 onward | `scripts/pull_free.py` |
| Palisades mountain operations account on X | Lift status posts (the events to explain) | X API, pay per use. Raw posts are not redistributed. |

`scripts/pull_probe*.py`, `scripts/wwg_*.py` are the exploration scripts used to find each source's depth and request format.

## Re-running

Raw data goes in `data/raw/` (git-ignored). Scripts read API credentials from files kept outside the repo, never from the repo itself.
