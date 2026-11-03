#!/bin/sh
set -eu

source_dir="${1:?Usage: sh apply-php-patches.sh PHP_SOURCE_DIRECTORY PATCH_DIRECTORY}"
patch_dir="${2:?Missing patch directory}"
export LC_ALL=C

# Each series declares its exact source baseline; never guess from hunk matches.
source_version="$(sed -n 's/^#define PHP_VERSION[[:space:]]*"\([^"]*\)"$/\1/p' "$source_dir/main/php_version.h")"
if [ "$source_version" != "$(cat "$patch_dir/baseline")" ]; then
    echo >&2 "Patch series is not for PHP $source_version"
    exit 1
fi

# Only plain patch filenames are allowed, once each, in filename order. Reject
# unlisted files too, so adding a patch without refreshing the manifest fails.
patch_names="$(awk '
    NF != 2 || length($1) != 64 || $1 !~ /^[0-9a-f]+$/ ||
    $2 !~ /^[0-9]+-[A-Za-z0-9.+_-]+\.patch$/ { exit 1 }
    { print $2 }
' "$patch_dir/series.sha256")"
actual_names="$(for patch_file in "$patch_dir"/*.patch; do
    [ -f "$patch_file" ] && [ ! -L "$patch_file" ] || exit 1
    printf '%s\n' "${patch_file##*/}"
done)"
if [ -z "$patch_names" ] || [ "$patch_names" != "$actual_names" ]; then
    echo >&2 "Patch manifest does not match the ordered patch files"
    exit 1
fi
(cd "$patch_dir" && sha256sum --check --strict series.sha256)

# Verify the whole series before changing source, then stop on any failed hunk.
while read -r checksum patch_name || [ -n "$checksum" ]; do
    echo >&2 "Applying PHP $source_version backport: $patch_name"
    patch --batch --forward --fuzz=0 --no-backup-if-mismatch -p1 -d "$source_dir" < "$patch_dir/$patch_name"
done < "$patch_dir/series.sha256"

# Retain an inventory in the source archive for downstream extension rebuilds.
cp "$patch_dir/series.sha256" "$source_dir/.php-postgres-patches.sha256"
