# xkcd Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add weekly xkcd comic selection and display to News, Fixed newspapers.

**Architecture:** New `xkcd.py` module handles fetching, caching, AI analysis, and selection. CLI gets new `xkcd` subcommand group. PDF generator accepts optional xkcd data and renders it on page 2.

**Tech Stack:** Python, httpx (HTTP client), Anthropic API (vision), Click (CLI), Typst (PDF)

---

## Task 1: Create xkcd Data Storage Layer

**Files:**
- Create: `code/src/xkcd.py`

**Step 1: Write the failing test**

Create `code/src/test_xkcd.py`:

```python
"""Tests for xkcd module."""
import json
import tempfile
from pathlib import Path
import pytest


def test_load_empty_cache():
    """Loading non-existent cache returns empty dict."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))
        cache = manager.load_cache()
        assert cache == {}


def test_save_and_load_cache():
    """Can save and reload cache data."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        test_data = {
            "3174": {
                "num": 3174,
                "title": "Test Comic",
                "alt": "Alt text",
                "img": "https://imgs.xkcd.com/comics/test.png",
                "date": "2025-11-28"
            }
        }

        manager.save_cache(test_data)
        loaded = manager.load_cache()

        assert loaded == test_data


def test_load_empty_rejected():
    """Loading non-existent rejected list returns empty dict."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))
        rejected = manager.load_rejected()
        assert rejected == {}


def test_reject_comic():
    """Can reject a comic with reason."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        manager.reject_comic(3150, "too_complex")

        rejected = manager.load_rejected()
        assert "3150" in rejected
        assert rejected["3150"]["reason"] == "too_complex"
```

**Step 2: Run test to verify it fails**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py -v`

Expected: ModuleNotFoundError: No module named 'xkcd'

**Step 3: Write minimal implementation**

Create `code/src/xkcd.py`:

```python
#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""xkcd comic management for News, Fixed newspaper."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class XkcdManager:
    """Manages xkcd comic fetching, analysis, and selection."""

    REJECTION_REASONS = [
        "too_complex",
        "adult_humor",
        "too_dark",
        "multi_panel",
        "requires_context",
        "other"
    ]

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the xkcd manager.

        Args:
            data_dir: Directory for cache files. Defaults to project data/ dir.
        """
        if data_dir is None:
            # Default: project_root/data/
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.data_dir / "xkcd_cache.json"
        self.rejected_file = self.data_dir / "xkcd_rejected.json"
        self.selected_file = self.data_dir / "xkcd_selected.json"

    def load_cache(self) -> Dict:
        """Load the comic cache from disk."""
        if not self.cache_file.exists():
            return {}
        with open(self.cache_file, 'r') as f:
            return json.load(f)

    def save_cache(self, cache: Dict) -> None:
        """Save the comic cache to disk."""
        with open(self.cache_file, 'w') as f:
            json.dump(cache, f, indent=2)

    def load_rejected(self) -> Dict:
        """Load the rejected comics list from disk."""
        if not self.rejected_file.exists():
            return {}
        with open(self.rejected_file, 'r') as f:
            return json.load(f)

    def save_rejected(self, rejected: Dict) -> None:
        """Save the rejected comics list to disk."""
        with open(self.rejected_file, 'w') as f:
            json.dump(rejected, f, indent=2)

    def load_selected(self) -> Dict:
        """Load the selected comics history from disk."""
        if not self.selected_file.exists():
            return {}
        with open(self.selected_file, 'r') as f:
            return json.load(f)

    def save_selected(self, selected: Dict) -> None:
        """Save the selected comics history to disk."""
        with open(self.selected_file, 'w') as f:
            json.dump(selected, f, indent=2)

    def reject_comic(self, comic_num: int, reason: str) -> None:
        """
        Add a comic to the rejected list.

        Args:
            comic_num: Comic number
            reason: Rejection reason (must be in REJECTION_REASONS)
        """
        if reason not in self.REJECTION_REASONS:
            raise ValueError(f"Invalid reason. Must be one of: {self.REJECTION_REASONS}")

        rejected = self.load_rejected()
        rejected[str(comic_num)] = {
            "reason": reason,
            "rejected_at": datetime.now().strftime("%Y-%m-%d")
        }
        self.save_rejected(rejected)
```

**Step 4: Run test to verify it passes**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py -v`

Expected: 4 passed

**Step 5: Commit**

```bash
git add code/src/xkcd.py code/src/test_xkcd.py
git commit -m "feat(xkcd): add data storage layer for cache and rejections"
```

---

## Task 2: Add xkcd API Fetching

**Files:**
- Modify: `code/src/xkcd.py`
- Modify: `code/src/test_xkcd.py`

**Step 1: Write the failing test**

Add to `code/src/test_xkcd.py`:

```python
def test_fetch_comic_metadata():
    """Can fetch metadata for a specific comic."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        # Fetch a known comic (use a low number that definitely exists)
        comic = manager.fetch_comic(1)

        assert comic["num"] == 1
        assert "title" in comic
        assert "alt" in comic
        assert "img" in comic


