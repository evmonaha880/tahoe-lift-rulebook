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
    "Squaw One": r"squaw one(?: express)?",
    "Squaw Creek": r"squaw creek",
    "Hot Wheels": r"hot wheels",
    "Kaya Carpet": r"kaya(?: carpet)?",
    "Tucker Carpet": r"tucker(?: carpet)?",
    "Little Carpet": r"little carpet",
    "Olympic Lady": r"olympic lady",
    "Sherwood Express": r"sherwood express",
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
    ("P-013", "hold_start", "'All other (scheduled) lifts ... on wind hold / on delay' (lift = ALL_OTHER, with the named lifts as exceptions)"),
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
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“]|$)|\n+", t) if s.strip()]
    out = []
    for p in parts:   # split compound sentences: 'A is on hold, B and C are open, D will be closed'
        for c in re.split(r",\s+(?=[A-Z][\w’' -]{1,30}?\s+(?:is|are|will|on|has|have)\b)|\s+but\s+(?=[A-Za-z])|\s+and\s+(?=(?:off\s+(?:the\s+)?schedule|closed|opened|open)\b)", p):
            if c and c.strip(): out.append(c.strip())
    return out


SEC_RE = re.compile(r"\b(Wind|Mechanical|Patrol|Maintenance|Electrical)\s+Holds?\s*:|\b(Wind\s+Closures?)\s*:|\b(Hold\s*/\s*Delay(?:ed)?)\s*:|\b(Delayed(?:\s+Opening)?)\s*:|\b(Off(?:\s+the)?\s+Schedule|Closed)\s*:", re.I)
def roster_with_sections(t, add, rule, body_start=0):
    """Roster posts ('Open at 9am: ... Wind Hold: X Delayed: Y') carry hold/delay/closed sections inside. Emit those, return roster text."""
    ms = list(SEC_RE.finditer(t))
    roster = t[body_start: ms[0].start()] if ms else t[body_start:]
    for i, m in enumerate(ms):
        seg = t[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(t)]
        lifts = find_lifts(seg)
        h = re.sub(r"\s+", " ", m.group(0).lower()).strip(": ")
        if "closure" in h: add("P-020", "closed_day", lifts, "wind")
        elif h.startswith("hold"): add("P-011", "hold_start", lifts, None)
        elif "hold" in h: add("P-011", "hold_start", lifts, {"maintenance": "mechanical", "electrical": "mechanical"}.get(h.split()[0], h.split()[0]))
        elif h.startswith("delay"): add("P-030", "delay", lifts, None)
        else: add("P-020", "closed_day", lifts, None)
    for m in re.finditer(r"\(([^)]*(?:mid-?station|m(?:ou)?n(?:ta)?i?n?\.? ?run|must download|download|access to|terrain closed|sightseeing)[^)]*)\)|\bto mid\b|sightseeing only|for sightseeing", roster, re.I):
        pl = find_lifts(roster[max(0, m.start() - 40): m.start()])
        if pl: add("P-070", "partial", pl[-1:], None, detail="restricted")
    for m in re.finditer(r"([\w ]{3,30}?)\s+to (?:the )?mid-?station\b", roster, re.I):
        pl = find_lifts(m.group(1))
        if pl: add("P-070", "partial", pl[-1:], None, detail="mid_station_only")
    for m in re.finditer(r"\(([^)]*wind alert[^)]*)\)", roster, re.I):
        pl = find_lifts(roster[max(0, m.start() - 40): m.start()])
        if pl: add("P-012", "warning", pl[-1:], "wind")
    return roster

def fill_causes(t, ev):
    """If an event has no cause but the post states one ('due to high winds', 'because of lightning'), attach it. Only when the post names exactly one cause."""
    m = re.search(r"(?:due to|because of|caused by)\s+([^.!]*)", t, re.I)
    if not m: return ev
    found = {c for c, p in (("wind", r"wind"), ("weather", r"lightning|ice|icing|rain|snow level"), ("patrol", r"avalanche|snow safety|patrol"), ("mechanical", r"mechanical|maintenance|electrical|power")) if re.search(p, m.group(1), re.I)}
    if len(found) == 1:
        c = found.pop()
        for e in ev:
            if e["event_type"] in ("hold_start", "closed_day", "delay", "partial") and not e["cause"]:
                e["cause"], e["cause_source"] = c, "observed"; e["note_cause"] = "post-level"
    return ev

