#!/usr/bin/env bash
# Caselaw Access Project bulk volumes (CC0). Two reporters are needed because
# neither covers the whole window on its own:
#   us    vols 500-572  official U.S. Reports, 1991-2014
#   s-ct  vols 134-140  Supreme Court Reporter, 2014-2020 (CAP's us set stops at 572)
# Volumes below 500 are pre-web and cannot contain URLs; starting at 500 leaves
# headroom to let the data show when the first URL actually appears.
set -u
cd "$(dirname "$0")/raw" || exit 1
mkdir -p cap && cd cap

fetch () { # reporter volume
  out="$1-$2.zip"
  if [ -s "$out" ]; then echo "have $out"; return; fi
  code=$(curl -sL "https://static.case.law/$1/$2.zip" -o "$out" -w "%{http_code}")
  if [ "$code" = "200" ]; then
    echo "$out $(stat -c%s "$out")b"
  else
    echo "FAILED $out http=$code"; rm -f "$out"
  fi
}

for v in $(seq 500 572); do fetch us "$v"; done
for v in $(seq 134 140); do fetch s-ct "$v"; done
echo "=== done: $(ls -1 *.zip | wc -l) volumes, $(du -sh . | cut -f1) ==="
