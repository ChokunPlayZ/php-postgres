# PHP Apache PostgreSQL Docker Base Images

PHP Apache base images with PostgreSQL support, production defaults, engine security checks and automated vulnerability scans. No base image can guarantee protection against application vulnerabilities or every exploit.

## Supported PHP Versions & Tags

Images are built for both `linux/amd64` and `linux/arm64` architectures.

- **PHP 8.4**: `8.4`, `8.4-latest`, `latest`
- **PHP 8.5**: `8.5`, `8.5-latest`
- **PHP 8.3**: `8.3`, `8.3-latest`
- **PHP 8.2**: `8.2`, `8.2-latest`
- **PHP 8.1 (EOL)**: `8.1`, `8.1-latest`
- **PHP 8.0 (EOL)**: `8.0`, `8.0-latest`
- **PHP 7.4 (EOL)**: `7.4`, `7.4-latest`

### PHP2Shell security update

The build requires PHP **8.2.35 / 8.3.36 / 8.4.27 / 8.5.12 or newer within the same branch**, fixing **CVE-2026-109618 and CVE-2026-109619**. Stale or unsupported runtimes fail the build instead of producing an apparently patched image.

For **7.4.33, 8.0.30 and 8.1.34**, the build applies the PHP security team's [official emergency source backports](https://www.php.net/archive/2026.php#2026-10-21-5), pinned to immutable commits and SHA-256 digests, and **recompiles both the CLI and Apache module**. Extensions are built afterward, and the retained source archive is also patched. The backport record is `/usr/local/share/php-postgres/php2shell-backport`; the PHP version string is unchanged. Legacy OOM now terminates the worker immediately, without shutdown callbacks; expect failed requests and worker replacement when limits are reached.