MARK_RE = re.compile(
    r"(?P<hold>(?:(?P<hc>wind|mechanical|patrol|maintenance|electrical)\s+holds?|hold\s*/\s*delay(?:ed)?|(?:will\s+)?(?:begin|start)\s+the\s+day\s+on\s+(?:a\s+)?(?:(?P<hc2>wind|mechanical|patrol)\s+)?hold)\s*[:,-]?)"
    r"|(?P<delay>(?:(?:are|is)\s+on\s+delay|likely\s+(?:snow\s+safety\s+)?delays\s+for|delay(?:ed)?(?:\s+openings?)?)\s*[:,-]?)"
    r"|(?P<closed>(?:off(?:\s+the)?\s+schedule(?:\s+for\s+the\s+day)?|(?P<cc>wind)\s+closures?)\s*[:-]?)"
    r"|(?P<sched>(?:scheduled|planned|expected(?:\s+very\s+close\s+to)?|projected)\s+(?:for|at)?\s*\d+(?::\d\d)?\s*(?:am|pm|a|p)?\b\s*[:-]?|\d+\s*(?:am|pm)\s+opening|open\s+at\s+\d+\s*(?:am|pm)?\s*:?)"
    r"|(?P<open>(?:the\s+following\s+lifts\s+are\s+)?(?:now\s+)?\bopen\s*:)", re.I)

def sectional(t, add):
    """Status posts built from labelled lift lists ('Wind Hold: A B C  Delayed: D  Open: E'). Each list becomes events of its kind.
    Returns True if it handled the post. Rule ids P-011 hold, P-030 delay, P-020 closed, P-001 scheduled, P-002 open-now."""
    ms = list(MARK_RE.finditer(t))
    if not ms: return False
    segs = []
    for i, m in enumerate(ms):
        seg = t[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(t)]
        if not m.group(0).rstrip().endswith(":"):
            seg = re.split(r"[.!?](?:\s|$)", seg, maxsplit=1)[0]          # no colon: only the same sentence can be this marker's list
            if not (re.match(r"\s*-", seg) or LIFT_RE.match(seg.lstrip(" ,"))): seg = ""
        kind = m.lastgroup if m.lastgroup in ("hold", "delay", "closed", "sched", "open") else next(k for k in ("hold", "delay", "closed", "sched", "open") if m.group(k))
        segs.append((kind, m, seg, find_lifts(seg)))
    withlifts = [x for x in segs if x[3]]
    colon = any(x[1].group(0).rstrip().endswith(":") for x in withlifts)
    if not withlifts or not (len({x[0] for x in withlifts}) >= 2 or colon or any(len(x[3]) >= 2 for x in withlifts)): return False
    if len(segs) == 1 and segs[0][0] == "delay" and not colon and len(segs[0][3]) < 2: return False
    for kind, m, seg, lifts in segs:
        if not lifts: continue
        if kind == "hold": add("P-011", "hold_start", lifts, (m.group("hc") or m.group("hc2") or "").lower().replace("maintenance", "mechanical").replace("electrical", "mechanical") or None)
        elif kind == "delay": add("P-030", "delay", lifts, "patrol" if re.search(r"snow\s+safety", m.group(0), re.I) else None)
        elif kind == "closed": add("P-020", "closed_day", lifts, "wind" if m.group("cc") else None)
        elif kind == "sched": roster_with_sections(seg, add, "P-001"); add("P-001", "scheduled_opening", lifts, None, note="roster")
        else: roster_with_sections(seg, add, "P-002"); add("P-002", "reopen", lifts, None, note="status_roster")
    return True

def parse_post(p):
    ev = fill_causes(" ".join(p["text"].replace("&amp;", "&").split()), _parse_post(p))
    seen, out = set(), []
    for e in ev:   # the same fact can be reached by two rules; keep one
        k = (e["lift"], e["event_type"], e["parse_rule_id"])
        if k not in seen: seen.add(k); out.append(e)
    return out

