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
