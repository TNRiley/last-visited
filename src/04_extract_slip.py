#!/usr/bin/env python3
"""URLs from born-digital slip opinion PDFs (OT2020-OT2025).

pdftotext runs with -layout deliberately. Its default mode treats a hyphen at a
line break as hyphenation and deletes it, so a URL printed as "foo-/nbar" comes
back as "foobar". The Bluebook does not hyphenate URLs, so a trailing hyphen is
always part of the address and must survive.

These are not OCR, so the text is exact -- which makes this cohort the clean
control for the OCR noise in the CAP volumes. Long URLs still break across lines,
but here the break is a real newline and is joined back without the guesswork
the scanned volumes need.

Case name, date and docket come from each term's index table rather than the PDF.
Which opinion a URL sits in is inferred from the most recent opinion header above
it ("JUSTICE KAGAN, dissenting"), mirroring CAP's majority/concurrence/dissent.
"""
import json, os, re, subprocess, sys, collections, datetime

SRC  = os.path.dirname(os.path.abspath(__file__))
SLIP = os.path.join(SRC, "raw", "slip")
TERMS = ["20", "21", "22", "23", "24", "25"]

BODY = r"[^\s<>\"'()\[\]{}|\^`]"
START_RE = re.compile(r"(?i)\b(?:https?://|www\.)")
BREAKABLE = tuple("./-=?&_~#%")
CONT_RE  = re.compile(r"^[a-z0-9][a-z0-9\-]*(?:\.[a-z]{2,}|/)")
HEAD_RE  = re.compile(r"(?m)^\s*(?:(?:CHIEF\s+)?JUSTICE\s+([A-Z]+)[^\n]*?"
                      r"(delivered the opinion|concurring in part and dissenting|dissenting|concurring)"
                      r"|PER\s+CURIAM)")
VISIT_RE = re.compile(r"(?i)\(\s*last\s+visited\s+([A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})\s*\)")
BLANKET_RE = re.compile(r"(?i)all\s+internet\s+materials\s+(?:were\s+)?(?:as\s+|last\s+)?visited\s+"
                        r"([A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})")
TLDS = set("""gov edu org com net int mil us info biz co io me tv cc ly gl ag ms
uk ca au de fr jp nl se no fi dk it es ch at be ie nz za br mx ar cl pe ru cn in
kr hk sg tw il tr pl cz gr pt hu ro bg hr si sk ee lv lt lu is mt cy""".split())

# A URL broken after a hyphen. The Bluebook does not hyphenate URLs, so a trailing
# hyphen belongs to the address -- perma.cc codes ("2AQU-3PME") break exactly there,
# and the continuation is a bare alphanumeric run with no dot or slash for CONT_RE to
# recognise. Requiring an uppercase letter or a digit keeps ordinary prose out
# ("... /a- and then" must not become "/a-and").
CODE_RE = re.compile(r"^[A-Za-z0-9]{2,8}(?:-[A-Za-z0-9]{2,8})?$")

def code_after_hyphen(tok):
    """Second half of an opaque code split at its own hyphen: perma.cc/2AQU-3PME
    broken as "2AQU-" + "3PME". Either half may be all letters, so only the shape
    and a capital are required. A URL ending in a hyphen is already strong evidence
    of a break, because the Bluebook does not hyphenate URLs."""
    t = strip_tail(tok)
    return bool(CODE_RE.match(t)) and bool(re.search(r"[A-Z]", t))

def code_after_slash(tok):
    """Whole code pushed onto the next line: perma.cc/ + "2AQU-3PME". A trailing
    slash is weak evidence on its own, so this also demands a digit -- otherwise
    "see http://x.gov/ See also" would become ".../See"."""
    t = strip_tail(tok)
    return code_after_hyphen(tok) and bool(re.search(r"\d", t))

def host_of(u):
    m = re.match(r"https?://([^/:]+)", u, re.I)
    return m.group(1).lower().strip(".") if m else ""
def good_host(u):
    h = host_of(u)
    if not (h and "." in h and 4 <= len(h) <= 100 and re.match(r"^[a-z0-9.\-]+$", h)):
        return False
    t = h.rsplit(".", 1)[-1]
    return t in TLDS or bool(re.match(r"^[a-z]{2}$", t))
def strip_tail(u):
    while u and u[-1] in ".,;:!?'\u2019\u201d": u = u[:-1]
    while u.endswith(")") and u.count("(") < u.count(")"): u = u[:-1]
    return u.rstrip(".,;:")

