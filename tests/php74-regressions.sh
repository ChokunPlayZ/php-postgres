#!/bin/sh
set -eu

# Run a bounded selection of the supplied upstream regression tests against the
# installed engine/extensions, using the retained (not freshly downloaded) source.
# Deliberately exclude the multi-gigabyte SOAP QName and metaphone test cases.
test "$(php -r 'echo PHP_VERSION;')" = 7.4.33
docker-php-source extract
trap 'docker-php-source delete' EXIT HUP INT TERM
cd /usr/src/php
cmp .php-postgres-patches.sha256 /usr/local/share/php-postgres/php74-patches.sha256

set -- \
    ext/xml/tests/gh14834.phpt \
    ext/xml/tests/toffset_bounds.phpt \
    ext/standard/tests/crypt/bcrypt_salt_dollar.phpt \
    ext/standard/tests/password/password_bcrypt_short.phpt \
    ext/standard/tests/password/password_bcrypt_errors.phpt \
    ext/filter/tests/ghsa-w8qr-v226-r27w.phpt \
    ext/filter/tests/filter_sanitize_encoded_0xff.phpt \
    ext/standard/tests/filters/ghsa-r977-prxv-hc43.phpt \
    ext/standard/tests/filters/ghsa-88hq-2827-7pg6.phpt \
    ext/standard/tests/network/ghsa-3cr5-j632-f35r.phpt \
    ext/standard/tests/streams/ghsa-3cr5-j632-f35r.phpt \
    ext/standard/tests/image/gh20584.phpt \
    ext/standard/tests/array/GHSA-h96m-rvf9-jgm2.phpt \
    ext/phar/tests/GHSA-jqcx-ccgc-xwhv.phpt \
    ext/soap/tests/GHSA-85c2-q967-79q5.phpt \
    ext/soap/tests/GHSA-m33r-qmcv-p97q.phpt \
    ext/soap/tests/GHSA-hmxp-6pc4-f3vv.phpt \
    ext/date/tests/DatePeriod_double_constructor_call.phpt
for test_file do
    test -f "$test_file"
done
export NO_INTERACTION=1 REPORT_EXIT_STATUS=1
export TEST_PHP_EXECUTABLE=/usr/local/bin/php
php run-tests.php -q -p "$TEST_PHP_EXECUTABLE" "$@"
