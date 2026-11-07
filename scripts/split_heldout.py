"""Set aside a fixed 20% of a winter's posts as the held-out exam. Deterministic: decided by a hash of the post id,
so it can never drift between runs. Rules are never tuned on the held-out file.
usage: python3 -I scripts/split_heldout.py 2023"""
import os, sys, json, hashlib
Y = int(sys.argv[1]); W = f"{Y}-{str(Y+1)[2:]}"
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
posts = json.load(open(os.path.join(root, "raw", "x", W + ".json")))
held = lambda p: int(hashlib.sha256(("held-out-v1:" + p["id"]).encode()).hexdigest(), 16) % 5 == 0
train, test = [p for p in posts if not held(p)], [p for p in posts if held(p)]
os.makedirs(os.path.join(root, "derived"), exist_ok=True)
json.dump(sorted(train, key=lambda p: p["created_at"]), open(os.path.join(root, "derived", f"{W}_train.json"), "w"))
json.dump(sorted(test, key=lambda p: p["created_at"]), open(os.path.join(root, "derived", f"{W}_heldout.json"), "w"))
print(f"{W}: {len(train)} train, {len(test)} held-out ({len(test)/len(posts):.1%})")
