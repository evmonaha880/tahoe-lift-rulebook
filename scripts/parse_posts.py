"""Deterministic parser: ops posts -> typed events. Every event records the rule that made it (parse_rule_id).
Observed = the post states it. Nothing here infers from weather; that happens later and is tagged separately.
usage: python3 -I scripts/parse_posts.py 2023 [train|heldout|all]   -> data/derived/<winter>_<split>_events.json
Rules ledger is exported to rules/ledger_<winter>.json (data, so other mountains can reuse the method)."""
import os, re, sys, json, collections
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ---- lift vocabulary (canonical name -> regex alias). Lift->mountain mapping is NOT done here (modeling decision later).
LIFTS = {
    "Base to Base Gondola": r"(?:the )?base to base(?: gondola)?|b2b(?: gondola)?|gondola",
    "Tram": r"(?:the )?tram",
    "Funitel": r"(?:the )?funi(?:tel)?",
    "KT-22": r"kt-?22|\bkt\b",
    "Red Dog": r"red dog(?! side)",
    "Resort Chair": r"resort(?: chair)?(?! side)",
    "Wa She Shu": r"wa she shu",
    "Siberia": r"siberia",
    "Headwall": r"headwall",
    "Emigrant": r"emigrant",
    "Silverado": r"silverado",
    "Solitude": r"solitude",
    "Granite Chief": r"granite(?: chief)?",
    "Big Blue": r"big blue",
    "Shirley Lake": r"shirley(?: lake)?",
    "Bailey's Beach": r"bailey[’']?s(?: beach)?",
    "Belmont": r"belmont",
    "Mountain Meadow": r"(?:mountain|mtn)? ?meadow(?! road)",
    "High Camp Carpet": r"high camp(?: carpet)?",
    "Gold Coast": r"gold coast",
    "Lakeview": r"lakeview",
    "Yellow": r"yellow(?: chair)?",
    "Exhibition": r"exhibition|exhi\b",
    "First Venture": r"first v(?:enture)?",
    "Far East": r"far east",
    "Big Carpet": r"big carpet",
    "Alpine Bowl": r"alpine bowl(?: chair)?",
    "Summit": r"summit(?: chair)?",
    "Roundhouse": r"roundhouse",
    "Kangaroo": r"kangaroo",
    "Scott": r"scott(?: chair)?",
    "Treeline Cirque": r"treeline(?: cirque)?",
    "Sherwood": r"sherwood",
    "Subway": r"subway",
    "Broken Arrow": r"broken arrow",
    "Ahsoka Carpet": r"ahsoka|ashoka",
}
LIFT_RE = re.compile(r"\b(?:" + "|".join(f"(?P<L{i}>{p})" for i, p in enumerate(LIFTS.values())) + r")\b", re.I)
LIFT_NAMES = list(LIFTS.keys())

def find_lifts(span):
    out = []
    for m in LIFT_RE.finditer(span):
        name = LIFT_NAMES[int(m.lastgroup[1:])]
        if name not in out: out.append(name)
    return out

CAUSE_RE = [("wind", r"wind"), ("mechanical", r"mechanical|hose|power|electrical|maintenance"), ("patrol", r"patrol|avalanche|snow safety|control"), ("weather", r"icy|ice\b|storm|snow(?:fall)?|rain|conditions"),]
def cause_in(s):
    for c, p in CAUSE_RE:
        if re.search(p, s, re.I): return c
    return None

# ---- RULES: id, event_type, description. The code below applies them in this order; first matching rule claims the sentence.
RULES = [
    ("P-001", "scheduled_opening", "Post starts 'Palisades'/'Alpine' and gives 'N lifts', 'Open at <time>' or 'lifts scheduled for'"),
    ("P-002", "scheduled_opening", "'Open:' / 'Now open:' / 'Operating Update' lift roster (status snapshot, lifts listed with no verb)"),
    ("P-010", "hold_start", "'<lifts> is/are (now) on a [cause] hold' or 'will start/begin the day on [cause] hold'"),
    ("P-011", "hold_start", "Section header form 'Wind Hold: <lifts>' / 'Mechanical Hold:' / 'Patrol Hold:'"),
    ("P-012", "warning", "'expected to go on wind hold', 'going on a wind hold any minute', 'winds may impact lifts', 'likely snow safety delays'"),
    ("P-020", "closed_day", "'<lifts> closed for the day/remainder' or 'off (the) schedule' or 'now closed'"),
    ("P-021", "closed_day", "'All lifts ... are now closed for the day' (lifts = all)"),
    ("P-030", "delay", "'Delayed Opening' or '<lift> on a mechanical delay'"),
    ("P-040", "reopen", "'<lifts> is/are (now/also) open' or 're-opened'"),
    ("P-050", "parking", "Parking lots full / parking at <alternate lot>"),
    ("P-003", "scheduled_opening", "No prefix needed: 4+ lifts named with a time range (e.g. 9am-4pm) and no hold/close verb"),
    ("P-070", "partial", "Downloads only / mid-station only / sightseeing only / closing at <time> for maintenance"),
    ("P-060", "other", "Weather report: starts 'Palisades:' / 'Alpine:' / 'Snow and Weather:' with no lift roster (filtered)"),
    ("P-090", "other", "Road status, promotions, safety message, events (filtered)"),
]
RID = {r[0]: r for r in RULES}

