#!/usr/bin/env python3
"""A slow, serial pass over the perma.cc links alone.

perma.cc is the headline finding of this study -- the Court adopted it as a
citation convention in OT2025 -- so its links get measured carefully rather than
swept up in the bulk pass. It answers 403 to automated clients intermittently:
the same link can return 200 and then 403 minutes later, and a handful return 403
every time. Hammering it 60 times in 90 seconds, as the bulk recheck does, turns
most of them into false negatives.

So: one request at a time, five seconds apart, three attempts per link, and the
best answer wins (a 200 anywhere beats a 403, because a 403 from a rate limiter is
not evidence that an archive is missing). Results append to recheck.jsonl, which
later readers key by URL so these supersede the bulk pass.

A 403 that survives all three attempts is still recorded as "blocked", which the
page counts as indeterminate -- never as dead.
"""
import json, os, subprocess, time, collections

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SRC, "recheck.jsonl")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
RANK = {"ok": 0, "soft": 1, "notfound": 2, "blocked": 3, "other": 4,
        "timeout": 5, "conn": 6, "ssl": 7, "server": 8, "dns": 9}

def fetch(url):
    cmd = ["curl", "-s", "-o", os.devnull, "-L", "--max-time", "30",
           "--connect-timeout", "12", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "-w", "%{http_code} %{url_effective}", url]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=45)
    except subprocess.TimeoutExpired:
        return "timeout", 0, ""
    if p.returncode != 0:
        return {6: "dns", 7: "conn", 28: "timeout"}.get(p.returncode, "conn"), 0, ""
    parts = p.stdout.decode("utf-8", "replace").strip().split(" ", 1)
    try: code = int(parts[0])
    except Exception: return "conn", 0, ""
    final = parts[1] if len(parts) > 1 else url
    if 200 <= code < 300:       return "ok", code, final
    if code in (404, 410):      return "notfound", code, final
    if code in (401, 403, 429): return "blocked", code, final
    if 500 <= code < 600:       return "server", code, final
    return "other", code, final

def main():
    urls = set()
    for fn in ("cap_urls.json", "slip_urls.json"):
        p = os.path.join(SRC, fn)
        if os.path.exists(p):
            for r in json.load(open(p)):
                if r["host"] == "perma.cc":
                    urls.add(r["url"])
    urls = sorted(urls)
    print(f"{len(urls)} perma.cc links, three attempts each, 5s apart", flush=True)

    out = []
    for i, u in enumerate(urls, 1):
        best = None
        for attempt in range(3):
            st, code, final = fetch(u)
            if best is None or RANK[st] < RANK[best[0]]:
                best = (st, code, final)
            if st == "ok":
                break                      # nothing beats a 200; stop asking
            time.sleep(5)
        out.append({"url": u, "state": best[0], "code": best[1], "final": best[2]})
        if i % 10 == 0:
            print(f"  {i}/{len(urls)}", flush=True)
        time.sleep(5)

    with open(OUT, "a", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    print("\nperma states:", collections.Counter(r["state"] for r in out).most_common())
    live = sum(1 for r in out if r["state"] == "ok")
    ans  = sum(1 for r in out if r["state"] in ("ok", "soft", "notfound"))
    print(f"{live} resolve; {ans} gave a definite answer; "
          f"{len(out) - ans} still refused an automated client")

if __name__ == "__main__":
    main()
