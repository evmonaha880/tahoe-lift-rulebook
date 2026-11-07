"""Build the static demo page (docs/index.html) from the recovered rulebook and results.
Reads rules/rulebook_palisades.json, results/loo_results.json, and (for the replay only) data/derived/lift_days.csv.
Only counts and per-lift hold/no-hold flags go into the page; post text is never copied.
usage: python3 -I scripts/build_demo.py"""
import os, csv, json, html
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
book = json.load(open(os.path.join(ROOT, "rules", "rulebook_palisades.json")))
res = json.load(open(os.path.join(ROOT, "results", "loo_results.json")))
rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "derived", "lift_days.csv"))))
WINTERS = sorted(res["day_level"])
e = html.escape

# ---- day-level held-out table
dl = []
for w in WINTERS:
    d = res["day_level"][w]
    dl.append((w, d["learned"]["n"], d["learned"]["base_rate"], d["rule"], d["learned"], d["baseline"]))
mean = lambda xs: sum(xs) / len(xs)
lf, bf = mean([x[4]["f1"] for x in dl]), mean([x[5]["f1"] for x in dl])
# ---- lift-level (two-stage) table
ts = [(w, res["two_stage"][w]) for w in WINTERS if w in res["two_stage"]]
tf, tb = mean([v["learned"]["f1"] for _, v in ts]), mean([v["baseline"]["f1"] for _, v in ts])
tw = sum(v["learned"]["f1"] > v["baseline"]["f1"] for _, v in ts)

# ---- replay days: one hit, one false alarm, both from a winter the day rule never saw
REPLAY = [("2023-12-12", "A miss: the rule fired and nothing held"), ("2024-01-06", "A hit: the rule fired and 17 of 22 lifts held")]
def replay(date, title):
    rs = [r for r in rows if r["date"] == date and r["scheduled"] == "True"]
    w = rs[0]["winter"]
    rule = res["day_level"][w]["rule"]
    thr = float(rule.split(">=")[1])
    g = float(rs[0]["day_gust"])
    lifts = sorted(({"lift": r["lift"], "held": r["held"] == "1", "wind": r["held_wind"] == "1"} for r in rs), key=lambda x: (not x["held"], x["lift"]))
    return dict(date=date, title=title, winter=w, rule=rule, thr=thr, gust=g, early=float(rs[0]["early_gust"]) if rs[0]["early_gust"] else None,
                predicted=g >= thr, n=len(rs), held=sum(x["held"] for x in lifts), lifts=lifts)
RP = [replay(d, t) for d, t in REPLAY]

def f2(x): return "n/a" if x is None else f"{x:.2f}"
dl_rows = "".join(f"<tr><td>{w}</td><td>{n}</td><td>{br:.0%}</td><td class=m>{e(rule)}</td><td class=g>{l['f1']:.2f}</td><td>{f2(l['precision'])}</td><td>{f2(l['recall'])}</td><td class=b>{b['f1']:.2f}</td><td>{f2(b['precision'])}</td></tr>" for w, n, br, rule, l, b in dl)
ts_rows = "".join(f"<tr><td>{w}</td><td>{v['learned']['n']:,}</td><td class=m>{e(v['rule'])}</td><td class=g>{v['learned']['f1']:.2f}</td><td class=b>{v['baseline']['f1']:.2f}</td></tr>" for w, v in ts)
top = book[:14]
rule_rows = "".join(f"<tr><td>{e(r['lift'])}</td><td class=m>{e(r['rule'])}</td><td><span class=tag>{e(r['tag'])}</span></td><td>{r['hold_rate_above']:.0%} <small>of {r['n_above']} days</small></td><td>{r['hold_rate_below']:.0%} <small>of {r['n_below']} days</small></td><td>{r['observed_wind_stated_days']}<small> / {r['observed_held_days']} hold days</small></td><td>{r['unstated_cause_days']}</td></tr>" for r in top)
cf = res["cause_families"]
cf_rows = ""
for k, v in cf.items():
    vals = [x.split("(")[0].strip() for x in v["folds"].values()]
    ok = [x for x in vals if x not in ("n/a", "")]
    cf_rows += f"<tr><td>{e(k)}</td><td>{v['days']}</td><td class=m>{e(v['best'][0])} &ge; {v['best'][1]}</td><td>{e(', '.join(ok)) if ok else 'n/a'}</td></tr>"

