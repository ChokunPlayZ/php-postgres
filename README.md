# PHP PostgreSQL Docker Base Images (Apache / Nginx)

PHP base images with Apache or Nginx + PHP-FPM, PostgreSQL support, production defaults, engine security checks and automated vulnerability scans. No base image can guarantee protection against application vulnerabilities or every exploit.

## Supported PHP Versions & Tags

Images are built for both `linux/amd64` and `linux/arm64` architectures.

Existing tags continue to use **Apache**:

- **PHP 8.4**: `8.4`, `8.4-latest`, `latest`
- **PHP 8.5**: `8.5`, `8.5-latest`
- **PHP 8.3**: `8.3`, `8.3-latest`
- **PHP 8.2**: `8.2`, `8.2-latest`
- **PHP 8.1 (EOL)**: `8.1`, `8.1-latest`
- **PHP 8.0 (EOL)**: `8.0`, `8.0-latest`
- **PHP 7.4 (EOL)**: `7.4`, `7.4-latest`

For **Nginx + PHP-FPM**, append `-nginx` to any of those tags: `8.4-nginx`, `8.4-latest-nginx`, `latest-nginx`, `8.5-nginx`, etc. Both `latest` and `latest-nginx` track PHP 8.4 in their respective flavors. The same PHP versions and EOL warnings apply to both flavors.

### PHP2Shell security update

The build requires PHP **8.2.35 / 8.3.36 / 8.4.27 / 8.5.12 or newer within the same branch**, fixing **CVE-2026-109618 and CVE-2026-109619**. Stale or unsupported runtimes fail the build instead of producing an apparently patched image.

For **7.4.33, 8.0.30 and 8.1.34**, the build applies the PHP security team's [official emergency source backports](https://www.php.net/archive/2026.php#2026-10-21-5), pinned to immutable commits and SHA-256 digests, and **recompiles both the CLI and the Apache module or PHP-FPM binary**. Extensions are built afterward, and the retained source archive is also patched. The backport record is `/usr/local/share/php-postgres/php2shell-backport`; the PHP version string is unchanged. Legacy OOM now terminates the worker immediately, without shutdown callbacks; expect failed requests and worker replacement when limits are reached.

