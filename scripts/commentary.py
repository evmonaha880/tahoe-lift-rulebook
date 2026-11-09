"""Spot-check helper: everything the human commentary says about one day, in one place, to use when a number or a parse is in doubt.
Reads only saved files (no network, no spend). Shows: our own lift-day summary for the day, the blog posts of that day and the days around it (sentences that mention lifts, wind, closures, snow or the day itself),
the blog's forecast numbers (blog_forecast.csv), the forecaster's tweets of that day (@TahoeWeather, where pulled), NWS Reno storm reports naming Palisades/Squaw/Alpine and the forecast-discussion lines on wind, and calendar or lift-history entries near the date.
COMMENTARY IS NEVER FITTED OR SCORED: it is evidence for a human. Quotes are cut to 25 words.
usage: python3 -I scripts/commentary.py 2024-03-02 [--lift "KT-22"] [--days 1]"""
import os, sys, re, json, csv, glob, html
from datetime import date, timedelta, datetime
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I mode does not put the script folder on the path
from config import LA
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
args = sys.argv[1:]
if not args or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args[0]): raise SystemExit('usage: python3 -I scripts/commentary.py YYYY-MM-DD [--lift "KT-22"] [--days 1]')
try: day = date.fromisoformat(args[0])
except ValueError: raise SystemExit("not a real date: " + args[0])
lift = args[args.index("--lift") + 1] if "--lift" in args else None; span = int(args[args.index("--days") + 1]) if "--days" in args else 1
W = lambda d: f"{d.year}-{str(d.year + 1)[2:]}" if d.month >= 8 else f"{d.year - 1}-{str(d.year)[2:]}"
KEY = re.compile(r"lift|wind|gust|mph|clos|hold|delay|open|snow|avalanche|storm|ice|power|funitel|tram|gondola|KT|siberia|summit", re.I)
def cut(s, n=25): w = s.split(); return " ".join(w[:n]) + (" ..." if len(w) > n else "")
def hdr(t): print("\n" + "=" * 8, t)
print(f"SPOT CHECK {day} ({W(day)})" + (f", lift {lift}" if lift else "") + f", +/- {span} day(s). Commentary is for a person to read; it is never fitted.")
# ---- our table
p = os.path.join(ROOT, "data", "derived", "lift_days.csv")
if os.path.exists(p):
    rows = [r for r in csv.DictReader(open(p)) if r["date"] == str(day)]
    hdr("our lift-day table")
    if not rows: print("  no rows for this day (outside the 8 parsed winters, or no lift mentioned)")
    else:
        sc = [r for r in rows if r["scheduled"] == "True"]; held = [r for r in rows if r["held"] == "1"]
        print(f"  {len(rows)} rows, {len(sc)} scheduled, {len(held)} held ({sum(r['held_wind'] == '1' for r in held)} for wind), closed_all {sum(r['closed_all'] == '1' for r in rows)}; day gust {rows[0].get('day_gust')} mph, early gust {rows[0].get('early_gust')}, new snow {round(float(rows[0]['new_snow24']), 1) if rows[0].get('new_snow24') else 'n/a'} in")
        for r in rows:
            if lift and r["lift"].lower() == lift.lower(): print(f"  {r['lift']}: scheduled {r['scheduled']}, held {r['held']} (wind {r['held_wind']}, cause_first {r['cause_first']}), hold_minutes {r['hold_minutes']}")
