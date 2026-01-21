# Web Sharing via fly.io - Phase 4

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

## Phase 4: Flask Web Application

**Goal:** Web interface with landing page and download endpoint.

**Done when:** `flask run` serves landing page, download button returns PDF.

---

### Task 1: Add Flask and Gunicorn Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add Flask and Gunicorn to dependencies**

In `pyproject.toml`, add to the `dependencies` list (after `httpx`):

```toml
    "flask>=3.0.0",
    "gunicorn>=21.0.0",
```

**Step 2: Sync dependencies**

Run: `uv sync`
Expected: Flask and Gunicorn install successfully

**Step 3: Verify Flask installed**

Run: `uv run python -c "import flask; print(flask.__version__)"`
Expected: Shows Flask version (3.x.x)

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add Flask and Gunicorn dependencies

Required for web application deployment."
```

---

### Task 2: Create Flask Application

**Files:**
- Create: `code/src/web.py`

**Step 1: Create the Flask application**

Create `code/src/web.py`:

```python
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Flask web application for News, Fixed."""

import os
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent.parent / "templates"),
    static_folder=str(Path(__file__).parent.parent / "static")
)

# Configuration
app.config['CACHE_DIR'] = Path(os.getenv('CACHE_DIR', 'cache'))


def get_current_week() -> str:
    """Get current ISO week in YYYY-WWW format."""
    from datetime import datetime
    now = datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


def get_cached_pdf_path() -> Path | None:
    """Get path to current week's cached PDF if it exists."""
    week = get_current_week()
    cache_dir = app.config['CACHE_DIR']
    pdf_path = cache_dir / week / "combined.pdf"

    if pdf_path.exists():
        return pdf_path
    return None


@app.route('/')
def index():
    """Landing page."""
    week = get_current_week()
    has_pdf = get_cached_pdf_path() is not None

    return render_template(
        'landing.html',
        week=week,
        has_pdf=has_pdf
    )


@app.route('/download')
def download():
    """Download the current week's PDF."""
    pdf_path = get_cached_pdf_path()

    if pdf_path is None:
        return jsonify({
            'error': 'No PDF available for this week yet',
            'week': get_current_week()
        }), 404

    week = get_current_week()
    download_name = f"news_fixed_{week}.pdf"

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )


@app.route('/health')
def health():
    """Health check endpoint for fly.io."""
    return jsonify({
        'status': 'healthy',
        'service': 'news-fixed',
        'week': get_current_week()
    }), 200


if __name__ == '__main__':
    # Development server only - use gunicorn in production
    app.run(debug=True, port=8080)
```

**Step 2: Verify Flask app loads**

Run: `cd code && python -c "from web import app; print('App loaded:', app.name)"`
Expected: `App loaded: web`

**Step 3: Commit**

```bash
git add code/src/web.py
git commit -m "feat: create Flask web application

Routes:
- / : Landing page
- /download : PDF download
- /health : Health check for fly.io"
```

---

### Task 3: Create Landing Page Template

**Files:**
- Create: `code/templates/landing.html`

**Step 1: Create the landing page template**

Create `code/templates/landing.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News, Fixed - Weekly Edition</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 2rem 1rem;
            background: #fafafa;
        }

        header {
            text-align: center;
            margin-bottom: 2rem;
        }

        h1 {
            font-family: 'Times New Roman', serif;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }

        .tagline {
            color: #666;
            font-style: italic;
        }

        .alpha-notice {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 2rem;
        }

        .alpha-notice h2 {
            font-size: 1rem;
            color: #856404;
            margin-bottom: 0.5rem;
        }

        .alpha-notice p {
            font-size: 0.9rem;
            color: #856404;
        }

        .download-section {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            margin-bottom: 2rem;
        }

        .week-label {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 1rem;
        }

        .download-btn {
            display: inline-block;
            background: #2563eb;
            color: white;
            padding: 1rem 2rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            font-size: 1.1rem;
            transition: background 0.2s;
        }

        .download-btn:hover {
            background: #1d4ed8;
        }

        .download-btn.disabled {
            background: #9ca3af;
            cursor: not-allowed;
        }

        .not-available {
            color: #666;
            font-style: italic;
        }

        .about {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 1.5rem;
        }

        .about h2 {
            font-size: 1.2rem;
            margin-bottom: 1rem;
        }

        .about p {
            margin-bottom: 1rem;
            font-size: 0.95rem;
        }

        .about ul {
            margin-left: 1.5rem;
            margin-bottom: 1rem;
        }

        .about li {
            margin-bottom: 0.5rem;
            font-size: 0.95rem;
        }

        footer {
            text-align: center;
            margin-top: 2rem;
            color: #666;
            font-size: 0.85rem;
        }

        footer a {
            color: #2563eb;
        }
    </style>