def test_fetch_recent_comics():
    """Can fetch multiple recent comics."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        comics = manager.fetch_recent_comics(count=3)

        assert len(comics) == 3
        # Should be in descending order (newest first)
        assert comics[0]["num"] > comics[1]["num"] > comics[2]["num"]


def test_fetch_caches_results():
    """Fetched comics are cached."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        # Fetch a comic
        manager.fetch_comic(1)

        # Check it's in cache
        cache = manager.load_cache()
        assert "1" in cache
        assert cache["1"]["num"] == 1
```

**Step 2: Run test to verify it fails**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py::test_fetch_comic_metadata -v`

Expected: AttributeError: 'XkcdManager' object has no attribute 'fetch_comic'

**Step 3: Write minimal implementation**

Add to `code/src/xkcd.py` (add import at top, add methods to class):

```python
# Add at top with other imports:
import httpx

# Add these methods to XkcdManager class:

    def fetch_comic(self, comic_num: Optional[int] = None) -> Dict:
        """
        Fetch comic metadata from xkcd API.

        Args:
            comic_num: Comic number. If None, fetches latest.

        Returns:
            Comic metadata dict with keys: num, title, alt, img, date, etc.
        """
        if comic_num is None:
            url = "https://xkcd.com/info.0.json"
        else:
            url = f"https://xkcd.com/{comic_num}/info.0.json"

        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Normalize the data
        comic = {
            "num": data["num"],
            "title": data["title"],
            "safe_title": data.get("safe_title", data["title"]),
            "alt": data["alt"],
            "img": data["img"],
            "date": f"{data['year']}-{data['month'].zfill(2)}-{data['day'].zfill(2)}",
            "fetched_at": datetime.now().isoformat()
        }

        # Cache the result
        cache = self.load_cache()
        cache[str(comic["num"])] = comic
        self.save_cache(cache)

        return comic

    def fetch_recent_comics(self, count: int = 10) -> list[Dict]:
        """
        Fetch the most recent comics.

        Args:
            count: Number of recent comics to fetch

        Returns:
            List of comic metadata dicts, newest first
        """
        # First get the latest to find current number
        latest = self.fetch_comic()
        latest_num = latest["num"]

        comics = [latest]

        # Fetch previous comics
        for num in range(latest_num - 1, latest_num - count, -1):
            if num < 1:
                break
            comic = self.fetch_comic(num)
            comics.append(comic)

        return comics
```

**Step 4: Run test to verify it passes**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py -v -k fetch`

Expected: 3 passed

**Step 5: Commit**

```bash
git add code/src/xkcd.py code/src/test_xkcd.py
git commit -m "feat(xkcd): add API fetching with caching"
```

---

## Task 3: Add Claude Vision Analysis

**Files:**
- Modify: `code/src/xkcd.py`
- Modify: `code/src/test_xkcd.py`
- Create: `code/prompts/xkcd_analysis.txt`

**Step 1: Create the prompt template**

Create `code/prompts/xkcd_analysis.txt`:

```
Analyze this xkcd comic for use in a children's newspaper (ages 10-14).

Comic title: {title}
Alt text (hover text): {alt}

Look at the image and return ONLY valid JSON (no markdown, no explanation):

{{
  "panel_count": <int - count distinct panels/frames in the comic>,
  "age_appropriate": <bool - no adult themes, violence, or mature humor>,
  "requires_specialized_knowledge": <bool - needs programming, advanced math, obscure science, or niche internet culture>,
  "knowledge_domains": [<list of domains required, e.g. "programming", "physics", empty if none>],
  "topic_tags": [<2-4 general topic tags like "science", "technology", "relationships">],
  "brief_summary": "<1-2 sentences explaining what the comic is about and why it's funny>"
}}

Age-appropriate means: suitable for a 10-14 year old, no sexual content, extreme violence, or dark/morbid themes.

