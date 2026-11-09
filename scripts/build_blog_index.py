"""Index the saved blog (data/raw/blog) for lookup: one row per post in data/derived/blog_posts.csv and the cleaned text in data/derived/blog_text.jsonl.
This is the COMMENTARY layer: human narrative kept so a person (or scripts/commentary.py) can check a number or a parse against what the operators wrote. It is never fitted or scored.
A post that sits in several categories appears once, with all its categories. `date` is the site's Pacific local time; `tz_offset_h` is date_gmt minus date, which must equal the Pacific offset (7 or 8) - scripts/check_architecture.py tests that.
usage: python3 -I scripts/build_blog_index.py"""
import os, re, json, csv, html, glob, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = os.path.join(ROOT, "data", "raw", "blog"); OUT = os.path.join(ROOT, "data", "derived")
def clean(h):
    h = re.sub(r"(?is)<(script|style|figure|svg).*?</\1>", "", h); h = re.sub(r"(?i)</(p|div|li|h\d|tr)>|<br\s*/?>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", "", h)).replace(" ", " ")
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t)).strip()
manifest = json.load(open(os.path.join(RAW, "manifest.json")))
by = {}
for fn in sorted(glob.glob(os.path.join(RAW, "*.json"))):
    cat = os.path.basename(fn)[:-5]
    if cat == "manifest": continue
    for r in json.load(open(fn)):
        e = by.setdefault(r["id"], dict(r, cats=[]))
        e["cats"].append(cat)
if not by: raise SystemExit("no blog posts in data/raw/blog; run scripts/pull_blog.py first")
rows, n = [], 0
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "blog_text.jsonl.tmp"), "w") as tf:
    for pid, r in sorted(by.items(), key=lambda kv: kv[1]["date"]):
        text = clean(r["content"]["rendered"]); title = html.unescape(r["title"]["rendered"])
        a = __import__("datetime").datetime.fromisoformat(r["date"]); b = __import__("datetime").datetime.fromisoformat(r["date_gmt"])
        off = round((b - a).total_seconds() / 3600)
        rows.append(dict(id=pid, date=r["date"], date_gmt=r["date_gmt"], tz_offset_h=off, categories="|".join(sorted(r["cats"])), slug=r["slug"], title=title, link=r["link"], chars=len(text)))
        tf.write(json.dumps(dict(id=pid, date=r["date"], categories=sorted(r["cats"]), title=title, link=r["link"], text=text), ensure_ascii=False) + "\n"); n += 1
os.replace(os.path.join(OUT, "blog_text.jsonl.tmp"), os.path.join(OUT, "blog_text.jsonl"))
with open(os.path.join(OUT, "blog_posts.csv.tmp"), "w", newline="") as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
os.replace(os.path.join(OUT, "blog_posts.csv.tmp"), os.path.join(OUT, "blog_posts.csv"))
c = collections.Counter(c for r in rows for c in r["categories"].split("|"))
print(f"{n} distinct posts from {sum(manifest['categories'][k]['posts'] for k in manifest['categories'])} category rows; by category: {dict(c)}")
