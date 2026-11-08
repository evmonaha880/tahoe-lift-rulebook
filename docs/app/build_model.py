"""Builds model.js for the app from the repo's lift_days.csv and post files. Read-only on the repo.
Re-run after the final parser pass:  python3 build_model.py"""
import csv, json, os, collections, glob, statistics, html, re
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = next((os.path.abspath(os.path.join(HERE, *([".."]*n))) for n in (1, 2, 3) if os.path.exists(os.path.join(HERE, *([".."]*n), "data", "derived", "lift_days.csv"))), os.path.expanduser("~/tahoe-lift-rulebook"))
os.chdir(HERE)
rows = list(csv.DictReader(open(f"{ROOT}/data/derived/lift_days.csv")))
NUM = ["early_gust","early_spd","day_gust","day_spd","fnt_day_gust","temp_base","swe24","swe6","prec24s","new_snow24","depth","avy"]
for r in rows:
    for k in NUM: r[k] = float(r[k]) if r[k] != "" else None
    for k in ("held","held_wind","held_unstated","held_patrol","held_mech","held_weather"): r[k] = int(r[k])
    r["scheduled"] = r["scheduled"] == "True"
FEATS = ["early_gust","day_gust","early_spd","day_spd","avy","temp_base","swe24","swe6","prec24s"]
WINTERS = sorted({r["winter"] for r in rows})
S = [r for r in rows if r["scheduled"]]
def f1(tp,fp,fn): return 2*tp/(2*tp+fp+fn) if tp else 0.0
def fit(rs, y, feats):
    best=None
    for f in feats:
        sub=[r for r in rs if r[f] is not None]
        vals=sorted({r[f] for r in sub})
        if len(vals)<3: continue
        step=max(1,len(vals)//40)
        P=sum(1 for r in sub if r[y])
        for t in vals[::step]:
            tp=sum(1 for r in sub if r[f]>=t and r[y]); fp=sum(1 for r in sub if r[f]>=t and not r[y]); fn=P-tp
            s=f1(tp,fp,fn)
            if best is None or s>best[0]: best=(s,f,t)
    return best
def rule_for(tr, L):
    fs = FEATS + (["fnt_day_gust"] if L=="Funitel" else [])
    b = fit(tr,"held",fs)
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
    d=days.setdefault(k,dict(date=r["date"],winter=r["winter"],x={f:r[f] for f in FEATS+["fnt_day_gust"]},act={}))
    if r["scheduled"] or r["held"]:
        cause="w" if r["held_wind"] else "p" if r["held_patrol"] else "m" if r["held_mech"] else "x" if r["held_weather"] else "u" if r["held_unstated"] else ""
        d["act"][r["lift"]]=[r["held"],cause]
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
model=dict(lifts=LIFTS,book=book,loo=loo,days=D,posts={d["date"]:posts.get(d["date"],[]) for d in D},medians=med,arch=archetypes,agree=agree,disagree=disagree,winters=WINTERS,built=datetime.now().strftime("%Y-%m-%d %H:%M"))
open("model.js","w").write("window.MODEL = "+json.dumps(model,separators=(",",":"))+";\n")
print("lifts",len(LIFTS),"days",len(D),"posts",sum(len(v) for v in posts.values()),"size KB",os.path.getsize("model.js")//1024)
