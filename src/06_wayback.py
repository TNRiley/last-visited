#!/usr/bin/env python3
"""Was each cited URL ever captured by the Internet Archive, and was it captured
around the time the Court relied on it?

This is the half of the study that makes the other half honest. Roughly half the
corpus is OCR of printed reporters, and a scanning error ("geodties.com" for
geocities.com) produces a URL that is dead for reasons that have nothing to do
with the web. A Wayback snapshot of the address *as printed* is evidence the
address is real, so:

    archived + dead today  -> genuine rot
    never archived + dead  -> reported separately; could be OCR damage, or a page
                              too obscure ever to be crawled. Either way it is not
                              evidence of rot and is not counted as such.

Two lookups per URL against the /wayback/available endpoint rather than the CDX
API: CDX refuses most requests under any useful concurrency, which silently
turned three lookups in four into nulls when this ran inside 05_check.py.

  near  - closest capture to 1 June of the year the opinion issued
  any   - closest capture to now, which also answers "archived at all"

Resumable: results append to wayback.jsonl.
"""
import json, os, threading, queue, time, collections
import urllib.parse as up
import requests

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SRC, "wayback.jsonl")
API = "https://archive.org/wayback/available"
UA  = "Mozilla/5.0 (compatible; quick-projects link-rot study; +https://github.com/TNRiley)"
WORKERS = 12                                  # each lookup takes ~20s against this endpoint,
                                              # so throughput needs threads, not haste per thread

def load_urls():
    urls = {}
    for fn in ("cap_urls.json", "slip_urls.json"):
        p = os.path.join(SRC, fn)
        if not os.path.exists(p): continue
        for r in json.load(open(p)):
            u = r["url"]
            if u not in urls or r["year"] < urls[u]:
                urls[u] = r["year"]            # earliest citation is the one to date from
    return urls

def look(s, url, timestamp=None):
    params = {"url": url}
    if timestamp: params["timestamp"] = timestamp
    for attempt in range(4):
        try:
            r = s.get(API, params=params, timeout=30)
            if r.status_code in (429, 503):
                time.sleep(5 * (attempt + 1)); continue
            if r.status_code != 200:
                return None
            snap = (r.json().get("archived_snapshots") or {}).get("closest")
            if not snap: return {"found": False}
            return {"found": True, "ts": snap.get("timestamp"), "status": snap.get("status")}
        except Exception:
            time.sleep(3 * (attempt + 1))
    return None

def main():
    urls = load_urls()
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(line)["url"])
            except Exception: pass
    todo = [(u, y) for u, y in urls.items() if u not in done]
    print(f"{len(urls)} urls; {len(done)} done; {len(todo)} to go", flush=True)

    q = queue.Queue()
    for item in todo: q.put(item)
    lock, fh, n = threading.Lock(), open(OUT, "a", encoding="utf-8"), [0]
    t0 = time.time()

    def worker():
        s = requests.Session(); s.headers.update({"User-Agent": UA})
        while True:
            try: url, year = q.get_nowait()
            except queue.Empty: return
            near = look(s, url, "%04d0601" % year)
            any_ = look(s, url)
            with lock:
                fh.write(json.dumps({"url": url, "year": year, "near": near, "any": any_}) + "\n")
                fh.flush(); n[0] += 1
                if n[0] % 50 == 0:
                    print(f"  {n[0]}/{len(todo)}  {n[0]/max(1e-9,time.time()-t0)*60:.0f}/min", flush=True)
            time.sleep(0.2)
            q.task_done()

    ts = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for t in ts: t.start()
    for t in ts: t.join()
    fh.close()

    res = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    ok = [r for r in res if r["any"] is not None]
    print(f"\nlookups returning an answer: {len(ok)}/{len(res)}")
    print("archived at all:", sum(1 for r in ok if r["any"]["found"]))
    print("never archived:", sum(1 for r in ok if not r["any"]["found"]))
    nr = [r for r in res if r["near"] is not None]
    print("captured near the citation date:", sum(1 for r in nr if r["near"]["found"]))

if __name__ == "__main__":
    import warnings; warnings.filterwarnings("ignore")
    main()
