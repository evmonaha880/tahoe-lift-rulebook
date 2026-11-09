"""Read the forecaster's morning posts (blog category `weather`) into forecast numbers per target day.
One row per (post, target date), horizon 0 = the post's own day, 1 = next day, 2 = the day after. DERIVED BY RULE FROM TEXT (a regex reader), never observed; stored apart from
lift_days.csv. Reading rules: a post is split into sections at lines that end in ':' (e.g. 'Sunday - Monday:', 'Thursday Night - Friday Storm:', 'Snowfall Report:' = the past, skipped);
a section's day labels give its target days; a sentence that names its own weekday overrides the section. Only sentences with 'gust' or 'ridgetop/up top/mountain top' and an mph figure count.
'60-70+ mph' is stored as hi=70, lo=60, plus=1 (a lower bound). Numbers are the forecaster's words, in mph, for the ridgetop. `posted_local` is the site's own clock (Pacific, checked against date_gmt).
usage: python3 -I scripts/blog_forecast.py    -> data/derived/blog_forecast.csv"""
import os, re, json, csv, html, datetime
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
rows = json.load(open(os.path.join(ROOT, "data", "raw", "blog", "weather.json")))
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_RE = re.compile(r"\b(mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat(?:ur)?|sun)(?:day)?s?\b", re.I)
def wd(tok):
    t = tok.lower()[:3]; return {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}[t]
def clean(h):
    h = re.sub(r"(?is)<(script|style|figure|svg).*?</\1>", "", h); h = re.sub(r"(?i)</(p|div|li|h\d|tr)>|<br\s*/?>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", "", h)).replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"[ \t]+", " ", t)
def days_in(text, d0):
    """target dates (offsets 0..6 from the post date d0) named in text; 'Friday - Sunday' expands forward; 'today', 'tonight', 'tomorrow', 'weekend' understood"""
    toks = []
    for m in DAY_RE.finditer(text):
        w = m.group(0)
        if w.lower() == m.group(1).lower() and not w[0].isupper(): continue      # a bare lower-case 'sun' or 'sat' is not a weekday
        toks.append((m.start(), m.end(), wd(m.group(1))))
    off, i = set(), 0
    def off_of(w): return (w - d0.weekday()) % 7
    while i < len(toks):
        s0, e0, w = toks[i]; o = off_of(w)
        if i + 1 < len(toks):
            between = re.sub(r"\b(night|evening|morning|afternoon|early|late)\b", " ", text[e0:toks[i + 1][0]].lower()).strip()
            if between in ("-", "through", "thru", "to", "into", "- early"):
                o2 = off_of(toks[i + 1][2]); off.update(range(o, o2 + 1) if o2 >= o else [o, o2]); i += 2; continue
        off.add(o); i += 1
    low = text.lower()
    if re.search(r"\b(today|tonight|this (?:morning|afternoon|evening))\b", low): off.add(0)
    if re.search(r"\btomorrow\b", low): off.add(1)
    if re.search(r"\bweekend\b", low):
        sat = (5 - d0.weekday()) % 7; off.update({sat, sat + 1} if d0.weekday() < 5 else ({0, 1} if d0.weekday() == 5 else {0}))
    return {o for o in off if 0 <= o <= 6}
GUST = re.compile(r"(\d{2,3})\s*(?:-\s*(\d{2,3}))?\s*(\+)?\s*mph", re.I)
WINDW = re.compile(r"gust|ridge\s?top|up top|mountain\s?top|top of the mountain", re.I)
LIFTW = re.compile(r"lift", re.I); IMPACT = re.compile(r"affect|impact|limit|hold|delay|clos|disrupt|could|may|likely", re.I)
SNOW = re.compile(r"(\d{1,3})(?:\s*-\s*(\d{1,3}))?\s*\+?\s*(inch(?:es)?|in\.|feet|foot|ft\.?)\b[^.]{0,40}?(?:snow|new)|(?:snow|new snow)[^.]{0,40}?(\d{1,3})(?:\s*-\s*(\d{1,3}))?\s*\+?\s*(inch(?:es)?|feet|foot)", re.I)
out = []
for r in rows:
    d_local = datetime.datetime.fromisoformat(r["date"]); d0 = d_local.date()
    text = clean(r["content"]["rendered"])
    # split into (header, body) sections; a header is a short line ending with ':'
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    secs, cur = [], ("", [])
    for l in lines:
        if l.endswith(":") and len(l) < 70: secs.append(cur); cur = (l[:-1], [])
        else: cur[1].append(l)
    secs.append(cur)
    per = {o: dict(hi=None, lo=None, plus=0, n=0, lift=0, snow=None) for o in range(3)}
    for head, body in secs:
        hl = head.lower()
        if "snowfall report" in hl or "snowfall reports" in hl or "overnight" in hl and "storm" not in hl: continue   # the past
        h_off = days_in(head, d0) if head else set()
        for s in re.split(r"(?<=[.!?])\s+", " ".join(body)):
            s_off = days_in(s, d0) or h_off or ({0} if not head else set())
            if not s_off: continue
            if WINDW.search(s):
                for m in GUST.finditer(s):
                    hi = int(m.group(2) or m.group(1)); lo = int(m.group(1)); plus = 1 if m.group(3) else 0
                    if hi < 15 or hi > 250: continue
                    for o in s_off:
                        if o in per:
                            p = per[o]; p["n"] += 1
                            if p["hi"] is None or hi > p["hi"]: p["hi"], p["lo"], p["plus"] = hi, lo, plus
            if LIFTW.search(s) and IMPACT.search(s) and re.search(r"wind|gust|ridge|storm|snow|weather|avalanche|ice", s, re.I):
                for o in s_off:
                    if o in per: per[o]["lift"] = 1
            if SNOW.search(s) and not re.search(r"snow level", s, re.I):
                for m in SNOW.finditer(s):
                    g = [x for x in m.groups() if x]; unit = g[-1].lower(); nums = [int(x) for x in g[:-1] if x.isdigit()]
                    if not nums: continue
                    v = max(nums) * (12 if unit.startswith(("feet", "foot", "ft")) else 1)
                    if v > 150: continue
                    for o in s_off:
                        if o in per and (per[o]["snow"] is None or v > per[o]["snow"]): per[o]["snow"] = v
    for o, p in per.items():
        tgt = d0 + datetime.timedelta(days=o)
        out.append(dict(post_id=r["id"], link=r["link"], posted_local=r["date"], post_date=str(d0), tgt_date=str(tgt), horizon=o,
                        asof_by_0900=int(d_local.hour < 9 or (d_local.hour == 9 and d_local.minute == 0)), asof_by_0700=int(d_local.hour < 7),
                        fc_gust_hi=p["hi"], fc_gust_lo=p["lo"], fc_gust_plus=p["plus"], fc_gust_mentions=p["n"], fc_lift_impact=p["lift"], fc_snow_hi_in=p["snow"],
                        reader="regex-v1"))
cols = list(out[0]); path = os.path.join(ROOT, "data", "derived", "blog_forecast.csv")
with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(out)
h0 = [x for x in out if x["horizon"] == 0]
print(f"{len(rows)} posts, {len(out)} rows; horizon 0 with a gust figure {sum(x['fc_gust_hi'] is not None for x in h0)}, lift impact {sum(x['fc_lift_impact'] for x in h0)}, snow figure {sum(x['fc_snow_hi_in'] is not None for x in h0)}; posted by 09:00 {sum(x['asof_by_0900'] for x in h0)}")
