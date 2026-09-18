#!/usr/bin/env bash
# fetch.sh URL [OUTFILE]  — curl with a browser UA (maxroll/diablo2.io/traderie all answer 200 to this; python-requests default UA is NOT verified).
# Prints "HTTP_CODE BYTES URL" on stderr. Cache: if OUTFILE exists and is non-empty, the fetch is skipped.
set -u
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
url="$1"; out="${2:-/dev/stdout}"
if [ "$out" != "/dev/stdout" ] && [ -s "$out" ]; then echo "cached $out" >&2; exit 0; fi
curl -sL -A "$UA" --max-time 60 -o "$out" -w "%{http_code} %{size_download} $url\n" "$url" >&2
