#!/usr/bin/env python3
"""Headline figures for the page, and the verification table REBUILD.md needs."""
import json, os, collections
SRC = os.path.dirname(os.path.abspath(__file__))

cites = json.load(open(os.path.join(SRC, "cap_urls.json"))) + \
        json.load(open(os.path.join(SRC, "slip_urls.json")))
live = {}
for l in open(os.path.join(SRC, "checked.jsonl"), encoding="utf-8"):
    r = json.loads(l); live[r["url"]] = r
# the curl recheck and the perma pass supersede the bulk pass, exactly as 09_payload.py
# merges them -- without this the figures here disagree with the ones on the page
p = os.path.join(SRC, "recheck.jsonl")
if os.path.exists(p):
    for l in open(p, encoding="utf-8"):
        r = json.loads(l); live[r["url"]] = r
wb = {}
p = os.path.join(SRC, "wayback.jsonl")
if os.path.exists(p):
    for l in open(p, encoding="utf-8"):
        r = json.loads(l); wb[r["url"]] = r

# drop URLs left in the jsonl files by an earlier extraction run, as 09_payload.py does,
# so these figures and the page's cannot drift apart
cited = {c["url"] for c in cites}
live = {u: r for u, r in live.items() if u in cited}

DEAD  = {"notfound", "dns", "conn", "timeout", "server"}
AMBIG = {"blocked", "ssl", "other"}

def bucket(state):
    if state == "ok":   return "live"
    if state == "soft": return "soft"
    if state in DEAD:   return "dead"
    return "indeterminate"

print(f"citations {len(cites)}   unique urls {len({c['url'] for c in cites})}")
print(f"opinions citing a url {len({(c['case'], c['date'], c['type']) for c in cites})}")
print(f"cases {len({(c['case'], c['date']) for c in cites})}")
print(f"years {min(c['year'] for c in cites)}-{max(c['year'] for c in cites)}")

states = collections.Counter(live[u]["state"] for u in live)
print("\nraw states:", dict(states.most_common()))
b = collections.Counter(bucket(live[u]["state"]) for u in live)
tot = sum(b.values())
print("\nby bucket (unique urls):")
for k in ("live", "soft", "dead", "indeterminate"):
    print(f"  {k:15s} {b[k]:5d}  {100*b[k]/tot:5.1f}%")
det = b["live"] + b["soft"] + b["dead"]
print(f"\nexcluding indeterminate ({b['indeterminate']} urls the server would not answer for):")
print(f"  still resolves as cited   {b['live']:5d}  {100*b['live']/det:5.1f}%")
print(f"  gone or redirected to root{b['dead']+b['soft']:5d}  {100*(b['dead']+b['soft'])/det:5.1f}%")

print("\nrot by decade of citation (unique url, earliest citation year):")
first = {}
for c in cites:
    if c["url"] not in first or c["year"] < first[c["url"]]:
        first[c["url"]] = c["year"]
era = collections.defaultdict(collections.Counter)
for u, y in first.items():
    if u in live:
        era[(y // 5) * 5][bucket(live[u]["state"])] += 1
for k in sorted(era):
    e = era[k]; n = sum(e.values()); d = e["live"] + e["soft"] + e["dead"]
    print(f"  {k}-{k+4}  n={n:4d}  live {100*e['live']/d:5.1f}%   dead+soft {100*(e['dead']+e['soft'])/d:5.1f}%")

if wb:
    print("\narchive coverage:")
    ok = [r for r in wb.values() if r["any"] is not None]
    arch = sum(1 for r in ok if r["any"]["found"])
    print(f"  ever archived            {arch}/{len(ok)}  {100*arch/len(ok):.1f}%")
    near = [r for r in wb.values() if r["near"] is not None]
    nf = sum(1 for r in near if r["near"]["found"])
    print(f"  captured near citation   {nf}/{len(near)}  {100*nf/len(near):.1f}%")
    deadu = [u for u in live if bucket(live[u]["state"]) in ("dead", "soft")]
    da = [u for u in deadu if u in wb and wb[u]["any"] and wb[u]["any"]["found"]]
    print(f"  of {len(deadu)} dead/soft urls, {len(da)} are in the Wayback Machine "
          f"({100*len(da)/max(1,len(deadu)):.1f}%) -- recoverable")
    nev = [u for u in deadu if u in wb and wb[u]["any"] and not wb[u]["any"]["found"]]
    print(f"  {len(nev)} dead urls were never archived at all "
          f"-- unrecoverable, and the group where OCR damage would hide")

print("\nthe Court's own citation practice:")
vis = sum(1 for c in cites if c.get("visited"))
print(f"  citations carrying a visitation date  {vis}/{len(cites)}")
print(f"  citations noting a copy in the Clerk's case file  {sum(1 for c in cites if c.get('clerk'))}")
perma = [c for c in cites if c["host"] == "perma.cc"]
print(f"  perma.cc citations {len(perma)}; terms: "
      f"{dict(collections.Counter(c['vol'] for c in perma))}")
byyear_perma = collections.Counter(c["year"] for c in perma)
print(f"  perma.cc by year: {dict(sorted(byyear_perma.items()))}")

print("\ntop hosts:", collections.Counter(c["host"] for c in cites).most_common(10))
print("\nby opinion type:", collections.Counter(c["type"] for c in cites).most_common())
gov = sum(1 for c in cites if c["host"].endswith(".gov"))
print(f"\n.gov citations {gov}/{len(cites)} ({100*gov/len(cites):.1f}%)")
govlive = [c for c in cites if c["host"].endswith(".gov") and c["url"] in live]
gd = sum(1 for c in govlive if bucket(live[c["url"]]["state"]) == "dead")
print(f"  of .gov citations with a result, {100*gd/max(1,len(govlive)):.1f}% dead")