def read_url(text, i):
    m = re.compile(BODY + "+").match(text, i)
    if not m: return None, i
    url, end = m.group(0), m.end()
    for _ in range(3):
        core = strip_tail(url)
        nxt = re.compile(r"[ \t\r\n]+(" + BODY + r"+)").match(text, end)
        if not nxt: break
        tok = nxt.group(1)
        probe = ("http://" + core) if core.lower().startswith("www.") else core
        joinable = url.endswith(BREAKABLE) or core.endswith(BREAKABLE) or not good_host(probe)
        continues = (CONT_RE.match(tok.lower())
                     or (core.endswith("-") and code_after_hyphen(tok))
                     or (core.endswith("/") and code_after_slash(tok)))
        if joinable and continues:
            url, end = core + tok, nxt.end()
        else: break
    url = strip_tail(url)
    if url.lower().startswith("www."): url = "http://" + url
    m2 = re.match(r"(?i)(https?://)([^/]+)(.*)$", url)
    if m2: url = m2.group(1).lower() + m2.group(2).lower() + m2.group(3)
    return url, end

def index_meta(term):
    p = os.path.join(SLIP, f"index_{term}.html")
    out = {}
    if not os.path.exists(p): return out
    html = open(p, encoding="utf-8", errors="replace").read()
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        pdf = re.search(rf"/opinions/{term}pdf/([\w.\-]+\.pdf)", tr)
        if not pdf: continue
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in
                 re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) < 6: continue
        out[pdf.group(1)] = {"date": cells[1], "docket": cells[2],
                             "case": re.sub(r"\s+", " ", cells[3]), "cite": cells[5]}
    return out

def opinion_kind(text, pos):
    kind, who = "majority", ""
    for m in HEAD_RE.finditer(text, 0, pos):
        g2 = (m.group(2) or "").lower()
        who = m.group(1) or ""
        if "delivered" in g2: kind = "majority"
        elif "concurring in part" in g2: kind = "concurring-in-part-and-dissenting-in-part"
        elif "dissent" in g2: kind = "dissent"
        elif "concur" in g2: kind = "concurrence"
        else: kind = "majority"
    return kind, who.title()

def main():
    rows, npdf, nfail = [], 0, 0
    for term in TERMS:
        meta = index_meta(term)
        d = os.path.join(SLIP, term)
        if not os.path.isdir(d): continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".pdf"): continue
            npdf += 1
            try:
                txt = subprocess.run(["pdftotext", "-q", "-layout", os.path.join(d, fn), "-"],
                                     capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
            except Exception:
                nfail += 1; continue
            if not txt.strip(): nfail += 1; continue
            m = meta.get(fn, {})
            date = m.get("date", "")
            try:
                dt = datetime.datetime.strptime(date, "%m/%d/%y").date()
                iso, year = dt.isoformat(), dt.year
            except Exception:
                iso, year = "", 2000 + int(term)
            blanket = BLANKET_RE.search(txt)
            pos, seen = 0, set()
            while True:
                s = START_RE.search(txt, pos)
                if not s: break
                url, pos = read_url(txt, s.start())
                if not url or not good_host(url): continue
                kind, who = opinion_kind(txt, s.start())
                lv = VISIT_RE.search(txt, s.start(), s.start() + 160)
                k = (url, kind)
                if k in seen: continue
                seen.add(k)
                rows.append({
                    "url": url, "host": host_of(url), "year": year, "date": iso,
                    "case": m.get("case", fn), "cite": m.get("cite", ""),
                    "type": kind, "author": who, "src": "slip", "vol": term,
                    "visited": re.sub(r"\s+", " ", lv.group(1)) if lv
                               else (re.sub(r"\s+", " ", blanket.group(1)) if blanket else None),
                    "clerk": False,
                })
        print(f"  term {term}: {len(rows)} urls so far", flush=True)

    json.dump(rows, open(os.path.join(SRC, "slip_urls.json"), "w"), separators=(",", ":"))
    print(f"\npdfs {npdf} (text-extraction failures {nfail})")
    print(f"citations {len(rows)}  unique urls {len({r['url'] for r in rows})}")
    print("by year:", dict(sorted(collections.Counter(r['year'] for r in rows).items())))
    print("with visit date:", sum(1 for r in rows if r['visited']))
    print("top hosts:", collections.Counter(r['host'] for r in rows).most_common(8))

if __name__ == "__main__":
    main()
