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
