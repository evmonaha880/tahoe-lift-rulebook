# Parsing the ops posts

The posts are the evidence for *what happened*. Getting them right is the most critical data work in this project. Wording and format will drift between winters, so we go **one winter at a time** and keep a running ledger of rules.

## Per-winter loop
1. **Pull** one winter's posts (raw JSON, stored locally, never committed). Query: originals only (`from:<ops account> -is:retweet`); size the effect of excluding replies before deciding about replies.
2. **Discover** the winter's templates by reading the posts and the residual queue (posts that match no rule). No whole-winter long-context read was run.
3. **Parse** with deterministic rules into typed events (below). Each event records the rule that produced it.
4. **Verify** (next section).
5. **Update the ledger**, then re-run earlier winters to confirm no regression.
6. Move to the next winter. Order: 2023-24, 2024-25, 2025-26, then older.

## Event types
| Type | Meaning |
|---|---|
| scheduled_opening | Morning post listing lifts and hours |
| hold_start | A lift goes on hold (cause stated or not) |
| reopen | A held lift reopens |
| delay | Opens late or "slightly delayed" |
| partial | Mid-station only, sightseeing only, limited hours |
| closed_day | Not operating for the day |
| parking | Parking status. Kept as a separate signal for later; useful for the future morning module |
| other | Promotions, events, unrelated news. **Filtered out** of the lift events |

Cause categories seen in earlier private work (reference only, to be confirmed in the new parse): wind, patrol (avalanche control), mechanical, unstated or delayed, mid-station only, not connected to the other base.

## Verification (the parser must not grade itself)
- **Held-out 20%:** set aside before writing rules; never tune on them; report accuracy on them.
- **Blind second reader:** a different model family labels a random sample (about 100 posts per winter) without seeing the parser's output; review every disagreement.
- **Residual queue:** posts that matched no rule, grouped by template, most frequent first. Target: shrink it each winter.
- **Drift check:** compare each winter's template mix and vocabulary with the previous winter and flag shifts.
- **Sanity checks:** days with zero lift posts; events with an end before a start; lifts that never reopen.
- **Optional independent check:** an earlier private lift-day table, labelled as reference.

## Rules ledger
One row per rule. Rules may apply to some winters only.

| Field | Meaning |
|---|---|
| rule_id | Stable ID (for example `P-001`) |
| event_type | What the rule produces |
| pattern | The match (regex or description) |
| winters | Which winters it applies to |
| examples | 2-3 real posts (store IDs here; raw text stays local) |
| accuracy | On the held-out set, per winter |
| status | proposed, active, winter-specific, retired |
| notes | Why it exists, quirks, what it replaced |

The ledger is stored as data (`rules/ledger_<winter>.json`) so the later per-mountain adapters can reuse the method. This ledger is itself archaeology: recovered rules, each tagged with its evidence.

## Final numbers (2026-11-07)
- **Coverage:** 7,044 posts, 23,966 events, 150 posts (2.1%) match no rule. 191 regression tests (`tests/golden.py`), all passing. Rule P-022 (whole-resort or whole-side closure, e.g. "Palisades Tahoe is CLOSED today", "ALL LIFTS CLOSED TODAY") and the ALL_ON_HOLD scope ("all lifts that were on wind hold are now closed") were added on 2026-11-07 after the deadline, with patterns taken from train posts only; every hold, closure, delay and warning event now also carries `cause_tags`, a multi-label list read from the post text (the single `cause` field is unchanged).
- **Hand check (the parser grading itself is not enough):** 15 random held-out posts per winter, drawn before any fixing, graded once by one reader: two samples of 120. A post counts as right only if every event is right. Pooled over both samples about 90% (84% and 93% for the same old parser on the two samples, so plus or minus 5 points). The held-out split was never used to write rules; an error seen there was fixed only if the same pattern also appeared in the training posts.
- **Re-check after the closure rule (2026-11-07 evening, independent model reader, one reader, not a human):** 174 held-out posts graded strictly from the post text and the event definitions, without reading the parser code. 120 random held-out posts (15 per winter): 109 fully right (91%), 1 unclear. 54 held-out posts about closures: 35 fully right (65%). Overall 144 of 174 (83%). Error themes: closure scope (a post saying "Palisades Tahoe Alpine is closed" came out as both sides; "Alpine also closed" missed), a closure announced for a later day parsed as today, "lifts that were previously on wind hold are now closed" read as reopenings, hedged "may impact lift operations" language missed as a warning, limited operations (hike-only, resort guests only) read as closures or partials, runs and trails ("Mountain Run is closed") read as lifts, and long rosters with missing lifts. By decision 24 these held-out errors were not fixed unless the same pattern was already in the train posts; the sheet and grades are kept outside the repo because they carry post text.
- **Independent blind readers:** Subquadratic (all 7,044 posts) and Meta Muse (7,040; 4 calls failed on a length limit) labeled each post for seven classes without seeing the parser. Agreement over all posts and classes: parser and Subquadratic 93.1%, parser and Muse 97.2%, the two readers 94.6%. The readers have no "warning" class, so hedged posts ("expect delays") disagree with them by design. Agreement is not truth.
- **Judgement calls recorded:** hedged wording is a warning, not a hold or delay; Squaw One is Wa She Shu and Squaw Creek is Resort Chair (confirmed from public sources); Alpine's Meadow and Mountain Meadow are separate lifts; "upper mountain" follows the operators' own lists (`rules/lift_groups.json`).
- **Known weaknesses:** mixed-cause sentences, "all open except holds on: list", rosters with no header in some winters, and posts that give only a count of scheduled lifts.
