"""Builds docs/app/model.js, the only data the app reads, from the repo pipeline: lift_days.csv, the parsed posts and results/baselines.json.
Every number the app shows is written here (rules, odds, per-winter scores, reader agreement); the page does no fitting or scoring of its own.
usage: python3 -I scripts/build_app_model.py   (run after build_dataset.py, recover_rules.py and baselines.py)"""
import json, os, collections, glob, statistics, html, re, subprocess, sys
from zoneinfo import ZoneInfo
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ruleslib import ROOT, rows, FEATS, WINTERS, f1, fit        # the project's one definition of how rules are fitted
APP = os.path.join(ROOT, "docs", "app")
for r in rows:
    for k in [k for k in r if k.startswith("tag_")]: r[k]=int(r[k])
INF = {}                                                    # inferred causes (scripts/infer_causes.py): confident ones only, shown as inferred in the app
_f = os.path.join(ROOT, "data", "derived", "cause_inferred.csv")
if os.path.exists(_f):
    import csv as _csv
    for _r in _csv.DictReader(open(_f)):
        if _r["confident"] == "1": INF[(_r["winter"], _r["date"], _r["lift"])] = {"wind": "w", "patrol": "p", "mechanical": "m", "weather": "x"}[_r["cause_inferred"]]
S = [r for r in rows if r["fit_ok"]]
def rule_for(tr, L):
    b = fit(tr,"held",FEATS)
    if not b: return None
    _,f,t = b
    a=[r for r in tr if r[f] is not None and r[f]>=t]; bl=[r for r in tr if r[f] is not None and r[f]<t]
    return dict(f=f,t=round(t,2),above=round(sum(r["held"] for r in a)/max(1,len(a)),3),na=len(a),
                below=round(sum(r["held"] for r in bl)/max(1,len(bl)),3),nb=len(bl))
cnt=collections.Counter(r["lift"] for r in S); LIFTS=sorted([l for l,n in cnt.items() if n>=40], key=lambda l:-cnt[l])
book={}; loo={W:{} for W in WINTERS}
for L in LIFTS:
    full=[r for r in S if r["lift"]==L]
    rl=rule_for(full,L)
    rl.update(days=len(full), held_days=sum(r["held"] for r in full), wind_days=sum(r["held_wind"] for r in full), unstated=sum(r["held_unstated"] for r in full))
    book[L]=rl
    for W in WINTERS:
        tr=[r for r in full if r["winter"]!=W]
        if len(tr)<25: continue
        x=rule_for(tr,L)
        if x: loo[W][L]=x
# days
days={}
for r in rows:
    k=(r["winter"],r["date"])
    d=days.setdefault(k,dict(date=r["date"],winter=r["winter"],x={f:r[f] for f in FEATS+["fnt_day_gust","sib_h60"]},act={}))
    if r["closed_all"]:
        t=d.setdefault("ca",dict(t=r["closed_all_time"],tags=[]))
        t["t"]=min(t["t"],r["closed_all_time"]) if r["closed_all_time"] else t["t"]
        t.setdefault("sides",[]); t["sides"]=sorted(set(t["sides"])|{r["side"]})
        for g in ("avalanche","snow","ice","visibility","lightning","power","flood"):
            if r["tag_"+g] and g not in t["tags"]: t["tags"].append(g)
    if r["expected"]:
        cause="c" if r["closed_all"] else "w" if r["held_wind"] else "p" if r["held_patrol"] else "m" if r["held_mech"] else "x" if r["held_weather"] else "u" if r["held_unstated"] else ""
        d["act"][r["lift"]]=[r["held"],cause]+([INF[(r["winter"],r["date"],r["lift"])]] if cause=="u" and (r["winter"],r["date"],r["lift"]) in INF else [])
D=sorted([d for d in days.values() if d["act"]],key=lambda d:d["date"])

