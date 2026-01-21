# Web Sharing via fly.io - Phase 5

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

## Phase 5: Caching Layer

**Goal:** Cache generated PDFs by ISO week for instant downloads.

**Done when:** Second request for same week returns cached PDF instantly.

---

### Task 1: Create Cache Manager Module

**Files:**
- Create: `code/src/cache.py`

**Step 1: Create the cache manager**

Create `code/src/cache.py`:

```python
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""PDF caching layer for News, Fixed web application."""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


def get_current_week() -> str:
    """
    Get current ISO week in YYYY-WWW format.

    Returns:
        String like '2026-W03' for week 3 of 2026
    """
    now = datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


def get_week_for_date(date: datetime) -> str:
    """
    Get ISO week for a specific date.

    Args:
        date: datetime object

    Returns:
        String like '2026-W03'
    """
    return f"{date.year}-W{date.isocalendar()[1]:02d}"


class PDFCache:
    """Manages cached PDF files organized by ISO week."""

    def __init__(self, cache_dir: Path | str = None):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Base directory for cache (default: CACHE_DIR env var or 'cache')
        """
        if cache_dir is None:
            cache_dir = os.getenv('CACHE_DIR', 'cache')

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _week_dir(self, week: str) -> Path:
        """Get the directory for a specific week."""
        return self.cache_dir / week

    def get_cached_pdf(self, week: str = None) -> Optional[Path]:
        """
        Get path to cached PDF for a week if it exists.

        Args:
            week: ISO week string (default: current week)

        Returns:
            Path to PDF file or None if not cached
        """
        if week is None:
            week = get_current_week()

        pdf_path = self._week_dir(week) / "combined.pdf"

        if pdf_path.exists():
            return pdf_path
        return None

    def cache_pdf(self, pdf_source: Path, week: str = None) -> Path:
        """
        Cache a PDF file for a specific week.

        Args:
            pdf_source: Path to the PDF file to cache
            week: ISO week string (default: current week)

        Returns:
            Path to the cached PDF
        """
        if week is None:
            week = get_current_week()

        week_dir = self._week_dir(week)
        week_dir.mkdir(parents=True, exist_ok=True)

        pdf_dest = week_dir / "combined.pdf"

        # Copy file to cache
        shutil.copy2(pdf_source, pdf_dest)

        # Save metadata
        metadata = {
            'week': week,
            'cached_at': datetime.now().isoformat(),
            'source': str(pdf_source),
            'size_bytes': pdf_dest.stat().st_size
        }

        metadata_path = week_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return pdf_dest

    def get_metadata(self, week: str = None) -> Optional[dict]:
        """
        Get metadata for a cached week.

        Args:
            week: ISO week string (default: current week)

        Returns:
            Metadata dict or None if not cached
        """
        if week is None:
            week = get_current_week()

        metadata_path = self._week_dir(week) / "metadata.json"

        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return None

    def is_cached(self, week: str = None) -> bool:
        """
        Check if a week has a cached PDF.

        Args:
            week: ISO week string (default: current week)

        Returns:
            True if PDF is cached
        """
        return self.get_cached_pdf(week) is not None

    def clear_week(self, week: str) -> bool:
        """
        Clear cached data for a specific week.

        Args:
            week: ISO week string

        Returns:
            True if anything was cleared
        """
        week_dir = self._week_dir(week)

        if week_dir.exists():
            shutil.rmtree(week_dir)
            return True
        return False

    def list_cached_weeks(self) -> list[str]:
        """
        List all cached weeks.

        Returns:
            List of ISO week strings with cached PDFs
        """
        weeks = []
        for item in self.cache_dir.iterdir():
            if item.is_dir() and item.name.startswith('20') and '-W' in item.name:
                if (item / "combined.pdf").exists():
                    weeks.append(item.name)
        return sorted(weeks, reverse=True)


if __name__ == "__main__":
    # Test the cache manager
    print("Testing PDFCache...")

    cache = PDFCache()
    print(f"Cache directory: {cache.cache_dir}")
    print(f"Current week: {get_current_week()}")
    print(f"Is current week cached: {cache.is_cached()}")
    print(f"Cached weeks: {cache.list_cached_weeks()}")
```

