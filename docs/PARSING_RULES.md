# Parsing the ops posts

The posts are the evidence for *what happened*. Getting them right is the most critical data work in this project. Wording and format will drift between winters, so we go **one winter at a time** and keep a running ledger of rules.

## Per-winter loop
1. **Pull** one winter's posts (raw JSON, stored locally, never committed). Query: originals only (`from:<ops account> -is:retweet`); size the effect of excluding replies before deciding about replies.
2. **Discover** the winter's templates: read the whole winter at once (long-context model) and list recurring message shapes.
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

The ledger is stored as data (`rules/`, to be created) so the later per-mountain adapters can reuse the method. This ledger is itself archaeology: recovered rules, each tagged with its evidence.
