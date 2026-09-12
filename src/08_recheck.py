#!/usr/bin/env python3
"""Second pass, through curl, over the URLs that answered ambiguously.

Why this exists: perma.cc -- the Court's own archiving service, and the most-cited
host in the current term -- returned 403 to every one of its 60-odd links on the
first pass. Reporting those as "blocked" would have buried the most interesting
finding in the corpus under an artefact of the measuring instrument.

Changing the User-Agent does not fix it. perma.cc returns 403 to python-requests
and 200 to curl with byte-identical headers, so the block is on the TLS/HTTP
client fingerprint rather than on the string. Hence curl, not a header tweak.

Only states that are genuinely ambiguous are retried: blocked (401/403/429), ssl,
other, timeout and conn. A 404 is a 404 regardless of client and is not retried;
neither is a host that does not resolve.

Results go to recheck.jsonl. 09_payload.py prefers a recheck result where one
exists and records which pass produced it, so the page can say how many verdicts
changed.
"""
import json, os, subprocess, threading, queue, time, collections
import urllib.parse as up

SRC = os.path.dirname(os.path.abspath(__file__))
IN  = os.path.join(SRC, "checked.jsonl")
OUT = os.path.join(SRC, "recheck.jsonl")
RETRY = {"blocked", "ssl", "other", "timeout", "conn"}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
TIMEOUT, WORKERS = 25, 6

def path_of(u):
    try: return up.urlsplit(u).path.rstrip("/").lower()
    except Exception: return ""

def classify(cited, resp):
    code, final = resp.status_code, resp.url
    if 200 <= code < 300:
        cp, fp = path_of(cited), path_of(final)
        if cp and len(cp) > 1 and fp in ("", "/"):
            return "soft", code, final
        return "ok", code, final
    if code in (404, 410):      return "notfound", code, final
    if code in (401, 403, 429): return "blocked", code, final
    if 500 <= code < 600:       return "server", code, final
    return "other", code, final

CURL_ERR = {6: "dns", 7: "conn", 28: "timeout", 35: "ssl", 51: "ssl", 60: "ssl", ",": "conn"}

def live(url):
    """Fetch with curl and report (state, code, final url)."""
    cmd = ["curl", "-s", "-o", os.devnull, "-L", "--max-time", str(TIMEOUT),
           "--connect-timeout", "12", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "-w", "%{http_code} %{url_effective}", url]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT + 15)
    except subprocess.TimeoutExpired:
        return "timeout", 0, ""
    if p.returncode != 0:
        return CURL_ERR.get(p.returncode, "conn"), 0, ""
    out = p.stdout.decode("utf-8", "replace").strip().split(" ", 1)
    try: code = int(out[0])
    except Exception: return "conn", 0, ""
    final = out[1] if len(out) > 1 else url
    if 200 <= code < 300:
        cp, fp = path_of(url), path_of(final)
        if cp and len(cp) > 1 and fp in ("", "/"):
            return "soft", code, final
        return "ok", code, final
    if code in (404, 410):      return "notfound", code, final
    if code in (401, 403, 429): return "blocked", code, final
    if code == 0:               return "conn", 0, ""
    if 500 <= code < 600:       return "server", code, final
    return "other", code, final

def main():
    first = {}
    for l in open(IN, encoding="utf-8"):
        r = json.loads(l); first[r["url"]] = r
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(l)["url"])
            except Exception: pass
    todo = [u for u, r in first.items() if r["state"] in RETRY and u not in done]
    print(f"{len(todo)} ambiguous urls to retry through curl", flush=True)

    q = queue.Queue()
    for u in todo: q.put(u)
    lock, fh, n = threading.Lock(), open(OUT, "a", encoding="utf-8"), [0]
    host_last, host_lock = {}, threading.Lock()

    def worker():
        while True:
            try: u = q.get_nowait()
            except queue.Empty: return
            host = up.urlsplit(u).netloc.lower()
            with host_lock:                     # perma.cc alone accounts for ~60 urls
                wait = max(0.0, 1.5 - (time.time() - host_last.get(host, 0)))
                host_last[host] = time.time() + wait
            if wait: time.sleep(wait)
            state, code, final = live(u)
            with lock:
                fh.write(json.dumps({"url": u, "state": state, "code": code, "final": final}) + "\n")
                fh.flush(); n[0] += 1
                if n[0] % 25 == 0: print(f"  {n[0]}/{len(todo)}", flush=True)
            q.task_done()

    ts = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for t in ts: t.start()
    for t in ts: t.join()
    fh.close()

    res = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    print("\nrecheck states:", collections.Counter(r["state"] for r in res).most_common())
    changed = sum(1 for r in res if r["state"] != first[r["url"]]["state"])
    print(f"changed verdict: {changed}/{len(res)}")
    rescued = sum(1 for r in res if r["state"] == "ok" and first[r["url"]]["state"] != "ok")
    print(f"now resolving that previously did not: {rescued}")

if __name__ == "__main__":
    import warnings; warnings.filterwarnings("ignore")
    main()
