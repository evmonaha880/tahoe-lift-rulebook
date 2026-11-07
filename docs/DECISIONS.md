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
| 15 | Tools: **SubQ** (long context) for template discovery and as an independent reader; **Meta Muse API** as an independent verifier | Gemini and MongoDB skipped (not needed). Fetch.ai reconsidered: see decision 18. Meta credit claims close 3:00 PM PT on Nov 7 and need billing set up; the Meta API is US-only, so keep a fallback model. |
| 16 | Docs split: **public repo docs + a private handoff file outside the repo** | Public docs are safe for judges to read. The private file holds spend, credential locations and session state. |
| 17 | Raw data not in git | X posts cannot be redistributed; weather files are re-pullable. |
| 18 | **Prize tracks considered; nothing built for them yet.** Overall is the core target. SubQ and Meta Muse are used inside the real pipeline and measured. Fetch.ai only as a last-phase layer. | Fetch.ai's track ("Agents That Prove Their Work") names reconstruction agents that separate observed from inferred, which is this project. It requires an Agentverse-registered agent speaking the Agent Chat Protocol, usable end to end inside an ASI:One conversation, a public repo with run instructions, and a registration through the AIE Summit ASI:One Submission Agent after the Cerebral Valley submission. Start it only if core results exist by about 2:30 PM. Whether one project can enter several sponsor prizes is **unconfirmed** (ask in `#questions`). Cash prizes are upside, not a plan. |
| 19 | **UI deferred.** Candidate: an ASI:One agent as the UI (it would also meet the Fetch.ai requirement and replace a custom page). Fallback: a static rulebook-and-replay page. | No UI work during data work. The rulebook is stored as data so either front end can read it. Record a backup screen capture if the demo runs inside ASI:One, because event wifi can fail. |
| 20 | **Avalanche danger ratings** from the public Sierra Avalanche Center API are a candidate feature for patrol-related holds | Free, no key, daily since about 2020. Zone coverage of Palisades unverified. See `DATA_SOURCES.md` section 5. |