Specialized knowledge means: the joke won't land without understanding specific technical concepts, obscure references, or internet culture that kids wouldn't know.
```

**Step 2: Write the failing test**

Add to `code/src/test_xkcd.py`:

```python
def test_analyze_comic_returns_expected_fields():
    """Analysis returns all expected fields."""
    from xkcd import XkcdManager
    import os

    # Skip if no API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        # Use comic #1 - simple and known
        comic = manager.fetch_comic(1)
        analysis = manager.analyze_comic(comic)

        assert "panel_count" in analysis
        assert "age_appropriate" in analysis
        assert "requires_specialized_knowledge" in analysis
        assert "topic_tags" in analysis
        assert "brief_summary" in analysis
        assert isinstance(analysis["panel_count"], int)
        assert isinstance(analysis["age_appropriate"], bool)


def test_analyze_comic_caches_result():
    """Analysis result is cached in comic data."""
    from xkcd import XkcdManager
    import os

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        comic = manager.fetch_comic(1)
        manager.analyze_comic(comic)

        # Reload cache and check analysis is there
        cache = manager.load_cache()
        assert "analysis" in cache["1"]
        assert "panel_count" in cache["1"]["analysis"]
```

**Step 3: Run test to verify it fails**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py::test_analyze_comic_returns_expected_fields -v`

Expected: AttributeError: 'XkcdManager' object has no attribute 'analyze_comic'

**Step 4: Write minimal implementation**

Add to `code/src/xkcd.py`:

```python
# Add to imports at top:
import base64
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

# Add these methods to XkcdManager class:

    def analyze_comic(self, comic: Dict, force: bool = False) -> Dict:
        """
        Analyze a comic using Claude vision API.

        Args:
            comic: Comic metadata dict (must have img, title, alt, num)
            force: If True, re-analyze even if cached

        Returns:
            Analysis dict with panel_count, age_appropriate, etc.
        """
        comic_num = str(comic["num"])
        cache = self.load_cache()

        # Check if already analyzed
        if not force and comic_num in cache and "analysis" in cache[comic_num]:
            return cache[comic_num]["analysis"]

        # Fetch and encode the image
        image_url = comic["img"]
        image_response = httpx.get(image_url, timeout=30)
        image_response.raise_for_status()
        image_data = base64.standard_b64encode(image_response.content).decode("utf-8")

        # Determine media type
        if image_url.endswith(".png"):
            media_type = "image/png"
        elif image_url.endswith(".jpg") or image_url.endswith(".jpeg"):
            media_type = "image/jpeg"
        else:
            media_type = "image/png"  # Default assumption

        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "xkcd_analysis.txt"
        with open(prompt_path, 'r') as f:
            prompt_template = f.read()

        prompt = prompt_template.format(
            title=comic["title"],
            alt=comic["alt"]
        )

        # Call Claude vision API
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        response_text = message.content[0].text

        # Parse JSON response
        import json
        try:
            # Handle potential markdown wrapping
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            analysis = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Return a failed analysis that marks comic as needing manual review
            analysis = {
                "panel_count": -1,
                "age_appropriate": False,
                "requires_specialized_knowledge": True,
                "knowledge_domains": ["parse_error"],
                "topic_tags": ["error"],
                "brief_summary": f"Failed to parse analysis: {e}",
                "parse_error": True
            }

        # Add timestamp
        analysis["analyzed_at"] = datetime.now().isoformat()

        # Cache the result
        if comic_num not in cache:
            cache[comic_num] = comic
        cache[comic_num]["analysis"] = analysis
        self.save_cache(cache)

        return analysis
```

