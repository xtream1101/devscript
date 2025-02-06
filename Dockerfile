# Use Python 3.12 slim as base image
FROM python:3.12-slim AS builder

# Install uv
# Docs: https://docs.astral.sh/uv/guides/integration/docker/#available-images
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies using uv
RUN uv sync --locked --no-dev --no-install-project

# Install Node.js dependencies and build styles
RUN npm ci && \
    npm run build-styles

# Create final image
FROM python:3.12-slim

ARG VERSION

ENV VERSION=$VERSION

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy built files from builder
WORKDIR /app
COPY --from=builder /app /app

# Make entrypoint script executable
RUN chmod +x /app/docker/entrypoint.sh

# Expose ports for FastAPI and mkdocs
EXPOSE 8000 8080

# Set entrypoint
ENTRYPOINT ["/app/docker/entrypoint.sh"]
