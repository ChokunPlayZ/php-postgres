#!/bin/sh
set -eu

policy=/usr/local/lib/php-postgres
export DEBIAN_FRONTEND=noninteractive

# Reject unsupported branches and outdated maintained runtimes before doing work.
# Legacy runtimes are checked after their source backport has been compiled.
branch="$(php -r 'echo PHP_MAJOR_VERSION, ".", PHP_MINOR_VERSION;')"
case "$branch" in
    7.4|8.0|8.1) ;;
    *) php "$policy/security-policy.php" ;;
esac

# Do not retain the compilers inherited from the official image in the runtime.
apt-mark auto autoconf dpkg-dev file g++ gcc libc6-dev make pkg-config re2c > /dev/null
saved_apt_mark="$(apt-mark showmanual)"
apt-get update
apt-get upgrade -y --with-new-pkgs \
    -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold
# Intentional splitting: PHPIZE_DEPS is the official image's package list.
# shellcheck disable=SC2086
apt-get install -y --no-install-recommends \
    $PHPIZE_DEPS \
    apache2-dev libargon2-dev libcurl4-openssl-dev libonig-dev \
    libreadline-dev libsodium-dev libsqlite3-dev libssl-dev libxml2-dev \
    libpq-dev libpng-dev libjpeg-dev libfreetype6-dev libwebp-dev \
    libzip-dev libicu-dev libbz2-dev zlib1g-dev patch \
    ca-certificates curl git unzip

sh "$policy/patch-legacy-php.sh"
php "$policy/security-policy.php"

docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp
docker-php-ext-install -j"$(nproc)" \
    bcmath bz2 calendar exif gd gettext intl mysqli pcntl \
    pdo_mysql pdo_pgsql pgsql soap sockets zip
# OPcache is built into PHP 8.5+. PDO, XML and mbstring are already in the base.
if ! php -r 'exit(extension_loaded("Zend OPcache") ? 0 : 1);'; then
    docker-php-ext-install -j"$(nproc)" opcache
fi
pecl install redis-6.3.0
docker-php-ext-enable redis

# Preserve patched source for downstream docker-php-ext-install invocations too.
# Otherwise an extension rebuild could silently reintroduce the old OPcache code.
if [ -f /usr/local/share/php-postgres/php2shell-backport ]; then
    tar -cJf /usr/src/php.tar.xz -C /usr/src php
fi
docker-php-source delete

apt-mark auto '.*' > /dev/null
# Intentional splitting: apt-mark expects one argument per package.
# shellcheck disable=SC2086
apt-mark manual $saved_apt_mark ca-certificates curl git unzip > /dev/null
# Retain runtime libraries used by PHP, its extensions and Apache's rebuilt module.
find /usr/local /usr/lib/apache2/modules -type f \( -executable -o -name '*.so' \) \
    -exec ldd '{}' ';' 2>/dev/null \
    | awk '/=>/ { path = $(NF-1); if (index(path, "/usr/local/") == 1) next; gsub("^/(usr/)?", "", path); print "*" path }' \
    | sort -u \
    | xargs -r dpkg-query --search \
    | awk 'sub(":$", "", $1) { print $1 }' \
    | sort -u \
    | xargs -r apt-mark manual > /dev/null
apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false
rm -rf /var/lib/apt/lists/* /tmp/pear
php "$policy/security-policy.php"
php -m