**Step 5: Run test to verify it passes**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py -v -k analyze`

Expected: 2 passed (or skipped if no API key)

**Step 6: Commit**

```bash
git add code/src/xkcd.py code/src/test_xkcd.py code/prompts/xkcd_analysis.txt
git commit -m "feat(xkcd): add Claude vision analysis for comics"
```

---

## Task 4: Add Candidate Selection Logic

**Files:**
- Modify: `code/src/xkcd.py`
- Modify: `code/src/test_xkcd.py`

**Step 1: Write the failing test**

Add to `code/src/test_xkcd.py`:

```python
def test_get_candidates_filters_rejected():
    """Candidates exclude rejected comics."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        # Create some fake cached comics with analysis
        cache = {
            "100": {
                "num": 100, "title": "Test 1", "alt": "Alt 1", "img": "http://x.png", "date": "2025-01-01",
                "analysis": {"panel_count": 1, "age_appropriate": True, "requires_specialized_knowledge": False}
            },
            "101": {
                "num": 101, "title": "Test 2", "alt": "Alt 2", "img": "http://x.png", "date": "2025-01-02",
                "analysis": {"panel_count": 1, "age_appropriate": True, "requires_specialized_knowledge": False}
            },
            "102": {
                "num": 102, "title": "Test 3", "alt": "Alt 3", "img": "http://x.png", "date": "2025-01-03",
                "analysis": {"panel_count": 1, "age_appropriate": True, "requires_specialized_knowledge": False}
            }
        }
        manager.save_cache(cache)

        # Reject one
        manager.reject_comic(101, "too_complex")

        candidates = manager.get_candidates()

        candidate_nums = [c["num"] for c in candidates]
        assert 101 not in candidate_nums
        assert 100 in candidate_nums
        assert 102 in candidate_nums


def test_get_candidates_filters_multi_panel():
    """Candidates exclude multi-panel comics."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        cache = {
            "100": {
                "num": 100, "title": "Single", "alt": "Alt", "img": "http://x.png", "date": "2025-01-01",
                "analysis": {"panel_count": 1, "age_appropriate": True, "requires_specialized_knowledge": False}
            },
            "101": {
                "num": 101, "title": "Multi", "alt": "Alt", "img": "http://x.png", "date": "2025-01-02",
                "analysis": {"panel_count": 4, "age_appropriate": True, "requires_specialized_knowledge": False}
            }
        }
        manager.save_cache(cache)

        candidates = manager.get_candidates()

        candidate_nums = [c["num"] for c in candidates]
        assert 100 in candidate_nums
        assert 101 not in candidate_nums


def test_get_candidates_filters_not_age_appropriate():
    """Candidates exclude non-age-appropriate comics."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        cache = {
            "100": {
                "num": 100, "title": "Good", "alt": "Alt", "img": "http://x.png", "date": "2025-01-01",
                "analysis": {"panel_count": 1, "age_appropriate": True, "requires_specialized_knowledge": False}
            },
            "101": {
                "num": 101, "title": "Bad", "alt": "Alt", "img": "http://x.png", "date": "2025-01-02",
                "analysis": {"panel_count": 1, "age_appropriate": False, "requires_specialized_knowledge": False}
            }
        }
        manager.save_cache(cache)

        candidates = manager.get_candidates()

        candidate_nums = [c["num"] for c in candidates]
        assert 100 in candidate_nums
        assert 101 not in candidate_nums


def test_get_candidates_returns_top_3():
    """Candidates returns at most 3 comics."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        # Create 5 valid comics
        cache = {}
        for i in range(100, 105):
            cache[str(i)] = {
                "num": i, "title": f"Test {i}", "alt": "Alt", "img": "http://x.png", "date": f"2025-01-{i-99:02d}",
                "analysis": {"panel_count": 1, "age_appropriate": True, "requires_specialized_knowledge": False}
            }
        manager.save_cache(cache)

        candidates = manager.get_candidates()

        assert len(candidates) <= 3
```

**Step 2: Run test to verify it fails**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py::test_get_candidates_filters_rejected -v`

Expected: AttributeError: 'XkcdManager' object has no attribute 'get_candidates'

**Step 3: Write minimal implementation**

Add to `code/src/xkcd.py`:

```python
    def get_candidates(self, max_count: int = 3) -> list[Dict]:
        """
        Get candidate comics for selection.

        Filters in order:
        1. Not in rejected list
        2. Not used in last 8 weeks
        3. Single-panel (panel_count == 1)
        4. Age-appropriate
        5. Doesn't require specialized knowledge
        6. Sorted by recency (newest first)
        7. Return top N

        Args:
            max_count: Maximum candidates to return

        Returns:
            List of comic dicts (with analysis) that are valid candidates
        """
        cache = self.load_cache()
        rejected = self.load_rejected()
        selected = self.load_selected()

        # Get recently used comic numbers (last 8 weeks)
        recent_weeks = set()
        for week_key, selection in selected.items():
            # Parse week key like "2025-W48"
            # For simplicity, just track last 8 entries
            recent_weeks.add(str(selection.get("num", "")))
        # Only keep last 8 selections
        if len(recent_weeks) > 8:
            recent_weeks = set(list(recent_weeks)[-8:])

        candidates = []

        for comic_num, comic in cache.items():
            # Filter 1: Not rejected
            if comic_num in rejected:
                continue

            # Filter 2: Not recently used
            if comic_num in recent_weeks:
                continue

            # Must have analysis
            analysis = comic.get("analysis", {})
            if not analysis:
                continue

            # Filter 3: Single-panel
            if analysis.get("panel_count", 0) != 1:
                continue

            # Filter 4: Age-appropriate
            if not analysis.get("age_appropriate", False):
                continue

            # Filter 5: Doesn't require specialized knowledge
            if analysis.get("requires_specialized_knowledge", True):
                continue

            candidates.append(comic)

        # Sort by comic number descending (newer = higher number)
        candidates.sort(key=lambda c: c["num"], reverse=True)

        return candidates[:max_count]
```

