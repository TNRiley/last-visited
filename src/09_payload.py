#!/usr/bin/env python3
"""Join citations, liveness, the browser recheck and Wayback into payload.json."""
import json, os, collections, datetime
SRC = os.path.dirname(os.path.abspath(__file__))

def load(fn):
    p = os.path.join(SRC, fn)
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []

cites = json.load(open(os.path.join(SRC, "cap_urls.json"))) + \
        json.load(open(os.path.join(SRC, "slip_urls.json")))
first = {r["url"]: r for r in load("checked.jsonl")}
again = {r["url"]: r for r in load("recheck.jsonl")}
wb    = {r["url"]: r for r in load("wayback.jsonl")}

# the browser pass supersedes the study-client pass wherever it ran
final, changed, rescued = {}, 0, 0
for u, r in first.items():
    if u in again:
        if again[u]["state"] != r["state"]:
            changed += 1
            if again[u]["state"] == "ok" and r["state"] != "ok":
                rescued += 1
        final[u] = dict(again[u], pass_="browser")
    else:
        final[u] = dict(r, pass_="study")

DEAD  = {"notfound", "dns", "conn", "timeout", "server"}
def bucket(s):
    if s == "ok":   return "live"
    if s == "soft": return "soft"
    if s in DEAD:   return "dead"
    return "indet"

# Each URL is dated by its earliest citation: a URL re-cited years later has still
# been exposed to the web for as long as its first appearance.
firstyear = {}
for c in cites:
    u = c["url"]
    if u not in firstyear or c["year"] < firstyear[u]:
        firstyear[u] = c["year"]

# checked.jsonl accumulates across runs and the extractors have been re-run since,
# so it can hold URLs that no longer appear in any citation. Keep only the current set.
stale = [u for u in final if u not in firstyear]
for u in stale:
    del final[u]
BK = {u: bucket(r["state"]) for u, r in final.items()}
if stale:
    print(f"ignored {len(stale)} stale urls left over from an earlier extraction")

years = sorted({c["year"] for c in cites})
byYear = []
for y in years:
    us = [u for u, fy in firstyear.items() if fy == y and u in BK]
    cnt = collections.Counter(BK[u] for u in us)
    byYear.append({"y": y, "n": len(us), "live": cnt["live"], "soft": cnt["soft"],
                   "dead": cnt["dead"], "indet": cnt["indet"],
                   "cites": sum(1 for c in cites if c["year"] == y)})

def archived(u):
    r = wb.get(u)
    return bool(r and r["any"] and r["any"]["found"])
def archivedNear(u):
    r = wb.get(u)
    return bool(r and r["near"] and r["near"]["found"])

deadish = [u for u in BK if BK[u] in ("dead", "soft")]
archive = {
    "urls": len(BK),
    "archived": sum(1 for u in BK if archived(u)),
    "near": sum(1 for u in BK if archivedNear(u)),
    "deadTotal": len(deadish),
    "deadArchived": sum(1 for u in deadish if archived(u)),
    "deadNever": sum(1 for u in deadish if not archived(u)),
    "liveArchived": sum(1 for u in BK if BK[u] == "live" and archived(u)),
}

# Rot measured only on URLs the Internet Archive can vouch for. Half this corpus is
# OCR of printed reporters, and a mis-scanned character yields an address that was
# never real; restricting to archived URLs removes most of that noise.
conf = [u for u in BK if archived(u) and BK[u] != "indet"]
confirmed = {
    "n": len(conf),
    "live": sum(1 for u in conf if BK[u] == "live"),
    "dead": sum(1 for u in conf if BK[u] in ("dead", "soft")),
}
confYear = []
for y in years:
    us = [u for u in conf if firstyear[u] == y]
    if not us: continue
    confYear.append({"y": y, "n": len(us),
                     "dead": sum(1 for u in us if BK[u] in ("dead", "soft"))})

