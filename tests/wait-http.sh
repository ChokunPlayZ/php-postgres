#!/bin/bash
set -euo pipefail

url="${1:?Usage: bash tests/wait-http.sh URL}"
response="$(mktemp)"
trap 'rm -f "$response"' EXIT

# Docker can reset connections before the web server starts listening. Retry
# readiness only, including resets/empty replies, and keep the wait bounded.
# A file lets curl discard partial response bodies before retrying.
curl --fail --silent --show-error --retry 30 --retry-all-errors --retry-delay 1 \
    --retry-max-time 60 --connect-timeout 2 --max-time 3 \
    --output "$response" "$url"
if [[ "$(cat "$response")" != OK ]]; then
    echo >&2 "Unexpected health response from $url:"
    cat "$response" >&2
    exit 1
fi
