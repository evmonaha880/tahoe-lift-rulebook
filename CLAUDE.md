# CLAUDE.md: Palisades lift-hold rulebook

Read this first. It is short on purpose.

## What this project is
Software archaeology on an unwritten system: **when and why do Palisades Tahoe lifts hold, open late, or close?** The operators follow rules nobody published. We recover those rules from two kinds of evidence (what the ops account posted, and what the weather stations measured), keep *observed* separate from *inferred*, and test every rule on winters it never saw.

Built from an empty repo on 2026-11-07 at the AIE Code Summit Hackathon (problem statement: Software Archaeology). Submissions are due 5:00pm PT that day.

## What this project is NOT
It is **not** an earlier private project (a morning decision product). This one recovers the rulebook.
- Anything from that earlier project is old work.
- Old notes, old data folders and old derived tables exist outside this repo. They are **reference only**: never import their code, never copy their tables in. One allowed use: an old table can be an *independent check* on the new parser, labelled as such.
- The hackathon rule is new work only. If unsure whether something is old, ask.
- Exact locations of old assets are in the owner's private handoff notes, not in this public repo.

## Scope
- **Today:** Palisades Tahoe and Alpine Meadows only. Base output: a recovered rulebook plus a replay that predicts, then reveals.
- **Later (not today):** Heavenly, Northstar, Kirkwood, Mt Rose; a "what to do this morning" module. Keep the structure ready for them (one folder per mountain, rulebook stored as data), but do not build them now.

## First-read order
1. This file.
2. `docs/PROJECT.md`: goal, definitions, event schema, output.
3. `docs/DATA_SOURCES.md`: where every dataset is and how to get it.
4. `docs/PARSING_RULES.md`: the per-winter tweet parsing loop and the rules ledger.
5. `docs/DECISIONS.md`: what was chosen and what was rejected.
6. `docs/SPONSOR_TRACKS.md`: prize requirements (Fetch.ai, Meta, Subquadratic) and submission steps. Reference only; nothing built for them yet.
7. The owner's private `STATE.md` (outside the repo) for current status, spend and next action. Ask the owner for it if it was not provided.

## Working rules
- **Stop and ask before:** spending money (X API pulls, paid APIs), publishing anything outside this repo, or changing any rules or instruction file.
- Credentials live outside the repo. Never put a token, key or personal path in any file here.
- Raw data stays out of git (`data/raw/` is ignored; it is re-pullable and large). The owner confirmed on 2026-11-07 that posts may be shown and redistributed, so the app can quote them.
- Label every claim **verified** or **unverified**. Do not state a depth, count or cost as fact unless it was checked.
- One file per artifact. Revise in place, no `v2` siblings.
- Commit often with clear messages. Git history is the proof of new work.
- Banned by the hackathon: a dashboard as the main feature, basic RAG, Streamlit, image analyzers (full list in `docs/PROJECT.md`).

## Data rules (added 2026-11-07, from the post-hackathon architecture review)
- **Rebuild with one command:** `scripts/run_all.sh` (parse, tests, build, fit, checks, manifest). Before pushing: tests pass, `scripts/diff_events.py results/baseline_events.json.gz` lists only the posts you meant to change, `scripts/check_data.py` and `scripts/check_app_model.py` pass, and any doc or app line that quotes a changed number is updated in the same commit.
- **Raw is never edited;** derived tables are rebuilt, never hand-patched. Observed (from posts) and inferred (modelled) stay in separate columns and files.
- **Every parser behaviour change bumps `PARSER_VERSION`** in `scripts/parse_posts.py` and gets a golden test.
- **Every lift-day column is described in `rules/features.json`,** including when it is known. Full-day hindsight features describe a day; only morning (as-of) features may be presented as a prediction. Name the split (leave-one-winter-out) and the as-of basis next to every score.
- **Validation sample:** `results/validation_sample_ids.json` is frozen. Do not read those posts or grade them more than once; a fix prompted by them needs a new sample.
- **Guesses carry a flag** (for example `fnt_src`, `note: fallback`); never fill a gap silently.

