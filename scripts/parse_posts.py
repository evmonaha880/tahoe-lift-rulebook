"""Deterministic parser: ops posts -> typed events. Every event records the rule that made it (parse_rule_id).
Observed = the post states it. Nothing here infers from weather; that happens later and is tagged separately.
usage: python3 -I scripts/parse_posts.py 2023 [train|heldout|all]   -> data/derived/<winter>_<split>_events.json
Rules ledger is exported to rules/ledger_<winter>.json (data, so other mountains can reuse the method)."""
import os, re, sys, json, collections
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ---- lift vocabulary (canonical name -> regex alias). Lift->mountain mapping is NOT done here (modeling decision later).
LIFTS = {
    "Base to Base Gondola": r"(?:the )?base (?:to|2) base(?: gondola)?|base-to-base(?: gondola)?|b ?2 ?b(?: gondola)?|gondola",
    "Tram": r"(?:the )?tram",
    "Funitel": r"(?:the )?funi(?:tel)?",
    "KT-22": r"kt-?22|\bkt\b",
    "Red Dog": r"red do[dg](?! side)|reddog",
    "Resort Chair": r"resort(?: chair)?(?! side)|squaw (?:creek|cr)\b",
    "Wa She Shu": r"wa ?she ?(?:shu|she)|squaw (?:one|1)(?: express)?",
    "Siberia": r"siberia|sibo",
    "Headwall": r"headwall",
    "Emigrant": r"emigrant",
    "Silverado": r"silverado",
    "Solitude": r"solitude|sol(?=\s*(?:$|[,&.\n-]))",
    "Granite Chief": r"granite(?: chief)?(?! peak)",
    "Big Blue": r"(?:big|bg|b\.?) blue",
    "Shirley Lake": r"shirley(?: lake)?",
    "Bailey's Beach": r"bailey[’']?s(?: beach)?",
    "Belmont": r"belmont|blm(?:o|n)?nt",
    "Mountain Meadow": r"(?:(?:mountain|mtn)\.? ?(?:meadows?|mdw|mdow)|meadow|(?<=[-•,&] )meadows)(?! road)",
    "High Camp Carpet": r"(?<!to )high camp(?: carpet)?|(?:hc|camp|high) carpet",
    "Gold Coast": r"gold coast|gld coast|gol?d coast",
    "Lakeview": r"lakeview",
    "Yellow": r"yellow(?: chair)?",
    "Exhibition": r"exhi(?:b(?:ition)?)?",
    "First Venture": r"(?:first|1st) v(?:ent(?:ure)?)?",
    "Far East": r"far east",
    "Big Carpet": r"big carpet|big(?= (?:&amp;|&|and) little carpets?)",
    "Alpine Bowl": r"alpine bowl(?: chair)?|abc",
    "Summit": r"summit(?: chair)?",
    "Roundhouse": r"round ?house",
    "Kangaroo": r"kangaroo",
    "Scott": r"scott?(?: chair)?",
    "Treeline Cirque": r"treel(?:ine|ing)(?: cirque)?|tlc",
    "Sherwood": r"sherwood",
    "Subway": r"subway",
    "Broken Arrow": r"broken arrow",
    "Ahsoka Carpet": r"ahsoka|ashoka",
    "Hot Wheels": r"hot wheels",
    "Kaya Carpet": r"kaya(?: carpet)?",
    "Tucker Carpet": r"tucker(?: carpet)?",
    "Little Carpet": r"little carpets?",
    "Olympic Lady": r"olympic lady|oly\.? lady",
    "Sherwood Express": r"sherwood express",
    "Boomer": r"boomer(?: magic)?(?: carpet)?",
    "Carpets": r"(?<!\d )(?<!tubing )(?<!chairs and )(?<!chairs & )(?<!lifts and )(?<!lifts & )(?:(?:the|both|all|ski school|snow school|lower|upper|beginner)\s+)?(?:magic )?carpets?\b",   # generic; resolved to Alpine Carpets / Palisades Carpets by context in find_lifts
    "SnoVentures": r"sno-?v(?:entures?)?\+?(?: carpet| area)?(?! tubing)",
}
LIFT_RE = re.compile(r"\b(?:" + "|".join(f"(?P<L{i}>{p})" for i, p in enumerate(LIFTS.values())) + r")\b", re.I)
LIFT_NAMES = list(LIFTS.keys())

# Alpine's "Meadow" (366 m, beside Subway) and Palisades' "Mountain Meadow" (High Camp, 850 m) are two lifts (rules/lift_groups.json).
# A bare "Meadow" is Alpine's when its own span, or failing that the whole post, names Alpine lifts and no Palisades-only lift.
ALPINE_ONLY = {"Alpine Bowl", "Big Carpet", "Kangaroo", "Roundhouse", "Summit", "Yellow", "Lakeview", "Scott", "Subway", "Treeline Cirque", "Sherwood", "Sherwood Express", "Little Carpet"}
PALISADES_ONLY = {"Tram", "Funitel", "KT-22", "Red Dog", "Resort Chair", "Wa She Shu", "Siberia", "Headwall", "Emigrant", "Silverado", "Solitude", "Granite Chief", "Big Blue",
                  "Shirley Lake", "Bailey's Beach", "Belmont", "High Camp Carpet", "Gold Coast", "Far East", "Exhibition", "Broken Arrow", "Olympic Lady", "First Venture"}
_CTX = {"t": ""}
def _raw_hits(text):
    return [(LIFT_NAMES[int(m.lastgroup[1:])], m.group(0)) for m in LIFT_RE.finditer(text)]
def _alpine_side(span):
    hits = {n for n, _ in _raw_hits(span)}
    if hits & ALPINE_ONLY and not hits & PALISADES_ONLY: return True
    if hits & PALISADES_ONLY and not hits & ALPINE_ONLY: return False
    if re.search(r"\balpine\b(?! meadows? road)", span, re.I) and not re.search(r"\b(?:palisades|squaw)\b", span, re.I): return True
    return None

def find_lifts(span):
    out = []
    for m in LIFT_RE.finditer(span):
        name = LIFT_NAMES[int(m.lastgroup[1:])]
        if name == "Carpets":
            side = _alpine_side(span)
            if side is None:
                ctx = _CTX["t"]; side = _alpine_side(ctx) if ctx else False
                if side is None and re.search(r"#alpine|\balpine\b", ctx or "", re.I) and not re.search(r"#palisades|#squaw", ctx or "", re.I): side = True
            name = "Alpine Carpets" if side else "Palisades Carpets"
        if name == "Mountain Meadow" and not re.search(r"mountain|mtn|mdow", m.group(0), re.I):
            side = _alpine_side(span)
            if side is None:
                ctx = _CTX["t"]; side = _alpine_side(ctx) if ctx else False
                if side is None and re.search(r"#alpine|\balpine\b", ctx or "", re.I) and not re.search(r"#palisades|#squaw", ctx or "", re.I): side = True
            if side: name = "Alpine Meadow"
        if name not in out: out.append(name)
    return out

CAUSE_RE = [("wind", r"wind"), ("mechanical", r"mechanical|hose|power|electrical|maintenance"), ("patrol", r"patrol|avalanche|snow safety|control"), ("weather", r"\bicy\b|\bice\b|rime|icing|lightning|storm|snow(?:fall)?|rain|conditions"),]
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
    ("P-014", "hold_start", "Group scope: 'all upper mountain lifts', 'all lifts at Alpine' ... on hold / delayed / closed (lift = UPPER_MOUNTAIN, LOWER_MOUNTAIN, ALL_ALPINE, ALL_PALISADES; not expanded to individual lifts)"),
    ("P-020", "closed_day", "'<lifts> closed for the day/remainder' or 'off (the) schedule' or 'now closed'"),
    ("P-021", "closed_day", "'All lifts ... are now closed for the day' (lifts = all)"),
    ("P-022", "closed_day", "Whole-resort or whole-side closure with no lift named: 'Palisades Tahoe is CLOSED today', 'ALL LIFTS CLOSED TODAY', 'will not have any lift operations' (lift = ALL_PALISADES / ALL_ALPINE / ALL)"),
    ("P-012h", "warning", "Hedged wording in any post: 'winds may impact lift operations', 'please EXPECT DELAYS', 'possible wind holds' (a prediction; post-level, lift None)"),
    ("P-030", "delay", "'Delayed Opening' or '<lift> on a mechanical delay'"),
    ("P-040", "reopen", "'<lifts> is/are (now/also) open' or 're-opened'"),
    ("P-050", "parking", "Parking lots full / parking at <alternate lot>"),
    ("P-003", "scheduled_opening", "No prefix needed: 4+ lifts named with a time range (e.g. 9am-4pm) and no hold/close verb"),
    ("P-070", "partial", "Downloads only / mid-station only / sightseeing only / closing at <time> for maintenance"),
    ("P-060", "other", "Weather report: starts 'Palisades:' / 'Alpine:' / 'Snow and Weather:' with no lift roster (filtered)"),
    ("P-090", "other", "Road status, promotions, safety message, events (filtered)"),
]
RID = {r[0]: r for r in RULES}

HEDGE_RE = re.compile(r"\bexpect(?:ing|ed)?\b[^.!?]{0,30}\bdelays?\b|\b(?:may|might|could)\b[^.!?]{0,40}\b(?:delays?|delayed|(?:go|be put|be placed) on (?:a |an )?(?:\w+ )?hold)\b|\b(?:possible|potential(?:ly)?|likely|anticipat\w*)\s+(?:\w+ ){0,2}(?:delays?|holds?)\b|\bdelays?\s+(?:are\s+|is\s+)?(?:expected|likely|possible|anticipated)\b(?!\s*\))|\blikely to go on\b|\bprepared for (?:\w+ )?delays?\b|\banticipat\w+ (?:some )?delays?\b")
def split_sentences(t):
    t = re.sub(r"\s*#\w+\s*", ". ", t)
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“]|$)|\n+", t) if s.strip()]
    out = []
    for p in parts:
        n0 = len(out)   # split compound sentences: 'A is on hold, B and C are open, D will be closed'
        m_and = re.search(r"^(.*?\b(?:is|are|will|has|have)\b[^.]*?),?\s+and\s+((?:the\s+)?[A-Z][\w’' -]{1,30}?\s+(?:is|are|will|has been|have been)\b.*)$", p)
        if m_and and not re.search(r"\b(?:is|are|will|has|have)\b", m_and.group(1).rsplit(",", 1)[-1]): m_and = None   # 'A is X, B and C are Y': the 'and' joins a subject list
        for piece in (list(m_and.groups()) if m_and else [p]):
            for c in re.split(r",\s+(?=[A-Z][\w’' -]{1,30}?\s+(?:is|are|will|on|has|have)\b)|\s+but\s+(?=[A-Za-z])|,?\s+while\s+(?=[A-Z][\w’' -]{1,30}?\s+(?:is|are|will|remains?|has|have)\b)|\s+and\s+(?=(?:off\s+(?:the\s+)?schedule|closed|opened|open)\b)|(?<=\bhold)\s+(?=[A-Z][\w ]{1,30}?\s+(?:has|have|is|are)\b)", piece):
                if c and c.strip():
                    if len(out) > n0 and LIFT_RE.match(c.strip()) and not re.search(r"\b(?:is|are|has|have|will|been)\b", out[-1]) and not out[-1].endswith(":"):
                        out[-1] += ", " + c.strip(); continue
                    out.append(c.strip())
    return out