perma_cites = [c for c in cites if c["host"] == "perma.cc"]
perma_urls  = {c["url"] for c in perma_cites}
# perma.cc refuses automated clients intermittently (see 08b_perma.py), so its
# links are reported against the ones that gave a definite answer, not against all.
perma_bk = collections.Counter(BK[u] for u in perma_urls if u in BK)
perma = {
    "cites": len(perma_cites), "urls": len(perma_urls),
    "byYear": dict(sorted(collections.Counter(c["year"] for c in perma_cites).items())),
    "live": perma_bk["live"],
    "dead": perma_bk["dead"] + perma_bk["soft"],
    "indet": perma_bk["indet"],
    "answered": perma_bk["live"] + perma_bk["dead"] + perma_bk["soft"],
    "checked": sum(1 for u in perma_urls if u in BK),
}

hosts = collections.Counter(c["host"] for c in cites)
hostrows = []
for h, n in hosts.most_common(40):
    us = {c["url"] for c in cites if c["host"] == h and c["url"] in BK}
    det = [u for u in us if BK[u] != "indet"]
    hostrows.append({"h": h, "n": n, "urls": len(us),
                     "dead": sum(1 for u in det if BK[u] in ("dead", "soft")),
                     "det": len(det)})

practice = []
for y in years:
    cy = [c for c in cites if c["year"] == y]
    practice.append({"y": y, "n": len(cy),
                     "visited": sum(1 for c in cy if c.get("visited")),
                     "clerk": sum(1 for c in cy if c.get("clerk")),
                     "perma": sum(1 for c in cy if c["host"] == "perma.cc")})

STATE_I = ["ok", "soft", "notfound", "dns", "conn", "timeout", "server", "blocked", "ssl", "other"]
rows = []
for c in sorted(cites, key=lambda c: (c["date"], c["case"])):
    u = c["url"]; f = final.get(u)
    rows.append([
        u, c["year"], c["case"][:80], c["cite"], c["type"][:4], c["author"][:22],
        STATE_I.index(f["state"]) if f else -1,
        (2 if archivedNear(u) else 1) if archived(u) else 0,
        c["src"], 1 if c.get("visited") else 0,
    ])

gov = [c for c in cites if c["host"].endswith(".gov")]
govu = {c["url"] for c in gov if c["url"] in BK and BK[c["url"]] != "indet"}

payload = {
    "generated": datetime.date.today().isoformat(),
    "corpus": {
        "citations": len(cites), "urls": len(BK),
        "opinions": len({(c["case"], c["date"], c["type"]) for c in cites}),
        "cases": len({(c["case"], c["date"]) for c in cites}),
        "y0": min(years), "y1": max(years),
        "capCases": 196474,
        "slipPdfs": 380,
    },
    "states": dict(collections.Counter(final[u]["state"] for u in final)),
    "buckets": dict(collections.Counter(BK.values())),
    "byYear": byYear, "archive": archive, "confirmed": confirmed, "confYear": confYear,
    "perma": perma, "hosts": hostrows, "practice": practice,
    "recheck": {"retried": len(again), "changed": changed, "rescued": rescued},
    "gov": {"cites": len(gov), "urls": len(govu),
            "dead": sum(1 for u in govu if BK[u] in ("dead", "soft"))},
    "stateIndex": STATE_I,
    "rows": rows,
}
out = os.path.join(SRC, "payload.json")
json.dump(payload, open(out, "w"), separators=(",", ":"))
print("payload %.2f MB   %d citation rows" % (os.path.getsize(out) / 1e6, len(rows)))
b = payload["buckets"]; det = b["live"] + b["soft"] + b["dead"]
print(f"live {b['live']}  soft {b['soft']}  dead {b['dead']}  indeterminate {b['indet']}")
print(f"of {det} determinate: {100*b['live']/det:.1f}% still resolve")
print(f"confirmed-real subset: {confirmed['n']} urls, {100*confirmed['dead']/confirmed['n']:.1f}% dead")
print(f"perma: {perma['cites']} citations; {perma['live']}/{perma['answered']} answering urls live, {perma['indet']} refused")
print(f"recheck: {changed} verdicts changed, {rescued} rescued")
