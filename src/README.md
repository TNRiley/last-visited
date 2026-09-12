# Pipeline

Run in order. Everything is resumable and idempotent; intermediates stay in `src/` and
are gitignored.

| step | does | writes |
|---|---|---|
| `01_download_cap.sh` | Caselaw Access Project volumes (`us` 500–572, `s-ct` 134–140) | `src/raw/cap/*.zip` (~390 MB) |
| `02_extract_cap.py` | URLs out of OCR'd opinion text, line breaks repaired | `src/cap_urls.json` |
| `03_slip_opinions.sh` | slip opinion PDFs, OT2020–OT2025 | `src/raw/slip/**` (~137 MB) |
| `04_extract_slip.py` | URLs out of born-digital PDFs via `pdftotext -layout` | `src/slip_urls.json` |
| `05_check.py` | does each URL still resolve | `src/checked.jsonl` |
| `06_wayback.py` | was each URL ever archived, and archived near its citation | `src/wayback.jsonl` |
| `07_stats.py` | headline figures, for checking the prose | — |
| `08_recheck.py` | re-fetches ambiguous results through curl | `src/recheck.jsonl` |
| `08b_perma.py` | slow serial pass over perma.cc alone | appends to `src/recheck.jsonl` |
| `09_payload.py` | joins all four into the page payload | `src/payload.json` |
| `10_inject.py` | splices payload + `app.js` into `template.html`, wraps, links | `index.html` |
| `test_page.js` | runs the built page against a stub DOM, asserts its claims | — |

## Why there are three checking passes

`05_check.py` is the bulk pass and is polite: one request per host per second, a study
user-agent, no retries.

`08_recheck.py` exists because that politeness produces false deaths. A meaningful number
of hosts refuse non-browser clients — and it is not the User-Agent string that they
object to. perma.cc returns **403 to python-requests and 200 to curl with byte-identical
headers**, because the refusal is keyed on the TLS/HTTP client fingerprint. So the retry
shells out to curl. Only ambiguous states are retried; a 404 is a 404 whoever asks.

`08b_perma.py` exists because perma.cc is the single most important host in this corpus —
the Court adopted it as a citation convention in OT2025 — and it rate-limits. Sixty
requests in ninety seconds turns most of its links into false 403s. One at a time, five
seconds apart, three attempts, best answer wins.

A 403 that survives all of that is recorded as **no answer**, never as dead. Reporting the
Supreme Court's own archive links as broken because of a rate limiter would be the worst
available error on this page.

## Why `available` and not CDX

`06_wayback.py` uses `https://archive.org/wayback/available`. The CDX API returns richer
data but refuses roughly three requests in four under any useful concurrency, and a
refused lookup is indistinguishable from "never archived" unless you are careful — which
is exactly the silent failure that would gut the OCR-confound argument this page rests on.
CDX was tried first and abandoned for that reason.

## Regenerating after changing an extractor

Changing `02_extract_cap.py` or `04_extract_slip.py` changes the URL set. `05_check.py`
and `06_wayback.py` will pick up the new URLs on a re-run, and `09_payload.py` ignores
entries in the jsonl files that no longer appear in any citation. Nothing needs deleting.
