#!/usr/bin/env python3
"""Does each cited URL still resolve? (Archival coverage is 06_wayback.py.)

The two checks were one script until the Internet Archive's CDX endpoint started
refusing three lookups in four under concurrency, which would have quietly turned
the archival half of the study into noise. They are separate passes now, each
resumable on its own, so neither can spoil the other.

What a result means here:

  ok        2xx, and the response still comes from the path that was cited
  soft      2xx, but the server redirected a cited document to the site root -
            the domain survived, the page did not. Counting this as "alive" is
            the standard way link-rot studies overstate survival, so it is kept
            apart.
  notfound  404 or 410 - the honest dead
  blocked   401/403/429 - indeterminate, not dead. Bot walls, paywalls and rate
            limits all land here and must not be counted either way.
  dns       the host no longer resolves at all
  conn / timeout / ssl / server / other - reachability failures, recorded
            separately because they are weaker evidence than a 404

Resumable: results append to checked.jsonl; re-runs skip URLs already present.
"""
import json, os, threading, queue, time, collections
import urllib.parse as up
import requests
from requests.adapters import HTTPAdapter

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SRC, "checked.jsonl")
UA  = "Mozilla/5.0 (compatible; quick-projects link-rot study; +https://github.com/TNRiley)"
TIMEOUT, WORKERS = 15, 12

def load_urls():
    urls = {}
    for fn in ("cap_urls.json", "slip_urls.json"):
        p = os.path.join(SRC, fn)
        if not os.path.exists(p): continue
        for r in json.load(open(p)):
            urls.setdefault(r["url"], r["year"])
    return urls

def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*",
                      "Accept-Language": "en-US,en;q=0.9"})
    s.mount("http://",  HTTPAdapter(max_retries=0, pool_maxsize=4))
    s.mount("https://", HTTPAdapter(max_retries=0, pool_maxsize=4))
    return s

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

def live(s, url):
    for method in ("head", "get"):
        try:
            r = s.request(method, url, timeout=TIMEOUT, allow_redirects=True,
                          stream=(method == "get"))
            if method == "head" and r.status_code in (403, 405, 501):
                r.close(); continue            # some hosts refuse HEAD; try GET
            out = classify(url, r); r.close(); return out
        except requests.exceptions.SSLError:
            try:                               # a bad certificate is not a dead page
                r = s.get(url, timeout=TIMEOUT, allow_redirects=True, verify=False, stream=True)
                code, final = r.status_code, r.url; r.close()
                return "ssl", code, final
            except Exception:
                return "conn", 0, ""
        except requests.exceptions.ConnectionError as e:
            m = str(e).lower()
            dns = any(k in m for k in ("name or service", "nodename", "getaddrinfo",
                                       "name resolution", "no address associated",
                                       "failed to resolve"))
            return ("dns" if dns else "conn"), 0, ""
        except requests.exceptions.Timeout:
            return "timeout", 0, ""
        except Exception:
            return "conn", 0, ""
    return "conn", 0, ""

def main():
    urls = load_urls()
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(line)["url"])
            except Exception: pass
    todo = [u for u in urls if u not in done]
    print(f"{len(urls)} unique urls; {len(done)} done; {len(todo)} to go", flush=True)

    q = queue.Queue()
    for u in todo: q.put(u)
    lock, fh, n = threading.Lock(), open(OUT, "a", encoding="utf-8"), [0]
    host_last, host_lock = {}, threading.Lock()
    t0 = time.time()

    def worker():
        s = session()
        while True:
            try: u = q.get_nowait()
            except queue.Empty: return
            host = up.urlsplit(u).netloc.lower()
            with host_lock:                    # never more than one hit per host per second
                wait = max(0.0, 1.0 - (time.time() - host_last.get(host, 0)))
                host_last[host] = time.time() + wait
            if wait: time.sleep(wait)
            state, code, final = live(s, u)
            with lock:
                fh.write(json.dumps({"url": u, "state": state, "code": code, "final": final}) + "\n")
                fh.flush(); n[0] += 1
                if n[0] % 50 == 0:
                    rate = n[0] / max(1e-9, time.time() - t0)
                    print(f"  {n[0]}/{len(todo)}  {rate*60:.0f}/min", flush=True)
            q.task_done()

    ts = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for t in ts: t.start()
    for t in ts: t.join()
    fh.close()

    res = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    print("\nstates:", collections.Counter(r["state"] for r in res).most_common())

if __name__ == "__main__":
    import warnings; warnings.filterwarnings("ignore")
    main()
