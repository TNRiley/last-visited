#!/usr/bin/env bash
# Slip opinions from supremecourt.gov for terms the Caselaw Access Project does not
# reach (CAP's Supreme Court Reporter stops at volume 140, OT2019/2020). The site
# keeps only recent terms online; 2020-2025 are what it currently serves.
set -u
cd "$(dirname "$0")/raw" || exit 1
mkdir -p slip && cd slip
UA="Mozilla/5.0 (quick-projects link-rot study; contact via github.com/TNRiley)"
for t in 20 21 22 23 24 25; do
  idx="index_$t.html"
  [ -s "$idx" ] || curl -s -A "$UA" "https://www.supremecourt.gov/opinions/slipopinion/$t" -o "$idx"
  mkdir -p "$t"
  grep -o "/opinions/${t}pdf/[a-zA-Z0-9_.\-]*\.pdf" "$idx" | sort -u | while read -r p; do
    f="$t/$(basename "$p")"
    [ -s "$f" ] && continue
    curl -s -A "$UA" "https://www.supremecourt.gov$p" -o "$f"
    sleep 0.3
  done
  echo "term $t: $(ls -1 "$t" | wc -l) pdfs"
done
echo "=== total $(find . -name '*.pdf' | wc -l) pdfs, $(du -sh . | cut -f1) ==="
