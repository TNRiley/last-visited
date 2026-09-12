# Rebuilding Last Visited

A recipe, not a summary. Assumes a shell, Python 3, Node, `curl` and `pdftotext`
(poppler), and no other context.

## 1. What is being built

A single self-contained HTML page holding every web address cited in a United States
Supreme Court opinion since the first one in 1996, each fetched again and each looked
up in the Internet Archive.

The effect it exists to show: **a citation is a promise that the reader can check the
source, and for most of these the promise has expired.** Fewer than half the addresses
that give a definite answer still resolve to what was cited. The failure is graded by
age — citations from the late 2000s are almost entirely gone, recent ones mostly fine —
which is what distinguishes rot from noise.

The second finding is that the Court knew. Its citation practice has changed three
times: a blanket visitation note in the opinion text ("all Internet materials as visited
June 16, 2015, and available in Clerk of Court's case file"), then a period with almost
no convention at all, then — in OT2025 and essentially not before — `(archived at
https://perma.cc/XXXX-XXXX)` appended to link after link. perma.cc is now the most-cited
host in the corpus.

## 2. Data sources

No single source spans the period, so there are two, spliced.

### Caselaw Access Project bulk volumes (CC0)

<https://static.case.law/>

- `us` volumes **500–572** — official U.S. Reports, 1991–2014
- `s-ct` volumes **134–140** — Supreme Court Reporter, 2014–2020

`https://static.case.law/<reporter>/<volume>.zip`, ~5 MB each, ~390 MB total. Each zip
holds `json/`, `html/` and `metadata/`; the case JSON carries full opinion text with
`casebody.opinions[].text`, an opinion `type` (majority / concurrence / dissent) and an
`author`. **Inside the zip the path is `json/0001-01.json` — filtering on `"/json/"`
with a leading slash matches nothing and yields a silent zero.**

CAP's `us` set stops at volume 572, which is why `s-ct` is needed at all: it is the only
open full-text source for 2015–2020. Opinions printed in both reporters are de-duplicated
on (case, date, opinion type, URL).

Volumes below 500 are pre-web. Starting at 500 rather than 517 is deliberate — it lets
the data show when the first URL actually appears rather than assuming it.

### supremecourt.gov slip opinions (public domain)

`https://www.supremecourt.gov/opinions/slipopinion/<term>` for terms **20–25**.
The site serves only recent terms; 06, 10, 14, 15 and 16 all redirect. Scrape
`/opinions/<term>pdf/<name>.pdf` out of the index page, and take case name, date, docket
and citation from the index table rather than from the PDFs — it is cleaner and gives
the opinion author.

~380 PDFs, ~137 MB.

## 3. Extraction, and the four traps

Print breaks long URLs across lines, and each corpus breaks them differently.

**Trap 1 — OCR turns the break into a space.** The scanned volumes contain
`http://www.txdmv. gov/motorists/license-plates`. A whitespace-terminated pattern
silently truncates that to `http://www.txdmv`, which then reads as a dead link. Rejoin
across the gap, but only where a typesetter would actually break — after `. / - = ? & _ ~ # %`
— and only when the next token looks like a host or path continuation.

**Trap 2 — a naive TLD test hides trap 1.** `www.txdmv` passes `/\.[a-z]{2,}$/`, because
`.txdmv` looks like a TLD. Validate against a real TLD list or the truncation survives
undetected.

**Trap 3 — `pdftotext` de-hyphenates.** Its default mode treats a hyphen at a line end as
hyphenation and deletes it, so `perma.cc/2AQU-3PME` broken across a line comes back as
`perma.cc/2AQU3PME`. Use `-layout`. (perma.cc happens to accept both, which is exactly
why this is easy to miss — on any other host it would be a fabricated dead link.)

**Trap 4 — opaque codes have no dots or slashes to recognise.** `perma.cc/2AQU-` + `3PME`
cannot be rejoined by a rule that expects a host or a path. Allow a short alphanumeric
run as a continuation, but split the rule by where the break is: after a hyphen, require
only the shape and a capital; after a slash, require a digit too, or `http://x.gov/ See
also` becomes `http://x.gov/See`.

One perma link (`perma.cc/LZG3-`) still cannot be recovered: its code is split across a
page boundary with the running header in between. That is 1 of 62 and is left alone rather
than papered over with page-furniture heuristics.

Also worth capturing while parsing: the blanket visitation note, the Clerk's-case-file
note, and which opinion each URL sits in.

## 4. Checking, and the instrument problem

Three passes, all resumable, all keyed by URL.

**Liveness** (`05_check.py`). HEAD, falling back to GET; follow redirects; record the
final URL. Classify:

| state | meaning |
|---|---|
| `ok` | 2xx at the path that was cited |
| `soft` | 2xx, but redirected to the site root — the page is gone, the domain is not |
| `notfound` | 404 / 410 |
| `dns` | host does not resolve — the publisher is gone |
| `conn` / `timeout` / `server` / `ssl` | reachability failures |
| `blocked` | 401 / 403 / 429 — the server refused to say |

`soft` must be kept separate. Counting a redirect-to-homepage as alive is the standard way
link-rot studies overstate survival.

**The instrument has to be corrected** (`08_recheck.py`). This is the part that is easy to
get wrong and fatal if you do. Every one of the Court's perma.cc links returns **403 to
python-requests and 200 to `curl` with byte-identical headers** — the block is on the TLS
and HTTP client fingerprint, not on the User-Agent string, so changing the UA achieves
nothing. Re-fetch the ambiguous states through curl. Never retry a 404: it is a 404
whoever asks.

perma.cc additionally rate-limits and refuses intermittently, so it gets its own serial
pass (`08b_perma.py`) — three attempts, five seconds apart, best answer wins. A 403 that
survives all three is recorded as no answer, **never as dead**. Getting this wrong would
report the Court's own archive links as broken.

**Archive coverage** (`06_wayback.py`). Use `https://archive.org/wayback/available`, not
the CDX API: CDX refuses roughly three requests in four under any useful concurrency and
returns nulls that look like "not archived". Two lookups per URL — closest capture to
1 June of the citation year, and closest capture to now.

This is what bounds the OCR confound. A Wayback capture proves the address *as printed*
once existed, so `archived + dead today` is genuine rot, while `never archived + dead`
could be OCR damage and is reported apart rather than counted.

## 5. Verification table

Figures move — the live web is the instrument — but these should be close, and the
*shapes* are stable:

| quantity | expected |
|---|---|
| CAP cases scanned | ~196,000 |
| slip opinion PDFs | ~380 |
| citations extracted | ~1,380 |
| distinct URLs | ~1,330 |
| opinions containing at least one URL | ~530 |
| cases | ~470 |
| first URL ever cited | *Denver Area Ed. Telecomms. Consortium v. FCC*, 1996-06-28, a concurrence |
| still resolves, of those giving a definite answer | ~44% |
| hosts that no longer resolve at all | ~160 |
| ever archived by the Wayback Machine | ~58% |
| citations carrying a visitation date | ~450 |
| citations noting a copy in the Clerk's case file | ~100 |
| perma.cc citations | ~75, of which ~73 in OT2025 |
| perma.cc citations before OT2025 | 2 |
| most-cited host | perma.cc, then www.census.gov |
| `.gov` share of citations | ~43% |

Recognisable checkpoints: *Muscarello v. United States* (1998) cites IMDb in dissent, over
the meaning of "carry". *Walker v. Texas Div., Sons of Confederate Veterans* (2015) carries
the `txdmv` URL that trap 1 truncates. If the first cited year is not 1996, or if perma.cc
appears before 2025, something in the corpus assembly is wrong.

## 6. Running it

```bash
bash src/01_download_cap.sh      # ~390 MB of CAP volumes
python src/02_extract_cap.py     # -> src/cap_urls.json
bash src/03_slip_opinions.sh     # ~380 PDFs
python src/04_extract_slip.py    # -> src/slip_urls.json
python src/05_check.py           # -> src/checked.jsonl     (resumable)
python src/06_wayback.py         # -> src/wayback.jsonl     (resumable, slow)
python src/07_stats.py           # headline figures
python src/08_recheck.py         # -> src/recheck.jsonl     (curl, ambiguous only)
python src/08b_perma.py          # gentle serial pass over perma.cc
python src/09_payload.py         # -> src/payload.json
python src/10_inject.py          # -> index.html, then wrap + catalog link
node src/test_page.js            # executes the page, asserts its claims
```

`09_payload.py` drops URLs in `checked.jsonl` that no longer appear in any citation — the
jsonl files accumulate across runs, and re-running an extractor changes the URL set.

## 7. What the page must say about itself

- It cannot see **content drift**. A URL that still returns 200 may serve something
  entirely unlike what the Justice read, and no status code reveals that. This is the
  largest single limitation and belongs near the top of the methods panel.
- `blocked` is not `dead`. Keep it out of every percentage rather than guessing.
- Counts are of addresses, not of how load-bearing each one was.
- OT2015–OT2019 rests on the Supreme Court Reporter alone, because supremecourt.gov no
  longer serves those terms.
- A liveness check is a snapshot. Print the date it was taken, on the page.