**Legacy PHP remains end-of-life. These minimal backports address PHP2Shell, not all other known or future PHP CVEs.** Upgrade to maintained PHP or use an extended-security vendor if you need comprehensive legacy coverage. PHP 7.0–7.3 are not supported by this project. See [PHP's support schedule](https://www.php.net/supported-versions.php); PHP 8.2 reaches EOL on December 31, 2026.

`session.upload_progress.enabled=Off` is applied before request parsing and locked in Apache configuration. This also blocks the follow-up session vector **CVE-2026-115560**, per [PHP's October 23 advisory](https://www.php.net/archive/2026.php#2026-10-23-1). Disabling this feature alone is **not** a PHP2Shell fix.

Already-running containers are not patched by a repository change: after a successful image publication, **pull and recreate every web container and long-running PHP worker**, including derived application images. For Compose: `docker compose pull && docker compose up -d --force-recreate`. Rebuild derived images with `docker build --pull --no-cache` first. Old registry digests and cached copies remain vulnerable.

### Additional protections and compatibility changes

- Uses `php.ini-production`; errors are logged, not displayed; PHP/Apache version disclosure is reduced.
- Disables remote PHP includes and dynamic extension loading. PHP shell functions are not blanket-disabled: Composer and some applications need subprocesses, and `disable_functions` is not a memory-safety boundary.
- Apache rejects bodies over **32 MiB**, including chunked requests. PHP uploads are limited to **16 MiB per file**, 10 files, 1,000 variables and 32 nesting levels; request read timeouts reduce slow-client exposure.
- Disables directory listings, TRACE, CGI execution and server-side includes; denies dotfiles (except `.well-known`), common deployment files and PHP-like files under `/var/www/html/uploads`. Add equivalent rules for **every other application upload directory**, and preferably store uploads outside the document root.
- `.htaccess` rewrite/authentication rules still work, but PHP and `Options` overrides are no longer permitted. Move PHP settings into startup INI or trusted Apache configuration. Audit custom configuration for invalid/deprecated directives.
- Application files are root-owned, not web-worker-owned. Grant `www-data` write access only to specific cache/session/upload directories, never the entire codebase. Bind mounts retain host permissions.
- The starter dashboard is **disabled by default** to avoid exposing versions and database details. For private development only, opt in with `-e ENABLE_STARTER_DASHBOARD=1`; it is not an authenticated admin UI.
- `/healthz` checks Apache independently of the application's database and routes. It is a liveness check, not an application-readiness check.
- OS packages are upgraded during clean builds, temporary build dependencies are removed, and Redis is pinned to compatible release `6.3.0`.

Keep application dependencies patched (`composer audit --locked`), validate uploads and user input, isolate database credentials and restrict outbound networking. Never mount the Docker socket or run these containers privileged. Set container memory/CPU limits and use `--security-opt no-new-privileges:true`; Apache's parent still starts as root and drops privileges for request workers. These images are not a sandbox for untrusted PHP.

Session cookies default to HttpOnly and SameSite=Lax. Set `session.cookie_secure=On` in a trusted INI file for HTTPS deployments; HSTS and a site-specific CSP belong at your TLS/application boundary.

## Included PHP Extensions

These images include the following commonly required PHP extensions out-of-the-box:
- **Database**: `pdo`, `pdo_pgsql`, `pgsql`, `pdo_mysql`, `mysqli`
- **Caching & Performance**: `opcache`, `redis` (via PECL)
- **Utilities**: `zip`, `bz2`, `calendar`, `exif`, `gd` (with FreeType, JPEG, and WebP support), `gettext`, `intl`, `mbstring`, `soap`, `xml`, `bcmath`, `pcntl`, `sockets`
- **Tools**: **Composer** is pre-installed at `/usr/bin/composer`
- **Apache**: Rewrite module (`mod_rewrite`) is enabled by default.

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

### Docker Compose Example

Here is a template to spin up your PHP Apache container alongside a PostgreSQL database:

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

# 2. Production INI and security defaults are already installed

# 3. Add custom PHP ini configurations (optional)
# RUN echo "memory_limit = 512M" > /usr/local/etc/php/conf.d/zzz-app.ini

# 4. Copy your application code to the Apache document root
COPY . /var/www/html/

# 5. Run Composer installs if a composer.json is present
RUN if [ -f "composer.json" ]; then \
        composer install --no-dev --optimize-autoloader --prefer-dist; \
    fi

# 6. Keep code root-owned; grant write access only to your app's required directories
# RUN install -d -o www-data -g www-data -m 0750 /var/www/html/var/cache
```

## Local Development & Building

You can build and test images locally using the provided `./build.sh` script, which builds from the unified `Dockerfile` using the `--build-arg PHP_VERSION` option.

Container smoke tests require a running Docker daemon, Bash, curl and Python 3. Downstream extension builds must install their development packages (including `$PHPIZE_DEPS`) first, since compilers are no longer retained in the runtime image.

```bash
# Build default version (PHP 8.4), refreshing packages as well as the base
./build.sh --no-cache

# Build a specific PHP version (e.g. PHP 8.4)
./build.sh --tag 8.4

# Build PHP 7.4 with the emergency engine backport (still EOL)
./build.sh --tag 7.4 --no-cache

# Run policy, extension, bounded legacy OOM and HTTP security smoke tests
bash tests/smoke.sh php-postgres:8.4

# Test build-script arguments without Docker
python3 tests/build-script-test.py
```

## GitHub Actions Automated Builds

This project is configured with GitHub Actions to automatically build and push multi-architecture (`amd64` and `arm64`) Docker images to **GitHub Container Registry (GHCR)**.

- **Triggers**:
  - Pushes to the `main` branch
  - Tag releases matching the `v*` pattern
  - Pull requests targeting `main` (build verification only)
  - Weekly clean rebuilds and manual workflow dispatch (refreshes OS security updates)

Each PHP version is built and smoke-tested on **both architectures**, including legacy OOM behavior and Apache protections. Trivy retains a JSON report of **all known findings, including unfixed vulnerabilities**, and blocks publication for **fixable HIGH/CRITICAL findings**. Unfixed findings are reported, not proof of safety; review the artifacts, especially for EOL images. There are no blanket CVE suppressions. A version-only scanner may still report PHP2Shell on an emergency-backported legacy runtime; inspect the source-backport record and regression results rather than concealing findings.

Only the exact tested/scanned platform image digests are assembled into public multi-architecture tags—there is no unchecked rebuild after scanning. Staging tags use `build-<run>-<attempt>-php<version>-<arch>` and are not release tags. If any matrix check fails, release tags are not updated.

## License

MIT License
