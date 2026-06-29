# PHP Apache PostgreSQL Docker Base Images

Production-ready, highly optimized PHP Apache base images pre-configured with PostgreSQL support and other commonly required PHP extensions.

## Supported PHP Versions & Tags

Images are built for both `linux/amd64` and `linux/arm64` architectures.

- **PHP 8.4**: `8.4`, `8.4-latest`, `latest`
- **PHP 8.3**: `8.3`, `8.3-latest`
- **PHP 8.2**: `8.2`, `8.2-latest`
- **PHP 8.1**: `8.1`, `8.1-latest`
- **PHP 8.0**: `8.0`, `8.0-latest`
- **PHP 7.4**: `7.4`, `7.4-latest`

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
docker run -d -p 8080:80 -v $(pwd):/var/www/html --name my-php-app ghcr.io/chokunplayz/php-postgres:8.4

# Run PHP 7.4 image
docker run -d -p 8080:80 -v $(pwd):/var/www/html --name my-php-app ghcr.io/chokunplayz/php-postgres:7.4
```

Then visit `http://localhost:8080` in your browser.

### Docker Compose Example

Here is a template to spin up your PHP Apache container alongside a PostgreSQL database:

```yaml
version: '3.8'

services:
  web:
    image: ghcr.io/chokunplayz/php-postgres:8.4
    ports:
      - "8080:80"
    volumes:
      - .:/var/www/html
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

# 2. Configure production settings if needed
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"

# 3. Add custom PHP ini configurations (optional)
# RUN echo "memory_limit = 512M" > /usr/local/etc/php/conf.d/custom-limits.ini

# 4. Copy your application code to the Apache document root
COPY . /var/www/html/

# 5. Run Composer installs if a composer.json is present
RUN if [ -f "composer.json" ]; then \
        composer install --no-dev --optimize-autoloader --prefer-dist; \
    fi

# 6. Secure ownership permissions for Apache www-data user
RUN chown -R www-data:www-data /var/www/html
```

## Local Development & Building

You can build and test images locally using the provided `./build.sh` script, which builds from the unified `Dockerfile` using the `--build-arg PHP_VERSION` option.

```bash
# Build default version (PHP 8.2)
./build.sh

# Build a specific PHP version (e.g. PHP 8.4)
./build.sh --tag 8.4

# Build PHP 7.4
./build.sh --tag 7.4
```

## GitHub Actions Automated Builds

This project is configured with GitHub Actions to automatically build and push multi-architecture (`amd64` and `arm64`) Docker images to **GitHub Container Registry (GHCR)**.

- **Triggers**:
  - Pushes to the `main` branch
  - Tag releases matching the `v*` pattern
  - Pull requests targeting `main` (build verification only)

## License

MIT License