**Legacy PHP remains end-of-life. These minimal backports address PHP2Shell, not all other known or future PHP CVEs.** Upgrade to maintained PHP or use an extended-security vendor if you need comprehensive legacy coverage. PHP 7.0–7.3 are not supported by this project. See [PHP's support schedule](https://www.php.net/supported-versions.php); PHP 8.2 reaches EOL on December 31, 2026.

Debian Bullseye bases use Debian's frozen archive for security packages because those package files are no longer on the live security mirror. Archive signatures remain verified, but **this does not provide ongoing OS security updates**. Newer Debian bases keep their normal repositories.

`session.upload_progress.enabled=Off` is applied before request parsing and locked in Apache or PHP-FPM configuration. This also blocks the follow-up session vector **CVE-2026-115560**, per [PHP's October 23 advisory](https://www.php.net/archive/2026.php#2026-10-23-1). Disabling this feature alone is **not** a PHP2Shell fix.

Already-running containers are not patched by a repository change: after a successful image publication, **pull and recreate every web container and long-running PHP worker**, including derived application images. For Compose: `docker compose pull && docker compose up -d --force-recreate`. Rebuild derived images with `docker build --pull --no-cache` first. Old registry digests and cached copies remain vulnerable.

### Additional protections and compatibility changes

- Uses `php.ini-production`; errors are logged, not displayed; PHP/web server version disclosure is reduced.
- Disables remote PHP includes and dynamic extension loading. PHP shell functions are not blanket-disabled: Composer and some applications need subprocesses, and `disable_functions` is not a memory-safety boundary.
- Both web servers reject bodies over **32 MiB**, including chunked requests. PHP uploads are limited to **16 MiB per file**, 10 files, 1,000 variables and 32 nesting levels; request read timeouts reduce slow-client exposure.
- Disables directory listings, TRACE, CGI execution and server-side includes; denies dotfiles (except `.well-known`), common deployment files and PHP-like files under `/var/www/html/uploads`. Add equivalent rules for **every other application upload directory**, and preferably store uploads outside the document root.
- In Apache, `.htaccess` rewrite/authentication rules still work, but PHP and `Options` overrides are no longer permitted. Move PHP settings into startup INI or trusted Apache configuration. Audit custom configuration for invalid/deprecated directives.
- Nginx does **not** read `.htaccess`. It uses front-controller routing to `index.php` by default and only forwards existing `.php` files to PHP-FPM. PHP-FPM listens on a local Unix socket, not TCP port 9000; application environment variables remain available to PHP.
- Application files are root-owned, not web-worker-owned. Grant `www-data` write access only to specific cache/session/upload directories, never the entire codebase. Bind mounts retain host permissions.
- The starter dashboard is **disabled by default** to avoid exposing versions and database details. For private development only, opt in with `-e ENABLE_STARTER_DASHBOARD=1`; it is not an authenticated admin UI.
- `/healthz` checks the web server independently of the application's database and routes. It is a liveness check, not an application-readiness check. In the Nginx flavor, a supervisor script stops the container if either Nginx or PHP-FPM exits and gracefully stops both on container shutdown.
- OS packages are upgraded during clean builds, temporary build dependencies are removed, and Redis is pinned to compatible release `6.3.0`.

Keep application dependencies patched (`composer audit --locked`), validate uploads and user input, isolate database credentials and restrict outbound networking. Never mount the Docker socket or run these containers privileged. Set container memory/CPU limits and use `--security-opt no-new-privileges:true`; server master processes still start as root and drop privileges to `www-data` for request workers. These images are not a sandbox for untrusted PHP.

If using `--cap-drop ALL`, retain `CHOWN`, `SETUID`, `SETGID`, `KILL` and `NET_BIND_SERVICE`, as in the smoke tests. `KILL` lets the root master processes signal their `www-data` workers; removing it can prevent PHP-FPM/Nginx from shutting down.

Session cookies default to HttpOnly and SameSite=Lax. Set `session.cookie_secure=On` in a trusted INI file for HTTPS deployments; HSTS and a site-specific CSP belong at your TLS/application boundary.

## Included PHP Extensions

These images include the following commonly required PHP extensions out-of-the-box:
- **Database**: `pdo`, `pdo_pgsql`, `pgsql`, `pdo_mysql`, `mysqli`
- **Caching & Performance**: `opcache`, `redis` (via PECL)
- **Utilities**: `zip`, `bz2`, `calendar`, `exif`, `gd` (with FreeType, JPEG, and WebP support), `gettext`, `intl`, `mbstring`, `soap`, `xml`, `bcmath`, `pcntl`, `sockets`
- **Tools**: **Composer** is pre-installed at `/usr/bin/composer`
- **Apache**: Rewrite module (`mod_rewrite`) is enabled by default.
- **Nginx flavor**: Nginx and PHP-FPM run together in one container, with access/error logs sent to container stdout/stderr. Apache is not installed.

## Usage

### Quick Start (Run Apache)

To run a container and mount your current working directory to the Apache document root (`/var/www/html`):

```bash
# Run PHP 8.4 image
docker run -d -p 8080:80 -v "$(pwd):/var/www/html:ro" --name my-php-app ghcr.io/chokunplayz/php-postgres:8.4

# Mount code read-only where possible; create separate writable application volumes.
docker run -d --memory=512m --cpus=2 --security-opt=no-new-privileges:true -p 8080:80 -v "$(pwd):/var/www/html:ro" --name my-php-app-hardened ghcr.io/chokunplayz/php-postgres:8.4
```

Then visit `http://localhost:8080` in your browser.

### Quick Start (Run Nginx + PHP-FPM)

Use the same port, document root and database environment variables as the Apache flavor:

```bash
docker run -d -p 8080:80 -v "$(pwd):/var/www/html:ro" --name my-php-nginx ghcr.io/chokunplayz/php-postgres:8.4-nginx
```

For custom routing, replace `/etc/nginx/conf.d/default.conf` in a derived image or mount your configuration there read-only. Preserve the health endpoint and security rules from `docker/nginx-default.conf`, and add execution denials for any additional upload directories. Pool overrides belong in `/usr/local/etc/php-fpm.d/zzz-app.conf`; startup INI overrides belong in `/usr/local/etc/php/conf.d/zzz-app.ini`. Nginx ignores `.htaccess`, so migrate any application rewrite/authentication rules before switching flavors.

The default command starts both services. Overriding it with `php`, `composer` or another command runs only that command; overriding it with `nginx` alone will not start PHP-FPM.

### Docker Compose Example

Here is a template to spin up your PHP Apache container alongside a PostgreSQL database. Use `image: ghcr.io/chokunplayz/php-postgres:8.4-nginx` for Nginx instead; the rest is unchanged:

```yaml
services:
  web:
    image: ghcr.io/chokunplayz/php-postgres:8.4
    ports:
      - "8080:80"
    volumes:
      - .:/var/www/html:ro
    mem_limit: 512m
    cpus: 2
    security_opt:
      - no-new-privileges:true
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=mydb
      - DB_USER=user
      - DB_PASS=password
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Database Connection Configuration

Configure your application using standard environment variables (or customize them in your code):
- `DB_HOST` - Database host address
- `DB_PORT` - Database port (default: `5432`)
- `DB_NAME` - Database name
- `DB_USER` - Database username
- `DB_PASS` - Database password

## Building Custom Images Based on This Base Image

You can easily build custom production images for your applications using this image as your base. 

Create a `Dockerfile` in your application root:

```dockerfile
# 1. Use the pre-built image matching your desired PHP version
FROM ghcr.io/chokunplayz/php-postgres:8.4
# For Nginx + PHP-FPM, use ghcr.io/chokunplayz/php-postgres:8.4-nginx instead

# 2. Production INI and security defaults are already installed

# 3. Add custom PHP ini configurations (optional)
# RUN echo "memory_limit = 512M" > /usr/local/etc/php/conf.d/zzz-app.ini

# 4. Copy your application code to the document root (same for both flavors)
COPY . /var/www/html/

# 5. Run Composer installs if a composer.json is present
RUN if [ -f "composer.json" ]; then \
        composer install --no-dev --optimize-autoloader --prefer-dist; \
    fi

# 6. Keep code root-owned; grant write access only to your app's required directories
# RUN install -d -o www-data -g www-data -m 0750 /var/www/html/var/cache
```

## Local Development & Building

You can build and test images locally using the provided `./build.sh` script. It uses `Dockerfile` for Apache (the default) or `Dockerfile.nginx` for `--flavor nginx`, passing the PHP branch with `--build-arg PHP_VERSION` in both cases. Nginx builds are tagged with `-nginx` and never overwrite Apache tags.

Container smoke tests require a running Docker daemon, Bash, curl 7.71+ and Python 3. Startup health probes retry connection resets and empty replies within a bounded retry window; subsequent security assertions still fail normally. Downstream extension builds must install their development packages (including `$PHPIZE_DEPS`) first, since compilers are no longer retained in the runtime image.

Use a native builder for legacy images: QEMU-emulated ARM64 builds can segfault while upgrading Debian Bullseye's `libc-bin` (post-install script exit 139). Build ARM64 on an ARM64 Docker host and AMD64 on an AMD64 host; do not skip package upgrades to bypass this failure.

```bash
# Build default version (PHP 8.4), refreshing packages as well as the base
./build.sh --no-cache

# Build a specific PHP version (e.g. PHP 8.4)
./build.sh --tag 8.4

# Build PHP 7.4 with the emergency engine backport (still EOL)
./build.sh --tag 7.4 --no-cache

# Build Nginx + PHP-FPM (php-postgres:8.4-nginx and latest-nginx)
./build.sh --flavor nginx --tag 8.4 --no-cache

# Run policy, extension, bounded legacy OOM and HTTP security smoke tests
bash tests/smoke.sh php-postgres:8.4
bash tests/smoke.sh php-postgres:8.4-nginx nginx

# Test commands, container permissions, APT, HTTP readiness and supervision without Docker
python3 tests/build-script-test.py
python3 tests/smoke-command-test.py
python3 tests/apt-sources-test.py
python3 tests/http-readiness-test.py
python3 tests/nginx-start-test.py # Lifecycle tests require Bash 4.3+; skipped on older Bash
```

## GitHub Actions Automated Builds

This project is configured with GitHub Actions to automatically build and push multi-architecture (`amd64` and `arm64`) Docker images to **GitHub Container Registry (GHCR)**.

Builds and smoke tests run on native `ubuntu-24.04` (AMD64) and `ubuntu-24.04-arm` (ARM64) runners, without QEMU emulation. Each job verifies the Docker daemon architecture before building.

- **Triggers**:
  - Pushes to the `main` branch
  - Tag releases matching the `v*` pattern
  - Pull requests targeting `main` (build verification only)
  - Weekly clean rebuilds and manual workflow dispatch (refreshes OS security updates)

Each PHP version and **both server flavors** are built and smoke-tested on **both architectures**, including legacy OOM behavior and web server protections. Nginx tests also cover front-controller routing, missing scripts, FastCGI isolation and process shutdown. Trivy retains a JSON report of **all known findings, including unfixed vulnerabilities**, and blocks publication for **fixable HIGH/CRITICAL findings**. Unfixed findings are reported, not proof of safety; review the artifacts, especially for EOL images. There are no blanket CVE suppressions. A version-only scanner may still report PHP2Shell on an emergency-backported legacy runtime; inspect the source-backport record and regression results rather than concealing findings.

Only the exact tested/scanned platform image digests are assembled into public multi-architecture tags—there is no unchecked rebuild after scanning. Staging tags use `build-<run>-<attempt>-php<version>-<flavor>-<arch>` and are not release tags. Caches, vulnerability reports and tested digests are isolated by flavor. If any matrix check fails, release tags are not updated.

## License

MIT License
