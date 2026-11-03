#!/bin/bash
set -euo pipefail

image="${1:?Usage: bash tests/smoke.sh IMAGE [apache|nginx]}"
flavor="${2:-apache}"
case "$flavor" in
    apache) sapi=apache2handler ;;
    nginx) sapi=fpm-fcgi ;;
    *) echo >&2 "Unsupported flavor: $flavor"; exit 1 ;;
esac
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
if [[ "$flavor" == nginx ]]; then
    docker run --rm "$image" nginx -t
    docker run --rm "$image" php-fpm --test
fi

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

# Masters need KILL to stop their www-data workers after the workers change UID.
docker run -d --name "$container" --memory 512m --cpus 2 \
    --security-opt no-new-privileges:true --cap-drop ALL --cap-add CHOWN \
    --cap-add SETUID --cap-add SETGID --cap-add KILL --cap-add NET_BIND_SERVICE \
    -p 127.0.0.1::80 "$image" > /dev/null
port="$(docker port "$container" 80/tcp)"
base="http://$port"
bash "$root/tests/wait-http.sh" "$base/healthz"
curl --fail --silent --show-error --retry 30 --retry-connrefused --retry-delay 1 \
    --max-time 3 "$base/" | grep -qx 'PHP application container is running.'

docker cp "$root/tests/security-test.php" "$container:/var/www/html/security-test.php"
curl --fail --silent --show-error "$base/security-test.php" \
    | python3 -c 'import json, sys; result = json.load(sys.stdin); assert result["ok"] and result["sapi"] == sys.argv[1], result' "$sapi"

docker exec "$container" mkdir -p /var/www/html/.git /var/www/html/uploads /var/www/html/listing
docker cp "$root/tests/fixtures/secret.txt" "$container:/var/www/html/.env"
docker cp "$root/tests/fixtures/secret.txt" "$container:/var/www/html/.git/config"
docker cp "$root/tests/fixtures/secret.txt" "$container:/var/www/html/composer.json"
docker cp "$root/tests/fixtures/secret.txt" "$container:/var/www/html/listing/visible.txt"
docker cp "$root/tests/fixtures/upload.php" "$container:/var/www/html/uploads/payload.php"
docker cp "$root/tests/fixtures/upload.php" "$container:/var/www/html/uploads/payload.phtml"
for path in /.env /.git/config /composer.json /uploads/payload.php /uploads/payload.phtml; do
    status="$(curl --path-as-is --silent --show-error -o /dev/null -w '%{http_code}' "$base$path")"
    [[ "$status" == 403 ]] || { echo >&2 "$path returned $status, expected 403"; exit 1; }
done
# Apache without mod_autoindex can return 404 instead of 403; neither may list files.
status="$(curl --silent --show-error -o /dev/null -w '%{http_code}' "$base/listing/")"
[[ "$status" == 403 || "$status" == 404 ]] || { echo >&2 "/listing/ returned $status, expected 403 or 404"; exit 1; }
[[ "$(curl --silent --show-error -X TRACE -o /dev/null -w '%{http_code}' "$base/")" == 405 ]]
headers="$(curl --fail --silent --show-error -D - -o /dev/null "$base/")"
if printf '%s\n' "$headers" | grep -Eiq '^X-Powered-By:|^Server:.*(PHP|/[0-9])'; then
    echo >&2 'Runtime version leaked in response headers'
    exit 1
fi
printf '%s\n' "$headers" | grep -Eiq '^X-Content-Type-Options: nosniff'

if [[ "$flavor" == nginx ]]; then
    # Front-controller routing, static assets, missing scripts and source disclosure.
    curl --fail --silent --show-error "$base/example/route?test=1" | grep -qx 'PHP application container is running.'
    curl --fail --silent --show-error "$base/listing/visible.txt" | cmp - "$root/tests/fixtures/secret.txt"
    [[ "$(curl --silent --show-error -o /dev/null -w '%{http_code}' "$base/missing.php")" == 404 ]]
    for path in /uploads/payload.php/extra /uploads/payload.phtml/extra /uploads/payload.php.txt /security-test.php/extra; do
        status="$(curl --path-as-is --silent --show-error -o /dev/null -w '%{http_code}' "$base$path")"
        [[ "$status" == 403 ]] || { echo >&2 "$path returned $status, expected 403"; exit 1; }
    done

    # FPM's inherited EXPOSE metadata must not mean a public FastCGI listener.
    docker exec "$container" php -r '$s = @fsockopen("127.0.0.1", 9000); if ($s) { fclose($s); exit(1); }'

    # A failed FPM master must stop Nginx and the container, not serve stale liveness.
    docker exec "$container" sh -c 'kill -TERM "$(cat /run/php-fpm.pid)"'
    python3 -c 'import subprocess, sys; result = subprocess.run(["docker", "wait", sys.argv[1]], capture_output=True, text=True, timeout=20, check=True); assert int(result.stdout) != 0, result' "$container"
    docker start "$container" > /dev/null
    port="$(docker port "$container" 80/tcp)"
    bash "$root/tests/wait-http.sh" "http://$port/healthz"
    docker stop --time 15 "$container" > /dev/null
    [[ "$(docker inspect --format '{{.State.ExitCode}}' "$container")" == 0 ]]
fi
echo "Security smoke tests passed: $image"
