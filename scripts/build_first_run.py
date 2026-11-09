"""First-run record per lift per winter: the day a lift was first meant to run, from announcements first, and what happened that day.
Sources, in order of use: (1) a tweet that announces or flags the lift ('NEW TERRAIN', 'added to the schedule', 'opening tomorrow', 'for the first time this season'), dated to the day the
sentence NAMES ('tomorrow', 'Saturday', 'this weekend'), not the day it was posted; (2) the blog calendar (rules/season_calendar.json, model-read, kind lift_first_run, not cancelled);
(3) fallback: the first day the lift is on a morning schedule or reopened. All three dates are kept side by side; `first_run` is blog > tweet announcement > fallback, and `basis` says which.
`day_outcome` is what the training tweets say about the lift on that day: ran (listed on the schedule or reopened), held, delayed, partial, closed, or not_mentioned.
Training posts only (heldout posts are never read here). DERIVED, stored apart from lift_days.csv; it is not a lift_days feature.
usage: python3 -I scripts/build_first_run.py   -> data/derived/first_run.csv"""
import os, re, json, csv, glob, html, datetime, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
src = open(os.path.join(ROOT, "scripts", "parse_posts.py")).read().split("\n")
ns = {}; exec("\n".join(src[:93]), ns)          # LIFTS table, LIFT_RE, find_lifts (the first 93 lines are definitions only)
find = ns["find_lifts"]
CUE = re.compile(r"new terrain|terrain expansion|\badded?\b(?! to the closed)|adding|will open|opening (?:tomorrow|today|saturday|sunday|friday|monday|this)|open(?:s|ing)? (?:tomorrow|on)|first time this season|opening day|\bnow open\b", re.I)
NEG = re.compile(r"closed list|wind hold|on hold|will be closed|remain closed|closed (?:today|for)|not (?:open|expected)|do not expect|cancel", re.I)
WD = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
def target(sentence, d0):
    """the day the sentence names: tomorrow = +1, a weekday name = next such day (today counts), this weekend = next Saturday, otherwise the post day"""
    s = sentence.lower()
    if "tomorrow" in s: return d0 + datetime.timedelta(days=1)
    m = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", s)
    if m: return d0 + datetime.timedelta(days=(WD[m.group(1)] - d0.weekday()) % 7)
    if "this weekend" in s: return d0 + datetime.timedelta(days=(5 - d0.weekday()) % 7)
    return d0
def side_of(lift):
    return "alpine" if lift in ns["ALPINE_ONLY"] or lift in ("Alpine Meadow", "Alpine Carpets") else "palisades"
def winter_of(d): return f"{d.year if d.month >= 8 else d.year - 1}-{str(d.year + (1 if d.month >= 8 else 0))[2:]}"
cal = json.load(open(os.path.join(ROOT, "rules", "season_calendar.json")))["events"]
blog = collections.defaultdict(list)
for e in cal:
    if e["kind"] != "lift_first_run" or e.get("status") == "cancelled" or not e.get("lift"): continue
    for l in find(e["lift"]): blog[(e["winter"], l)].append((e["date"], e["status"], e.get("quote", "")[:80]))