**Step 2: Verify module loads**

Run: `cd code && python -c "from cache import PDFCache, get_current_week; print('Week:', get_current_week())"`
Expected: Shows current week like `Week: 2026-W03`

**Step 3: Commit**

```bash
git add code/src/cache.py
git commit -m "feat: add PDFCache class for week-based PDF caching

Organizes cached PDFs by ISO week (YYYY-WWW format).
Stores metadata including cache timestamp and source."
```

---

### Task 2: Integrate Cache with Flask Application

**Files:**
- Modify: `code/src/web.py`

**Step 1: Update web.py to use PDFCache**

Replace the inline cache functions in `code/src/web.py` with imports from the cache module. Update the file:

```python
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Flask web application for News, Fixed."""

import os
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify
from dotenv import load_dotenv
from cache import PDFCache, get_current_week

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent.parent / "templates"),
    static_folder=str(Path(__file__).parent.parent / "static")
)

# Configuration
cache_dir = Path(os.getenv('CACHE_DIR', 'cache'))
pdf_cache = PDFCache(cache_dir)


@app.route('/')
def index():
    """Landing page."""
    week = get_current_week()
    has_pdf = pdf_cache.is_cached(week)
    metadata = pdf_cache.get_metadata(week)

    return render_template(
        'landing.html',
        week=week,
        has_pdf=has_pdf,
        cached_at=metadata.get('cached_at') if metadata else None
    )


@app.route('/download')
def download():
    """Download the current week's PDF."""
    week = get_current_week()
    pdf_path = pdf_cache.get_cached_pdf(week)

    if pdf_path is None:
        return jsonify({
            'error': 'No PDF available for this week yet',
            'week': week
        }), 404

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
    week = get_current_week()
    return jsonify({
        'status': 'healthy',
        'service': 'news-fixed',
        'week': week,
        'has_pdf': pdf_cache.is_cached(week)
    }), 200


if __name__ == '__main__':
    # Development server only - use gunicorn in production
    app.run(debug=True, port=8080)
```

**Step 2: Verify integration**

Run: `cd code && python -c "from web import app, pdf_cache; print('Cache dir:', pdf_cache.cache_dir)"`
Expected: Shows cache directory path

**Step 3: Commit**

```bash
git add code/src/web.py
git commit -m "feat: integrate PDFCache with Flask application

Uses cache module for PDF storage and retrieval."
```

---

### Task 3: Add Cache Tests

**Files:**
- Create: `code/src/test_cache.py`

**Step 1: Create cache tests**

Create `code/src/test_cache.py`:

```python
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Tests for PDF caching layer."""

import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from cache import PDFCache, get_current_week, get_week_for_date


class TestGetCurrentWeek:
    """Tests for get_current_week function."""

    def test_returns_iso_week_format(self):
        """Current week should be in YYYY-WWW format."""
        week = get_current_week()
        assert len(week) == 8  # e.g., "2026-W03"
        assert week[4] == '-'
        assert week[5] == 'W'

    def test_week_number_is_zero_padded(self):
        """Week number should be zero-padded to 2 digits."""
        week = get_current_week()
        week_num = week.split('-W')[1]
        assert len(week_num) == 2


class TestGetWeekForDate:
    """Tests for get_week_for_date function."""

    def test_specific_date(self):
        """Test with a known date."""
        # January 20, 2026 is in week 4
        date = datetime(2026, 1, 20)
        week = get_week_for_date(date)
        assert week == "2026-W04"


class TestPDFCache:
    """Tests for PDFCache class."""

    def test_creates_cache_directory(self):
        """Cache should create its directory on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "test_cache"
            cache = PDFCache(cache_dir)
            assert cache.cache_dir.exists()

    def test_is_cached_returns_false_for_empty_cache(self):
        """is_cached should return False when no PDF exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PDFCache(tmpdir)
            assert cache.is_cached("2026-W01") is False

    def test_cache_and_retrieve_pdf(self):
        """Should be able to cache and retrieve a PDF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PDFCache(tmpdir)

            # Create a fake PDF file
            fake_pdf = Path(tmpdir) / "source.pdf"
            fake_pdf.write_text("fake pdf content")

            # Cache it
            week = "2026-W03"
            cached_path = cache.cache_pdf(fake_pdf, week)

            # Verify
            assert cached_path.exists()
            assert cache.is_cached(week) is True
            assert cache.get_cached_pdf(week) == cached_path

    def test_metadata_stored_on_cache(self):
        """Caching should store metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PDFCache(tmpdir)

            # Create and cache a fake PDF
            fake_pdf = Path(tmpdir) / "source.pdf"
            fake_pdf.write_text("fake pdf content")
            cache.cache_pdf(fake_pdf, "2026-W03")

            # Check metadata
            metadata = cache.get_metadata("2026-W03")
            assert metadata is not None
            assert metadata['week'] == "2026-W03"
            assert 'cached_at' in metadata
            assert 'size_bytes' in metadata

    def test_clear_week(self):
        """Should be able to clear a week's cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PDFCache(tmpdir)

            # Create and cache a fake PDF
            fake_pdf = Path(tmpdir) / "source.pdf"
            fake_pdf.write_text("fake pdf content")
            cache.cache_pdf(fake_pdf, "2026-W03")

            # Clear it
            assert cache.clear_week("2026-W03") is True
            assert cache.is_cached("2026-W03") is False

    def test_list_cached_weeks(self):
        """Should list all cached weeks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PDFCache(tmpdir)

            # Create and cache fake PDFs for multiple weeks
            fake_pdf = Path(tmpdir) / "source.pdf"
            fake_pdf.write_text("fake pdf content")

            cache.cache_pdf(fake_pdf, "2026-W01")
            cache.cache_pdf(fake_pdf, "2026-W03")
            cache.cache_pdf(fake_pdf, "2026-W02")

            # List should be reverse sorted
            weeks = cache.list_cached_weeks()
            assert weeks == ["2026-W03", "2026-W02", "2026-W01"]
```

**Step 2: Run tests**

Run: `cd /var/home/louie/Projects/family/News-Fixed && uv run pytest code/src/test_cache.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add code/src/test_cache.py
git commit -m "test: add tests for PDFCache

Covers caching, retrieval, metadata, and listing functions."
```

---

### Task 4: Integration Test - Cache with Flask

**Files:**
- None (verification only)

**Step 1: Test cache integration with Flask test client**

Run:
```bash
cd code && python -c "
from web import app, pdf_cache
import tempfile
from pathlib import Path

# Create test PDF
with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
    f.write(b'%PDF-1.4 fake pdf')
    test_pdf = Path(f.name)

# Cache it for a test week
pdf_cache.cache_pdf(test_pdf, '2026-W99')

# Test Flask routes
with app.test_client() as client:
    # Health should show has_pdf for test week (but not current week)
    health = client.get('/health')
    print('Health:', health.json)

print('Cache test complete')
"
```

Expected: Shows health response with service info

**Step 2: Verify cached weeks**

Run: `cd code && python -c "from cache import PDFCache; c = PDFCache('cache'); print('Cached weeks:', c.list_cached_weeks())"`

**Step 3: Commit documentation**

```bash
git add -A
git commit -m "docs: Phase 5 complete - caching layer

- PDFCache class for week-based PDF caching
- Metadata storage with cache timestamps
- Flask integration complete
- Tests passing"
```

---

## Phase 5 Verification

After completing all tasks:

1. Verify cache module: `cd code && python -c "from cache import PDFCache; print('Module loaded')"`
2. Run cache tests: `uv run pytest code/src/test_cache.py -v`
3. Verify Flask integration: `cd code && python -c "from web import pdf_cache; print('Cache dir:', pdf_cache.cache_dir)"`

Phase 5 is complete when cache tests pass and Flask uses PDFCache for PDF storage.
