"""Write the blog posts a third model reader needs to CONFIRM lift first runs (what happened, not what was planned), one input file per winter.
Posts: category operations (any winter given) plus general-category posts that mention opening. Text only, HTML stripped, with post id, site date (Pacific) and title.
usage: python3 -I scripts/blog_confirm_inputs.py <out_dir> <winter> [<winter> ...]   -> <out_dir>/in_<winter>.json"""
import os, sys, json, re, html
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if len(sys.argv) < 3: sys.exit("usage: python3 -I scripts/blog_confirm_inputs.py <out_dir> <winter> [<winter> ...]")
out, wins = sys.argv[1], sys.argv[2:]; os.makedirs(out, exist_ok=True)
def winter(d): y, m = int(d[:4]), int(d[5:7]); s = y if m >= 8 else y - 1; return f"{s}-{str(s + 1)[2:]}"
def clean(h):
    h = re.sub(r"(?is)<(script|style|figure|svg).*?</\1>", "", h); h = re.sub(r"(?i)</(p|div|li|h\d|tr)>|<br\s*/?>", "\n", h)
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", "", h)))).strip()
posts = {}
for cat in ("operations", "general"):
    for r in json.load(open(os.path.join(ROOT, "data", "raw", "blog", cat + ".json"))):
        w = winter(r["date"][:10]); t = clean(r["content"]["rendered"])
        if w in wins and (cat == "operations" or re.search(r"\bopen", t, re.I)): posts[r["id"]] = dict(post_id=r["id"], post_date=r["date"][:10], title=html.unescape(r["title"]["rendered"]), text=t)
for w in wins:
    ps = sorted((p for p in posts.values() if winter(p["post_date"]) == w), key=lambda p: p["post_date"])
    json.dump(ps, open(os.path.join(out, f"in_{w}.json"), "w"), ensure_ascii=False); print(w, len(ps), "posts", sum(len(p["text"]) for p in ps), "chars")