</head>
<body>
    <header>
        <h1>News, Fixed</h1>
        <p class="tagline">Global Good News, One Day At A Time</p>
    </header>

    <div class="alpha-notice">
        <h2>Private Alpha</h2>
        <p>
            Hey! You're seeing this because Luis shared the link with you.
            This is a weekly newspaper of positive news stories, rewritten for kids ages 10-14.
            Print it out for your family's breakfast table!
        </p>
    </div>

    <div class="download-section">
        <p class="week-label">Week {{ week }}</p>
        {% if has_pdf %}
        <a href="/download" class="download-btn">Download This Week's Edition</a>
        {% else %}
        <p class="not-available">This week's edition is being prepared...</p>
        <p class="not-available" style="margin-top: 0.5rem; font-size: 0.85rem;">Check back Monday morning!</p>
        {% endif %}
    </div>

    <div class="about">
        <h2>What is News, Fixed?</h2>
        <p>
            A weekly 8-page newspaper featuring positive news from around the world,
            rewritten for bright 10-14 year olds. Each day covers a different theme:
        </p>
        <ul>
            <li><strong>Monday:</strong> Health & Education</li>
            <li><strong>Tuesday:</strong> Environment & Conservation</li>
            <li><strong>Wednesday:</strong> Technology & Energy</li>
            <li><strong>Thursday:</strong> Society & Youth Movements</li>
        </ul>
        <p>
            Content is sourced from <a href="https://fixthe.news" target="_blank">Fix The News</a>,
            a newsletter that highlights solutions journalism and evidence of human progress.
        </p>
    </div>

    <footer>
        <p>
            Made with care by <a href="https://lu.is" target="_blank">Luis Villa</a>
        </p>
    </footer>
</body>
</html>
```

**Step 2: Verify template renders**

Run: `cd code && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); t = env.get_template('landing.html'); print(t.render(week='2026-W03', has_pdf=True)[:100])"`
Expected: Shows first 100 chars of rendered HTML

**Step 3: Commit**

```bash
git add code/templates/landing.html
git commit -m "feat: add landing page template

Private alpha messaging with download button for weekly PDF."
```

---

### Task 4: Create Static Directory

**Files:**
- Create: `code/static/.gitkeep`

**Step 1: Create static directory**

Run: `mkdir -p code/static && touch code/static/.gitkeep`

**Step 2: Verify directory exists**

Run: `ls -la code/static/`
Expected: Shows `.gitkeep` file

**Step 3: Commit**

```bash
git add code/static/.gitkeep
git commit -m "feat: add static directory for web assets"
```

---

### Task 5: Test Flask Application Locally

**Files:**
- None (verification only)

**Step 1: Start Flask development server**

Run in background: `cd code/src && uv run python web.py &`

Wait 2 seconds, then:

Run: `curl -s http://localhost:8080/health`
Expected: `{"service":"news-fixed","status":"healthy","week":"2026-WXX"}`

**Step 2: Test landing page**

Run: `curl -s http://localhost:8080/ | grep -o "News, Fixed"`
Expected: `News, Fixed`

**Step 3: Test download (should 404 without cached PDF)**

Run: `curl -s http://localhost:8080/download`
Expected: `{"error":"No PDF available for this week yet",...}`

**Step 4: Stop Flask server**

Run: `pkill -f "python web.py"` (or use Ctrl+C if running in foreground)

**Step 5: Commit verification**

```bash
git add -A
git commit -m "docs: Phase 4 complete - Flask web application

- Flask app with /, /download, /health routes
- Landing page template with alpha messaging
- Ready for caching layer integration"
```

---

## Phase 4 Verification

After completing all tasks:

1. Verify Flask installed: `uv run python -c "import flask; print(flask.__version__)"`
2. Verify web.py exists: `ls code/src/web.py`
3. Verify landing template: `ls code/templates/landing.html`
4. Test health endpoint: `cd code/src && uv run python -c "from web import app; client = app.test_client(); print(client.get('/health').json)"`

Phase 4 is complete when Flask app serves all three routes correctly.