**Step 4: Run test to verify it passes**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py -v -k candidates`

Expected: 4 passed

**Step 5: Commit**

```bash
git add code/src/xkcd.py code/src/test_xkcd.py
git commit -m "feat(xkcd): add candidate selection with filtering logic"
```

---

## Task 5: Add Selection and Week Tracking

**Files:**
- Modify: `code/src/xkcd.py`
- Modify: `code/src/test_xkcd.py`

**Step 1: Write the failing test**

Add to `code/src/test_xkcd.py`:

```python
def test_select_comic_for_week():
    """Can select a comic for the current week."""
    from xkcd import XkcdManager
    from datetime import date

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        manager.select_comic(3170)

        selected = manager.load_selected()
        # Should have an entry for current week
        current_week = date.today().isocalendar()
        week_key = f"{current_week.year}-W{current_week.week:02d}"

        assert week_key in selected
        assert selected[week_key]["num"] == 3170


def test_get_selected_for_current_week():
    """Can check if a comic is selected for current week."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        # Initially nothing selected
        assert manager.get_selected_for_week() is None

        # Select a comic
        manager.select_comic(3170)

        # Now should return it
        selected = manager.get_selected_for_week()
        assert selected == 3170
```

**Step 2: Run test to verify it fails**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py::test_select_comic_for_week -v`

Expected: AttributeError: 'XkcdManager' object has no attribute 'select_comic'

**Step 3: Write minimal implementation**

Add to `code/src/xkcd.py`:

```python
    def select_comic(self, comic_num: int, week_date: Optional[datetime] = None) -> None:
        """
        Mark a comic as selected for a given week.

        Args:
            comic_num: Comic number to select
            week_date: Date within the target week. Defaults to today.
        """
        if week_date is None:
            week_date = datetime.now()

        # Get ISO week
        iso_cal = week_date.date().isocalendar()
        week_key = f"{iso_cal.year}-W{iso_cal.week:02d}"

        selected = self.load_selected()
        selected[week_key] = {
            "num": comic_num,
            "selected_at": datetime.now().isoformat()
        }
        self.save_selected(selected)

    def get_selected_for_week(self, week_date: Optional[datetime] = None) -> Optional[int]:
        """
        Get the comic selected for a given week.

        Args:
            week_date: Date within the target week. Defaults to today.

        Returns:
            Comic number if one is selected, None otherwise.
        """
        if week_date is None:
            week_date = datetime.now()

        iso_cal = week_date.date().isocalendar()
        week_key = f"{iso_cal.year}-W{iso_cal.week:02d}"

        selected = self.load_selected()

        if week_key in selected:
            return selected[week_key]["num"]
        return None
```

**Step 4: Run test to verify it passes**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py -v -k select`

Expected: 2 passed

**Step 5: Commit**

```bash
git add code/src/xkcd.py code/src/test_xkcd.py
git commit -m "feat(xkcd): add comic selection and week tracking"
```

---

## Task 6: Add Image Download Helper

**Files:**
- Modify: `code/src/xkcd.py`
- Modify: `code/src/test_xkcd.py`

**Step 1: Write the failing test**

Add to `code/src/test_xkcd.py`:

```python
def test_download_comic_image():
    """Can download comic image to a file."""
    from xkcd import XkcdManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = XkcdManager(data_dir=Path(tmpdir))

        # Fetch a comic first
        comic = manager.fetch_comic(1)

        # Download its image
        dest = Path(tmpdir) / "comic.png"
        result_path = manager.download_comic_image(comic["num"], dest)

        assert result_path == dest
        assert dest.exists()
        assert dest.stat().st_size > 0
```

**Step 2: Run test to verify it fails**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py::test_download_comic_image -v`

Expected: AttributeError: 'XkcdManager' object has no attribute 'download_comic_image'

**Step 3: Write minimal implementation**

Add to `code/src/xkcd.py`:

```python
    def download_comic_image(self, comic_num: int, dest_path: Path) -> Path:
        """
        Download a comic's image to a local file.

        Args:
            comic_num: Comic number
            dest_path: Destination file path

        Returns:
            Path to the downloaded file
        """
        cache = self.load_cache()
        comic_key = str(comic_num)

        if comic_key not in cache:
            # Fetch it first
            self.fetch_comic(comic_num)
            cache = self.load_cache()

        comic = cache[comic_key]
        image_url = comic["img"]

        response = httpx.get(image_url, timeout=30)
        response.raise_for_status()

        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, 'wb') as f:
            f.write(response.content)

        return dest_path
```

**Step 4: Run test to verify it passes**

Run: `cd /var/home/louie/Projects/News-Fixed/code/src && python -m pytest test_xkcd.py::test_download_comic_image -v`

Expected: 1 passed

**Step 5: Commit**

```bash
git add code/src/xkcd.py code/src/test_xkcd.py
git commit -m "feat(xkcd): add image download helper"
```

---

## Task 7: Add CLI Commands

**Files:**
- Modify: `news-fixed`

**Step 1: Write the failing test**

Run the command and verify it fails:

Run: `./news-fixed xkcd --help`

Expected: Error: No such command 'xkcd'.

**Step 2: Write minimal implementation**

Add to `news-fixed` after the existing imports and before `@click.group()`:

```python
# Add after the CODE_DIR definition, around line 50:
from src.xkcd import XkcdManager
```

Add the xkcd command group after the `test` command (before `if __name__ == '__main__':`):

```python
@cli.group()
def xkcd():
    """Manage xkcd comics for the newspaper."""
    pass


@xkcd.command()
@click.option('--count', '-n', default=10, help='Number of recent comics to fetch')
def fetch(count):
    """Fetch recent xkcd comics and analyze them."""
    ensure_dirs()

    sys.path.insert(0, str(CODE_DIR))
    from src.xkcd import XkcdManager

    manager = XkcdManager(data_dir=DATA_DIR)

    click.echo(f"Fetching {count} recent xkcd comics...")
    comics = manager.fetch_recent_comics(count=count)
    click.echo(f"Fetched {len(comics)} comics")

    # Analyze any that haven't been analyzed
    rejected = manager.load_rejected()
    analyzed_count = 0

    for comic in comics:
        comic_num = str(comic["num"])

        # Skip rejected
        if comic_num in rejected:
            click.echo(f"  #{comic['num']}: {comic['title']} (rejected)")
            continue

        # Check if already analyzed
        cache = manager.load_cache()
        if comic_num in cache and "analysis" in cache[comic_num]:
            click.echo(f"  #{comic['num']}: {comic['title']} (cached)")
            continue

        click.echo(f"  #{comic['num']}: {comic['title']} (analyzing...)")
        try:
            manager.analyze_comic(comic)
            analyzed_count += 1
        except Exception as e:
            click.echo(f"    Error: {e}")

    if analyzed_count > 0:
        click.echo(f"\nAnalyzed {analyzed_count} new comics")

    click.echo("\nRun './news-fixed xkcd candidates' to see recommendations")


@xkcd.command()
def candidates():
    """Show candidate comics for this week."""
    ensure_dirs()

    sys.path.insert(0, str(CODE_DIR))
    from src.xkcd import XkcdManager

    manager = XkcdManager(data_dir=DATA_DIR)

    # Check if already selected
    selected = manager.get_selected_for_week()
    if selected:
        click.echo(f"Already selected for this week: #{selected}")
        click.echo("Run './news-fixed xkcd select <num>' to change selection")
        return

    candidates = manager.get_candidates()

    if not candidates:
        click.echo("No candidates available. Run './news-fixed xkcd fetch' first.")
        return

    click.echo("Candidate comics for this week:\n")

    for i, comic in enumerate(candidates, 1):
        analysis = comic.get("analysis", {})
        click.echo(f"{i}. #{comic['num']}: {comic['title']}")
        click.echo(f"   Alt: {comic['alt'][:80]}..." if len(comic['alt']) > 80 else f"   Alt: {comic['alt']}")
        click.echo(f"   Summary: {analysis.get('brief_summary', 'N/A')}")
        click.echo(f"   Tags: {', '.join(analysis.get('topic_tags', []))}")
        click.echo(f"   View: https://xkcd.com/{comic['num']}/")
        click.echo()

    click.echo("Select with: ./news-fixed xkcd select <number>")
    click.echo("Reject with: ./news-fixed xkcd reject <number> <reason>")


@xkcd.command()
@click.argument('comic_num', type=int)
def select(comic_num):
    """Select a comic for this week's newspaper."""
    ensure_dirs()

    sys.path.insert(0, str(CODE_DIR))
    from src.xkcd import XkcdManager

    manager = XkcdManager(data_dir=DATA_DIR)
    manager.select_comic(comic_num)

    click.echo(f"Selected #{comic_num} for this week's newspaper")


