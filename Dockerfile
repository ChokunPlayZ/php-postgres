# Minor tags receive upstream security releases; the runtime policy rejects stale bases.
ARG PHP_VERSION=8.4
FROM php:${PHP_VERSION}-apache

COPY docker/ /usr/local/lib/php-postgres/

# Rebuild legacy engines with the official PHP2Shell backports before building extensions.
RUN sh /usr/local/lib/php-postgres/install-php.sh

RUN cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
COPY docker/php-security.ini /usr/local/etc/php/conf.d/zz-security.ini
COPY docker/apache-security.conf /etc/apache2/conf-available/zz-php-postgres-security.conf
RUN set -eux; \
    a2enmod rewrite headers reqtimeout; \
    a2dismod -f autoindex status; \
    a2enconf zz-php-postgres-security; \
    mkdir -p /usr/local/share/php-postgres; \
    printf 'OK\n' > /usr/local/share/php-postgres/health.txt; \
    php /usr/local/lib/php-postgres/security-policy.php; \
    apache2ctl configtest

# Stay on Composer's stable major, not an unbounded latest tag.
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html
COPY index.php .

# Application code must not be writable by the web worker. Grant write access only
# to application-specific cache/upload directories in derived images.
RUN chown root:root /var/www/html /var/www/html/index.php \
    && chmod 0755 /var/www/html \
    && chmod 0644 /var/www/html/index.php

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["curl", "--fail", "--silent", "--show-error", "--max-time", "3", "http://127.0.0.1/healthz"]