ROSTER_HDR = re.compile(r"(?:\b\d+\s+lifts?\b[^:.]{0,60}|\blifts?\b[^:.]{0,40}\b(?:today|on tap|on the schedule)|on the schedule(?: today)? at (?:palisades|alpine)|at (?:palisades|alpine)[^:.]{0,20}on schedule|today.s lifts|following lifts (?:open|will operate)[^:.]{0,30}|plan is to have the following lifts|(?:we )?anticipate having the following lifts[^:.]{0,30}|expect to start the day with the following lifts|(?:are )?projecting a? ?[\d:]+ opening for the following|updated (?:palisades|alpine) plan for [^:.]{0,12}|estimated opening time is[^:.]{0,30}for the following|(?:are )?(?:projected|projecting)[^:.]{0,30}for the following|(?<!open )(?<!now )(?<!spinning )at (?:palisades|alpine)|today at (?:squaw|alpine)[^:.]{0,30}|(?:attempting|trying|planning) to open the following lifts[^:.]{0,30}|what we got spinning today|(?:will have|we anticipate) the following lifts? at \d+ ?(?:am|pm)|starting the day at [^:.]{0,30}|(?:alpine meadows |squaw )?planned openings)\s*:", re.I)
SEC_RE = re.compile(r"\b(Wind|Mechanical|Patrol|Maintenance|Electrical)\s+Holds?(?:\s+at\s+(?:alpine|palisades|squaw))?\s*:|\b(Wind\s+Closures?)\s*:|\b(Hold\s*/\s*Delay(?:ed)?)\s*:|\b(Delay(?:ed)?(?:\s+Openings?)?)\s*:|\b(Weather\s+Impacts?)\s*:|\b(Off[-\s](?:the\s+)?Schedule(?:\s+for\s+Today)?|Removed|Closed(?:\s+for\s+the\s+day)?)\s*:", re.I)
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
        elif "hold" in h: add("P-011", "hold_start", lifts, {"maintenance": "mechanical", "electrical": "mechanical", "lightning": "weather", "icing": "weather", "ice": "weather", "icy": "weather"}.get(h.split()[0], h.split()[0]))
        elif h.startswith("delay"): add("P-030", "delay", lifts, None)
        elif "impact" in h: add("P-012", "warning", lifts, "weather")
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
    found = {c for c, p in (("wind", r"wind"), ("weather", r"lightning|\bice\b|icing|rain|snow level"), ("patrol", r"avalanche|snow safety|patrol"), ("mechanical", r"mechanical|maintenance|electrical|power")) if re.search(p, m.group(1), re.I)}
    if len(found) == 1:
        c = found.pop()
        for e in ev:
            if e["event_type"] in ("hold_start", "closed_day", "delay", "partial") and not e["cause"]:
                e["cause"], e["cause_source"] = c, "observed"; e["note_cause"] = "post-level"
    return ev

MARK_RE = re.compile(
    r"(?P<warn>(?:please\s+)?(?:expect(?:ed)?|possible|potential|anticipated)\s+(?:(?:snow\s+safety|weather|wind|operational|lift)\s+)?delays?\s*:)"
    r"|(?P<hold>(?:(?P<hc>wind|mechanical|patrol|maintenance|electrical)\s+holds?(?:\s+at\s+(?:alpine|palisades|squaw))?|(?<![\w-])(?<!schedule/on )(?<!schedule/)holds?(?:\s+at\s+\w+)?(?=\s*:)|weather\s+holds?|mechan\.?\s+holds?|hold\s*/\s*delay(?:ed)?|(?:will\s+)?(?:begin|start)\s+the\s+day\s+on\s+(?:a\s+)?(?:(?P<hc2>wind|mechanical|patrol)\s+)?hold)\s*[:-]?)"
    r"|(?P<delay>(?:(?:are|is)\s+on\s+delay|likely\s+(?:snow\s+safety\s+)?delays\s+for|scheduled\s+but\s+(?:on\s+)?delay(?:ed)?(?:\s*\([^)]*\))?|operational\s+delay(?:\s*\([^)]*\))?|experiencing\s+(?:\w+\s+)?delays?\s+[^:.]{0,70}following\s+lifts(?=\s*:)|delay(?:ed)?(?:\s+lifts?)?(?:\s+openings?)?(?:\s+at\s+(?:alpine|palisades|squaw))?)\s*[:,-]?)"
    r"|(?P<closed>(?:off[-\s](?:the\s+)?schedule(?:\s+for\s+(?:the\s+day|today))?|(?P<cc>wind)\s+closures?|(?<!and )closed\s+for\s+the\s+day(?=\s*:)|removed(?=\s*:))\s*[:-]?)"
    r"|(?P<sched>(?:est(?:imated)?\.?|anticipated|projected)\s+\d{1,2}(?::\d\d)?\s*(?:am|pm|a|p)?\s*(?:open(?:ing)?)?\s*:|(?:scheduled|planned|expected(?:\s+very\s+close\s+to)?|projected)\s+(?:for|at)?\s*\d+(?::\d\d)?\s*(?:am|pm|a|p)?\b\s*[:-]?|\d+\s*(?:am|pm)\s+opening|\d{1,2}\s*(?:am|a)\s+open\s*:|open\s+at\s+\d+\s*(?:am|pm)?\s*:?)"
    r"|(?P<open>(?:the\s+following\s+lifts\s+are\s+)?(?:now\s+)?\bopen\s*:|all\s+open\s+now\s*:|(?:lifts\s+)?(?:have\s+)?re-?opened\s*:)", re.I)

_LEFT = []   # prose that followed a list inside sectional(); parsed again by the caller
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
            if not (re.match(r"\s*-", seg) or LIFT_RE.match(seg.lstrip())): seg = ""
        if m.group(0).rstrip().endswith(":") and m.lastgroup != "sched":
            _cut = re.split(r"\.\s+(?=[A-Z][^.]*\b(?:is|are|will|has|have|remains?)\b)", seg, maxsplit=1)   # a prose sentence after the list is not part of it
            seg = _cut[0]
            if len(_cut) > 1: _LEFT.append(_cut[1])
        kind = m.lastgroup if m.lastgroup in ("hold", "delay", "closed", "sched", "open", "warn") else next(k for k in ("hold", "delay", "closed", "sched", "open", "warn") if m.group(k))
        segs.append((kind, m, seg, find_lifts(seg)))
    withlifts = [x for x in segs if x[3]]
    colon = any(x[1].group(0).rstrip().endswith(":") for x in withlifts)
    if not withlifts or not (len({x[0] for x in withlifts}) >= 2 or colon or any(len(x[3]) >= 2 for x in withlifts)): return False
    if len(segs) == 1 and segs[0][0] == "delay" and not colon and len(segs[0][3]) < 2: return False
    pre = t[:segs[0][1].start()]
    if segs[0][0] in ("hold", "delay", "closed", "warn") and len(find_lifts(pre)) >= 2 and not re.search(r"\bhold|delay|closed|off[- ]schedule|remov|will not|not operate|\bare open\b|now open|spinning", pre, re.I):
        add("P-001", "scheduled_opening", find_lifts(pre), None, note="roster_before_sections")     # 'At Alpine: 13 lifts on the schedule: A B C  Wind hold: D E'
    for kind, m, seg, lifts in segs:
        if not lifts: continue
        for pm in re.finditer(r"([\w’' ]{3,30}?)\s*\(([^)]*(?:download|mid-?station|sightseeing)[^)]*)\)", seg, re.I):
            pl = find_lifts(pm.group(1))[-1:]
            if pl: add("P-070", "partial", pl, None, detail="download_only" if "download" in pm.group(2).lower() else "restricted")
        if kind == "hold": add("P-011", "hold_start", lifts, (m.group("hc") or m.group("hc2") or "").lower().replace("maintenance", "mechanical").replace("electrical", "mechanical") or None)
        elif kind == "warn":
            add("P-012", "warning", lifts, cause_in(m.group(0) + " " + t[max(0, m.start() - 60): m.start()]) or None)
            if re.search(r"\b\d+ (?:\w+ )?lifts? (?:are )?(?:scheduled|on the schedule)", pre, re.I) and m is segs[0][1]: add("P-001", "scheduled_opening", lifts, None, note="roster")
        elif kind == "delay": add("P-030", "delay", lifts, "patrol" if re.search(r"snow\s+safety", m.group(0), re.I) else None)
        elif kind == "closed": add("P-020", "closed_day", lifts, "wind" if m.group("cc") else None)
        elif kind == "sched": roster_with_sections(seg, add, "P-001"); add("P-001", "scheduled_opening", lifts, None, note="roster")
        else: roster_with_sections(seg, add, "P-002"); add("P-002", "reopen", lifts, None, note="status_roster")
    return True

GRP_RE = re.compile(r"\b(?:all (?:of our )?(?:the )?(?:scheduled )?(?:(?:aerial|chair) )?lifts (?:at|on|in) (?P<site>alpine(?: meadows)?|palisades(?: tahoe)?|squaw(?: valley)?)|all (?:of our )?(?:scheduled )?(?P<ud>upper|lower)[- ]mountain(?: lifts)?(?: (?:at|on) (?:palisades|squaw)(?: valley)?)?|(?P<ud2>upper|lower)[- ]mountain(?: lifts)?(?: (?:at|on) (?:palisades|squaw)(?: valley)?)?)\b", re.I)
# ---- P-022 whole-resort / whole-side closure ("Palisades Tahoe is CLOSED today", "ALL LIFTS CLOSED TODAY", "will not have any lift operations").
# Emitted only when the post names no individual lift, so it never competes with lift-level rules. Scope: ALL_PALISADES, ALL_ALPINE or ALL (both sides).
_WC_EXCL = re.compile(r"\broad\b|\brd\b|\bmountain run\b|\b(?:upper|lower)[- ]mountain\b|\bparking\b|\blots?\b|\btubing\b|\bhighway\b|\bhwy\b|\bi-80\b|\bshuttles?\b|terrain park|\bpark\b|\bvillage\b|\bshops?\b|\brentals?\b|\btickets?\b|\bhotel\b|\bbackcountry\b|\bsummer\b|uphill", re.I)
_WC_ALL = re.compile(r"\ball (?:lifts|chair ?lifts|chairs|lift operations|lift ops|operations|lifts and terrain)\b[^.!?]{0,75}?\b(?:closed|not operat|suspended|closing)", re.I)
_EXC = re.compile(r"\b(?:except(?: for)?|with the exception of|other than)\b", re.I)
_WC_NOSKI = re.compile(r"\bno\s+(?:skiing|riding|lift service)(?: and (?:skiing|riding))?\b[^.!?]{0,25}\b(?:today|tomorrow)\b", re.I)
_DAYS = ["mon", "tues", "wednes", "thurs", "fri", "satur", "sun"]
def _weekdays(sent):
    """weekday numbers named in a sentence, ranges like 'Friday-Sunday' expanded; None when none"""
    out = set(); tok = re.findall(r"\b(mon|tues|wednes|thurs|fri|satur|sun)day\b(\s*(?:-|to|through|thru)\s*(mon|tues|wednes|thurs|fri|satur|sun)day\b)?", sent, re.I)
    for a, rg, b in tok:
        i = _DAYS.index(a.lower()); out.add(i)
        if b:
            j = _DAYS.index(b.lower()); k = i
            while k != j: k = (k + 1) % 7; out.add(k)
    return out or None
_WC_NOOP = re.compile(r"\b(?:will not|won.t|are not|is not|not)\s+(?:be\s+)?(?:have|having|running|operating|open|opening|offer|offering)\b[^.!?]{0,30}?\b(?:any\s+)?lift (?:operations|service)\b|\bno lift (?:operations|service)\b|\blift operations? (?:are |is )?(?:closed|suspended|cancel+ed)\b", re.I)
_WC_SUBJ = re.compile(r"\b(?:palisades tahoe|squaw valley(?:\s*[|&/]?\s*alpine meadows)?|alpine meadows|squaw alpine|both (?:sides|mountains|resorts|areas)|the resort|our resort|the mountain|palisades|alpine)\b[^.!?]{0,60}?\b(?:is|are|will be|will remain|remains?|has been|have been|is being)\b[^.!?]{0,14}\bclosed\b", re.I)
_WC_PARTIAL = re.compile(r"\blifts?\b[^.!?]{0,25}\bon (?:an? )?(?:wind |mechanical |patrol )?hold|\blifts? (?:that|which) (?:were|are|was)\b|\b(?:that|which)\b[^.!?]{0,30}\bon (?:an? )?(?:\w+ )?hold", re.I)
_WC_FUTURE = re.compile(r"\b(?:tomorrow|tonight|(?:on|for) (?:mon|tues|wednes|thurs|fri|satur|sun)day|\d{1,2}/\d{1,2}(?:/\d{2,4})?|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2})\b", re.I)
def _wc_scope(s):
    sl = s.lower()
    if re.search(r"\ball (?:\w+ )?lifts (?:at|on) (?:palisades tahoe|palisades|squaw valley|squaw)\b(?!\s*(?:and|&|\|)\s*alpine)", sl) and not re.search(r"\bboth\b|alpine", sl): return "ALL_PALISADES"
    if re.search(r"palisades tahoe alpine", sl): return "ALL_ALPINE"
    if re.search(r"\bboth\b|palisades tahoe(?! road)|squaw valley\s*[|&/]?\s*alpine|squaw alpine|squaw and alpine|alpine and (?:palisades|squaw)|(?:palisades|squaw) and alpine", sl): return "ALL"
    pal = re.search(r"palisades|squaw|olympic valley", sl); alp = re.search(r"alpine(?! meadows road)", sl)
    if pal and alp: return "ALL"
    if alp: return "ALL_ALPINE"
    if pal: return "ALL_PALISADES"
    return "ALL"