def replay_html(i, p):
    lifts = "".join(f"<li class='{'held' if x['held'] else 'ran'}'>{e(x['lift'])}<span>{'HELD' if x['held'] else 'ran'}</span></li>" for x in p["lifts"])
    return f"""<div class=replay id=rp{i}><h3>{e(p['title'])}</h3>
<p class=sm>{p['date']} &middot; winter {p['winter']} (the rule below was fitted on the other seven winters)</p>
<div class=card><b>Step 1. The weather that morning.</b> Day-max gust at the summit stations: <b>{p['gust']:.0f}</b> (station units, see limits). Rule: <code>{e(p['rule'])}</code>.</div>
<div class=card><b>Step 2. Predict.</b> <button onclick="document.getElementById('rv{i}').hidden=false;this.hidden=true">Show the prediction and what happened</button>
<div id=rv{i} hidden><p>The rule says: <b>{'lifts will hold' if p['predicted'] else 'no wind holds'}</b>. Of {p['n']} scheduled lifts, <b>{p['held']} held</b>. Verdict: <b>{'hit' if p['predicted'] == (p['held'] > 0) else 'miss'}</b>.</p>
<ul class=lifts>{lifts}</ul></div></div></div>"""

page = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Palisades lift-hold rulebook</title>
<style>
:root{{--bg:#0f1419;--fg:#e6edf3;--mut:#8b98a5;--card:#18202a;--acc:#5eb0ef;--ok:#6fcf97;--bad:#eb7a6b;--line:#2a3542}}
@media(prefers-color-scheme:light){{:root{{--bg:#fafbfc;--fg:#1c2733;--mut:#5b6b7a;--card:#fff;--acc:#1566b0;--ok:#1a7f4b;--bad:#b4402f;--line:#d8dee4}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 -apple-system,Segoe UI,Helvetica,Arial,sans-serif}}
main{{max-width:980px;margin:0 auto;padding:32px 24px 80px}}
h1{{font-size:34px;margin:0 0 6px}}h2{{margin-top:48px;border-top:1px solid var(--line);padding-top:24px}}h3{{margin-bottom:2px}}
.lede{{font-size:19px;color:var(--mut);max-width:760px}}.sm,small{{color:var(--mut);font-size:13px}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}}th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line)}}th{{color:var(--mut);font-weight:600}}
td.m,code{{font-family:ui-monospace,Menlo,monospace;font-size:13px}}td.g{{color:var(--ok);font-weight:700}}td.b{{color:var(--bad)}}
.tag{{border:1px solid var(--acc);color:var(--acc);border-radius:10px;padding:0 8px;font-size:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:10px 0}}
.big{{display:flex;gap:16px;flex-wrap:wrap}}.big .card{{flex:1;min-width:220px}}.big b{{font-size:30px;display:block}}
button{{background:var(--acc);color:#fff;border:0;border-radius:6px;padding:8px 14px;font-size:15px;cursor:pointer}}
.replays{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
ul.lifts{{list-style:none;padding:0;columns:2;font-size:14px}}ul.lifts li{{display:flex;justify-content:space-between;padding:2px 8px;margin:2px 0;border-radius:4px;break-inside:avoid}}
li.held{{background:color-mix(in srgb,var(--bad) 22%,transparent)}}li.ran{{background:color-mix(in srgb,var(--ok) 15%,transparent)}}li span{{font-size:11px;font-weight:700}}
</style></head><body><main>
<h1>Palisades lift-hold rulebook</h1>
<p class=lede>Palisades Tahoe and Alpine Meadows lifts hold, open late or close by rules nobody published. We recovered them from eight winters of the ops account's posts and the weather station record, kept what was <b>observed</b> apart from what was <b>inferred</b>, and tested every rule on a winter it never saw.</p>

<div class=big>
<div class=card><small>Day-level wind rule, held-out winters (mean F1)</small><b>{lf:.2f}</b><small>vs {bf:.2f} for the naive &ldquo;gust &ge; 25&rdquo; rule</small></div>
<div class=card><small>Per-lift two-stage rule, held-out winters (mean F1)</small><b>{tf:.2f}</b><small>vs {tb:.2f} naive: a tie, wins {tw} of {len(ts)} winters. Reported as a negative result.</small></div>
<div class=card><small>Evidence base</small><b>{len(WINTERS)} winters</b><small>{sum(x[1] for x in dl):,} days with lift posts, {len(book)} lifts with rules</small></div>
</div>

<h2>Replay a morning: predict, then reveal</h2>
<p>One day where the rule was right and one where it was wrong. Both come from a winter the rule never saw.</p>
<div class=replays>{replay_html(1, RP[1])}{replay_html(2, RP[0])}</div>

<h2>Does it beat noise? Held-out winters, day level</h2>
<p>Question: did any lift hold for wind that day? The rule is fitted on seven winters and scored on the eighth, then rotated. The baseline is the obvious guess, gusts of 25 or more.</p>
<table><tr><th>Held-out winter</th><th>Days</th><th>Hold rate</th><th>Rule fitted on the other 7</th><th>F1</th><th>Precision</th><th>Recall</th><th>Baseline F1</th><th>Baseline precision</th></tr>{dl_rows}</table>
<p class=sm>The baseline never misses a hold (recall 1.00) because it fires on nearly every windy day; its precision is 0.23 to 0.57. The learned threshold lands near 60 in every fold, so the rule is stable across winters, which is the evidence it is not noise.</p>

<h2>Per lift: which chair holds? This part did not beat the naive rule</h2>
<p>Stage one is the day-level wind rule. Stage two keeps a lift only if it held at least a third of the time when that rule fired in the training winters. Scored on every scheduled lift-day of the held-out winter. It wins in {tw} of {len(ts)} winters and loses in the rest, so we do not claim it.</p>
<table><tr><th>Held-out winter</th><th>Lift-days</th><th>Wind rule used</th><th>Two-stage F1</th><th>Baseline F1</th></tr>{ts_rows}</table>

<h2>The recovered rulebook (top lifts by scheduled days)</h2>
<p>Each rule is a single threshold fitted on all eight winters. Every rule here is <span class=tag>inferred</span> from weather. The last two columns are <b>observed</b>: days where a post itself named wind, and hold days where no cause was stated.</p>
<table><tr><th>Lift</th><th>Rule</th><th>Kind</th><th>Held when rule fired</th><th>Held when it did not</th><th>Observed wind-stated days</th><th>Cause unstated</th></tr>{rule_rows}</table>
<p class=sm>Full file for all {len(book)} lifts: rules/rulebook_palisades.json.</p>

<h2>What we tried that did not work</h2>
<p>Wind is the rule. The other cause families are not recoverable from these weather files, and we say so.</p>
<table><tr><th>Stated cause</th><th>Days</th><th>Best single feature</th><th>Held-out F1 by winter</th></tr>{cf_rows}</table>
<ul>
<li><b>Snow safety and avalanche control:</b> a two-feature rule (new snow and snowpack depth) beat &ldquo;always say hold&rdquo; in only 3 of 8 held-out winters. Patrol decisions are not in the weather data.</li>
<li><b>Mechanical holds:</b> no weather feature predicts them, as expected. They stay in an &ldquo;unexplained&rdquo; bucket, labelled as such.</li>
<li><b>Lightning, ice, rain:</b> too few days (about 50) for a stable rule.</li>
<li><b>Per-lift prediction:</b> averages the same F1 as the naive rule and is far below the day-level wind rule. Knowing a windy day is easy; knowing which chair stops is not, from these features. The per-lift thresholds in the table below are descriptive (hold rate above vs below), not a validated predictor.</li>
</ul>

<h2>Limits we know about</h2>
<ul>
<li>Gust units come straight from the station feed and were not independently confirmed here; read thresholds as relative, not as a posted limit.</li>
<li>The day-level rule uses the whole day's maximum gust. A morning-only version was not fitted on held-out winters, so the replay is a same-day check, not a forecast.</li>
<li>Labels come from a parser (76 golden test cases) plus two independent model readers; 3 to 6% of posts per winter stay unmatched.</li>
<li>Whether pre-event data pulls are acceptable to the organizers is unconfirmed. All code in this repo was written at the event.</li>
</ul>
<p class=sm>Built at the AIE Code Summit Hackathon, Software Archaeology track, 2026-11-07. Source: github.com/evmonaha880/tahoe-lift-rulebook.</p>
</main></body></html>"""
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
open(os.path.join(ROOT, "docs", "index.html"), "w").write(page)
print("wrote docs/index.html", len(page), "bytes;", f"day F1 {lf:.3f} vs {bf:.3f}; two-stage {tf:.3f} vs {tb:.3f}")
for p in RP: print(p["date"], p["rule"], p["gust"], p["predicted"], p["held"], "/", p["n"])
