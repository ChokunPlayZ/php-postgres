#!/bin/bash

# Build script for PHP PostgreSQL Docker image
# Builds either server flavor and always refreshes the upstream base.

set -euo pipefail

# Configuration
IMAGE_NAME="php-postgres"
PHP_VERSION="8.4"
FLAVOR="apache"
DOCKERFILE=""
BUILD_FLAGS=(--pull)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    print_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

# Check if Dockerfile exists
check_dockerfile() {
    print_info "Checking for Dockerfile: $DOCKERFILE"
    
    if [ ! -f "$DOCKERFILE" ]; then
        print_error "Dockerfile '$DOCKERFILE' not found in current directory"
        exit 1
    fi
    
    print_success "Dockerfile found: $DOCKERFILE"
}

# Build the Docker image
build_image() {
    print_info "Building Docker image: $IMAGE_NAME:$IMAGE_TAG"
    print_info "Using Dockerfile: $DOCKERFILE"
    
    # Build the image
    if docker build "${BUILD_FLAGS[@]}" -f "$DOCKERFILE" --build-arg PHP_VERSION="$PHP_VERSION" -t "$IMAGE_NAME:$IMAGE_TAG" .; then
        print_success "Docker image built successfully: $IMAGE_NAME:$IMAGE_TAG"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
    
    # Never let an EOL or older branch replace the default latest tag.
    if [[ "$PHP_VERSION" == "8.4" ]] && docker tag "$IMAGE_NAME:$IMAGE_TAG" "$IMAGE_NAME:$LATEST_TAG"; then
        print_success "Image tagged as: $IMAGE_NAME:$LATEST_TAG"
    fi
}

# Show image information
show_image_info() {
    print_info "Image information:"
    docker images | grep "$IMAGE_NAME" || true
    
    print_info "Image size:"
    docker inspect "$IMAGE_NAME:$IMAGE_TAG" --format='{{.Size}}' | numfmt --to=iec || true
}

# Main execution
main() {
    echo "🐳 Building PHP PostgreSQL Docker Image"
    echo "======================================"
    
    check_docker
    check_dockerfile
    build_image
    show_image_info
    
    echo ""
    print_success "Build completed successfully!"
    echo ""
    print_info "To run the container:"
    echo "  docker run -d -p 8080:80 --name php-postgres-container $IMAGE_NAME:$IMAGE_TAG"
    echo ""
    print_info "To run with PostgreSQL connection:"
    echo "  docker run -d -p 8080:80 -e POSTGRES_HOST=your-host -e POSTGRES_DB=your-db -e POSTGRES_USER=your-user -e POSTGRES_PASSWORD=your-password --name php-postgres-container $IMAGE_NAME:$IMAGE_TAG"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name|--tag|--flavor|--dockerfile)
            if [[ $# -lt 2 || -z "$2" || "$2" == --* ]]; then
                print_error "Option $1 requires a value"
                exit 1
            fi
            ;;
    esac
    case $1 in
        --name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --tag)
            PHP_VERSION="$2"
            shift 2
            ;;
        --flavor)
            FLAVOR="$2"
            shift 2
            ;;
        --dockerfile)
            DOCKERFILE="$2"
            shift 2
            ;;
        --no-cache)
            BUILD_FLAGS+=(--no-cache)
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --name NAME        Set the image name (default: php-postgres)"
            echo "  --tag TAG          Set the PHP version / tag (default: 8.4)"
            echo "  --flavor FLAVOR    Set the web server: apache or nginx (default: apache)"
            echo "  --dockerfile FILE  Override the flavor's Dockerfile"
            echo "  --no-cache         Refresh OS packages and all build layers"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Build with default settings"
            echo "  $0 --name my-php --tag 8.4            # Build with custom tag"
            echo "  $0 --flavor nginx --tag 8.4           # Build php-postgres:8.4-nginx"
            echo "  $0 --dockerfile Dockerfile.custom    # Use a different Dockerfile"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

case "$FLAVOR" in
    apache)
        DOCKERFILE="${DOCKERFILE:-Dockerfile}"
        IMAGE_TAG="$PHP_VERSION"
        LATEST_TAG=latest
        ;;
    nginx)
        DOCKERFILE="${DOCKERFILE:-Dockerfile.nginx}"
        IMAGE_TAG="$PHP_VERSION-nginx"
        LATEST_TAG=latest-nginx
        ;;
    *)
        print_error "Unsupported flavor: $FLAVOR (expected apache or nginx)"
        exit 1
        ;;
esac

# Run the main function
main