def whole_closure(t, dt=None):
    """-> list of (scope, sentence, announced_for_later_day) or []. Applies only to posts that name no individual lift."""
    out = []
    for sent in split_sentences(t):
        if _WC_EXCL.search(sent) or _WC_PARTIAL.search(sent): continue
        if find_lifts(re.sub(r"\b(?:alpine meadows|palisades tahoe|palisades|squaw valley|squaw|olympic valley|granite peak)\b|\balpine\b(?!\s+bowl)|\b(?:the |our )?resort\b(?!\s+chair)", " ", _EXC.split(sent, 1)[0], flags=re.I)): continue      # a sentence that names a lift is a lift-level statement
        if _WC_ALL.search(sent) or _WC_NOOP.search(sent) or _WC_NOSKI.search(sent) or (_WC_SUBJ.search(sent) and re.search(r"\b(?:today|for the day|all day|tomorrow|remainder|rest of the day|for the season|(?:mon|tues|wednes|thurs|fri|satur|sun)day)\b|^\W*(?:palisades|squaw|alpine)[^.!?]{0,40}closed", sent, re.I)) or re.search(r"^\W*(?:the\s+)?(?:resort|mountain)\s+(?:remains|is|will remain)\s+closed\b", sent, re.I):
            if re.search(r"\b(?:reopen|re-open|will open|opening at|is open|are open|now open)\b", sent, re.I) and not re.search(r"\bclosed\b", sent, re.I): continue
            wd = _weekdays(sent)
            if wd is not None and dt is not None and not re.search(r"\btoday\b", sent, re.I): fut = dt.weekday() not in wd           # 'Alpine is CLOSED Monday and Tuesday' posted on a Tuesday is today
            else: fut = bool(_WC_FUTURE.search(sent)) and not re.search(r"\btoday\b|\bthis (?:morning|afternoon|evening)\b", sent, re.I)
            out.append((_wc_scope(sent), sent, fut))
    return out
PARSER_VERSION = "2026.11.07.11"      # bump on every behaviour change; written into every event so a number can be traced to the parser that made it
TAGS = [("wind", r"\bwinds?\b|gusts?"), ("avalanche", r"avalanche|snow safety|control work|mitigation|hazard reduction"), ("snow", r"\bsnow|storm|blizzard|shovel|powder"),
        ("patrol", r"patrol"), ("mechanical", r"mechanical|maintenance|hose|electrical|technical|repair|winch"), ("ice", r"\bicy\b|\bice\b|icing|rime|freezing"),
        ("visibility", r"visibility|\bfog\b|whiteout|white-out|low vis"), ("lightning", r"lightning|thunder"), ("power", r"power (?:outage|failure|loss)|outage"),
        ("flood", r"flood"), ("grooming", r"groom"), ("rain", r"\brain\b|slush"), ("weather", r"\bweather\b|\bconditions\b")]
def cause_tags(s):
    """Multi-label cause words in the post text (post level, not sentence level). `cause` stays the single first-match family."""
    return [k for k, p in TAGS if re.search(p, s, re.I)]

def group_scopes(s):
    out = []
    if re.search(r"lifts (?:at|on) (?:alpine|palisades|squaw)[\w ]*? and (?:alpine|palisades|squaw)", s, re.I): return ["ALL"]
    for m in GRP_RE.finditer(s):
        if m.group("site"): g = "ALL_ALPINE" if m.group("site").lower().startswith("alpine") else "ALL_PALISADES"
        else: g = "UPPER_MOUNTAIN" if (m.group("ud") or m.group("ud2")).lower() == "upper" else "LOWER_MOUNTAIN"
        if g not in out: out.append(g)
    return out

def split_roster_prose(raw):
    """'Open: <header>: / bullet lines / then a prose sentence about other lifts' -> (roster text, prose text), else None.
    Without this the prose sentence is swallowed by the roster and its on-hold lifts come out as open."""
    lines = raw.split("\n")
    seen_header = bullets = 0
    for j, l in enumerate(lines):
        x = l.strip()
        if not x: continue
        if x.endswith(":"): seen_header += 1; continue
        if re.match(r"^[•\-\*–]", x) or len(x.split()) <= 4 and not re.search(r"\b(?:is|are|will|remains?)\b", x): bullets += 1; continue
        if seen_header and bullets >= 2 and len(x.split()) >= 5 and re.search(r"\b(?:is|are|will|remains?|have|has)\b", x) and find_lifts(x) \
                and re.search(r"\bhold\b|\bdelay|off[- ]schedule|closed|\bnot open", x, re.I) and not x.startswith("#"):
            return "\n".join(lines[:j]), "\n".join(lines[j:])
        if len(x.split()) >= 5: return None
    return None

# ---- P-012h hedged wording: a prediction, not an event ("winds may impact lift operations", "please EXPECT DELAYS", "possible wind holds").
# Added to any post that has such a sentence and no warning event yet. Always post-level (lift None).
HEDGE = re.compile(r"\b(?:may|might|could|can|will)\s+(?:also\s+)?(?:have an?\s+)?(?:impact|affect)\b[^.!?]{0,45}\b(?:lifts?|lift operations?|operations?|operation|status)\b|\b(?:lift operations?|operations?|openings?)\b[^.!?]{0,25}\b(?:may|might|could|will)\s+(?:be\s+)?(?:impact(?:ed)?|affect(?:ed)?|limit(?:ed)?|delay(?:ed)?)\b|\b(?:please\s+)?expect\s+(?:some\s+|possible\s+)?delays?\b|\b(?:may|might|could)\s+(?:result in|cause|see|bring)\s+(?:some\s+)?(?:delays?|holds?|closures?)\b|\bpossible\s+(?:wind\s+)?(?:holds?|delays?|closures?)\b|\bwinds?\s+(?:may|might|could)\b[^.!?]{0,35}\b(?:lifts?|operations?)\b", re.I)
def hedged_warnings(p, ev, text):
    if any(e["event_type"] == "warning" for e in ev) or re.search(r"\b(?:accident|hwy|highway|i-80|traffic|roads?|chains?|collision|crash|shuttle|parking)\b", text, re.I): return []      # road delays are not lift warnings
    out = []
    for sent in split_sentences(text):
        m = HEDGE.search(sent)
        if not m or re.search(r"\bwill have an? (?:slightly )?delayed (?:opening|start)\b", sent, re.I): continue
        dt = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles"))
        base = {"source_post_id": p["id"], "start": dt.isoformat(timespec="minutes"), "end": None, "event_type": "warning", "parse_rule_id": "P-012h", "confidence": 1.0}
        cause = cause_in(sent) or ("wind" if re.search(r"\bwinds?\b|gust", text, re.I) else None)
        cause = {"lightning": "weather"}.get(cause, cause)
        out.append({**base, "lift": None, "cause": cause, "cause_source": "observed" if cause else "unstated"})   # post-level: a roster in the same sentence would otherwise make every listed lift a subject
        break
    return out

# ---- P-014e and friends (2026-11-07 evening, from the three-model hand check): named groups, 'also closed', schedule swaps and exclusions, sightseeing, runs.
NONLIFT = re.compile(r"\b(?:border cross|half ?pipe|terrain park|snow ?park)\b", re.I)
def clean_text(text):
    """sentences about runs, parks and features are not lift statements; 'open until 4pm' is the normal closing time, not a limited operation"""
    def keep(m):
        sent = m.group(0)
        return " " if (NONLIFT.search(sent) and not find_lifts(NONLIFT.sub(" ", sent))) else sent
    text = re.sub(r"[^.!?\n]+[.!?]?", keep, text)
    text = re.sub(r"\((?:lower|upper|mid)\s+headwall(?: terminal)?\)|\b(?:lower|upper|mid)\s+headwall terminal\b", " ", text, flags=re.I)      # a snow-level landmark, not the lift
    text = re.sub(r"\bmountain run (?:is|are) (?:now )?closed(?:,? (?:so|and)\s+)?", "", text, flags=re.I)
    return re.sub(r"\b(open|operating|spinning|running)\s+(?:until|till)\s+(?:4|4:00|4:30|5)\s*pm\b", r"\1", text, flags=re.I)
