#!/bin/bash
set -euo pipefail

nginx -t
php-fpm --test

php-fpm --nodaemonize &
fpm_pid=$!
nginx -g 'daemon off;' &
nginx_pid=$!

shutdown() {
    trap '' TERM INT QUIT
    kill -QUIT "$nginx_pid" "$fpm_pid" 2>/dev/null || true
    wait "$nginx_pid" 2>/dev/null || true
    wait "$fpm_pid" 2>/dev/null || true
}
trap 'shutdown; exit 0' TERM INT QUIT

# Either daemon exiting unexpectedly must stop the container, not leave half a stack.
if wait -n; then
    status=1
else
    status=$?
fi
shutdown
exit "$status"