@xkcd.command()
@click.argument('comic_num', type=int)
@click.argument('reason', type=click.Choice([
    'too_complex', 'adult_humor', 'too_dark',
    'multi_panel', 'requires_context', 'other'
]))
def reject(comic_num, reason):
    """Reject a comic (won't be shown as candidate again)."""
    ensure_dirs()

    sys.path.insert(0, str(CODE_DIR))
    from src.xkcd import XkcdManager

    manager = XkcdManager(data_dir=DATA_DIR)
    manager.reject_comic(comic_num, reason)

    click.echo(f"Rejected #{comic_num} ({reason})")


@xkcd.command()
@click.argument('comic_num', type=int)
def show(comic_num):
    """Show details for a specific comic."""
    ensure_dirs()

    sys.path.insert(0, str(CODE_DIR))
    from src.xkcd import XkcdManager

    manager = XkcdManager(data_dir=DATA_DIR)
    cache = manager.load_cache()

    comic_key = str(comic_num)
    if comic_key not in cache:
        click.echo(f"Comic #{comic_num} not in cache. Fetching...")
        comic = manager.fetch_comic(comic_num)
    else:
        comic = cache[comic_key]

    click.echo(f"\n#{comic['num']}: {comic['title']}")
    click.echo(f"Date: {comic['date']}")
    click.echo(f"Alt: {comic['alt']}")
    click.echo(f"Image: {comic['img']}")
    click.echo(f"URL: https://xkcd.com/{comic['num']}/")

    analysis = comic.get("analysis")
    if analysis:
        click.echo(f"\nAnalysis:")
        click.echo(f"  Panels: {analysis.get('panel_count', 'N/A')}")
        click.echo(f"  Age-appropriate: {analysis.get('age_appropriate', 'N/A')}")
        click.echo(f"  Specialized knowledge: {analysis.get('requires_specialized_knowledge', 'N/A')}")
        click.echo(f"  Tags: {', '.join(analysis.get('topic_tags', []))}")
        click.echo(f"  Summary: {analysis.get('brief_summary', 'N/A')}")
    else:
        click.echo("\n(Not yet analyzed. Run './news-fixed xkcd fetch' to analyze.)")

    # Check if rejected
    rejected = manager.load_rejected()
    if comic_key in rejected:
        click.echo(f"\nREJECTED: {rejected[comic_key]['reason']}")