def split_sentences(t):
    t = re.sub(r"#\w+", "", t)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“]|$)|\n+", t) if s.strip()]

def parse_post(p):
    raw = p["text"]
    t = " ".join(raw.replace("&amp;", "&").split())
    dt = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles"))
    base = {"source_post_id": p["id"], "start": dt.isoformat(timespec="minutes"), "end": None}
    ev = []
    def add(rule, typ, lifts, cause=None, **kw):
        for l in (lifts or [None]):
            ev.append({**base, "lift": l, "event_type": typ, "cause": cause,
                       "cause_source": "observed" if cause else "unstated", "parse_rule_id": rule, "confidence": 1.0, **kw})
    low = t.lower()
    # P-001 scheduled opening
    if re.match(r"^(?:palisades|alpine)[^:]{0,20}:", t, re.I) and re.search(r"\b\d+ lifts?\b|open at \d|lifts? (?:are )?(?:scheduled|on the schedule)", t, re.I):
        lifts = find_lifts(t.split(":", 1)[1])
        add("P-001", "scheduled_opening", lifts, None, note="roster" if lifts else None,
            wind_warning=bool(re.search(r"wind", t, re.I) and re.search(r"impact", t, re.I)))
        return ev
    if re.match(r"^(?:palisades|alpine)\s+open at \d", t, re.I):
        add("P-001", "scheduled_opening", find_lifts(t), None); return ev
    if re.match(r"^(?:palisades|alpine)?\s*(?:operations? update|update|now open|open)\s*:", t, re.I) and not re.search(r"\bhold\b", t, re.I):
        add("P-002", "scheduled_opening", find_lifts(t), None); return ev
    # P-011 section headers (can coexist in one post)
    hdr = re.findall(r"(Wind|Mechanical|Patrol) Hold:\s*([^:]*?)(?=\s+(?:Off(?: the)? Schedule|Delayed|Open|Closed)\s*:|$)", t, re.I)
    if hdr:
        for c, seg in hdr: add("P-011", "hold_start", find_lifts(seg), c.lower())
        for seg in re.findall(r"Off(?: the)? Schedule:\s*([^:]*?)(?=\s+\w+ Hold:|$)", t, re.I): add("P-020", "closed_day", find_lifts(seg), None)
        return ev
    if re.search(r"\bdelayed\s*:", t, re.I) and re.search(r"\bopen\s*:", t, re.I):
        for seg in re.findall(r"Delayed:\s*([^:]*?)(?=\s+(?:Open|Closed|Off(?: the)? Schedule)\s*:|$)", t, re.I): add("P-030", "delay", find_lifts(seg), None)
        add("P-002", "scheduled_opening", find_lifts(re.split(r"delayed\s*:", t, flags=re.I)[0]), None); return ev
    if len(find_lifts(t)) >= 4 and re.search(r"\d\s*(?:am|a|pm|p)?\s*-\s*\d+\s*(?:am|a|pm|p)\b", t, re.I) and not re.search(r"\b(?:hold|closed|delayed)\b", t, re.I):
        add("P-003", "scheduled_opening", find_lifts(t), None); return ev
    for s in split_sentences(t):
        sl = s.lower()
        if re.search(r"download(?:s|ing)? only|downloads? only|mid-?station only|sightseeing only|closing at \d.*maintenance|will be closing at \d", sl) and find_lifts(s):
            add("P-070", "partial", find_lifts(s), cause_in(s) or ("wind" if re.search(r"wind", sl) else None), detail="download_only" if "download" in sl else "limited"); continue
        if re.search(r"may go on hold|may go on wind hold", sl): add("P-012", "warning", find_lifts(s), "wind"); continue
        if re.search(r"(?:added to the )?closed list|closing .* (?:for|due)|will be closed on|have gone on|has gone on", sl) and not re.search(r"patrol cup|stifel", sl):
            if re.search(r"gone on", sl): add("P-010", "hold_start", find_lifts(s.split("...")[-1]), cause_in(s) or "wind"); continue
            subj = re.split(r"\bhave been\b|\bwill be\b|, we are closing|we are closing|closing", s, maxsplit=1, flags=re.I)
            lifts = find_lifts(subj[0]) or find_lifts(s)
            dm = re.search(r"(?:due to|because of)(.*)", s, re.I); add("P-020", "closed_day", lifts, cause_in(dm.group(1)) if dm else None); continue
        if re.search(r"(?:\bnow|\bis|\bare)\s+on\s+(?:a\s+)?(\w+\s+)?holds?\b", sl) and find_lifts(s):
            hm = re.search(r"on\s+(?:a\s+)?(\w+)\s+holds?", s, re.I); hc = hm.group(1).lower() if hm else None
            hc = {"maintenance": "mechanical", "electrical": "mechanical"}.get(hc, hc if hc in ("wind", "mechanical", "patrol", "weather") else None)
            add("P-010", "hold_start", find_lifts(re.split(r"\b(?:now|is|are)\s+on\b", s, maxsplit=1, flags=re.I)[0]), hc); continue
        if re.search(r"not connected to alpine|palisades side only|minute schedule|patrol only|spinning for patrol", sl):
            add("P-070", "partial", find_lifts(s), "wind" if "wind" in sl else None, detail="limited"); continue
        if re.search(r"added to the schedule|are not open|not open\.", sl) and find_lifts(s):
            add("P-040" if "added" in sl else "P-020", "reopen" if "added" in sl else "closed_day", find_lifts(s), None); continue
        if re.search(r"stage \d+ wind alert|wind alert", sl): add("P-012", "warning", find_lifts(s), "wind"); continue
        if re.search(r"back up and running|up and running", sl): add("P-040", "reopen", find_lifts(s), None); continue
        if re.search(r"will be delayed|expect delays|snow safety delays|delays and closures are possible", sl):
            add("P-030", "delay", find_lifts(s), cause_in(s) or "patrol"); continue
        if re.search(r"(?:will be )?opening at \d|opening tomorrow|opening in", sl) and find_lifts(s):
            add("P-001", "scheduled_opening", find_lifts(s), None); continue
        if re.search(r"going on (?:a )?wind hold|going on hold", sl):
            add("P-012", "warning", find_lifts(s), "wind"); continue
        if re.search(r"calendar|safety message|deep snow safety|traffic|shuttle|blog|reservation|park & ride|terrain park|celebration|christmas|road\b|rd\b|snow top to bottom|express|tree wells", sl) and not find_lifts(s):
            add("P-090", "other", [], None); continue
        if re.match(r"^(?:we received|today.s forecast|todays forecast|snow showers|sunny|sun,|partly|clear|mostly|cloudy|\d+\"? overnight|\d+-\d+\"|palisades got|alpine got)", sl) and not re.search(r"\bhold\b", sl):
            add("P-060", "other", [], None); continue
        # P-012 warnings
        if re.search(r"expected to go on|going on a .*hold any minute|likely .*(delays|hold)|winds? (?:may|are likely to|will) impact|anticipated weather impacts", sl):
            add("P-012", "warning", find_lifts(s), cause_in(s) or "wind"); continue
        # P-050 parking
        if re.search(r"parking (?:lots?|is)|lots? (?:are|is) full|we are (?:now )?parking at", sl):
            add("P-050", "parking", [], None); continue
        # P-021 all lifts closed
        if re.search(r"all (?:the )?lifts.*(closed|on hold)|all lifts that", sl):
            add("P-021", "closed_day", ["ALL"], cause_in(s) or ("wind" if "wind hold" in sl else None)); continue
        # P-010 holds
        m = re.search(r"^(.*?)\s+(?:is|are|will be|will|also|-)\s*(?:all\s+)?(?:now\s+|also\s+|still\s+)?(?:(?:start|begin|starting|beginning|going)\s+the day\s+)?(?:on|begin the day on|start the day on)\s+(?:a\s+)?(\w+)?\s*(?:hold)\b", s, re.I)
        m2 = re.search(r"^(.*?)\s+(?:will\s+)?(?:start|begin)\s+the day\s+on\s+(?:a\s+)?(\w+)?\s*hold", s, re.I)
        m3 = re.search(r"^(.*?)\s*[-,]\s*also on (\w+)? ?hold", s, re.I)
        m4 = re.search(r"putting (?:the )?(.*?) on (?:a )?(\w+)? ?hold", s, re.I)
        mm = m or m2 or m3 or m4
        if mm:
            subj = mm.group(1)
            lifts = find_lifts(subj) or (["ALL"] if re.search(r"following lifts", subj, re.I) else [])
            if re.search(r"following lifts", subj, re.I): lifts = find_lifts(s.split(":", 1)[1]) if ":" in s else lifts
            hc = (mm.group(2) or "").lower(); hc = None if hc in ("", "a", "the", "hold") else ("mechanical" if hc in ("maintenance", "electrical") else ("weather" if hc in ("icy", "ice") else hc))
            if mm is m4: lifts = find_lifts(mm.group(1)); hc = "weather" if re.search(r"icy|ice", s, re.I) else hc
            add("P-010", "hold_start", lifts, hc, start_of_day=bool(re.search(r"start|begin", s, re.I))); continue
        # P-030 delays
        if re.search(r"delayed opening|mechanical delay|on a .*delay", sl):
            mm = re.search(r"^(.*?)\s+(?:will have|is on|are on)", s, re.I)
            add("P-030", "delay", find_lifts(mm.group(1) if mm else s), cause_in(s) or ("mechanical" if "mechanical" in sl else None)); continue
        # P-020 closed / off schedule
        if re.search(r"closed (?:for )?(?:the )?(?:day|remainder|rest)|off (?:the )?schedule|is closed|now closed|are closed|closed to the public", sl):
            if re.search(r"\broad\b|parking|exhibition will be closed to the public", sl): add("P-090", "other", [], None); continue
            subj = re.split(r"\b(?:is|are|will be)\b|[-:]|, (?:available|still)|\bclosed\b|\boff\b", s, maxsplit=1, flags=re.I)[0]
            lifts = find_lifts(subj) or find_lifts(s)
            dm = re.search(r"due to(.*)", s, re.I); c = cause_in(dm.group(1)) if dm else None
            add("P-020", "closed_day", lifts, c); continue
        # P-040 reopen
        if re.search(r"\b(?:is|are)\s+(?:now\s+|also\s+)?open\b|re-?opened|\balso open\b|\bnow open\b|^[\w\s’'&,.-]+ open!?$", sl) and not re.search(r"\broad\b|open at|will open|opening (?:tomorrow|soon)", sl):
            subj = re.split(r"\b(?:is|are|has)\b|, also|\bopen\b|\balso\b", s, maxsplit=1, flags=re.I)[0]
            add("P-040", "reopen", find_lifts(subj) or find_lifts(s), None); continue
    if ev: return ev
    if re.match(r"^(?:palisades|alpine)\b[^:]{0,15}:|^snow and weather|^today.s weather|^update:.*operating plan", t, re.I):
        add("P-060", "other", [], None); return ev
    add("P-090", "other", [], None, unmatched=True); return ev