# 2026-27 El Nino possibilities: medians of matching days from the El Nino winters in the data (2018-19 weak, 2019-20 weak, 2023-24 strong)
SL6=["day_gust","early_gust","day_spd","early_spd","swe24","avy"]
EN=[d for d in D if d["winter"] in ("2018-19","2019-20","2023-24") and d["x"]["day_gust"] is not None and d["x"]["swe24"] is not None]
def med6(sub): return {k:round(statistics.median([d["x"][k] for d in sub if d["x"].get(k) is not None]),1) for k in SL6}
ARCH=[("ar","Warm atmospheric river","Heavy precipitation on a strong southwest wind. Rain or slush can reach the 6,200 ft base while the upper mountain gets snow.",lambda x:x["swe24"]>=1.5 and x["day_gust"]>=60),
 ("pow","Big snow, light wind","The powder-day winter people hope for: a foot or more of snow with the wind staying down.",lambda x:x["swe24"]>=1.5 and x["day_gust"]<45),
 ("wind","Ridge-top wind storm","A cold front with little new snow and gusts over the ridges. The classic wind-hold morning.",lambda x:x["swe24"]<0.5 and x["day_gust"]>=85),
 ("dry","Dry spell between storms","Quiet, cold or mild, no snow and light wind. The break between systems.",lambda x:x["swe24"]<0.3 and x["day_gust"]<25)]
archetypes=[]
for aid,name,blurb,f in ARCH:
    sub=[d for d in EN if f(d["x"])]
    if len(sub)>=3: archetypes.append(dict(id=aid,name=name,blurb=blurb,n=len(sub),x=med6(sub)))
# posts by local date
def clean(t, n=420):
    t = html.unescape(t).replace("\n"," "); t = re.sub(r"\s+"," ",t).strip()
    return t if len(t)<=n else t[:n].rsplit(" ",1)[0]+" ..."
la=ZoneInfo("America/Los_Angeles"); posts=collections.defaultdict(list)
for f in glob.glob(f"{ROOT}/data/derived/20*_train.json")+glob.glob(f"{ROOT}/data/derived/20*_heldout.json"):
    try: P=json.load(open(f)); P=P if isinstance(P,list) else P.get("posts",[])
    except Exception: continue
    for p in P:
        try: dt=datetime.fromisoformat(p["created_at"].replace("Z","+00:00")).astimezone(la)
        except Exception: continue
        posts[dt.strftime("%Y-%m-%d")].append((dt.strftime("%H:%M"),clean(p["text"])))
for k in posts: posts[k].sort()
CLS={"hold":"hold","closed":"closed for the day","delay":"late opening","reopen":"reopening","partial":"partial operation","schedule":"scheduled opening","parking":"parking"}
PAR={"hold":"hold_start","closed":"closed_day","delay":"delay","reopen":"reopen","partial":"partial","schedule":"scheduled_opening","parking":"parking"}
ag=dict(ps=0,pm=0,sm=0,n=0,posts=0); dis_posts=set(); by=collections.Counter(); cand=[]
for W in WINTERS:
    for sp in ("train","heldout"):
        try:
            PP=json.load(open(f"{ROOT}/data/derived/{W}_{sp}.json")); PP=PP if isinstance(PP,list) else PP.get("posts",[])
            par=json.load(open(f"{ROOT}/data/derived/{W}_{sp}_postlabels.json")); sq=json.load(open(f"{ROOT}/data/derived/{W}_{sp}_labels_subq.json")); mu=json.load(open(f"{ROOT}/data/derived/{W}_{sp}_labels_muse.json"))
        except Exception: continue
        T={str(p["id"]):p for p in PP}
        ids=[i for i in par if "error" not in sq.get(i,{"error":1}) and "error" not in mu.get(i,{"error":1})]
        ag["posts"]+=len(ids)
        for i in ids:
            for c,t in PAR.items():
                P=t in par[i]; S=sq[i][c]>.5; U=mu[i][c]>=.5
                ag["ps"]+=P==S; ag["pm"]+=P==U; ag["sm"]+=S==U; ag["n"]+=1
                if S==U and S!=P:
                    dis_posts.add((W,i)); by[c]+=1
                    tx=clean(T[i]["text"],260) if i in T else ""
                    if tx and len(tx)<=200: cand.append(dict(w=W,cls=CLS[c],parser=bool(P),readers=bool(S),text=tx,key=c))
seen=set(); ex=[]
for want in (False,True):  # parser missed first, then parser over-called
    for c in cand:
        if c["parser"]==want and c["key"] not in seen and len(ex)<3:
            seen.add(c["key"]); ex.append({k:v for k,v in c.items() if k!="key"})
