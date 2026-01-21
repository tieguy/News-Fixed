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
    # Clean up apt cache
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies (without dev dependencies)
RUN uv sync --frozen --no-dev

# Copy application code
COPY code/ ./code/

# Create cache directory (will be mounted as persistent volume in production)
RUN mkdir -p /app/cache

# Set environment variables
ENV PYTHONPATH=/app/code/src
ENV CACHE_DIR=/app/cache
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run with gunicorn
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--chdir", "/app/code/src", "web:app"]
