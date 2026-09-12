#!/usr/bin/env python3
"""Pull every URL out of the CAP SCOTUS volumes.

CAP text is OCR of the printed reporters, and print breaks long URLs across lines.
The break survives OCR as a plain space, so the raw text contains

    http://www.txdmv. gov/motorists/license-plates

and a whitespace-terminated regex silently truncates it to "http://www.txdmv".
repair() rejoins across such a break, but only when the fragment ends on a
character a typesetter would break after (. / - = ? & _ ~ # %) and the next token
itself looks like a host or path continuation - so "see http://x.gov/ and then"
does not become "http://x.gov/and".

The Court does not use a per-URL "last visited" parenthetical. It puts one blanket
note in the opinion: "all Internet materials as visited June 16, 2015, and
available in Clerk of Court's case file." That is captured per opinion instead.
"""
import json, os, re, sys, zipfile, collections

SRC = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(SRC, "raw", "cap")

START_RE = re.compile(r"(?i)\b(?:https?://|www\.)")
BODY = r"[^\s<>\"'()\[\]{}|\^`]"
BREAKABLE = tuple("./-=?&_~#%")
CONT_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*(?:\.[a-z]{2,}|/)")   # host or path continuation
VISIT_RE = re.compile(r"""(?xi)
    (?:all\s+)?internet\s+(?:materials|sources)\s+
    (?:as\s+|last\s+)?(?:visited|viewed)\s+
    ([A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})
    | \(\s*last\s+visited\s+([A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})\s*\)
""")
CLERK_RE = re.compile(r"(?i)available\s+in\s+Clerk\s+of\s+Court'?s?\s+case\s+file")

def strip_tail(u):
    while u and u[-1] in ".,;:!?'\u2019\u201d\u2018\u201c":
        u = u[:-1]
    while u.endswith(")") and u.count("(") < u.count(")"):
        u = u[:-1]
    return u.rstrip(".,;:")

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

# A real TLD list matters here: "www.txdmv" (a URL broken after "txdmv.") otherwise
# passes a naive /\.[a-z]{2,}$/ test, and the truncation survives as a dead link.
TLDS = set("""gov edu org com net int mil us info biz co io me tv cc ly gl ag ms
uk ca au de fr jp nl se no fi dk it es ch at be ie nz za br mx ar cl pe ru cn in
kr hk sg tw il tr pl cz gr pt hu ro bg hr si sk ee lv lt lu is mt cy""".split())
STATE_TLD = re.compile(r"^[a-z]{2}$")

def good_host(u):
    h = host_of(u)
    if not (h and "." in h and 4 <= len(h) <= 100 and re.match(r"^[a-z0-9.\-]+$", h)):
        return False
    tld = h.rsplit(".", 1)[-1]
    return tld in TLDS or bool(STATE_TLD.match(tld))

def repair(text, i):
    """Read one URL starting at i, rejoining line breaks that OCR turned into spaces."""
    m = re.compile(BODY + "+").match(text, i)
    if not m: return None, i
    url, end = m.group(0), m.end()
    for _ in range(3):                       # a URL rarely breaks more than twice
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
        else:
            break
    url = strip_tail(url)
    if url.lower().startswith("www."):
        url = "http://" + url
    # normalise scheme and host case; paths stay as printed
    m2 = re.match(r"(?i)(https?://)([^/]+)(.*)$", url)
    if m2:
        url = m2.group(1).lower() + m2.group(2).lower() + m2.group(3)
    return url, end

def main():
    rows, cases, ops_with_urls = [], 0, 0
    for vi, zname in enumerate(sorted(os.listdir(CAP))):
        if not zname.endswith(".zip"): continue
        reporter, vol = zname[:-4].rsplit("-", 1)
        zf = zipfile.ZipFile(os.path.join(CAP, zname))
        for n in zf.namelist():
            if not (n.endswith(".json") and "json/" in n and "metadata" not in n): continue
            try: case = json.loads(zf.read(n).decode("utf-8"))
            except Exception: continue
            cases += 1
            date = case.get("decision_date") or ""
            year = int(date[:4]) if date[:4].isdigit() else None
            if not year or year < 1990: continue
            off = next((c["cite"] for c in (case.get("citations") or [])
                        if c.get("type") == "official"), "")
            for op in (case.get("casebody") or {}).get("opinions") or []:
                text = op.get("text") or ""
                if "http" not in text and "www." not in text: continue
                vm = VISIT_RE.search(text)
                visited = (vm.group(1) or vm.group(2)) if vm else None
                clerk = bool(CLERK_RE.search(text))
                hit = False
                pos = 0
                while True:
                    m = START_RE.search(text, pos)
                    if not m: break
                    url, pos = repair(text, m.start())
                    if not url or not good_host(url): continue
                    hit = True
                    rows.append({
                        "url": url, "host": host_of(url), "year": year, "date": date,
                        "case": case.get("name_abbreviation") or "", "cite": off,
                        "type": (op.get("type") or "").lower(), "author": op.get("author") or "",
                        "src": reporter, "vol": vol,
                        "visited": re.sub(r"\s+", " ", visited) if visited else None,
                        "clerk": clerk,
                    })
                if hit: ops_with_urls += 1
        if vi % 20 == 0: print(f"  {zname:14s} cases={cases:6d} urls={len(rows):6d}", flush=True)

    # the same opinion is printed in both reporters for the overlap years
    seen, ded = set(), []
    for r in rows:
        k = (r["case"], r["date"], r["type"], r["url"])
        if k in seen: continue
        seen.add(k); ded.append(r)

    json.dump(ded, open(os.path.join(SRC, "cap_urls.json"), "w"), separators=(",", ":"))
    print(f"\ncases {cases}   opinions citing a URL {ops_with_urls}")
    print(f"citations {len(rows)} -> {len(ded)} after cross-reporter dedupe;  unique urls {len({r['url'] for r in ded})}")
    print("by year:", dict(sorted(collections.Counter(r['year'] for r in ded).items())))
    print("with a visitation date:", sum(1 for r in ded if r['visited']),
          "| clerk's-file note:", sum(1 for r in ded if r['clerk']))
    print("top hosts:", collections.Counter(r['host'] for r in ded).most_common(8))

if __name__ == "__main__":
    main()