if __name__ == "__main__":
    Y = int(sys.argv[1]); split = sys.argv[2] if len(sys.argv) > 2 else "train"; W = f"{Y}-{str(Y+1)[2:]}"
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    posts = json.load(open(os.path.join(root, "data", "derived", f"{W}_{split}.json"))) if split != "all" else json.load(open(os.path.join(root, "data", "raw", "x", f"{W}.json")))
    events, residual, per_post = [], [], {}
    for p in posts:
        e = parse_post(p); events += e; per_post[p["id"]] = [x["event_type"] for x in e]
        if any(x.get("unmatched") for x in e): residual.append(p["text"])
    json.dump(events, open(os.path.join(root, "data", "derived", f"{W}_{split}_events.json"), "w"))
    json.dump(per_post, open(os.path.join(root, "data", "derived", f"{W}_{split}_postlabels.json"), "w"))
    c = collections.Counter(x["event_type"] for x in events); r = collections.Counter(x["parse_rule_id"] for x in events)
    print(f"{W} {split}: {len(posts)} posts -> {len(events)} events"); print("by type:", dict(c)); print("by rule:", dict(sorted(r.items())))
    print(f"residual (matched no rule): {len(residual)} posts ({len(residual)/len(posts):.1%})")
    os.makedirs(os.path.join(root, "data", "derived"), exist_ok=True)
    json.dump(residual, open(os.path.join(root, "data", "derived", f"{W}_{split}_residual.json"), "w"))
    os.makedirs(os.path.join(root, "rules"), exist_ok=True)
    json.dump([{"rule_id": a, "event_type": b, "pattern": d, "winters": [W], "status": "proposed"} for a, b, d in RULES],
              open(os.path.join(root, "rules", f"ledger_{W}.json"), "w"), indent=1)
