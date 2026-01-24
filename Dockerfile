# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

# FCIS: Docker image for News Fixed web application with WeasyPrint PDF generation.

FROM python:3.11-slim-bookworm

# Install system dependencies for WeasyPrint
# See: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint dependencies
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Fonts for PDF rendering
    fonts-liberation \
    fonts-dejavu-core \
    # For downloading supercronic
    curl \
    # Clean up apt cache
    && rm -rf /var/lib/apt/lists/*

# Install supercronic for cron scheduling (runs in foreground, no syslog needed)
ARG SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64
ARG SUPERCRONIC_SHA1SUM=71b0d58cc53f6bd72cf2f293e09e294b79c666d8
RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  supercronic-linux-amd64" | sha1sum -c - \
    && chmod +x supercronic-linux-amd64 \
    && mv supercronic-linux-amd64 /usr/local/bin/supercronic

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first (for layer caching)
# README.md is required by pyproject.toml metadata
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (without dev dependencies)
RUN uv sync --frozen --no-dev

# Copy application code
COPY code/ ./code/

# Copy crontab and startup script
COPY crontab ./crontab
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Create cache directory (will be mounted as persistent volume in production)
RUN mkdir -p /app/cache

# Set environment variables
ENV PYTHONPATH=/app/code/src
ENV CACHE_DIR=/app/cache
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Default command - runs both cron scheduler and web server
CMD ["/app/start.sh"]
