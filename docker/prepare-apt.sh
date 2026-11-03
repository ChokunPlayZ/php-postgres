#!/bin/sh
set -eu

. /etc/os-release
if [ "$ID" = debian ] && [ "${VERSION_CODENAME:-}" = bullseye ]; then
    # Bullseye's security indexes remain on the live mirror, but their .deb files
    # have moved to the archive. Keep the main/updates repositories unchanged.
    echo >&2 "WARNING: Debian Bullseye security packages are archived; no ongoing OS security updates are provided."
    updated_source="$(mktemp)"
    trap 'rm -f "$updated_source"' EXIT HUP INT TERM
    for source in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
        [ -f "$source" ] || continue
        sed -E 's#https?://(deb\.debian\.org|security\.debian\.org)/debian-security/?([[:space:]]|$)#https://archive.debian.org/debian-security\2#g' \
            "$source" > "$updated_source"
        cat "$updated_source" > "$source"
    done
fi

# Do not silently proceed with old indexes when any repository fails to refresh.
# Archive signatures are still verified; no trusted=yes or validity bypasses.
apt-get update -o APT::Update::Error-Mode=any -o Acquire::Retries=3
