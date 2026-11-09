"""Lift vocabulary and lift-name finder, shared by the parser and the first-run scripts.
LIFTS: canonical lift name -> regex alias. find_lifts(span) returns the canonical lift names in a span of text. _CTX["t"] holds the whole post, used to tell
Alpine from Palisades when a name (Carpets, Meadow) is ambiguous; the parser sets it for each post. Lift->mountain mapping is a modelling decision made later."""
import re

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