agree=dict(posts=ag["posts"],parser_subq=round(ag["ps"]/ag["n"],3),parser_muse=round(ag["pm"]/ag["n"],3),subq_muse=round(ag["sm"]/ag["n"],3))
disagree=dict(posts=len(dis_posts),of=ag["posts"],by_class={CLS[k]:v for k,v in by.most_common()},examples=ex)
med={f:round(statistics.median([r[f] for r in rows if r[f] is not None]),2) for f in FEATS+["fnt_day_gust"]}
# ---- every score the page shows, taken from results/baselines.json (written by baselines.py); the page never recomputes them
BL = json.load(open(os.path.join(ROOT, "results", "baselines.json")))
wind_days = collections.Counter(); 
for d in D: pass
hw = collections.defaultdict(set)
for r in rows:
    if r["held_wind"]: hw[r["winter"]].add(r["date"])
strata = {W: dict(days=BL["day_level"][W]["n_days"], wind_holds=len(hw[W]), score=BL["day_level"][W]["learned"]["f1"], baseline=BL["day_level"][W]["mph25"]["f1"], line=BL["day_level"][W]["line_mph"]) for W in WINTERS}
proof = dict(strata=strata, day_pooled=BL["day_level"]["pooled"], day_wins=BL["day_level"]["winters_learned_beats_25mph"],
             lift=BL["lift_level"], lift_all_named=BL["lift_level_all_named"],
             source="results/baselines.json (scripts/baselines.py): leave-one-winter-out, lift level on scheduled lift-days only")
try: commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
except Exception: commit = ""
LG = json.load(open(os.path.join(ROOT, "rules", "lift_groups.json")))
GATES = ("Tram", "Funitel", "Base to Base Gondola")
al = LG["alpine"]
groups = dict(upper=[l for l in LG["palisades"]["UPPER_MOUNTAIN"]["lifts"] if l not in GATES],
              lower=list(LG["palisades"]["LOWER_MOUNTAIN"]["lifts"]),
              alpine=list(dict.fromkeys(al["named_together"] + al["named_separately_not_upper"] + al["also_alpine"])))
PRESET_DATES = ("2024-12-15", "2024-12-16")                       # the "Set conditions" starting points read weather straight from the dataset
feat = {d["date"]: d["x"] for d in days.values() if d["date"] in PRESET_DATES}
# ---- plain-language findings the page quotes, computed here so the copy can never drift from the data
SW = [r for r in rows if r["fit_ok"] and r["day_gust"] is not None]
GATE = {"Tram", "Funitel"}; UPG, LOG = set(groups["upper"]), set(groups["lower"])
def rate(rs): return round(sum(r["held"] for r in rs) / len(rs), 3) if rs else None
bydate = collections.defaultdict(list)
for r in SW: bydate[(r["winter"], r["date"])].append(r)
up_g, up_ng, up_g_o, up_ng_o = [], [], [], []          # *_o: days with no whole-side closure, so the cascade is not just "everything closed together"
for rs in bydate.values():
    gate_held = any(r["lift"] in GATE and r["held"] for r in rs); shut = any(r["closed_all"] for r in rs)
    (up_g if gate_held else up_ng).extend(r for r in rs if r["lift"] in UPG)
    if not shut: (up_g_o if gate_held else up_ng_o).extend(r for r in rs if r["lift"] in UPG)
H = [r for r in SW if r["held"]]
def wshare(group):
    held = sum(b["held_days"] for l, b in book.items() if l in group); wind = sum(b["wind_days"] for l, b in book.items() if l in group)
    return round(wind / held, 3) if held else None
