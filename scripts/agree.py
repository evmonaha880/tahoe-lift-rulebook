"""Agreement of the parser with two blind readers, per class, on one split. usage: python3 -I scripts/agree.py 2023 heldout"""
import os, sys, json
Y, split = int(sys.argv[1]), sys.argv[2]; W = f"{Y}-{str(Y+1)[2:]}"
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "derived")
L = lambda n: json.load(open(os.path.join(d, f"{W}_{split}_{n}.json")))
par, sq, mu = L("postlabels"), L("labels_subq"), L("labels_muse")
M = {"hold": "hold_start", "closed": "closed_day", "delay": "delay", "reopen": "reopen", "partial": "partial", "schedule": "scheduled_opening", "parking": "parking"}
ids = [i for i in par if "error" not in sq.get(i, {"error": 1}) and "error" not in mu.get(i, {"error": 1})]
print(f"{W} {split}: {len(ids)} posts labelled by all three\n")
print(f"{'class':9} {'parser+':>7} {'subq+':>6} {'muse+':>6} | {'par=subq':>8} {'par=muse':>8} {'subq=muse':>9} | {'all3':>5}")
tot = {k: 0 for k in ("ps", "pm", "sm", "all")}; n = 0; dis = []
for c, t in M.items():
    P = {i: t in par[i] for i in ids}; S = {i: sq[i][c] > .5 for i in ids}; U = {i: mu[i][c] >= .5 for i in ids}
    ps = sum(P[i] == S[i] for i in ids); pm = sum(P[i] == U[i] for i in ids); sm = sum(S[i] == U[i] for i in ids); a3 = sum(P[i] == S[i] == U[i] for i in ids)
    print(f"{c:9} {sum(P.values()):7} {sum(S.values()):6} {sum(U.values()):6} | {ps/len(ids):8.1%} {pm/len(ids):8.1%} {sm/len(ids):9.1%} | {a3/len(ids):5.1%}")
    tot["ps"] += ps; tot["pm"] += pm; tot["sm"] += sm; tot["all"] += a3; n += len(ids)
    for i in ids:
        if S[i] == U[i] != P[i]: dis.append((c, i, "parser says " + str(P[i])))
print(f"\nOVERALL    par=subq {tot['ps']/n:.1%}  par=muse {tot['pm']/n:.1%}  subq=muse {tot['sm']/n:.1%}  all three {tot['all']/n:.1%}")
json.dump(dis, open(os.path.join(d, f"{W}_{split}_disagreements.json"), "w"))
print(f"{len(dis)} cases where BOTH readers agree with each other and the parser differs -> data/derived/{W}_{split}_disagreements.json")