# ---- blog
bp = os.path.join(ROOT, "data", "derived", "blog_text.jsonl")
if os.path.exists(bp):
    hdr("operations blog and other posts")
    posts = [json.loads(l) for l in open(bp)]
    near = [x for x in posts if abs((date.fromisoformat(x["date"][:10]) - day).days) <= span and "weather" not in x["categories"]]
    if not near: print("  no blog post within the window")
    for x in sorted(near, key=lambda x: x["date"]):
        print(f"  [{x['date'][:16]}] {'/'.join(x['categories'])}: {x['title']}  {x['link']}")
        lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", x["text"]) if len(s.strip()) > 25 and KEY.search(s)]
        pick = [s for s in lines if (lift and lift.lower() in s.lower()) or re.search(day.strftime("%B %-d") + "|" + day.strftime("%b %-d"), s)] or lines
        for s in pick[:4]: print("      - " + cut(s))
    fc = [x for x in posts if "weather" in x["categories"] and abs((date.fromisoformat(x["date"][:10]) - day).days) <= 0]
    for x in fc:
        print(f"  [{x['date'][:16]}] forecast post: {x['title']}  {x['link']}")
        for s in [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", x["text"]) if re.search(r"gust|ridge|mph|lift", s, re.I)][:3]: print("      - " + cut(s))
fp = os.path.join(ROOT, "data", "derived", "blog_forecast.csv")
if os.path.exists(fp):
    f = [r for r in csv.DictReader(open(fp)) if r["tgt_date"] == str(day) and r["fc_gust_hi"]]
    if f: hdr("blog forecast numbers for this day (read by rule, regex-v1)"); [print(f"  posted {r['posted_local'][:16]} horizon {r['horizon']}: ridge gust {r['fc_gust_lo']}-{r['fc_gust_hi']}{'+' if r['fc_gust_plus'] == '1' else ''} mph, lift impact {r['fc_lift_impact']}, by 09:00 {r['asof_by_0900']}") for r in f]
# ---- forecaster tweets
tw = []
for fn in glob.glob(os.path.join(ROOT, "data", "raw", "x_tahoeweather", "*.json")):
    d = json.load(open(fn))
    for q in (d if isinstance(d, list) else [x for j in d.values() if isinstance(j, dict) for x in j.get("data", [])]):
        if "created_at" not in q: continue
        t = datetime.fromisoformat(q["created_at"].replace("Z", "+00:00")).astimezone(LA)
        if abs((t.date() - day).days) <= 0: tw.append((t, q["text"]))
if tw:
    hdr("@TahoeWeather (forecaster) posts that day")
    for t, s in sorted(set((t, s) for t, s in tw))[:6]: print(f"  [{t:%H:%M}] " + cut(html.unescape(re.sub(r'https?://\S+', '', s)).strip(), 30))
# ---- NWS
nd = os.path.join(ROOT, "data", "raw", "nws_text")
if os.path.isdir(nd):
    hdr("NWS Reno")
    wf = f"{nd}/PNSREV_{W(day)}.txt"
    if os.path.exists(wf):
        txt = open(wf).read(); found = 0
        for prod in re.split(r"\n(?=\d{3} *\nNOUS)", txt):
            m = re.search(r"(\w{3}) (\w{3}) (\d{1,2}) (\d{4})", prod)
            if not m or date(int(m.group(4)), datetime.strptime(m.group(2), "%b").month, int(m.group(3))) not in [day + timedelta(days=i) for i in range(-span, span + 1)]: continue
            for l in prod.split("\n"):
                if re.search(r"palisades|squaw|alpine mead|olympic valley", l, re.I): print(f"  storm report ({m.group(2)} {m.group(3)}): " + re.sub(r"\s{2,}", " | ", l.strip())); found += 1
        if not found: print("  no storm-report line naming Palisades, Squaw or Alpine Meadows in the window")
    af = f"{nd}/AFDREV_{W(day)}.txt"
    if os.path.exists(af):
        n = 0
        for prod in re.split(r"\n(?=\d{3} *\nFXUS65 KREV)", open(af).read()):
            m = re.search(r"(\d{3,4}) (AM|PM) (PST|PDT) \w{3} (\w{3}) (\d{1,2}) (\d{4})", prod)
            if not m or date(int(m.group(6)), datetime.strptime(m.group(4).title(), "%b").month, int(m.group(5))) != day or m.group(2) != "AM": continue
            for s in [s.strip() for s in re.split(r"(?<=[.!?])\s+", prod.replace("\n", " ")) if re.search(r"ridge|crest|wind", s, re.I) and re.search(r"\d+\s*(mph|kt)", s, re.I)][:2]:
                print(f"  forecast discussion {m.group(1)} {m.group(2)}: " + cut(s, 30)); n += 1
            if n >= 3: break
# ---- calendar and lift history
cp = os.path.join(ROOT, "rules", "season_calendar.json")
if os.path.exists(cp):
    ev = [e for e in json.load(open(cp))["events"] if abs((date.fromisoformat(e["date"]) - day).days) <= 3 and e["status"] != "cancelled"]
    if ev:
        hdr("blog calendar entries within 3 days (read by two model readers, announced dates)")
        for e in ev[:8]: print(f"  {e['date']} {e['kind']} {e['side']} {e['lift'] or ''} [{e['status']}, {'both readers' if e['agreed'] else 'one reader'}] \"{cut(e['quote'])}\"  (post {e['post_id']})")
lh = json.load(open(os.path.join(ROOT, "rules", "lift_history.json"))) if os.path.exists(os.path.join(ROOT, "rules", "lift_history.json")) else None
if lh and lift:
    hits = [e for e in lh["events"] if lift.lower() in e["lift"].lower()]
    if hits: hdr(f"lift history for {lift}"); [print(f"  {e['date']}: {e['change']}") for e in hits]
