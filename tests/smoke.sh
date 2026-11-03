#!/bin/bash
set -euo pipefail

image="${1:?Usage: bash tests/smoke.sh IMAGE}"
root="$(cd "$(dirname "$0")/.." && pwd)"
container="php-postgres-security-${RANDOM}-$$"
cleanup() {
    docker logs "$container" >&2 2>/dev/null || true
    docker rm -f "$container" > /dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --rm -v "$root/tests:/tests:ro" "$image" php /tests/security-policy-test.php
docker run --rm -v "$root/tests:/tests:ro" "$image" php /tests/security-test.php
docker run --rm "$image" composer --version

branch="$(docker run --rm "$image" php -r 'echo PHP_MAJOR_VERSION, ".", PHP_MINOR_VERSION;')"
case "$branch" in
    7.4|8.0|8.1)
        # Harmless bounded allocation: the official EOL patch must _exit on OOM,
        # rather than run shutdown callbacks against potentially corrupt state.
        status=0
        output="$(docker run --rm --network none --memory 128m "$image" \
            php -d memory_limit=16M -d display_errors=0 -r \
            'register_shutdown_function(function () { echo "UNSAFE_SHUTDOWN"; }); str_repeat("x", 64 * 1024 * 1024);' 2>&1)" || status=$?
        if [[ "$status" != 1 || "$output" == *UNSAFE_SHUTDOWN* ]]; then
            echo >&2 "Legacy OOM backport regression (exit $status): $output"
            exit 1
        fi
        ;;
esac

docker run -d --name "$container" --memory 512m --cpus 2 \
    --security-opt no-new-privileges:true --cap-drop ALL --cap-add CHOWN \
    --cap-add SETUID --cap-add SETGID --cap-add NET_BIND_SERVICE \
    -p 127.0.0.1::80 "$image" > /dev/null
port="$(docker port "$container" 80/tcp)"
base="http://$port"
curl --fail --silent --show-error --retry 30 --retry-connrefused --retry-delay 1 \
    --max-time 3 "$base/healthz" | grep -qx OK
curl --fail --silent --show-error "$base/" | grep -qx 'PHP application container is running.'

docker cp "$root/tests/security-test.php" "$container:/var/www/html/security-test.php"
curl --fail --silent --show-error "$base/security-test.php" \
    | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["ok"], result'

docker exec "$container" mkdir -p /var/www/html/.git /var/www/html/uploads /var/www/html/listing
docker cp "$root/tests/fixtures/secret.txt" "$container:/var/www/html/.env"
docker cp "$root/tests/fixtures/secret.txt" "$container:/var/www/html/.git/config"
docker cp "$root/tests/fixtures/secret.txt" "$container:/var/www/html/listing/visible.txt"
docker cp "$root/tests/fixtures/upload.php" "$container:/var/www/html/uploads/payload.php"
docker cp "$root/tests/fixtures/upload.php" "$container:/var/www/html/uploads/payload.phtml"
for path in /.env /.git/config /uploads/payload.php /uploads/payload.phtml /listing/; do
    status="$(curl --path-as-is --silent --show-error -o /dev/null -w '%{http_code}' "$base$path")"
    [[ "$status" == 403 ]] || { echo >&2 "$path returned $status, expected 403"; exit 1; }
done
[[ "$(curl --silent --show-error -X TRACE -o /dev/null -w '%{http_code}' "$base/")" == 405 ]]
headers="$(curl --fail --silent --show-error -D - -o /dev/null "$base/")"
if printf '%s\n' "$headers" | grep -Eiq '^X-Powered-By:|^Server:.*(PHP|/[0-9])'; then
    echo >&2 'Runtime version leaked in response headers'
    exit 1
fi
printf '%s\n' "$headers" | grep -Eiq '^X-Content-Type-Options: nosniff'
echo "Security smoke tests passed: $image"