def day_out_needed(o): return o in ("ran", "partial", "held", "delayed", "closed")      # the training tweets mention the lift that day
rows = []
for tp in sorted(glob.glob(os.path.join(ROOT, "data", "derived", "20??-??_train.json"))):
    w = os.path.basename(tp)[:7]
    ev = json.load(open(tp.replace("_train.json", "_train_events.json"))) if os.path.exists(tp.replace("_train.json", "_train_events.json")) else None
    if ev is None: continue                                   # 2015-18 train posts not parsed yet
    ann = {}; sched = {}; by_day = collections.defaultdict(lambda: collections.defaultdict(set))
    for t in sorted(json.load(open(tp)), key=lambda t: t["created_at"]):
        d0 = datetime.datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")).astimezone(datetime.timezone(datetime.timedelta(hours=-8))).date()
        for s in re.split(r"(?<=[.!?])\s+|\n", html.unescape(t["text"])):
            if CUE.search(s) and not NEG.search(s):
                for l in find(s): ann.setdefault(l, (target(s, d0), re.sub(r"\s+", " ", s)[:90]))
    for e in ev:
        if not e["lift"]: continue
        day = e["start"][:10]
        by_day[(e["lift"], day)][e["event_type"]].add(e["parse_rule_id"])
        if e["event_type"] in ("scheduled_opening", "reopen"): sched.setdefault(e["lift"], day)
    for l in sorted(set(sched) | set(ann) | {k[1] for k in blog if k[0] == w}):
        if l == "ALL" or l not in ns["LIFTS"] and l not in ("Alpine Meadow", "Alpine Carpets", "Palisades Carpets"): continue
        a = ann.get(l); b = sorted(blog.get((w, l), []))
        a_d = str(a[0]) if a and winter_of(a[0]) == w else None; b_d = b[0][0] if b else None; s_d = sched.get(l)
        D = datetime.date.fromisoformat
        if a_d and s_d and D(a_d) > D(s_d) + datetime.timedelta(days=1): a_d = None      # an announcement after the lift already ran is not a first-run announcement
        first = b_d or a_d or s_d
        if not first: continue
        basis = "blog" if b_d else "tweet_announcement" if a_d else "first_schedule"
        if b_d and s_d and D(b_d) > D(s_d) + datetime.timedelta(days=7): first, basis = s_d, "schedule_earlier_than_blog"   # the blog date is a restart or reopening, the lift ran long before
        elif a_d and (not b_d) and s_d and D(a_d) > D(s_d) + datetime.timedelta(days=7): first, basis = s_d, "schedule_earlier_than_announce"
        types = set(by_day.get((l, first), {}))
        out = "held" if "hold_start" in types else "delayed" if "delay" in types else "partial" if "partial" in types else "closed" if "closed_day" in types else "ran" if types & {"scheduled_opening", "reopen"} else "not_mentioned"
        dates = [x for x in (b_d, a_d, s_d) if x]
        blog_happened = next((x[0] for x in b if x[1] == "happened" and abs((D(x[0]) - D(first)).days) <= 1), None)     # a blog post that says it opened, within a day of the chosen date
        gap = max(abs((D(x) - D(first)).days) for x in dates)
        if day_out_needed(out): conf = "confirmed_by_blog_and_tweet" if blog_happened else "confirmed_by_tweet"
        elif blog_happened: conf = "confirmed_by_blog"
        else: conf = "plan_only"
        if gap > 3 and conf != "confirmed_by_blog_and_tweet": conf += "+sources_conflict"
        rows.append(dict(winter=w, side=side_of(l), lift=l, first_run=first, basis=basis, blog_date=b_d, tweet_announce_date=a_d, first_schedule_date=s_d,
                         sources_disagree=int(len(set(dates)) > 1), day_outcome=out, confidence=conf, blog_confirmed_date=blog_happened or "", announce_text=a[1] if a else "", blog_status=b[0][1] if b else "", blog_quote=b[0][2] if b else ""))
ov = {(o["winter"], o["lift"]): o for o in json.load(open(os.path.join(ROOT, "rules", "first_run_overrides.json")))["overrides"]}
for r in rows:
    r["computed_first_run"] = r["first_run"]; r["skiing_start"] = ""; r["override_note"] = ""
    o = ov.get((r["winter"], r["lift"]))
    if o:
        for k in ("first_run", "confidence", "skiing_start"):
            if k in o: r[k] = o[k]
        r["override_note"] = o["note"]
path = os.path.join(ROOT, "data", "derived", "first_run.csv")
with open(path + ".tmp", "w", newline="") as fh:
    w_ = csv.DictWriter(fh, list(rows[0])); w_.writeheader(); w_.writerows(rows)
os.replace(path + ".tmp", path)
print(len(rows), "lift-winters")
print(collections.Counter(r["basis"] for r in rows)); print(collections.Counter(r["day_outcome"] for r in rows))
print(collections.Counter(r["confidence"] for r in rows)); print("sources disagree:", sum(r["sources_disagree"] for r in rows))