# ---- generic fallback (P-099): a lift named in a status sentence or list section that no other rule gave an event
_FUT = re.compile(r"\b(?:tomorrow|tonight|next (?:week|weekend|season)|this weekend|over the weekend|last year|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
_NOT_STATUS = re.compile(r"\b(?:avoid the|area\b|offload|access (?:to|from|is)|blog\b|what's going on|towers?\b|\d{1,2}/\d{1,2}|terrain|park\b|parking|road\b|shuttle|replace|construction|new (?:lift|chair)|6-?pack|lessons?|tickets?|tubing|dining|restaurant|bike|summer)\b", re.I)
_HEDGEY = re.compile(r"\b(?:may|might|could|if\b|pending|being assessed|assessing|hope|hoping|try|trying|possible|potential|likely|should)\b", re.I)
def _status_of(s):
    """('hold'|'closed'|'delay'|'reopen'|'schedule'|None, cause) for a clause or list header, by keyword; None when unsure."""
    sl = s.lower()
    if _FUT.search(sl) or _NOT_STATUS.search(sl): return None, None
    if re.search(r"\boff (?:of )?(?:the |a )?(?:\w+ )?hold\b", sl): return "reopen", None
    if re.search(r"\b(?:on|under|in|placed on|remain(?:s|ing)? on|returns? to)\s+(?:a\s+|an\s+|the\s+)?(?:\w+\s+)?hold\b|\bhold\b", sl) and not re.search(r"\bhold(?:s)? (?:until|off)\b", sl): return "hold", cause_in(s)
    if re.search(r"off (?:of )?the schedule|\bclosed\b|will not (?:open|operate|run|spin)|not (?:operating|open|running|spinning)|removed from the schedule|won't (?:open|operate)", sl): return "closed", cause_in(s)
    if _HEDGEY.search(sl): return None, None
    if re.search(r"\bexpect(?:ed|ing)?\b[^.!?]{0,25}\bdelays?\b|\bdelays?\s+(?:are\s+|is\s+)?(?:expected|possible|likely|anticipated)\b|\banticipat\w+[^.!?]{0,25}\bdelays?\b", sl): return None, None     # 'expect some delays' is a warning, not a delay for the list below it
    if re.search(r"\bdelay|estimated opening|opening times? (?:is|are)|opening shortly", sl): return "delay", cause_in(s)
    if re.search(r"\b(?:now|currently|already)\s+(?:open|spinning|running|operating)|\b(?:is|are|been|have|has)\s+(?:now\s+|also\s+)?(?:open(?:ed)?|spinning|running|operating)\b|\bhas opened\b|\bnow open\b|\bopen to the public\b|\bopen at \w+\s*:?\s*$|^open\b", sl): return "reopen", None
    if re.search(r"schedul|planning|plan to|plan on|anticipat|expect|project|set (?:for|to)|will (?:be )?(?:open|spin|run|operat)|to (?:spin|open)\b|opening at|open at \d|\d\s*(?:am|a)\b|spinning today|in the schedule|on the schedule", sl): return "schedule", None
    return None, None
def fallback_events(text, out, add, hour=12):
    covered = {e["lift"] for e in out if e["lift"] and e["event_type"] in ("scheduled_opening", "hold_start", "closed_day", "delay", "reopen", "partial", "warning")}
    covered |= {x for e in out for x in e.get("except", [])}
    if any((e["lift"] or "").startswith("ALL") for e in out if e["event_type"] in ("hold_start", "closed_day", "delay")): return
    emit = {"hold": "hold_start", "closed": "closed_day", "delay": "delay", "reopen": "reopen", "schedule": "scheduled_opening"}
    done = set(); section = []
    def put(lifts, st, cause, via_section=False):
        for l in lifts:
            if l in covered or l in done: continue
            if via_section: section.append(l)
            done.add(l); add("P-099", emit[st], l, cause if st in ("hold", "closed", "delay") else None, **{"note": "fallback"})
    cur = None; got_items = False                                                 # list section: 'Now open at Alpine:' / 'The following are all open.' then one lift (or a few) per line
    for ln in text.replace("\u2022", "\n").split("\n"):
        raw = ln.strip().strip("-*\u2022 ").strip()
        if not raw:
            if got_items: cur = None                                                # a blank line ends a list, unless the header has had no items yet
            continue
        plain = re.sub(r"\([^)]*\)", " ", raw)                                   # '(high winds may affect ops)' is not part of the status
        lf = [l for l in find_lifts(plain) if l != "Summit" or re.search(r"\bSummit\b", plain)]
        if not lf:
            st, c = _status_of(plain)
            if st: cur = (st, c); got_items = False
            elif re.search(r"\b\d{1,2}\s+lifts?\b", plain) and not re.search(r"hold|clos", plain, re.I): cur = ("schedule", None); got_items = False
            continue
        m = re.match(r"^([^:]{2,40}):\s*(.+)$", plain)                            # 'Headwall: delayed opening'
        if m and find_lifts(m.group(1)):
            st, c = _status_of(m.group(2))
            if st: put(find_lifts(m.group(1)), st, c); continue
        if cur and len(plain) < 70 and not re.search(r"[.!?]\s*$", plain) and not re.search(r"\b(?:hold|delay|off the schedule)\b", plain, re.I): put(lf, cur[0], cur[1], True); got_items = True; continue
        if plain.endswith(":"):
            st, c = _status_of(plain)
            if st: cur = (st, c); got_items = False; put(lf, st, c)
            continue
        for sent in split_sentences(plain):
            for piece in re.split(r"\bbut\b|\bwhile\b|;", sent, flags=re.I):
                lf2 = [l for l in find_lifts(piece) if l != "Summit" or re.search(r"\bSummit\b", piece)]
                if not lf2: continue
                st, c = _status_of(piece)
                if st: put(lf2, st, c)

def _side_scope(t):
    """ALL_PALISADES / ALL_ALPINE when the post names only one side, else ALL"""
    a = bool(re.search(r"\balpine\b", re.sub(r"#\w+", " ", t), re.I)); pl = bool(re.search(r"palisades|squaw|olympic valley", re.sub(r"#\w+", " ", t), re.I))
    return "ALL_ALPINE" if a and not pl else "ALL_PALISADES" if pl and not a else "ALL"
def fix_patterns(p, ev, text, dt):
    base = {"source_post_id": p["id"], "start": dt.isoformat(timespec="minutes"), "end": None, "confidence": 1.0}
    out = list(ev); added = []
    def add(rule, typ, lift, cause=None, **kw):
        added.append({**base, "event_type": typ, "lift": lift, "cause": cause, "cause_source": "observed" if cause else "unstated", "parse_rule_id": rule, **kw})
    sched = sorted({e["lift"] for e in ev if e["event_type"] == "scheduled_opening" and e["lift"]})
    grp = lambda w: "UPPER_MOUNTAIN" if w.lower() == "upper" else "LOWER_MOUNTAIN"
    for sent in split_sentences(text):
        m = re.search(r"\b(?:the\s+)?(?:entire|whole)\s+(upper|lower)[- ]mountain\b", sent, re.I)                # 'the entire upper mountain ... will start the day on wind hold'
        if m and not re.search(r"anticipated weather impact|\b(?:may|might|could)\b|expected to", sent, re.I):
            if re.search(r"\bon (?:\w+ )?hold\b|start the day on", sent, re.I): add("P-014e", "hold_start", grp(m.group(1)), cause_in(sent))
            elif re.search(r"\bclosed\b", sent, re.I): add("P-014e", "closed_day", grp(m.group(1)), cause_in(sent))
            elif re.search(r"\bdelay", sent, re.I): add("P-014e", "delay", grp(m.group(1)), cause_in(sent))
        m = re.search(r"\ball (upper|lower)[- ]mountain lifts(?: at \w+)?[^.!?]{0,60}\b(?:are|will be)\s+(?:now\s+)?closed", sent, re.I)   # 'all upper mountain lifts ... are closed'
        if m: add("P-014e", "closed_day", grp(m.group(1)), cause_in(sent) or cause_in(text))
        m = re.search(r"^(.*?)\b(?:is|are) also closed", sent, re.I)                                              # 'The Base to Base is also closed'
        if m and not re.search(r"\bterrain\b|\bside of\b|\barea\b|\bpocket\b|\bbowl\b|\btrail\b", sent, re.I):
            for l in find_lifts(m.group(1)): add("P-020", "closed_day", l, cause_in(text))
        m = re.search(r"([^.!?]*?)\b(?:is|are) open for (?:the )?mountain run", sent, re.I)                        # 'Funitel is open for Mountain Run access'
        if m:
            for l in find_lifts(m.group(1).split(" and ")[-1]):
                out = [e for e in out if not (e["event_type"] in ("reopen", "scheduled_opening") and e["lift"] == l)]
                add("P-070", "partial", l, None, detail="mountain_run_only")
        m = re.search(r"\ball other (?:scheduled )?lifts (?:are|will be) delayed(?: due to ([^.!?]*))?", sent, re.I)  # 'All other lifts are delayed due to icing'
        if m: add("P-013", "delay", "ALL_OTHER", cause_in(m.group(1) or ""), **{"except": sched})
        m = re.search(r"([^.!?\n]*?)\bwill (?:run|operate|spin|be open|open) (?:today )?instead of ([^.!?\n]+)", sent, re.I)   # 'Emigrant will run today instead of Granite Chief'
        if m:
            for a in find_lifts(m.group(1)): add("P-001s", "scheduled_opening", a)
            for b in find_lifts(m.group(2)): add("P-020s", "closed_day", b)
        if re.search(r"added to the schedule", sent, re.I) and re.search(r"delayed (?:opening|start)", sent, re.I):  # 'Exhibition has been added to the schedule and will have a delayed opening'
            for l in find_lifts(sent):
                out = [e for e in out if not (e["event_type"] == "scheduled_opening" and e["lift"] == l)]; add("P-030", "delay", l)
        for sm in re.finditer(r"sightseeing", sent, re.I):                                                         # sightseeing is a limited operation (an explicitly scheduled sightseeing run keeps both events)
            if re.search(r"\bsched", sent, re.I): break
            near = find_lifts(sent[max(0, sm.start() - 70): sm.start()])                                          # only the lift just before the word, not the whole roster in the same sentence
            for l in near[-1:]:
                out = [e for e in out if not (e["event_type"] in ("reopen", "scheduled_opening") and e["lift"] == l) and not (e["event_type"] == "partial" and e["lift"] == l)]
                add("P-070", "partial", l, None, detail="sightseeing")
    sents = split_sentences(text)
    for i, sent in enumerate(sents):
        m = re.search(r"^(.*?)\b(?:is|are) both open\b", sent, re.I)                                              # 'Headwall and Emigrant are both open!'
        if m:
            for l in find_lifts(m.group(1)): add("P-040", "reopen", l)
        m = re.search(r"^(.*?)\b(?:is|are) (?:now )?on (?:an? )?(wind|mechanical|patrol|maintenance) hold\b", sent, re.I)   # a hold stated in a second sentence after a list
        if m and not re.search(r"following lifts", sent, re.I):
            subj = re.split(r"[:•]|\s-\s", m.group(1))[-1]                                                       # the words just before 'is on ... hold', not a whole list above it
            sl = [] if re.search(r"\ball\b|\bother\b|\bopen\b|\bscheduled\b", subj, re.I) else find_lifts(subj)
            if not re.search(r"\bis\b", sent[m.end(1):m.end(1) + 6], re.I) and len(sl) > 4: sl = []
            for l in (sl[-1:] if re.search(r"\bis\b", sent[m.end(1):m.end(1) + 6], re.I) else sl):
                if not any(e["event_type"] == "hold_start" and e["lift"] == l for e in out + added): add("P-010", "hold_start", l, "mechanical" if m.group(2).lower() == "maintenance" else m.group(2).lower())
        m = re.search(r"\b(?:electrical|mechanical|technical|power)\s+(?:issues?|problems?|trouble|difficulties|challenges)\s+(?:on|with|at)\s+(?:the\s+)?([^.!?\n]+)", sent, re.I)   # 'electrical issues on the Funitel and Wa She Shu'
        if m:
            for l in find_lifts(m.group(1)):
                if not any(e["event_type"] == "hold_start" and e["lift"] == l for e in out + added): add("P-010", "hold_start", l, "mechanical")
        if i > 0 and re.search(r"^(?:it|they) (?:is|are) closed for (?:today|the day|the remainder)", sent, re.I):  # 'KT is having mechanical issues. It is closed for today'
            pl = find_lifts(sents[i - 1])
            for l in pl[-1:]: add("P-020", "closed_day", l, cause_in(sents[i - 1] + " " + sent))
            if pl: out = [e for e in out if not (e["event_type"] == "reopen" and e["lift"] is None)]
        m = re.search(r"^(.*?)\b(?:are|is) the remaining (?:lifts?|chairs?)(?: that are| still)? open", sent, re.I)   # 'Funitel and Gold Coast are the remaining lifts open'
        if m and not re.search(r"\bhold\b|\bdelay|patrol", text, re.I):
            ol = find_lifts(m.group(1))
            for l in ol: add("P-040", "reopen", l)
            if ol: add("P-013", "closed_day", "ALL_OTHER", None, **{"except": ol})
        m = re.search(r"([^.!?\n]*?)\b(?:will be|is|are)\s+(?:running|operating|doing)\s+(?:downloads?|download only)|([^.!?\n]*?)\bwill (?:run|operate)\s+downloads?\s+only", sent, re.I)   # 'The Funitel will be running downloads'
        if m:
            for l in find_lifts(m.group(1) or m.group(2) or "")[-1:]:
                out = [e for e in out if not (e["event_type"] in ("scheduled_opening", "reopen") and e["lift"] == l)]; add("P-070", "partial", l, None, detail="download_only")
    if re.search(r"\bwe plan (?:on|to) (?:spin(?:ning)?|run(?:ning)?|operat(?:e|ing)|open(?:ing)?)\b", text, re.I) and not re.search(r"\bnow open|reopen|are open|is open", text, re.I):   # a morning plan, not a reopening
        for e in out:
            if e["event_type"] == "reopen": e["event_type"] = "scheduled_opening"; e["parse_rule_id"] = "P-001p"
    if re.search(r"\b\d+\s+(?:chairs?|lifts?)\s+(?:and|&)\s+carpets", text, re.I):                          # '8 chairs and carpets at Squaw Valley': a count, not lifts
        out = [e for e in out if e["lift"] not in ("Palisades Carpets", "Alpine Carpets", "Carpets")]
        if not any(e["event_type"] == "scheduled_opening" for e in out + added): add("P-001", "scheduled_opening", None, None, note="count_only")
    for typ in ("closed_day", "hold_start", "reopen", "delay", "partial"):                                       # a list header must not leave a lift-less event beside the per-lift events
        if any(e["event_type"] == typ and e["lift"] for e in out + added): out = [e for e in out if not (e["event_type"] == typ and e["lift"] is None)]
    for m in re.finditer(r"(wind|mechanical|patrol)\s+hold\s*:", text, re.I):                                     # '+ALL other upper mtn lifts' at the end of a hold list
        mm = re.search(r"\+?\s*all other (upper|lower)\s*(?:mtn|mountain)\s*lifts?", text[m.end():], re.I)
        if mm: add("P-014e", "hold_start", grp(mm.group(1)), m.group(1).lower(), **{"except": sched})
    m = re.search(r"\b(?:at|on)\s+(alpine|palisades)\b[^.!?]{0,60}?\b\d+\s+lifts?\s+(?:are\s+)?(?:on|in)\s+the\s+schedule\W+(?:all lifts except(?: for)?|all lifts but)\s+([^.(!?\n]+)", text, re.I)   # '12 lifts on the schedule, all lifts except for ABC'
    if m:
        exc = find_lifts(m.group(2)); sd = "ALL_ALPINE" if m.group(1).lower() == "alpine" else "ALL_PALISADES"
        out = [e for e in out if e["event_type"] != "scheduled_opening"]
        add("P-001", "scheduled_opening", sd, None, **{"except": exc})
        for l in exc: add("P-020s", "closed_day", l)
    if re.search(r"\b(?:dining|roller|skating|terrace|marketplace|restaurant)\b", text, re.I) and not re.search(r"high camp carpet|\bcarpet\b", text, re.I):
        out = [e for e in out if e["lift"] != "High Camp Carpet"]                                                  # 'dining at High Camp' is a place, not the carpet
    m = re.search(r"\b(?:noted|marked|denoted|flagged) (?:with|by) (?:an? )?(?:\*|asterisk)[^:\n]*:?", text, re.I)       # '12 lifts scheduled ... impacts, noted with * below: Tram*, Funitel, Red Dog'
    if m and not any(e["event_type"] == "scheduled_opening" and e["lift"] and not e["lift"].startswith("ALL") for e in out):
        rest = text[m.end():]; out = [e for e in out if e["event_type"] != "warning"]
        for piece in re.split(r"[,\n\u2022]", rest):
            for l in find_lifts(piece):
                add("P-001a", "scheduled_opening", l, None, **{"note": "roster"})
                if piece.strip().rstrip("#").strip().endswith("*") or re.search(re.escape(piece.strip().split()[0] if piece.strip() else "x") + r"\*", piece): add("P-012a", "warning", l, "wind")
    for e in out:                                                                                                 # 'all lifts except X that were on hold are now closed': X is not on hold
        if e["lift"] == "ALL_ON_HOLD" and e.get("except"):
            ex = set(e["except"]); out = [x for x in out if not (x["event_type"] == "hold_start" and x["lift"] in ex)]
    # 'At Alpine: Summit, Scott and Lakeview are OFF schedule today': a header colon makes the roster rule read it as a schedule; it is a closure
    for mo in re.finditer(r"(?:^|[\n:.!?])\s*([^.!?\n]{4,160}?)\b(?:are|is)\s+off\s+(?:of\s+)?(?:the\s+)?schedule\b(?!\s+(?:until|after))", p["text"], re.I):
        lifts_off = find_lifts(mo.group(1))
        if lifts_off and not re.search(r"\bremain|\bexcept|\ball other|\bon the schedule\b", mo.group(1), re.I):
            had = [x for x in out + added if x["event_type"] == "scheduled_opening" and x["lift"] in lifts_off]
            if had:
                out = [x for x in out if x not in had]; added = [x for x in added if x not in had]
                for l in lifts_off: add("P-020o", "closed_day", l, None)
    # 'closed for the day, with the exception of X and Y': the exceptions are open, not closed
    for e in list(out + added):
        if e["event_type"] == "closed_day" and (e["lift"] or "").startswith("ALL") and e.get("except"):
            ex = set(e["except"]); out = [x for x in out if not (x["event_type"] == "closed_day" and x["lift"] in ex and x["source_post_id"] == e["source_post_id"])]; added = [x for x in added if not (x["event_type"] == "closed_day" and x["lift"] in ex)]
    # 'all other lifts that were on wind hold will be closed for the day': only the lifts already on hold, not every other lift
    m = re.search(r"\ball other (?:scheduled )?lifts[^.!?]{0,60}\b(?:that|which) (?:were|are) on (?:a |an )?(?:(\w+) )?hold[^.!?]{0,40}\b(?:will be|are|is|now)\s+(?:now\s+)?closed", text, re.I)
    if m:
        old = [e for e in out + added if e["lift"] == "ALL_OTHER" and e["event_type"] in ("hold_start", "delay")]
        if old:
            exc = old[0].get("except", [])
            out = [x for x in out if x not in old]; added = [x for x in added if x not in old]
            add("P-014h", "closed_day", "ALL_ON_HOLD", cause_in(m.group(0)) or old[0].get("cause"), **{"except": exc})
    # 'the only lift open at Squaw is X' and 'starting the day with X, Y, Z' under a weather impact: every other lift of that side has not opened
    if not any((e["lift"] or "").startswith("ALL") for e in out + added if e["event_type"] in ("hold_start", "delay", "closed_day")):
        for sent in split_sentences(text):
            sl = sent.lower()
            if re.search(r"\b(?:may|might|could|likely|hoping)\b|\bif\b", sl): continue
            mo = re.search(r"\bthe only (?:lifts?|chairs?)\b[^.!?]{0,40}\b(?:open|operating|running|spinning)\b|\bis the only (?:lift|chair)\b|\b(?:are|is) the only (?:lifts?|chairs?)\b", sl)
            if mo and find_lifts(sent) and re.search(r"\b(?:winds?|snow safety|weather|hold|delay\w*|impact\w*|avalanche|power|lightning|ice|icing)\b", text, re.I):
                add("P-014o", "hold_start" if "hold" in text.lower() else "delay", _side_scope(text), cause_in(text), **{"except": find_lifts(sent)}); break
        else:
            ms = re.search(r"(?:start|begin)\w*\s+the\s+day\s+(?:at\s+[\w ]{3,25}\s+)?with\s*:", text, re.I)
            if ms and re.search(r"\b(?:winds?|snow safety|weather|hold|delay|impact\w*|avalanche)\b", text, re.I):
                listed = find_lifts(text[ms.end():])
                if len(listed) >= 2: add("P-014o", "delay", _side_scope(text), cause_in(text), **{"except": listed})
    if not any((e["lift"] or "").startswith("ALL") for e in out + added if e["event_type"] in ("hold_start", "delay", "closed_day")):
        for sent in split_sentences(text):
            sl = sent.lower()
            if re.search(r"\b(?:may|might|could|expect(?:ed)? to|likely|hoping|if)\b|\bhope", sl): continue
            if re.search(r"\ball (?:lift )?operations\b[^.!?]{0,70}\b(?:on hold|suspended|halted)\b|\b(?:the )?scheduled lifts (?:are|remain) on (?:\w+ )?hold\b|\ball operations are on hold", sl):
                add("P-010w", "hold_start", _side_scope(text), cause_in(sent)); break           # 'all operations ... on hold', 'the scheduled lifts are on hold'
            if re.search(r"\ball (?:scheduled )?lifts\b[^.!?]{0,30}\b(?:will (?:be|have)|are) (?:a )?delayed", sl):
                add("P-030w", "delay", _side_scope(text), cause_in(sent)); break
    # an early post that sorts the day's lifts under Open / Delayed / Hold headings is the day's roster: every lift listed was on the schedule
    _st = collections.defaultdict(set)
    for e in out + added:
        if e["lift"] and not e["lift"].startswith("ALL") and e["event_type"] in ("reopen", "delay", "hold_start"): _st[e["event_type"]].add(e["lift"])
    if dt.hour < 10 and len(_st["reopen"]) >= 1 and len(_st["delay"] | _st["hold_start"]) >= 4 and not any(e["event_type"] == "scheduled_opening" and e["lift"] and not e["lift"].startswith("ALL") for e in out + added):
        for l in sorted(_st["reopen"] | _st["delay"] | _st["hold_start"]): add("P-001s", "scheduled_opening", l, None, **{"note": "status_list_roster"})
    fallback_events(p["text"], out + added, add, dt.hour)                                                          # keeps the line breaks the list sections need
    final = out + added
    for e in final:
        if e["lift"] is None and e["event_type"] in ("hold_start", "closed_day", "delay", "reopen", "partial"): e["event_type"] = "other"; e["note"] = "no_lift_named"
    return final

def parse_post(p):
    p = {**p, "text": clean_text(p["text"])}
    _CTX["t"] = " ".join(p["text"].replace("&amp;", "&").split())
    blk = [b for b in re.split(r"(?im)^(?=[^\n]*\bthe following lifts\b[^\n]*:[ \t]*$)", p["text"]) if b.strip()]
    sp = split_roster_prose(p["text"])
    hdr = re.findall(r"(?im)^[^\n]*\bthe following lifts\b[^\n]*:[ \t]*$", p["text"])
    if len(blk) > 1 and any(re.search(r"closed|off the schedule", h, re.I) for h in hdr) and any(re.search(r"\bopen\b", h, re.I) and not re.search(r"closed", h, re.I) for h in hdr):   # a closed list and an open list in one post
        evs = []
        for b in blk: evs += _parse_post({**p, "text": b})
        if any(e["event_type"] != "other" for e in evs): evs = [e for e in evs if e["event_type"] != "other"]
        ev = fill_causes(_CTX["t"], evs)
    elif sp:
        evs = _parse_post({**p, "text": sp[0]}) + _parse_post({**p, "text": sp[1]})
        ev = fill_causes(_CTX["t"], evs)
    else:
        ev = fill_causes(" ".join(p["text"].replace("&amp;", "&").split()), _parse_post(p))
    ev = fix_patterns(p, ev, _CTX["t"], datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles")))
    ev = ev + hedged_warnings(p, ev, _CTX["t"])
    SCOPES = ("ALL", "ALL_PALISADES", "ALL_ALPINE", "ALL_ON_HOLD", "UPPER_MOUNTAIN", "LOWER_MOUNTAIN")
    xs = _EXC.findall(_CTX["t"])
    if len(xs) == 1:                                                  # 'all lifts at Alpine with the exception of the Big Carpet are closed': the exception rides on the scope event
        exl = find_lifts(_EXC.split(_CTX["t"], 1)[1].split(".")[0])
        for e in ev:
            if e["lift"] in SCOPES and exl and "except" not in e: e["except"] = exl
    if re.search(r"\bmountain run\b", _CTX["t"], re.I):             # a run, not a lift
        ev = [e for e in ev if not (e["lift"] is None and e["event_type"] in ("reopen", "closed_day", "hold_start", "partial"))]
    for sent in split_sentences(_CTX["t"]):                          # hiking access is a limited operation, not a closure or a reopening
        if re.search(r"\bhik(?:e|ing)\b", sent, re.I):
            hl = find_lifts(sent)
            for e in ev:
                if e["lift"] in hl and e["event_type"] in ("reopen", "closed_day") and re.search(r"hik(?:e|ing)[- ]?(?:only|access)|for hiking|open for hik", sent, re.I): e["event_type"] = "partial"; e["detail"] = "hike_only"
            if not hl: ev = [e for e in ev if not (e["lift"] is None and e["event_type"] in ("reopen", "closed_day", "hold_start", "partial"))]
    for e in ev:
        if e["event_type"] in ("hold_start", "closed_day", "delay", "partial", "warning"): e["cause_tags"] = cause_tags(_CTX["t"])
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
        cause = {"lightning": "weather", "icing": "weather", "ice": "weather", "icy": "weather"}.get(cause, cause)   # one cause family for lightning / ice / rain
        for l in (lifts or [None]):
            ev.append({**base, "lift": l, "event_type": typ, "cause": cause,
                       "cause_source": "observed" if cause else "unstated", "parse_rule_id": rule, "confidence": 1.0, **kw})
    t = re.sub(r"\b(wind|mechanical|patrol)hold\b", r"\1 hold", t, flags=re.I)
    t = re.sub(r"\b(wind|mechanical|patrol) old\b", r"\1 hold", t, flags=re.I)     # typo seen in 2018-19
    t = re.sub(r"\boff (?:lift )?maintenance\b", "off maintenance hold", t, flags=re.I)
    low = t.lower()
    for sent in split_sentences(t):
        if re.search(r"\ball (?:of )?(?:the )?lifts\b[^.!?]{0,60}?\b(?:that|which)\b[^.!?]{0,30}\bon (?:\w+ )?hold\b[^.!?]{0,40}\b(?:closed|closing)\b", sent, re.I):
            exc = find_lifts(re.split(r"\b(?:that|which)\b", _EXC.split(sent, 1)[1], 1)[0]) if _EXC.search(sent) else []
            add("P-021", "closed_day", ["ALL_ON_HOLD"], cause_in(sent) or ("wind" if re.search(r"wind", sent, re.I) else None), **({"except": exc} if exc else {}))
            t = t.replace(sent, " "); low = t.lower()
    wc = whole_closure(t, dt)
    if wc:
        for sc, sent, fut in wc:
            exc = find_lifts(_EXC.split(sent, 1)[1]) if _EXC.search(sent) else []
            add("P-022", "warning" if fut else "closed_day", [sc], cause_in(sent) or cause_in(t), **({"note": "announced for a later day"} if fut else {}), **({"except": exc} if exc else {}))
        rest = t
        for _sc, sent, _f in wc: rest = rest.replace(sent, " ")
        if not find_lifts(rest) and not re.search(r"\bhold\b|\bdelay|\bopen\b|\bopening\b", rest, re.I): return ev      # nothing else in the post to read
        t = " ".join(rest.split()); low = t.lower()
    AO = re.compile(r"all other (?:scheduled )?(?:\w+ )?lifts?\b(?! that)(?:[^.!?]*?\b(?:are|remain)\b)?[^.!?]*?\bon (?:an? )?(?:(wind|mechanical|patrol|maintenance|lightning|weather impact|weather|operational) )?(hold|delay|standby)(?: due to ([^.!?]*))?[.!?]?", re.I)
    am = AO.search(t)
    if am:
        c = {"maintenance": "mechanical", "lightning": "weather", "weather impact": "weather", "operational": None}.get((am.group(1) or "").lower(), (am.group(1) or "").lower()) or (cause_in(am.group(3)) if am.group(3) else None)
        rest = (t[:am.start()] + " " + t[am.end():]).strip()
        add("P-013", "delay" if am.group(2).lower() == "delay" else "hold_start", ["ALL_OTHER"], c, **{"except": find_lifts(rest)})
        t = rest
    fm = re.search(r"(?:the )?(?:below|following) lifts (?:are|will [\w ]*?)\s*(?:on|begin the day on|start the day on)\s+(?:a\s+)?(?:(wind|mechanical|patrol)\s+)?(hold|delay)", t, re.I)
    if fm and not re.search(r"[:]", t[fm.end():fm.end() + 3]):
        tail = re.split(r"(?<=[.!?])\s+", t[fm.end():], maxsplit=1)
        lifts = find_lifts(tail[1] if len(tail) > 1 else "")
        if lifts:
            add("P-011" if fm.group(2).lower() == "hold" else "P-030", "hold_start" if fm.group(2).lower() == "hold" else "delay", lifts, (fm.group(1) or "").lower() or None); return ev
    dm = re.search(r"([^.!?\-•]*?)\bwill have an? (?:slightly )?delayed (?:opening|start)[^.!?]*[.!?]?", t, re.I)
    if dm and re.search(r"lifts?(?: at [\w ]+?)? (?:are|will be) now open|^(?:open at|these lifts are now open)", t, re.I) and find_lifts(dm.group(1)):
        add("P-030", "delay", find_lifts(dm.group(1)), None); t = t.replace(dm.group(0), " ")
    om = re.search(r"following lifts(?: at \w+)? (?:are|is)(?: now)? off (?:the )?(wind|mechanical|patrol) hold(?: and open[^:]*)?:", t, re.I)
    if om: add("P-040", "reopen", find_lifts(t[om.end():]), om.group(1).lower(), resolves_hold=True); return ev
    _LEFT.clear()
    if sectional(t, add):
        for extra in list(_LEFT):
            _LEFT.clear()
            ev.extend(_parse_post({**p, "text": extra}))
        return ev
    # P-001 scheduled opening
    if re.match(r"^(?:palisades|alpine)[^:]{0,20}:", t, re.I) and re.search(r"\b\d+ lifts?\b|open at \d|lifts? (?:are )?(?:scheduled|on the schedule)", t, re.I):
        roster = roster_with_sections(t, add, "P-001", t.index(":") + 1)
        lifts = find_lifts(roster)
        add("P-001", "scheduled_opening", lifts, None, note="roster" if lifts else None,
            wind_warning=bool(re.search(r"wind", t, re.I) and re.search(r"impact", t, re.I)))
        return ev
    rh = ROSTER_HDR.search(t)
    if rh and len(find_lifts(t[rh.end():])) >= 2 and not re.match(r"^(?:palisades|alpine)\W", t, re.I) \
            and not re.search(r"spinning|now open|\bare open\b|removed|\bclosed|off[- ]schedule|\bhold|delay|will not|not operate|not open", re.sub(r"\(delays? likely\)", "", t[max(0, rh.start() - 90): rh.end()], flags=re.I), re.I) \
            and rh.start() <= 160 \
            and not re.search(r"\bon\s+(?:a\s+|an\s+)?(?:\w+\s+)?hold\b|\bremoved from the schedule\b|open to the public|\bare open\b|\bis open\b|\bnow open\b", t[rh.end():], re.I):
        roster = roster_with_sections(t, add, "P-001", rh.end())
        add("P-001", "scheduled_opening", find_lifts(roster), None, note="roster"); return ev
    if re.match(r"^(?:palisades|alpine)\s+open at \d", t, re.I):
        roster = roster_with_sections(t, add, "P-001"); add("P-001", "scheduled_opening", find_lifts(roster), None); return ev
    if re.match(r"^(?:palisades|alpine)?\s*(?:operations? update|update|now open|open)\s*:", t, re.I) and find_lifts(t) and not re.match(r"^\W*(?:palisades|alpine)?\s*(?:operations? update|update)\s*:\s*(?:wind|mechanical|patrol) hold", t, re.I) and not re.search(r"\bhold\b|\bdelay|\bclos(?:ed|ing)\b|off[- ](?:the )?schedule", t, re.I):
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
    if len(find_lifts(t)) >= 4 and re.search(r"\d\s*(?:am|a|pm|p)?\s*-\s*\d+\s*(?:am|a|pm|p)\b", t, re.I) and not re.search(r"\b(?:hold|closed|delay(?:s|ed)?)\b", t, re.I):
        roster = roster_with_sections(t, add, "P-003"); add("P-003", "scheduled_opening", find_lifts(roster), None); return ev
    if re.search(r"^(?:open at|these lifts are now open|the following lifts are now open|projected for|for (?:alpine|palisades), we expect)", t, re.I):
        add("P-002", "reopen", find_lifts(t), None, note="status_roster"); return ev
    last_lifts = []
    _last_s = ""
    _hist = []
    for s in split_sentences(t):
        sl = s.lower()
        prev_lifts = last_lifts
        prev_s, _last_s = _last_s, s
        before = " ".join(_hist[-3:]).lower(); _hist.append(s)
        if find_lifts(s): last_lifts = find_lifts(s)
        # a bare list of lifts (no verb) in a post that announces a schedule: "10 lifts are scheduled at Alpine ... \n\nSummit, Roundhouse, Scott &amp; the carpet"
        cand = s
        bm = re.search(r"\s[-•]\s*(?=[A-Z])", s)
        if bm and len(find_lifts(s[bm.end():])) >= 2 and not s[:bm.start()].rstrip().endswith(":") and not re.search(r"now (?:open|spinning)|following|\bhold|delay|clos|remov|off[- ](?:the )?schedule|not (?:open|operat)", s[:bm.start()], re.I): cand = s[bm.end():]          # "...a high of 56. -Summit, Roundhouse, Scott"
        bl = find_lifts(cand)
        if len(bl) >= 2 and re.search(r"schedul|on tap|lifts? (?:at|on)\b", t, re.I) and (":" not in cand or re.match(r"\s*lifts?\s*:", cand, re.I)) \
                and len([w for w in re.findall(r"[A-Za-z]{4,}", LIFT_RE.sub(" ", cand)) if w.lower() not in ("chair", "area", "carpet", "carpets", "lifts", "mid", "station", "mountain", "only", "with", "from", "side", "and", "the", "upper", "lower", "beginner", "areas")]) <= (2 if cand != s else 1) \
                and not re.search(r"\b(?:is|are|will|has|have)\b|hold|delay|clos|remov|off (?:the )?schedule", cand.lower()) \
                and not re.search(r"hold|delay|clos|remov|off (?:the )?schedule|:\s*$", before):
            add("P-001", "scheduled_opening", bl, None, note="roster_list"); continue
        bh = re.search(r"following[^.]*\b(closed|off[- ](?:the )?schedule|removed|on (?:\w+ )?hold|delayed|on delay)\b[^.]*\.?\s*$", before)
        if len(bl) >= 2 and bh and cand == s and not re.search(r"\b(?:is|are|will|has|have)\b", sl) \
                and len([w for w in re.findall(r"[A-Za-z]{4,}", LIFT_RE.sub(" ", cand)) if w.lower() not in ("chair", "area", "carpet", "carpets", "lifts", "mid", "station", "mountain", "only", "the")]) <= 1:
            k = bh.group(1); closed = k.startswith(("closed", "off", "removed"))
            add("P-020" if closed else ("P-010" if "hold" in k else "P-030"), "closed_day" if closed else ("hold_start" if "hold" in k else "delay"), bl, cause_in(before)); continue
        if re.search(r"on the schedule but still on (?:a |an )?(\w+ )?hold|there goes [^:]{3,40}: (?:wind|mechanical|patrol) hold|experiencing (?:\w+ )?holds?\b", sl) and (find_lifts(s) or re.search(r"experiencing", sl)):
            hc = re.search(r"(wind|mechanical|patrol)\s+holds?", sl); add("P-010", "hold_start", find_lifts(s), hc.group(1) if hc else cause_in(s)); continue
        if re.search(r"\bwill not operate today\b|\bnot operate today\b|we have closed [^.]*? for the day|(?<!be )\bclosing (?!at\b|soon|time|in\b|down)(?:the )?\w", sl) and find_lifts(s) and not re.search(r"road|lot\b|parking|will be closing", sl):
            add("P-020", "closed_day", find_lifts(s.split("operate today")[-1]) if "following lifts" in sl and "not operate" in sl else find_lifts(s), cause_in(s)); continue
        if re.search(r"unable to run", sl) and find_lifts(s):
            add("P-010", "hold_start", find_lifts(s.split("unable to run")[-1]), cause_in(s) or "wind"); continue
        if re.search(r"is the only lift open|\b(?:is|are) also open at\b|: it.s open|\bopens today\b", sl) and find_lifts(s):
            add("P-040", "reopen", find_lifts(s), None); continue
        ph = re.search(r"placed (?:it|them) on (?:a |an )?(wind |mechanical |patrol |maintenance )?hold", sl)
        if ph and prev_lifts and not find_lifts(s):
            add("P-010", "hold_start", prev_lifts, ((ph.group(1) or "").strip().replace("maintenance", "mechanical") or None)); continue
        ah = re.search(r"\badd\b\s+(.+?)\s+to that (?:list|lift) of (wind |mechanical |patrol )?holds?", s, re.I)
        if ah and find_lifts(ah.group(1)):
            add("P-010", "hold_start", find_lifts(ah.group(1)), (ah.group(2) or "wind").strip().lower()); continue
        if re.search(r"evaluating the following", sl) and find_lifts(s):
            add("P-012", "warning", find_lifts(s), cause_in(s)); continue
        if re.search(r"open the following lifts\s*:", sl) and find_lifts(s) and re.search(r"allowed us|died down|now able", sl):
            add("P-040", "reopen", find_lifts(s), None, note="status_roster"); continue
        if re.search(r"expected opening time is \d", sl) and (find_lifts(s) or prev_lifts):
            add("P-030", "delay", find_lifts(s) or prev_lifts, cause_in(s)); continue
        if re.search(r"\b(?:open|operate|operating|spin|spinning|run|running|go)\b[^.:]{0,60}?\b(?:until|till) \d|last download at \d", sl) and (find_lifts(s) or prev_lifts):
            start = 0
            for em in re.finditer(r"\b(?:open|operate|operating|spin|spinning|run|running|go)\b[^.:]{0,60}?\b(?:until|till) \d|last download at \d", s, re.I):
                ll = find_lifts(s[start: em.end()])[-3:] or (prev_lifts if len(prev_lifts) == 1 else [])
                if ll: add("P-070", "partial", ll, None, detail="early_close")      # not terminal: the sentence may also schedule or open the lift
                start = em.end()
        if re.search(r"expected close to \d|anticipated to open at \d|estimated open time of \d", sl) and find_lifts(s):
            tm = re.search(r"(\d{1,2})(?::(\d\d))?\s*(am|pm)?", sl[sl.index("expected close to") if "expected close to" in sl else 0:])
            add("P-030", "delay", find_lifts(s), cause_in(s)) if re.search(r"delays? are due|icing|\bice\b", sl) or "close to 10" in sl else add("P-001", "scheduled_opening", find_lifts(s), None); continue
        if re.search(r"will not be opening|\bwe have closed\b|are now all closed|now all closed", sl) and find_lifts(s):
            add("P-020", "closed_day", find_lifts(s.split(" but ")[0]), cause_in(s)); 
            if re.search(r"\bbut opened\b", sl): add("P-040", "reopen", find_lifts(s.split(" but ")[-1]), None)
            continue
        if re.search(r"continues? to download|will continue to download", sl):
            dl = find_lifts(re.sub(r"from high camp", "", s, flags=re.I)) or (prev_lifts if len(prev_lifts) == 1 else [])
            if dl: add("P-070", "partial", dl, None, detail="download_only")   # not terminal: the same sentence may carry the hold
        if re.search(r"(?:are|is) planned for today|(?:we will be|we.re|we are) (?:running|hoping to run|aiming to open|planning to run)|(?:are|is) all scheduled\b|are on the schedule\b|are scheduled\b(?! to)", sl) and find_lifts(s) and not re.search(r"hold|delay|clos|off[- ]schedule|remov|not |tomorrow", sl) and (not re.search(r"mid-?station|only|sightseeing", sl) or re.search(r"(?:we will be|we.re|we are) (?:running|hoping|aiming|planning)", sl)):
            add("P-001", "scheduled_opening", find_lifts(re.split(r"\bwe are hoping to run\b", s)[-1]) if "hoping to run" in sl else find_lifts(s), None, note="roster"); continue
        if re.search(r"\b(?:is|are) scheduled to (?:spin|open)\b", sl) and find_lifts(s) and not re.search(r"hold|delay|tomorrow", sl):
            add("P-001", "scheduled_opening", find_lifts(s.split(" and the ")[0]) or find_lifts(s), None)
            if not re.search(r"sightseeing|sched\. for", sl): continue
        if re.search(r"(?:sched\.|scheduled) for sightseeing", sl) and (find_lifts(s) or prev_lifts):
            ll = find_lifts(s) or prev_lifts[-1:]
            add("P-001", "scheduled_opening", ll, None); add("P-070", "partial", ll, None, detail="sightseeing"); continue
        if re.search(r"will only be download", sl) and (find_lifts(s) or prev_lifts):
            add("P-070", "partial", find_lifts(s) or (prev_lifts if len(prev_lifts) == 1 else []), cause_in(s), detail="download_only"); continue
        if re.match(r"(?:wind|mechanical|patrol) hold on\b", sl) and find_lifts(s):
            add("P-010", "hold_start", find_lifts(s), sl.split()[0]); continue
        if re.search(r"\b(?:adding|added)\b.{0,60}\bto the (?:squaw |palisades |alpine )?schedule", sl) and find_lifts(s) and not re.search(r"hold|back|\bopen\b|\bspin", sl):
            add("P-001", "scheduled_opening", find_lifts(re.split(r"\band (?:moving|moved|sending)\b|\bas a result\b", s, flags=re.I)[0]), None); continue
        if re.search(r"now clear and open|now opened to the public|no longer (?:be )?uploading", sl) and find_lifts(s):
            if "uploading" in sl: add("P-070", "partial", find_lifts(s), cause_in(s), detail="no_upload")
            else: add("P-040", "reopen", find_lifts(s), None)
            continue
        if re.search(r"anticipating (?:approximately )?an? \d+ ?(?:minute|min)s? delay", sl) and find_lifts(s):
            add("P-012", "warning", find_lifts(s), cause_in(s)); continue
        if re.match(r"(?:it|they) will (?:have an? |be )(?:\w+ )?(?:on )?delay", sl) and prev_lifts and not find_lifts(s):   # "Yellow has been added to the schedule, but it will have a delayed opening"
            add("P-030", "delay", prev_lifts, cause_in(s)); continue
        sm = re.match(r"(?:still|currently) on (?:a |an )?(?:(wind|mechanical|patrol) )?hold\b", sl)
        if sm and prev_lifts and not find_lifts(s):   # "Funitel is on the schedule but still on Wind Hold." (split at 'but')
            add("P-010", "hold_start", prev_lifts, sm.group(1)); continue
        if re.search(r"(?:impacted by|experiencing) (?:\w+ )?(?:weather impacts?|winds?)\b[^.]*remains open", sl) and find_lifts(s):
            add("P-012", "warning", find_lifts(s), "wind" if "wind" in sl else "weather"); continue
        if re.search(r"\bis (?:also )?on the schedule\b", sl) and find_lifts(s) and not re.search(r"hold|delay", sl):
            add("P-001", "scheduled_opening", find_lifts(s), None); continue
        # hedged statements are forecasts, not events: "expect delays", "may go on hold", "possible delays", "likely to go on wind hold"
        if HEDGE_RE.search(sl) and not re.search(r"\bhas (?:been )?(?:delayed|put on)|\b(?:are|is) (?:now )?(?:on|delayed)\b(?! (?:the )?schedule)", sl.replace("may be delayed", "")) \
                and not re.search(r"(?:possible|potential|expect(?:ed)?|anticipated)\s+(?:\w+ ){0,2}delays?\s*:", sl):   # "Possible delays: A B C" list headers stay with the sectional code
            if not find_lifts(s) and not re.search(r"lift|operations", sl) and re.search(r"\broad\b|\brd\b|\bhwy\b|highway|\bi-80\b|traffic|accident|vehicle", t, re.I): add("P-090", "other", [], None, note="road"); continue
            add("P-012", "warning", find_lifts(s) or group_scopes(s), cause_in(s))
            if re.search(r"\b\d{1,2}\s+(?:\w+ )?lifts?\b[^.!?]{0,30}(?:schedul|on the schedule)", sl): add("P-001", "scheduled_opening", [], None, note="count_only")
            continue
        if find_lifts(s): last_lifts = find_lifts(s)
        if re.search(r"will be delayed|delayed (?:to|until)|(?:a few|\d+) minutes late|open(?:ing)? late", sl) and find_lifts(s) and not re.search(r"\bhold\b.*\bhold\b", sl):
            add("P-030", "delay", find_lifts(s) if not re.search(r"\bis on\b.*\band will be delayed", sl) else find_lifts(re.split(r"\band will be", s)[0]), cause_in(s) if re.search(r"due to", sl) else None)
        qm = re.search(r"download(?:s|ing)? only|mid-?station|advanced (?:levels? )?only|not servicing beginner|(?:mtn|mountain) run only|no return access|sightseeing only|limited terrain|offload|side only", sl)
        if qm and (find_lifts(s) or last_lifts) and not re.search(r"\bnot open\b", sl):
            near = find_lifts(re.sub(r"\bto (?:the )?high camp\b", "", s[max(0, qm.start() - 60): qm.start()], flags=re.I))
            add("P-070", "partial", near[-1:] or find_lifts(s) or last_lifts, "wind" if re.search(r"wind", sl) else None, detail="limited")
        if not find_lifts(s) and re.search(r"(?:the )?mountain (?:will )?remains? closed|(?:palisades(?: tahoe)?|alpine|squaw(?: valley)?)(?: alpine)? (?:is|are) (?:officially )?closed(?: for (?:today|the day))?|we are (?:now )?closed for (?:the )?(?:day|remainder|rest)|(?:will )?not be open for (?:skiing|riding)|all (?:the |\w+ )?lifts are (?:now )?closed", sl):
            sl = sl.replace("palisades tahoe alpine", "alpine")
            scope = "ALL_PALISADES" if re.search(r"palisades|squaw", sl) and not re.search(r"alpine", sl) else ("ALL_ALPINE" if re.search(r"alpine", sl) and not re.search(r"palisades|squaw", sl) else "ALL")
            add("P-021", "closed_day", [scope], cause_in(s)); continue
        if re.match(r"(?:\w+ )?parking update", sl): add("P-050", "parking", [], None); continue
        if re.match(r"(?:scheduled|projected|planned) for [\d:]+ ?(?:am|pm)? at (?:palisades|alpine) are\b", sl) and find_lifts(s):
            add("P-001", "scheduled_opening", find_lifts(s), None, note="roster"); continue
        if re.match(r"these (?:lifts )?(?:are )?(?:all )?(?:now )?open\b", sl):
            add("P-002", "reopen", find_lifts(t), None, note="status_roster"); continue
        if re.search(r"\bwill (?:not )?be (?:closed for (?:today|the day)|added back to the schedule)", sl) and find_lifts(s):
            subj = re.split(r"\bat (?:alpine|palisades),?\s*", s, flags=re.I)[-1]   # a roster line joined in front ("Treeline Cirque at Alpine, Tram and Gondola will be closed")
            add("P-020", "closed_day", find_lifts(subj), cause_in(s)); continue
        hl = re.search(r"added (.+?) to the (?:(wind|mechanical|patrol) )?hold list", s, re.I)
        if hl and find_lifts(hl.group(1)):
            add("P-010", "hold_start", find_lifts(hl.group(1)), (hl.group(2) or "").lower() or cause_in(s)); continue
        if re.search(r"back on the schedule", sl) and find_lifts(s) and not re.search(r"\boff (?:of )?(?:the )?(?:\w+ )?hold", sl):
            add("P-001", "scheduled_opening", find_lifts(s), None); continue
        if re.search(r"(?:about |around )?(?:\w+ |\d+ )(?:minutes?|mins?) late\b|\blooking at \d{1,2}:\d\d ?(?:am|pm)? for opening", sl) and (find_lifts(s) or prev_lifts):
            add("P-030", "delay", find_lifts(s) or prev_lifts, cause_in(s)); continue
        am = re.search(r"all other (?:scheduled )?(?:\w+ )?lifts?\b[^.]*?\bare\b[^.]*?\bon (?:a )?(?:(wind|mechanical|patrol|maintenance) )?(hold|delay)(?: due to ([^.]*))?", s, re.I)
        if am:
            c = (am.group(1) or "").lower().replace("maintenance", "mechanical") or (cause_in(am.group(3)) if am.group(3) else None)
            add("P-013", "hold_start" if am.group(2).lower() == "hold" else "delay", ["ALL_OTHER"], c, **{"except": find_lifts(t)}); continue
        if re.search(r"up and running (?:close to|around|by|at) \d|expected at \d+:\d+|will be open at approximately", sl) and (find_lifts(s) or last_lifts) and not re.search(r"\bhold\b", sl) or re.search(r"estimating .* up and running", sl):
            add("P-030", "delay", find_lifts(s) or last_lifts, cause_in(s)); continue
        gs = group_scopes(s)
        if gs and find_lifts(re.split(r"\bexcept\b|exception", s, maxsplit=1, flags=re.I)[0]): gs = []     # specific lifts are named: the sentence is about them
        if gs and not re.search(r"expected to go|may go|could go|\boff (?:the )?(?:\w+ )?hold|stage \d|wind alert|\bare open\b|\bis open\b", sl):
            st = None
            if re.search(r"(?:on|begin the day on|start the day on|placed on|put on)\s+(?:a\s+)?(?:\w+\s+)?holds?\b", sl): st = ("hold_start", "P-014")
            elif re.search(r"\bclosed\b|\bclosing\b|off[- ](?:the )?schedule", sl): st = ("closed_day", "P-014")
            elif re.search(r"delay|expected at \d+:\d\d", sl): st = ("delay", "P-014")
            if st:
                hm = re.search(r"(wind|mechanical|patrol|maintenance|electrical|lightning|icing)\s+holds?", sl)
                c = ({"maintenance": "mechanical", "electrical": "mechanical", "lightning": "weather", "icing": "weather"}.get(hm.group(1), hm.group(1)) if hm else None) or (cause_in(s) if re.search(r"due to|because of|as .* works to|\bwinds?\b|power", sl) else None)
                ex = find_lifts(re.split(r"\bexcept\b|exception", s, maxsplit=1, flags=re.I)[1]) if re.search(r"\bexcept\b|exception", sl) else []
                add(st[1], st[0], gs, c, **({"except": ex} if ex else {})); continue
        if re.search(r"(?<!all )scheduled lifts will open", sl) and not find_lifts(s):
            add("P-001", "scheduled_opening", [], None, note="all_scheduled"); continue
        if re.search(r"are scheduled for \d|will operate from|a go for \d|we expect the following|planning to run the following|lifts open \d|\d ?(?:am|a) ?- ?\d+ ?(?:pm|p) today|planned ops|(?<!all )scheduled lifts|lifts? projected|projected \w* ?open|est(?:imated)?\.? \w+ open|on deck|what we.re spinning|following lifts are spinning|today at #?squawalpine|looking to open|we plan to spin|here.s what|today.s ops|lifts accessing|lifts spinning|lifts? (?:&|and) \d+ trails|\d+ chairlifts", sl) and not re.search(r"\bhold\b|\bclosed\b", sl):
            roster = roster_with_sections(t, add, "P-001"); add("P-001", "scheduled_opening", find_lifts(roster), None); return ev
        if re.search(r"will operate from|lifts open \d|\d ?(?:am|a) ?- ?\d+ ?(?:pm|p) today", sl) and re.search(r"\bclosed\b", sl) and find_lifts(s):
            add("P-001", "scheduled_opening", [], None, note="mixed_with_closure")
        if re.search(r"\b\d{1,2}\s+(?:chair)?lifts?\b", sl) and not find_lifts(s) and not re.search(r"\bhold\b|\bdelay|\bclosed\b|\bnot open\b|storm total|\bnow\b.*\bopen\b|\bare open\b", sl):
            add("P-001", "scheduled_opening", [], None, note="count_only"); continue
        if re.search(r"on the schedule(?: for)?(?: today)?(?: is| we have| we are running|:)|we (?:will be|are) running|will (?:also |be )?(?:running|spin)\b|are on schedule for \d|that will spin for the first time|are spinning today for the first time", sl) and find_lifts(s) and not re.search(r"\bhold\b|\bclosed\b|\bdelay|\buntil\b|\bonly\b", sl):
            add("P-001", "scheduled_opening", find_lifts(s), None, note="roster"); continue
        if re.search(r"\boff (?:of )?(?:the )?(\w+ )?hold\b", sl) and find_lifts(s):
            hm = re.search(r"off (?:of )?(?:the )?(\w+) hold", sl); w = hm.group(1) if hm else None; c = {"maintenance": "mechanical", "electrical": "mechanical", "lightning": "weather", "icing": "weather", "ice": "weather", "icy": "weather"}.get(w) or (w if w in ("wind", "mechanical", "patrol") else None)
            add("P-040", "reopen", find_lifts(re.split(r"\b(?:is|are|has)\b", s, maxsplit=1, flags=re.I)[0]) or find_lifts(s), c, resolves_hold=True); continue
        if re.search(r"removed from (?:the |today.s )?schedule|will (?:be )?clos(?:e|ing) at \d|has been closed|have been closed|close the following lifts|had to close|closed for the season|will be closed \d", sl) and not re.search(r"\broad\b|\brd\b|parking", sl):
            c = cause_in(t) if re.search(r"gusts|winds?", sl) or cause_in(t) else None
            add("P-020", "closed_day", find_lifts(t if "following" in sl else s), "wind" if re.search(r"gusts|wind", sl) else c); continue
        if re.search(r"\b(?:is|are) (?:slightly |a bit )?delayed\b|delayed on the|operational delay|projected to open|looking more like \d|planned to open at \d|slight delay but", sl) and find_lifts(s):
            add("P-030", "delay", find_lifts(s), cause_in(s) or ("weather" if "rime" in sl else None)); continue
        if re.search(r"(?:now |is |are )?spinning!?|\bis loading\b|(?:is )?now loading\b|we.re loading\b|just opened|=\s*open\b|opened on time|open to the public|now open at|are open\b|\bis open\b|has opened", sl) and find_lifts(s) and not re.search(r"will be|today:|\bnot open|should be|about an hour|mid-?station|open daily|(?:end of|for the|rest of the) season|\bwhen\b|as soon as|\bonce\b", sl):
            add("P-040", "reopen", find_lifts(re.split(r"\b(?:is|are|has)\b|now spinning|spinning", s, maxsplit=1, flags=re.I)[0]) or find_lifts(s), None); continue
        if re.search(r"all (?:the )?lots|lots are now full|parking (?:available|at alpine and)|parking spots|parking reservation", sl):
            add("P-050", "parking", [], None); continue
        if re.search(r"\b\d+ (?:lower mountain )?lifts?\b.{0,40}(?:schedul|for \d|\d ?(?:am|a)\b)|lifts? (?:are )?(?:on the )?schedul", sl) and not re.search(r"on delay|on hold", sl):
            add("P-001", "scheduled_opening", find_lifts(s), None, note="count_only"); continue
        if re.search(r"tomorrow|next (?:week|weekend)|this weekend", sl) and re.search(r"opening|will open", sl):
            add("P-090", "other", [], None, note="announcement"); continue
        if re.search(r"(?:will open|will spin (?:around|at|by) \d|expected to open|aiming for an? \d|opening at|expected at|will open on schedule)", sl) and find_lifts(s) and not re.search(r"hold|delay|closed", sl):
            tm = re.search(r"(?:open(?:ing)?|expected) (?:at|for) (?:approximately |about |around )?(\d{1,2})(?::\d\d)?\s*(am|pm|a|p)?", sl)
            hh = int(tm.group(1)) if tm else 9; sfx = (tm.group(2) or "")[:1] if tm else ""
            hh = hh % 12 + 12 if sfx == "p" else (hh % 12 if sfx == "a" else (hh if hh >= 8 else hh + 12))
            late = bool(tm) and hh >= 10
            add("P-030" if late else "P-001", "delay" if late else "scheduled_opening", find_lifts(s), None); continue
        if re.search(r"back open|to the open list|is back open", sl) and find_lifts(s):
            add("P-040", "reopen", find_lifts(s), None); continue
        if re.search(r"list of (?:closures|wind holds?)|added to (?:the )?(?:list of )?(?:wind )?holds?|(?:been|be) put on (?:a )?(\w+ )?hold|adding .* to the list|back on wind hold", sl) and find_lifts(s):
            hc = cause_in(s) or "wind"
            add("P-010" if "hold" in sl else "P-020", "hold_start" if "hold" in sl else "closed_day", find_lifts(s), hc); continue
        if re.search(r"on delay|delays? due to icing|icing on lifts", sl):
            add("P-030", "delay", find_lifts(s) or ["ALL"], "weather" if "ic" in sl else cause_in(s)); continue
        if re.search(r"mid-?station|uploads? only|min(?:ute)? schedule|open (?:till|until) \d", sl) and find_lifts(s):
            qm2 = re.search(r"mid-?station|uploads? only", sl)
            pl = find_lifts(s[:qm2.start()])[-1:] if qm2 and len(find_lifts(s)) > 1 and find_lifts(s[:qm2.start()]) else find_lifts(s)   # only the lift named right before 'to the mid-station'
            add("P-070", "partial", pl, "wind" if "wind" in sl else None, detail="limited"); continue
        if re.search(r"safety (?:tip|alert|first)|unmarked hazards|shuttle|storm totals|\d+ ?(?:hour|hr|h) totals|hour totals|forecast is for|happy holidays|chance of", sl) and not re.search(r"\bhold\b", sl):
            add("P-060" if re.search(r"totals|forecast|chance", sl) else "P-090", "other", [], None); continue
        if re.search(r"\blot\b.*\bfull\b|hidden valley|deer park", sl):
            add("P-050", "parking", [], None); continue
        if re.search(r"(?:\bon|put on|added to|to the list of) (?:an? |the )?(?:\w+ )?(?:wind |mechanical |patrol |maintenance )?holds?\b", sl) and find_lifts(s) and not re.search(r"expected to go|may go|could go|will be put", sl):
            hm = re.search(r"(wind|mechanical|patrol|maintenance|electrical|icing|lightning)\s+holds?", sl)
            hc = {"maintenance": "mechanical", "electrical": "mechanical", "icing": "weather"}.get(hm.group(1), hm.group(1)) if hm else None
            subj = re.split(r"\b(?:remains?|is|are|will|also|have|has)\b", s, maxsplit=1, flags=re.I)[0]
            add("P-010", "hold_start", find_lifts(subj) or find_lifts(s), hc); continue
        if re.search(r"download(?:s|ing)? only|downloads? only|mid-?station only|sightseeing only|(?:mtn|mountain) run (?:access )?only|advanced only|no return access|access to .{0,25} only", sl) and (find_lifts(s) or last_lifts):
            add("P-070", "partial", find_lifts(s) or last_lifts, cause_in(s) or ("wind" if re.search(r"wind", sl) else None), detail="download_only" if "download" in sl else "limited"); continue
        if re.search(r"may go on hold|may go on wind hold", sl): add("P-012", "warning", find_lifts(s), "wind"); continue
        if re.search(r"(?:added to the )?closed list|closing .* (?:for|due)|will be closed on|have gone on|has gone on", sl) and not re.search(r"patrol cup|stifel|\broad\b|\brd\b", sl):
            if re.search(r"gone on", sl): add("P-010", "hold_start", find_lifts(s.split("...")[-1]), cause_in(s) or "wind"); continue
            subj = re.split(r"\bhave been\b|\bwill be\b|, we are closing|we are closing|closing", s, maxsplit=1, flags=re.I)
            lifts = find_lifts(subj[0]) or find_lifts(s)
            dm = re.search(r"(?:due to|because of)(.*)", s, re.I); add("P-020", "closed_day", lifts, cause_in(dm.group(1)) if dm else None); continue
        if re.search(r"(?:\bnow|\bis|\bare)\s+on\s+(?:a\s+)?(\w+\s+)?holds?\b", sl) and find_lifts(s):
            hm = re.search(r"on\s+(?:a\s+)?(\w+)\s+holds?", s, re.I); hc = hm.group(1).lower() if hm else None
            hc = {"maintenance": "mechanical", "electrical": "mechanical", "lightning": "weather", "icing": "weather", "ice": "weather", "icy": "weather"}.get(hc, hc if hc in ("wind", "mechanical", "patrol", "weather", "lightning") else None)
            add("P-010", "hold_start", find_lifts(re.split(r"\b(?:now|is|are)\s+on\b", s, maxsplit=1, flags=re.I)[0]), hc); continue
        if re.search(r"not connected to alpine|palisades side only|minute schedule|patrol only|spinning for patrol", sl):
            add("P-070", "partial", find_lifts(s), "wind" if "wind" in sl else None, detail="limited"); continue
        if re.search(r"added to (?:today.s |the )?schedule", sl) and re.search(r"now open|is open", sl) and find_lifts(s):
            add("P-001", "scheduled_opening", find_lifts(s), None); add("P-040", "reopen", find_lifts(s), None); continue
        if re.search(r"added to (?:today.s |the )?schedule|are not open|not open\.", sl) and find_lifts(s):
            add("P-001" if "added" in sl else "P-020", "scheduled_opening" if "added" in sl else "closed_day", find_lifts(s), None); continue
        if re.search(r"stage \d+ wind alert|wind alert", sl): add("P-012", "warning", find_lifts(s), "wind"); continue
        if re.search(r"back up and running|up and running", sl) and not re.search(r"should be|will be|about an hour", sl): add("P-040", "reopen", find_lifts(s), None); continue
        if re.search(r"will be delayed|may be delayed|delayed start|with a delay|delayed (?:to|open)|(?:a few|\d+) minutes late|open(?:ing)? late|expect (?:some )?delays|snow safety delays|delayed opening|delays and closures are possible", sl):
            add("P-030", "delay", find_lifts(s), cause_in(s) or ("patrol" if "snow safety" in sl else None)); continue
        if re.search(r"(?:will be )?opening at \d|opening tomorrow|opening in", sl) and find_lifts(s):
            add("P-001", "scheduled_opening", find_lifts(s), None); continue
        if re.search(r"going on (?:a )?wind hold|going on hold", sl):
            add("P-012", "warning", find_lifts(s), "wind"); continue
        if re.search(r"calendar|safety message|deep snow safety|traffic|shuttle|blog|reservation|park & ride|terrain park|celebration|christmas|road\b|rd\b|snow top to bottom|express|tree wells", sl) and not find_lifts(s):
            add("P-090", "other", [], None); continue
        if re.match(r"^(?:we received|today.s forecast|todays forecast|snow showers|sunny|sun,|partly|clear|mostly|cloudy|\d+\"? overnight|\d+-\d+\"|palisades got|alpine got)", sl) and not re.search(r"\bhold\b", sl):
            add("P-060", "other", [], None); continue
        # P-012 warnings
        if re.search(r"expected to go on|going on a .*hold any minute|likely .*(delays|hold)|winds? (?:may|are likely to|will) impact|anticipated weather impacts|winds?\b[^.!?]{0,40}\b(?:may|are likely to|will|could)\s+(?:have an? )?(?:impact|affect)|(?:operations?|lifts?)\b[^.!?]{0,30}\b(?:may|will) be (?:impacted|affected)|(?:impact|affect)(?:ing)? (?:the )?(?:operation of|lift operations?)|(?:have|be having) an? impact on lift|may experience delays", sl):
            add("P-012", "warning", find_lifts(s), cause_in(s) or "wind"); continue
        # P-050 parking
        if re.search(r"parking (?:lots?|is)|lots? (?:are|is) full|we are (?:now )?parking at", sl):
            add("P-050", "parking", [], None); continue
        am2 = re.search(r"all (?:scheduled )?lifts(?: at \w+)? (?:are|remain) (?:now )?(?:open|delayed)", sl)
        if am2:
            add("P-021", "delay" if "delayed" in am2.group(0) else "reopen", ["ALL"], None); continue
        # P-021 all lifts closed
        if re.search(r"all (?:of )?(?:the )?lifts\b[^.!?]{0,40}?\b(?:that|which|on (?:an? )?(?:\w+ )?hold)\b.*closed", sl):      # 'All lifts that were on wind hold are now closed': only the lifts already on hold, not every lift
            add("P-021", "closed_day", ["ALL_ON_HOLD"], cause_in(s) or ("wind" if "wind hold" in sl else None)); continue
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
        if re.search(r"closed (?:for )?(?:the )?(?:day|remainder|rest)|off[- ](?:the )?schedule|is closed|now closed|are closed|closed to the public", sl):
            if re.search(r"\broad\b|parking|exhibition will be closed to the public", sl): add("P-090", "other", [], None); continue
            subj = re.split(r"\b(?:is|are|will be)\b|[-:]|, (?:available|still)|\bclosed\b|\boff\b", s, maxsplit=1, flags=re.I)[0]
            lifts = find_lifts(subj) or find_lifts(s) or last_lifts
            dm = re.search(r"due to(.*)", s, re.I); c = cause_in(dm.group(1)) if dm else None
            add("P-020", "closed_day", lifts, c); continue
        # P-040 reopen
        if re.search(r"\b(?:is|are)\s+(?:now\s+|also\s+)?open\b|re-?opened|\balso open\b|\bnow open\b|^[\w\s’'&,.-]+ open!?$", sl) and not re.search(r"\broad\b|open at|will open|opening (?:tomorrow|soon)|\bwhen\b|as soon as|\bonce\b|update you", sl):
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
    for _e in events: _e["parser_version"] = PARSER_VERSION
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
