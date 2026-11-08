# Decisions

All dated 2026-11-07 unless noted.

| # | Decision | Rejected / why |
|---|---|---|
| 1 | Build in the **Software Archaeology** lane | Other lanes weighed. Games (done a lot), business systems (not interesting to the owner), Kodak edge codes (a lookup table, image-analyzer ban risk), traffic lights (no data), Soviet maps (no free scan found), stock data (crowded, off-interest). Apollo Guidance Computer and Bach chorale rules were finalists. Tahoe won on personal use and data in hand. |
| 2 | **Palisades Tahoe + Alpine Meadows is the core** | Heavenly has fewer winters of usable weather history (its stations ended mid-2025) and the ops feed is less detailed. Palisades has about 10 winters of both posts and station data. |
| 3 | **Not a wind-only hypothesis** | Wind is the biggest stated cause but many holds give no cause. Rules must cover snow loading, temperature and rain-vs-snow, pressure, and leave an honest "unexplained" bucket. |
| 4 | Heavenly, Northstar, Kirkwood, Mt Rose **later** | Out of scope today. Structure the repo with one folder per mountain so they can be added. Northstar, Kirkwood and Mt Rose looked thin on station data. |
| 5 | "What to do this morning" module **later** | Not part of the hackathon. It will read the same rulebook plus live feeds. |
| 6 | **Synoptic API is dead** for history | The account's token is refused for all history calls. Replaced by the Western Weather Group public report builder. |
| 7 | Weather: **hourly plus 15-minute** from the Western Weather Group builder | 1-minute returned nothing. Pull all fields at hourly; 15-minute for finer wind timing. Redundant derived fields (wind chill, heat index, daily max/min, equipment health) are dropped at analysis time, not at pull time. |
| 8 | Snow: **SNOTEL 784** hourly for 18 winters | Free, verified, includes wind since 2008; a long-history backup for station wind. |
| 9 | X posts **one winter at a time**, with a verifier and a rules ledger | A bulk pull would hide format drift. See `PARSING_RULES.md`. |
| 10 | X query = **originals only** for now; **replies decision pending** | Retweets add cost without information. Replies may carry cause information; size and sample them before deciding. |
| 11 | Winter order: 2023-24, 2024-25, 2025-26, then older | 2023-24 has an earlier independent table for checking and is a strong El Niño winter by ONI (+1.84) but moderate by RONI (+1.13); see DATA_SOURCES.md. The next two show drift up to the present. |
| 12 | Test with **leave-one-winter-out** across winters | One winter plus a few days is too weak to trust. |
| 13 | Label every winter by ONI/RONI; El Niño via **archetype days and a 2023-24 replay** | A synthetic whole-winter simulator is not supported by the data available. |
| 14 | Parsing rules are recovered with **observed vs inferred** tags, like the lift rules | Keeps the story consistent and the claims honest. |
| 15 | Tools: **Subquadratic** and **Meta Muse API** as independent blind labelers of the posts (they never see the parser's output) | Used for verification only. Template discovery was done by reading posts directly; no whole-winter Subquadratic read was run. Gemini and MongoDB not used. |
| 16 | Docs split: **public repo docs + a private handoff file outside the repo** | Public docs are safe for judges to read. The private file holds spend, credential locations and session state. |
| 17 | Raw pull files not in git; the app shows the text of public posts beside their parsed events | The raw X files are bulky and re-pullable, so they stay out of git. Evan decided on 2026-11-07 to show post text in the app because it is public and central to the project. |
| 18 | **Prize tracks: only Subquadratic and Meta Muse are used, as blind labelers inside the pipeline, and measured.** Fetch.ai, Gemini and MongoDB are not used and not claimed. | Fetch.ai's track needs an Agentverse agent speaking the Agent Chat Protocol; it was reviewed and not pursued. Cash prizes are upside, not a plan. |
| 19 | **UI: a static replay app in `docs/app/`**, built separately from the data work. No ASI:One agent. | The rulebook is stored as data, so any front end can read it. |
| 20 | **Avalanche danger ratings** from the public Sierra Avalanche Center API are a candidate feature for patrol-related holds | Free, no key, daily since about 2020. Zone coverage of Palisades unverified. See `DATA_SOURCES.md` section 5. |
| 21 | Alpine's "Meadow" and Palisades' "Mountain Meadow" are **two lifts**; "upper mountain" follows the operators' own lists | Read from the posts and a public lifts table, not from AI answers where they disagreed. See `rules/lift_groups.json`. |
| 22 | Squaw One = Wa She Shu, Squaw Creek = Resort Chair; old names folded into the new | Timing alone suggested the opposite pairing; a public source settled it. Tucker Carpet to Kaya Carpet is unverified and not merged. |
| 23 | Hedged wording ("expect delays", "may go on hold") is a **warning**, not a hold or delay | Predictions are not events. The blind readers have no warning class, so they disagree on these by design. |
| 24 | Held-out posts are for **measuring only**; an error seen there is fixed only if the same pattern appears in training posts | Keeps the held-out numbers honest. |
| 25 | Funitel-top wind is **estimated** where the station was off (2.16 + 0.13 x Siberia + 0.72 x Belmont, R2 0.89); 2025-26 uses the estimate throughout | The source returns no rows for those dates; the 2025-26 sensor reads differently from earlier years. Flagged in the data. |
| 26 | Lift-level results use **scheduled lift-days only** | Lift-days that exist only because a post named the lift as held are 76% held by construction and inflate every method. Both are reported in `RESULTS.md`. |
| 27 | **The app is a view of the pipeline, not a second analysis.** Every score, rule, odds table, lift grouping and reader-agreement figure in `docs/app/` is written by `scripts/build_app_model.py` from the repo's own outputs and checked by `scripts/check_app_model.py`; the page does no fitting or scoring of its own | The first version re-fitted its lines and re-scored its lift-level cards in the browser on a different row set, so its numbers contradicted `RESULTS.md`. The frozen first version is the git tag `v1-freeze`. |
