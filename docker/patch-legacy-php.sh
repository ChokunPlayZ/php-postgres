#!/bin/sh
set -eu

# PHP 7.4 uses the complete, vendored DirectAdmin backport series, including PHP2Shell.
# PHP 8.0/8.1 use the official emergency backports linked from:
# https://www.php.net/archive/2026.php#2026-10-21-5
# Pin both commit and patch digest; never execute a moving branch or an unchecked patch.
version="$(php -r 'echo PHP_VERSION;')"
case "$version" in
    7.4.33)
        patch_directory=/usr/local/lib/php-postgres/patches/php-7.4
        ;;
    8.0.30)
        commit=82f8f31b16a035c1b67cc253e79f7cc288f4cc20
        checksum=534478c973cef6f493605b7af907f639a364912ee92c24598ddae44c3bc72d1c
        ;;
    8.1.34)
        commit=1d7dec178a094e6e75b229ce22754045f8c6070a
        checksum=c85ad0fddcbff7f2318617eeaa54d271135463b5bf70a01228447e3ed78de96e
        ;;
    7.*|8.0.*|8.1.*)
        echo >&2 "Unsupported legacy baseline: $version. Use 7.4.33, 8.0.30 or 8.1.34."
        exit 1
        ;;
    *) exit 0 ;;
esac

echo >&2 "WARNING: PHP $version is EOL. Backports do not provide comprehensive security support."
docker-php-source extract
cd /usr/src/php
if [ "$version" = 7.4.33 ]; then
    sh /usr/local/lib/php-postgres/apply-php-patches.sh /usr/src/php "$patch_directory"
    backport="patchset-sha256:$(sha256sum "$patch_directory/series.sha256" | cut -d ' ' -f1)"
else
    backport="$commit"
    patch_file="$(mktemp)"
    trap 'rm -f "$patch_file"' EXIT HUP INT TERM
    curl --fail --silent --show-error --location --retry 3 \
        "https://github.com/php/php-src/commit/$commit.patch" -o "$patch_file"
    printf '%s  %s\n' "$checksum" "$patch_file" | sha256sum --check --strict
    patch --batch --forward --fuzz=0 -p1 < "$patch_file"
fi

# Reuse the official image's configure options and compiler hardening. No eval.
configure_options="$(php-config --configure-options)"
export CFLAGS="$PHP_CFLAGS" CPPFLAGS="$PHP_CPPFLAGS" LDFLAGS="$PHP_LDFLAGS"
set -f
# Official configure options contain no whitespace-bearing argument values.
# shellcheck disable=SC2086
./configure $configure_options
make -j"$(nproc)"
make install
make clean

# Check both installed SAPIs, not just a marker or PHP's unchanged version string.
nm -D /usr/local/bin/php | grep -q ' zend_mm_safe_error_ex$'
if command -v php-fpm > /dev/null; then
    nm -D "$(command -v php-fpm)" | grep -q ' zend_mm_safe_error_ex$'
else
    find /usr/lib/apache2/modules -name 'libphp*.so' -exec nm -D '{}' ';' \
        | grep -q ' zend_mm_safe_error_ex$'
fi
mkdir -p /usr/local/share/php-postgres
printf '%s %s\n' "$version" "$backport" > /usr/local/share/php-postgres/php2shell-backport
if [ "$version" = 7.4.33 ]; then
    cp .php-postgres-patches.sha256 /usr/local/share/php-postgres/php74-patches.sha256
fi