```

**Step 3: Run test to verify it passes**

Run: `./news-fixed xkcd --help`

Expected: Shows help text with fetch, candidates, select, reject, show commands

**Step 4: Commit**

```bash
git add news-fixed
git commit -m "feat(xkcd): add CLI commands for xkcd management"
```

---

## Task 8: Add Template Placeholder for xkcd

**Files:**
- Modify: `code/templates/newspaper.typ`

**Step 1: Identify the insertion point**

The xkcd section goes on page 2, just above the footer (before line 145).

**Step 2: Write the template addition**

Add this section before the `// === FOOTER PAGE 2 ===` comment (around line 144):

```typst
// === XKCD COMIC ===
{{XKCD_SECTION}}
```

The `{{XKCD_SECTION}}` placeholder will be replaced with either the full comic section or empty string if no comic is selected.

**Step 3: Verify template still compiles**

Run: `~/.local/bin/typst compile code/templates/newspaper.typ /dev/null` (will fail due to missing placeholders, that's OK)

**Step 4: Commit**

```bash
git add code/templates/newspaper.typ
git commit -m "feat(xkcd): add template placeholder for comic section"
```

---

## Task 9: Integrate xkcd into PDF Generator

**Files:**
- Modify: `code/src/pdf_generator_typst.py`

**Step 1: Modify generate_pdf signature**

Add optional `xkcd_comic` parameter to `generate_pdf` method:

```python
def generate_pdf(
    self,
    day_number: int,
    main_story: Dict,
    front_page_stories: List[Dict],
    mini_articles: List[Dict],
    statistics: List[Dict],
    output_path: str,
    date_str: str = "",
    day_of_week: str = "",
    theme: str = "",
    feature_box: Dict = None,
    tomorrow_teaser: str = "",
    xkcd_comic: Dict = None  # NEW PARAMETER
):
```

**Step 2: Add xkcd section builder method**

Add this method to `TypstNewspaperGenerator` class:

```python
    def _build_xkcd_section(self, comic: Dict, temp_dir: Path) -> str:
        """Build Typst markup for xkcd comic section."""
        if not comic:
            return ""

        # Download the image
        from xkcd import XkcdManager
        manager = XkcdManager()

        image_url = comic.get("img", "")
        if not image_url:
            return ""

        # Determine file extension
        ext = ".png" if image_url.endswith(".png") else ".jpg"
        image_path = temp_dir / f"xkcd_{comic['num']}{ext}"

        manager.download_comic_image(comic["num"], image_path)

        # Get relative path from code directory
        code_dir = Path(__file__).parent.parent
        try:
            rel_path = image_path.relative_to(code_dir)
        except ValueError:
            rel_path = image_path

        title = self._escape_typst(comic.get("title", ""))
        alt = self._escape_typst(comic.get("alt", ""))

        return f"""#v(10pt)
#line(length: 100%, stroke: 1pt + black)
#v(6pt)
#grid(
  columns: (2.2in, 1fr),
  column-gutter: 12pt,
  align: (center + horizon, left + top),
  [#image("{rel_path}", width: 2in)],
  [
    #text(size: 10pt, weight: "bold")[xkcd: {title}]
    #v(4pt)
    #text(size: 8pt, style: "italic")[{alt}]
    #v(4pt)
    #text(size: 7pt)[xkcd.com/{comic['num']}]
  ]
)
#v(8pt)
"""
```

**Step 3: Use the builder in generate_pdf**

In the `generate_pdf` method, before `# Load template`, add:

```python
        # Build xkcd section
        xkcd_section = self._build_xkcd_section(xkcd_comic, Path(output_path).parent) if xkcd_comic else ""
```

And add the replacement after the other replacements:

```python
        typst_content = typst_content.replace('{{XKCD_SECTION}}', xkcd_section)
```

**Step 4: Test the integration**

This will be tested as part of end-to-end testing.

**Step 5: Commit**

```bash
git add code/src/pdf_generator_typst.py
git commit -m "feat(xkcd): integrate comic into PDF generator"
```

---

## Task 10: Add xkcd to main.py Generation Flow

**Files:**
- Modify: `code/src/main.py`

**Step 1: Add xkcd import and loading**

Near the top of `main.py` where imports are, add:

```python
from xkcd import XkcdManager
```

**Step 2: Integrate into generation**

In the generation function, before calling `generator.generate_pdf()`, add logic to load the selected xkcd:

```python
# Load xkcd comic if selected for this week
xkcd_manager = XkcdManager()
xkcd_comic = None
selected_num = xkcd_manager.get_selected_for_week()
if selected_num:
    cache = xkcd_manager.load_cache()
    if str(selected_num) in cache:
        xkcd_comic = cache[str(selected_num)]
```

Then pass `xkcd_comic=xkcd_comic` to the `generate_pdf()` call.

**Step 3: Commit**

```bash
git add code/src/main.py
git commit -m "feat(xkcd): include selected comic in newspaper generation"
```

---

## Task 11: End-to-End Testing

**Files:** None (testing only)

**Step 1: Fetch and analyze comics**

Run: `./news-fixed xkcd fetch --count 5`

Expected: Fetches 5 comics, analyzes any not in cache

**Step 2: View candidates**

Run: `./news-fixed xkcd candidates`

Expected: Shows up to 3 candidate comics with their analysis

**Step 3: Select a comic**

Run: `./news-fixed xkcd select <num>` (use a number from candidates)

Expected: Confirms selection

**Step 4: Generate newspaper with comic**

Run: `./news-fixed generate <json-file> --day 1 --skip-curation`

Expected: PDF includes xkcd comic on page 2

**Step 5: Verify PDF output**

Open the generated PDF and verify:
- xkcd comic appears on page 2 above footer
- Image is visible
- Title and alt text are displayed
- Layout looks correct

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat(xkcd): complete xkcd integration with end-to-end testing"
```

---

## Summary

| Task | Description | Files Modified |
|------|-------------|----------------|
| 1 | Data storage layer | `code/src/xkcd.py`, `code/src/test_xkcd.py` |
| 2 | API fetching | `code/src/xkcd.py`, `code/src/test_xkcd.py` |
| 3 | Claude vision analysis | `code/src/xkcd.py`, `code/prompts/xkcd_analysis.txt` |
| 4 | Candidate selection | `code/src/xkcd.py`, `code/src/test_xkcd.py` |
| 5 | Week tracking | `code/src/xkcd.py`, `code/src/test_xkcd.py` |
| 6 | Image download | `code/src/xkcd.py`, `code/src/test_xkcd.py` |
| 7 | CLI commands | `news-fixed` |
| 8 | Template placeholder | `code/templates/newspaper.typ` |
| 9 | PDF generator integration | `code/src/pdf_generator_typst.py` |
| 10 | Main.py integration | `code/src/main.py` |
| 11 | End-to-end testing | (testing only) |
