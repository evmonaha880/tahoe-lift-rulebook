"""Merge two independent model readings of the operations blog into a season and lift calendar, and compare it with rules/season_windows.json.
Inputs: reader files out_A_<n>.json and out_B_<n>.json (events with kind, side, lift, date, status, quote, post_id) in the directory given on the command line.
A fact is AGREED when both readers give the same (kind, side, lift, date); otherwise it is single-reader and flagged. Every row keeps its post id and quote (<= 25 words).
DERIVED BY MODEL FROM TEXT: stored in rules/season_calendar.json, never merged into observed tweet data. Nothing here changes season_windows.json; disagreements are listed for a human.
usage: python3 -I scripts/build_season_calendar.py <reader_dir>   -> rules/season_calendar.json, data/derived/season_calendar_review.csv"""
import os, sys, json, glob, csv, re, collections, datetime, html
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
src = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: python3 -I scripts/build_season_calendar.py <reader_dir>")
def winter(d):
    y, m = int(d[:4]), int(d[5:7]); s = y if m >= 8 else y - 1; return f"{s}-{str(s + 1)[2:]}"
def norm_lift(x): return re.sub(r"[^a-z0-9 ]", "", (x or "").lower()).strip() or None
def squash(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).lower()
    t = t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2013", "-").replace("\u2014", "-").replace("\u00a0", " ")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()
POSTS = {r["id"]: (squash(r["content"]["rendered"] + " " + r["title"]["rendered"]), r["date"][:10]) for r in json.load(open(os.path.join(ROOT, "data", "raw", "blog", "operations.json")))}
def check(e):
    """quote_ok: the quote (first 8 words, punctuation ignored) occurs in the post text; post_ok: the post id exists and its date matches post_date"""
    text, pdate = POSTS.get(e.get("post_id"), (None, None))
    q = " ".join(squash(e.get("quote") or "").split()[:8])
    return int(bool(text and q and q in text)), int(text is not None and pdate == e.get("post_date"))
for reader in ("A", "B"):                                        # fail early and loudly, before anything is written
    files = glob.glob(os.path.join(src, f"out_{reader}_*.json"))
    if len(files) != 6: raise SystemExit(f"expected 6 reader-{reader} files (out_{reader}_1..6.json) in {src}, found {len(files)}; nothing written")
ev = collections.defaultdict(dict)   # key -> reader -> event
n_read = {}; skipped = []
for reader in ("A", "B"):
    for path in sorted(glob.glob(os.path.join(src, f"out_{reader}_*.json"))):
        d = json.load(open(path)); n_read[(reader, path)] = len(d["events"])
        for e in d["events"]:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", e.get("date") or ""): skipped.append((reader, e.get("kind"), e.get("date"), e.get("post_id"))); continue   # partial or missing dates are not facts we can place
            k = (e["kind"], e.get("side") or "unknown", norm_lift(e.get("lift")), e["date"])
            ev[k].setdefault(reader, e)
rows = []
for k, by in sorted(ev.items(), key=lambda kv: (kv[0][3], kv[0][0])):
    e = by.get("A") or by.get("B")
    quote = " ".join((e.get("quote") or "").split()[:25]); qok = {r_: check(x) for r_, x in by.items()}
    rows.append(dict(winter=winter(k[3]), kind=k[0], side=k[1], lift=e.get("lift"), date=k[3], date_end=e.get("date_end"), status=e.get("status"),
                     cause=e.get("cause"), agreed=int(len(by) == 2), readers="".join(sorted(by)), basis=e.get("basis"), confidence=e.get("confidence"),
                     post_id=e.get("post_id"), post_date=e.get("post_date"), quote_ok=min(v[0] for v in qok.values()), post_ok=min(v[1] for v in qok.values()), quote=quote))
if not rows: raise SystemExit("no events with a full date; nothing written")
def atomic(path, write):                                          # write to a temp file, then rename, so a crash never leaves a half-written file
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as fh: write(fh)
    os.replace(tmp, path)
atomic(os.path.join(ROOT, "rules", "season_calendar.json"), lambda fh: json.dump(dict(_about="Season and lift calendar read from the Palisades Tahoe operations blog by two independent model readers (A: Sonnet, B: Haiku). DERIVED BY MODEL, not observed. agreed=1 means both readers gave the same kind, side, lift and date. See docs/DECISIONS.md decision 61.",
               reader_event_counts={f"{r}:{os.path.basename(p)}": n for (r, p), n in n_read.items()}, events=rows), fh, indent=1))
def _csv(fh): w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
atomic(os.path.join(ROOT, "data", "derived", "season_calendar_review.csv"), _csv)
tot = len(rows); ag = sum(r["agreed"] for r in rows)
print(f"skipped (no full date): {len(skipped)}"); print(f"{tot} distinct facts; both readers {ag} ({ag / tot:.0%}); A only {sum(r['readers'] == 'A' for r in rows)}; B only {sum(r['readers'] == 'B' for r in rows)}")
by_kind = collections.Counter((r["kind"], r["agreed"]) for r in rows)
print(f"quote found in its post: {sum(r['quote_ok'] for r in rows)} of {tot}; post id and date match: {sum(r['post_ok'] for r in rows)} of {tot}")
for kd in sorted({r["kind"] for r in rows}): print(f"  {kd:18} both {by_kind[(kd, 1)]:4}  single {by_kind[(kd, 0)]:4}")
