# Web Sharing via fly.io - Phase 6

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

## Phase 6: fly.io Deployment

**Goal:** Deploy Flask app to fly.io with persistent storage.

**Done when:** `fly deploy` succeeds, app accessible at `news-fixed.fly.dev` (or similar).

---

### Task 1: Create Dockerfile

**Files:**
- Create: `Dockerfile`

**Step 1: Create multistage Dockerfile for Python + WeasyPrint**

Create `Dockerfile` in project root:

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies for WeasyPrint compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libcairo2-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libffi-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.11-slim-bookworm

# Install only runtime dependencies for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/code/src"

# Copy application code
COPY code/ ./code/
COPY data/ ./data/

# Create cache directory (will be overwritten by volume mount)
RUN mkdir -p /app/cache

# Expose port
EXPOSE 8080

# Set environment defaults
ENV CACHE_DIR=/app/cache
ENV FEATURE_DUKE_SPORTS=false
ENV FEATURE_SF_LOCAL=false
ENV FEATURE_XKCD=false

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-class", "sync", "--timeout", "120", "--chdir", "/app/code/src", "web:app"]
```

**Step 2: Test Docker build locally (optional)**

Run: `docker build -t news-fixed-test .`
Expected: Build completes successfully

Note: This step is optional if you don't have Docker installed locally. The fly.io build will test it.

**Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile for fly.io deployment

Multistage build with Python 3.11 + WeasyPrint runtime dependencies.
Uses uv for fast dependency installation."
```

---

### Task 2: Create .dockerignore

**Files:**
- Create: `.dockerignore`

**Step 1: Create .dockerignore**

Create `.dockerignore` in project root:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Git
.git/
.gitignore

# Testing
.pytest_cache/
.coverage
htmlcov/

# Local development
.env
.env.local
*.log

# Documentation
docs/
*.md
!README.md

# Output (local generated PDFs)
output/

# Development files
.claude/
.beads/
```

**Step 2: Verify file created**

Run: `cat .dockerignore | head -5`
Expected: Shows first 5 lines

**Step 3: Commit**

```bash
git add .dockerignore
git commit -m "feat: add .dockerignore for smaller Docker builds"
```

---

### Task 3: Create fly.toml Configuration

**Files:**
- Create: `fly.toml`

**Step 1: Create fly.toml**

Create `fly.toml` in project root:

```toml
# fly.toml - fly.io configuration for News, Fixed

app = "news-fixed"
primary_region = "sjc"  # San Jose (close to SF)

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

  [http_service.concurrency]
    type = "requests"
    hard_limit = 100
    soft_limit = 80

[[http_service.checks]]
  grace_period = "30s"
  interval = "30s"
  method = "GET"
  path = "/health"
  protocol = "http"
  timeout = "10s"

[env]
  FLASK_ENV = "production"
  CACHE_DIR = "/app/cache"
  FEATURE_DUKE_SPORTS = "false"
  FEATURE_SF_LOCAL = "false"
  FEATURE_XKCD = "false"

[[vm]]
  memory = "1gb"
  cpu_kind = "shared"
  cpus = 1

[[mounts]]
  source = "news_fixed_cache"
  destination = "/app/cache"
```

**Step 2: Verify TOML syntax**

Run: `python -c "import tomllib; tomllib.load(open('fly.toml', 'rb')); print('Valid TOML')"`
Expected: `Valid TOML`

**Step 3: Commit**

```bash
git add fly.toml
git commit -m "feat: add fly.toml configuration for deployment

- San Jose region (sjc)
- 1GB memory for PDF generation
- Persistent volume for cache
- Feature flags disabled for public version"
```

---

### Task 4: Create fly.io App and Volume

**Files:**
- None (fly.io CLI commands)

**Step 1: Login to fly.io (if not already)**

Run: `fly auth login`

**Step 2: Create the fly.io app**

Run: `fly apps create news-fixed`

If the name is taken, choose an alternative like `news-fixed-alpha`.

**Step 3: Create persistent volume**

Run: `fly volumes create news_fixed_cache --app news-fixed --region sjc --size 1`

Expected: Volume created with ~1GB storage

**Step 4: Set secrets (API key)**

Run: `fly secrets set ANTHROPIC_API_KEY="sk-ant-..." --app news-fixed`

Replace with actual API key value.

**Step 5: Verify setup**

Run: `fly volumes list --app news-fixed`
Expected: Shows the `news_fixed_cache` volume

**Step 6: Document the setup (no commit, just notes)**

Note the app name and volume name for future reference.

---

### Task 5: Deploy to fly.io

**Files:**
- None (deployment commands)

**Step 1: Deploy the application**

Run: `fly deploy --app news-fixed`

This will:
1. Build the Docker image on fly.io's builders
2. Deploy to the configured region
3. Start the health checks

Expected: Deployment succeeds with "deployed successfully" message

**Step 2: Verify deployment**

Run: `fly status --app news-fixed`
Expected: Shows app running with healthy status

**Step 3: Test health endpoint**

Run: `curl -s https://news-fixed.fly.dev/health`
Expected: JSON response with `{"status":"healthy",...}`

**Step 4: Test landing page**

Run: `curl -s https://news-fixed.fly.dev/ | grep -o "News, Fixed"`
Expected: `News, Fixed`

**Step 5: Commit deployment confirmation**

```bash
git add -A
git commit -m "docs: Phase 6 complete - fly.io deployment

App deployed to news-fixed.fly.dev
- Dockerfile with multistage build
- fly.toml with volume mount
- Health checks passing"
```

---

### Task 6: Verify Volume Persistence

**Files:**
- None (verification only)

**Step 1: SSH into the running machine**

Run: `fly ssh console --app news-fixed`

**Step 2: Check cache directory**

Inside the SSH session:
```bash
ls -la /app/cache
df -h /app/cache
exit
```

Expected: Shows cache directory mounted with available space

**Step 3: Document verification**

The volume is correctly mounted and persists across deployments.

---

## Phase 6 Verification

After completing all tasks:

1. App accessible: `curl -s https://news-fixed.fly.dev/health`
2. Landing page works: `curl -s https://news-fixed.fly.dev/ | grep "News, Fixed"`
3. Volume mounted: `fly ssh console -C "ls /app/cache" --app news-fixed`
4. App status: `fly status --app news-fixed`

Phase 6 is complete when the app is deployed and accessible on fly.io.

**Important Notes:**

- The actual app URL depends on availability (might be `news-fixed.fly.dev` or similar)
- Update the app name in fly.toml if you needed to use a different name
- The ANTHROPIC_API_KEY must be set as a secret before generating PDFs