# lift-days that exist only because a post named the lift on hold, delay or closure (not scheduled, not under a whole-side closure, not the COVID winter): held by construction
_no = [r for r in rows if not r["expected"] and r["covid_era"] != "restricted"]
_nof = round(sum(r["held"] for r in _no) / len(_no), 3) if _no else None
# whole-side closures by avalanche danger and by gust, over every in-season day that has at least one expected lift row
_days = {}
for r in SW: _days.setdefault((r["winter"], r["date"]), dict(gust=r["day_gust"], avy=r["avy"], closed=0))["closed"] |= r["closed_all"]
def _share(sel): sel = list(sel); return dict(n=len(sel), share=round(sum(d["closed"] for d in sel) / len(sel), 3) if sel else None)
_cb_avy = {str(a): _share(d for d in _days.values() if d["avy"] is not None and round(d["avy"]) == a) for a in (1, 2, 3, 4)}
_cb_gust = {lab: _share(d for d in _days.values() if lo <= d["gust"] < hi) for lab, lo, hi in (("under60", 0, 60), ("60to80", 60, 80), ("80to100", 80, 100), ("100to130", 100, 130), ("130plus", 130, 999))}
# storm days (2+ in of new snow, 1+ in of snow water in 24 h, or avalanche danger 3+) versus other days, wind under 60 mph: share of expected lifts held or closed, and share of days with any gateway or high lift held
def _isstorm(r): return (r["new_snow24"] is not None and r["new_snow24"] >= 2) or (r["swe24"] is not None and r["swe24"] >= 1.0) or (r["avy"] is not None and r["avy"] >= 3)
_calm = [r for r in SW if r["day_gust"] < 60 and (r["new_snow24"] is not None or r["avy"] is not None)]
_st, _ot = [r for r in _calm if _isstorm(r)], [r for r in _calm if not _isstorm(r)]
_storm = dict(held_storm=rate(_st), held_other=rate(_ot), n_storm=len(_st), n_other=len(_ot), days_storm=len({(r["winter"], r["date"]) for r in _st}), days_other=len({(r["winter"], r["date"]) for r in _ot}),
              gate_storm=rate([r for r in _st if r["lift"] in GATE]), gate_other=rate([r for r in _ot if r["lift"] in GATE]))
# duration: hours with gusts of 60 mph or more at Siberia (6am to 4pm), gateway lifts, days with a 60 to 100 mph peak
_g = [r for r in SW if r["lift"] in GATE and r["sib_h60"] is not None and 60 <= r["day_gust"] < 100]
_dur = {lab: dict(n=len(x), rate=rate(x)) for lab, x in (("h0to2", [r for r in _g if r["sib_h60"] <= 2]), ("h2to5", [r for r in _g if 2 < r["sib_h60"] <= 5]), ("h5to9", [r for r in _g if 5 < r["sib_h60"] <= 9]), ("h9plus", [r for r in _g if r["sib_h60"] > 9]))}
posts_total = sum(len(json.load(open(f))) for f in glob.glob(f"{ROOT}/data/derived/20*_train.json") + glob.glob(f"{ROOT}/data/derived/20*_heldout.json"))
facts = dict(posts_total=posts_total, posts_all3=ag["posts"],
             up_when_gate_held=rate(up_g), up_when_no_gate_held=rate(up_ng), up_when_gate_held_open=rate(up_g_o), up_when_no_gate_held_open=rate(up_ng_o),
             windy_hold_rate=dict(gates=rate([r for r in SW if r["lift"] in GATE and r["day_gust"] >= 60]), upper=rate([r for r in SW if r["lift"] in UPG and r["day_gust"] >= 60]), lower=rate([r for r in SW if r["lift"] in LOG and r["day_gust"] >= 60])),
             wind_named_share_upper=wshare(GATE | UPG), wind_named_share_lower=wshare(LOG),
             wind_named_holds_on_60=round(sum(1 for r in H if r["held_wind"] and r["day_gust"] >= 60) / max(1, sum(1 for r in H if r["held_wind"])), 3),
             holds_on_days_below_60=round(sum(1 for r in H if r["day_gust"] < 60) / len(H), 3),
             holds_no_cause=round(sum(r["held_unstated"] for r in H) / len(H), 3), holds_wind=round(sum(r["held_wind"] for r in H) / len(H), 3),
             hold_lift_days=len(H), scheduled_lift_days=len(SW),
             named_only_held=_nof, named_only_n=len(_no), coverage=BL.get("coverage"), morning=BL.get("day_level_morning"),
             closure_days=len({(r["winter"], r["date"]) for r in rows if r["closed_all"]}),
             closure_by_avy=_cb_avy, closure_by_gust=_cb_gust, storm=_storm, dur=_dur)
model=dict(facts=facts,feat=feat,groups=groups,proof=proof,commit=commit,lifts=LIFTS,book=book,loo=loo,days=D,posts={d["date"]:posts.get(d["date"],[]) for d in D},medians=med,arch=archetypes,agree=agree,disagree=disagree,winters=WINTERS,built=datetime.now().strftime("%Y-%m-%d %H:%M"))
open(os.path.join(APP,"model.js"),"w").write("window.MODEL = "+json.dumps(model,separators=(",",":"))+";\n")
print("lifts",len(LIFTS),"days",len(D),"posts",sum(len(v) for v in posts.values()),"size KB",os.path.getsize(os.path.join(APP,"model.js"))//1024)