def _parse_post(p):
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
    AO = re.compile(r"all other (?:scheduled )?(?:\w+ )?lifts?\b[^.!?]*?\bare\b[^.!?]*?\bon (?:a )?(?:(wind|mechanical|patrol|maintenance) )?(hold|delay)(?: due to ([^.!?]*))?[.!?]?", re.I)
    am = AO.search(t)
    if am:
        c = (am.group(1) or "").lower().replace("maintenance", "mechanical") or (cause_in(am.group(3)) if am.group(3) else None)
        rest = (t[:am.start()] + " " + t[am.end():]).strip()
        add("P-013", "hold_start" if am.group(2).lower() == "hold" else "delay", ["ALL_OTHER"], c, **{"except": find_lifts(rest)})
        t = rest
    fm = re.search(r"(?:the )?(?:below|following) lifts (?:are|will [\w ]*?)\s*(?:on|begin the day on|start the day on)\s+(?:a\s+)?(?:(wind|mechanical|patrol)\s+)?(hold|delay)", t, re.I)
    if fm and not re.search(r"[:]", t[fm.end():fm.end() + 3]):
        tail = re.split(r"(?<=[.!?])\s+", t[fm.end():], maxsplit=1)
        lifts = find_lifts(tail[1] if len(tail) > 1 else "")
        if lifts:
            add("P-011" if fm.group(2).lower() == "hold" else "P-030", "hold_start" if fm.group(2).lower() == "hold" else "delay", lifts, (fm.group(1) or "").lower() or None); return ev
    if sectional(t, add): return ev
    # P-001 scheduled opening
    if re.match(r"^(?:palisades|alpine)[^:]{0,20}:", t, re.I) and re.search(r"\b\d+ lifts?\b|open at \d|lifts? (?:are )?(?:scheduled|on the schedule)", t, re.I):
        roster = roster_with_sections(t, add, "P-001", t.index(":") + 1)
        lifts = find_lifts(roster)
        add("P-001", "scheduled_opening", lifts, None, note="roster" if lifts else None,
            wind_warning=bool(re.search(r"wind", t, re.I) and re.search(r"impact", t, re.I)))
        return ev
    if re.match(r"^(?:palisades|alpine)\s+open at \d", t, re.I):
        roster = roster_with_sections(t, add, "P-001"); add("P-001", "scheduled_opening", find_lifts(roster), None); return ev
    if re.match(r"^(?:palisades|alpine)?\s*(?:operations? update|update|now open|open)\s*:", t, re.I) and not re.match(r"^\W*(?:palisades|alpine)?\s*(?:operations? update|update)\s*:\s*(?:wind|mechanical|patrol) hold", t, re.I) and not re.search(r"\bhold\b|\bdelay", t, re.I):
        roster = roster_with_sections(t, add, "P-002"); add("P-002", "reopen", find_lifts(roster), None, note="status_roster"); return ev
    # P-011 section headers (can coexist in one post)
    hdr = re.findall(r"(Wind|Mechanical|Patrol) Hold:\s*([^:]*?)(?=\s+(?:Off(?: the)? Schedule|Delayed|Open|Closed)\s*:|$)", t, re.I)
    if hdr:
        for c, seg in hdr: add("P-011", "hold_start", find_lifts(seg), c.lower())
        for seg in re.findall(r"Off(?: the)? Schedule:\s*([^:]*?)(?=\s+\w+ Hold:|$)", t, re.I): add("P-020", "closed_day", find_lifts(seg), None)
        return ev
    if re.search(r"\bdelayed\s*:", t, re.I) and re.search(r"\bopen\s*:", t, re.I):
        for seg in re.findall(r"Delayed:\s*([^:]*?)(?=\s+(?:Open|Closed|Off(?: the)? Schedule)\s*:|$)", t, re.I): add("P-030", "delay", find_lifts(seg), None)
        add("P-002", "reopen", find_lifts(re.split(r"delayed\s*:", t, flags=re.I)[0]), None, note="status_roster"); return ev
    if len(find_lifts(t)) >= 4 and re.search(r"\d\s*(?:am|a|pm|p)?\s*-\s*\d+\s*(?:am|a|pm|p)\b", t, re.I) and not re.search(r"\b(?:hold|closed|delayed)\b", t, re.I):
        roster = roster_with_sections(t, add, "P-003"); add("P-003", "scheduled_opening", find_lifts(roster), None); return ev
    if re.search(r"^(?:open at|these lifts are now open|the following lifts are now open|projected for|for (?:alpine|palisades), we expect)", t, re.I):
        add("P-002", "reopen", find_lifts(t), None, note="status_roster"); return ev
    last_lifts = []
    for s in split_sentences(t):
        sl = s.lower()
        if find_lifts(s): last_lifts = find_lifts(s)
        if re.search(r"download(?:s|ing)? only|mid-?station|advanced (?:levels? )?only|not servicing beginner|(?:mtn|mountain) run only|no return access|sightseeing only|limited terrain|offload at", sl) and (find_lifts(s) or last_lifts) and not re.search(r"\bnot open\b", sl):
            add("P-070", "partial", find_lifts(s) or last_lifts, "wind" if re.search(r"wind", sl) else None, detail="limited")
        am = re.search(r"all other (?:scheduled )?(?:\w+ )?lifts?\b[^.]*?\bare\b[^.]*?\bon (?:a )?(?:(wind|mechanical|patrol|maintenance) )?(hold|delay)(?: due to ([^.]*))?", s, re.I)
        if am:
            c = (am.group(1) or "").lower().replace("maintenance", "mechanical") or (cause_in(am.group(3)) if am.group(3) else None)
            add("P-013", "hold_start" if am.group(2).lower() == "hold" else "delay", ["ALL_OTHER"], c, **{"except": find_lifts(t)}); continue
        if re.search(r"up and running (?:close to|around|by|at) \d|expected at \d+:\d+|will be open at approximately", sl) and (find_lifts(s) or last_lifts) and not re.search(r"\bhold\b", sl) or re.search(r"estimating .* up and running", sl):
            add("P-030", "delay", find_lifts(s) or last_lifts, cause_in(s)); continue
        if re.search(r"will operate from|a go for \d|we expect the following|planning to run the following|lifts open \d|\d ?(?:am|a) ?- ?\d+ ?(?:pm|p) today|planned ops|scheduled lifts|lifts? projected|projected \w* ?open|est(?:imated)?\.? \w+ open|on deck|what we.re spinning|following lifts are spinning|today at #?squawalpine|looking to open|we plan to spin|here.s what|today.s ops|lifts accessing|lifts spinning|lifts? (?:&|and) \d+ trails|\d+ chairlifts", sl) and not re.search(r"\bhold\b|\bclosed\b", sl):
            roster = roster_with_sections(t, add, "P-001"); add("P-001", "scheduled_opening", find_lifts(roster), None); return ev
        if re.search(r"will operate from|lifts open \d|\d ?(?:am|a) ?- ?\d+ ?(?:pm|p) today", sl) and re.search(r"\bclosed\b", sl) and find_lifts(s):
            add("P-001", "scheduled_opening", [], None, note="mixed_with_closure")
        if re.search(r"\boff (?:of )?(?:the )?(\w+ )?hold\b", sl) and find_lifts(s):
            hm = re.search(r"off (?:of )?(?:the )?(\w+) hold", sl); w = hm.group(1) if hm else None; c = {"maintenance": "mechanical", "electrical": "mechanical"}.get(w) or (w if w in ("wind", "mechanical", "patrol") else None)
            add("P-040", "reopen", find_lifts(re.split(r"\b(?:is|are|has)\b", s, maxsplit=1, flags=re.I)[0]) or find_lifts(s), c, resolves_hold=True); continue
        if re.search(r"removed from (?:the |today.s )?schedule|will (?:be )?clos(?:e|ing) at \d|has been closed|have been closed|close the following lifts|had to close|closed for the season|will be closed \d", sl) and not re.search(r"\broad\b|\brd\b|parking", sl):
            c = cause_in(t) if re.search(r"gusts|winds?", sl) or cause_in(t) else None
            add("P-020", "closed_day", find_lifts(t if "following" in sl else s), "wind" if re.search(r"gusts|wind", sl) else c); continue
        if re.search(r"\b(?:is|are) delayed\b|delayed on the|operational delay|projected to open", sl) and find_lifts(s):
            add("P-030", "delay", find_lifts(s), cause_in(s) or ("weather" if "rime" in sl else None)); continue
        if re.search(r"(?:now |is |are )?spinning!?|\bis loading\b|opened on time|open to the public|now open at|are open\b|\bis open\b|has opened", sl) and find_lifts(s) and not re.search(r"will be|today:|\bnot open|should be|about an hour|mid-?station|open daily|season|run only|advanced only", sl):
            add("P-040", "reopen", find_lifts(re.split(r"\b(?:is|are|has)\b|now spinning|spinning", s, maxsplit=1, flags=re.I)[0]) or find_lifts(s), None); continue
        if re.search(r"all (?:the )?lots|lots are now full|parking (?:available|at alpine and)|parking spots|parking reservation", sl):
            add("P-050", "parking", [], None); continue
        if re.search(r"\b\d+ (?:lower mountain )?lifts?\b.{0,40}(?:schedul|for \d|\d ?(?:am|a)\b)|lifts? (?:are )?(?:on the )?schedul", sl) and not re.search(r"on delay|on hold", sl):
            add("P-001", "scheduled_opening", find_lifts(s), None, note="count_only"); continue
        if re.search(r"tomorrow|next (?:week|weekend)|this weekend", sl) and re.search(r"opening|will open", sl):
            add("P-090", "other", [], None, note="announcement"); continue
        if re.search(r"(?:will open|expected to open|aiming for an? \d|opening at|expected at|will open on schedule)", sl) and find_lifts(s) and not re.search(r"hold|delay|closed", sl):
            tm = re.search(r"(?:open(?:ing)?|expected) (?:at|for) (?:approximately |about |around )?(\d{1,2})(?::\d\d)?\s*(am|pm|a|p)?", sl)
            late = bool(tm) and ((int(tm.group(1)) % 12) + (12 if (tm.group(2) or "").startswith("p") or (not tm.group(2) and int(tm.group(1)) < 8) else 0)) >= 10
            add("P-030" if late else "P-001", "delay" if late else "scheduled_opening", find_lifts(s), None); continue
        if re.search(r"back open|to the open list|is back open", sl) and find_lifts(s):
            add("P-040", "reopen", find_lifts(s), None); continue
        if re.search(r"list of (?:closures|wind holds?)|added to (?:the )?(?:list of )?(?:wind )?holds?|(?:been|be) put on (?:a )?(\w+ )?hold|adding .* to the list|back on wind hold", sl) and find_lifts(s):
            hc = cause_in(s) or "wind"
            add("P-010" if "hold" in sl else "P-020", "hold_start" if "hold" in sl else "closed_day", find_lifts(s), hc); continue
        if re.search(r"on delay|delays? due to icing|icing on lifts", sl):
            add("P-030", "delay", find_lifts(s) or ["ALL"], "weather" if "ic" in sl else cause_in(s)); continue
        if re.search(r"mid-?station|uploads? only|min(?:ute)? schedule|open (?:till|until) \d", sl) and find_lifts(s):
            add("P-070", "partial", find_lifts(s), "wind" if "wind" in sl else None, detail="limited"); continue
        if re.search(r"safety (?:tip|alert|first)|unmarked hazards|shuttle|storm totals|\d+ ?(?:hour|hr|h) totals|hour totals|forecast is for|happy holidays|chance of", sl) and not re.search(r"\bhold\b", sl):
            add("P-060" if re.search(r"totals|forecast|chance", sl) else "P-090", "other", [], None); continue
        if re.search(r"\blot\b.*\bfull\b|hidden valley|deer park", sl):
            add("P-050", "parking", [], None); continue
        if re.search(r"(?:\bon|put on|added to|to the list of) (?:a |the )?(?:\w+ )?(?:wind |mechanical |patrol |maintenance )?holds?\b", sl) and find_lifts(s) and not re.search(r"expected to go|may go|could go|will be put", sl):
            hm = re.search(r"(wind|mechanical|patrol|maintenance|electrical|icing)\s+holds?", sl)
            hc = {"maintenance": "mechanical", "electrical": "mechanical", "icing": "weather"}.get(hm.group(1), hm.group(1)) if hm else None
            subj = re.split(r"\b(?:remains?|is|are|will|also|have|has)\b", s, maxsplit=1, flags=re.I)[0]
            add("P-010", "hold_start", find_lifts(subj) or find_lifts(s), hc); continue
        if re.search(r"download(?:s|ing)? only|downloads? only|mid-?station only|sightseeing only|(?:mtn|mountain) run only|advanced only|no return access|access to .{0,25} only", sl) and (find_lifts(s) or last_lifts):
            add("P-070", "partial", find_lifts(s) or last_lifts, cause_in(s) or ("wind" if re.search(r"wind", sl) else None), detail="download_only" if "download" in sl else "limited"); continue
        if re.search(r"may go on hold|may go on wind hold", sl): add("P-012", "warning", find_lifts(s), "wind"); continue
        if re.search(r"(?:added to the )?closed list|closing .* (?:for|due)|will be closed on|have gone on|has gone on", sl) and not re.search(r"patrol cup|stifel|\broad\b|\brd\b", sl):
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
        if re.search(r"added to (?:today.s |the )?schedule", sl) and re.search(r"now open|is open", sl) and find_lifts(s):
            add("P-001", "scheduled_opening", find_lifts(s), None); add("P-040", "reopen", find_lifts(s), None); continue
        if re.search(r"added to (?:today.s |the )?schedule|are not open|not open\.", sl) and find_lifts(s):
            add("P-001" if "added" in sl else "P-020", "scheduled_opening" if "added" in sl else "closed_day", find_lifts(s), None); continue
        if re.search(r"stage \d+ wind alert|wind alert", sl): add("P-012", "warning", find_lifts(s), "wind"); continue
        if re.search(r"back up and running|up and running", sl) and not re.search(r"should be|will be|about an hour", sl): add("P-040", "reopen", find_lifts(s), None); continue
        if re.search(r"will be delayed|expect (?:some )?delays|snow safety delays|delayed opening|delays and closures are possible", sl):
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
        if re.search(r"all (?:the )?lifts.*(closed|on (?:\w+ )?hold)|all lifts that", sl):
            if re.search(r"on (?:\w+ )?hold", sl) and "closed" not in sl: add("P-021", "hold_start", ["ALL"], cause_in(s) or ("wind" if "wind hold" in sl else None))
            else: add("P-021", "closed_day", ["ALL"], cause_in(s) or ("wind" if "wind hold" in sl else None))
            continue
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
            lifts = find_lifts(subj) or find_lifts(s) or last_lifts
            dm = re.search(r"due to(.*)", s, re.I); c = cause_in(dm.group(1)) if dm else None
            add("P-020", "closed_day", lifts, c); continue
        # P-040 reopen
        if re.search(r"\b(?:is|are)\s+(?:now\s+|also\s+)?open\b|re-?opened|\balso open\b|\bnow open\b|^[\w\s’'&,.-]+ open!?$", sl) and not re.search(r"\broad\b|open at|will open|opening (?:tomorrow|soon)", sl):
            subj = re.split(r"\b(?:is|are|has)\b|, also|\bopen\b|\balso\b", s, maxsplit=1, flags=re.I)[0]
            add("P-040", "reopen", find_lifts(subj) or find_lifts(s), None); continue
    if ev: return ev
    if re.match(r"^(?:palisades|alpine)\b[^:]{0,15}:|^snow and weather|^today.s weather|^update:.*operating plan", t, re.I):
        add("P-060", "other", [], None); return ev
    if not find_lifts(t): add("P-090", "other", [], None, note="no_lift_named"); return ev
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
