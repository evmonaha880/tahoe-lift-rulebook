"""Pull the Palisades Tahoe blog (WordPress REST API, public, free) into data/raw/blog/ as immutable raw files.
One file per category: posts with id, date (site clock), date_gmt, modified_gmt, slug, link, title, content, categories. A manifest records when, what, and counts.
Uses curl: Python's own HTTP client was refused by the host's CDN while curl was served (checked 2026-11-08). Polite: 100 posts a page, one request at a time.
usage: python3 -I scripts/pull_blog.py        -> data/raw/blog/<category>.json, data/raw/blog/manifest.json"""
import os, json, subprocess, hashlib, datetime, time
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data", "raw", "blog"); os.makedirs(OUT, exist_ok=True)
API = "https://blog.palisadestahoe.com/wp-json/wp/v2"
FIELDS = "id,date,date_gmt,modified_gmt,slug,link,title,content,categories,status"
def get(url):
    r = subprocess.run(["curl", "-s", "-m", "90", "-D", "-", url], capture_output=True)   # bytes: headers end at the first blank CRLF line
    head, _, body = r.stdout.partition(b"\r\n\r\n")
    total = next((int(l.split(b":")[1]) for l in head.splitlines() if l.lower().startswith(b"x-wp-total:")), None)
    return json.loads(body.decode("utf-8")), total
cats, _ = get(f"{API}/categories?per_page=100&_fields=id,name,slug,count")
manifest = {"fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "api": API, "categories": {}}
for c in cats:
    if c["count"] == 0: continue
    rows, p, total = [], 1, None
    while True:
        x, t = get(f"{API}/posts?categories={c['id']}&per_page=100&page={p}&orderby=date&order=asc&_fields={FIELDS}")
        total = total or t
        if not isinstance(x, list): raise SystemExit(f"{c['slug']} page {p}: {str(x)[:200]}")
        rows += x
        if len(x) < 100: break
        p += 1; time.sleep(0.5)
    if total is not None and len(rows) != total: raise SystemExit(f"{c['slug']}: got {len(rows)} of {total}")
    path = os.path.join(OUT, f"{c['slug']}.json")
    json.dump(rows, open(path, "w"), ensure_ascii=False)
    manifest["categories"][c["slug"]] = dict(id=c["id"], posts=len(rows), first=rows[0]["date_gmt"] if rows else None, last=rows[-1]["date_gmt"] if rows else None,
                                             sha256=hashlib.sha256(open(path, "rb").read()).hexdigest())
    print(c["slug"], len(rows))
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
