# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Tests for PDF caching layer."""

import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

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

    def test_saturday_targets_next_week(self):
        """Saturday generation should target the following Monday's week."""
        # Saturday Feb 7, 2026 → should target Monday Feb 9 (W07)
        with patch('utils.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 7)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert get_current_week() == "2026-W07"

    def test_monday_targets_this_week(self):
        """Monday should target the current week."""
        # Monday Feb 9, 2026 → W07
        with patch('utils.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 9)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert get_current_week() == "2026-W07"

    def test_thursday_targets_this_week(self):
        """Thursday should still target the current week."""
        # Thursday Feb 12, 2026 → W07
        with patch('utils.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 12)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert get_current_week() == "2026-W07"

    def test_friday_targets_next_week(self):
        """Friday should target the following Monday's week."""
        # Friday Feb 13, 2026 → should target Monday Feb 16 (W08)
        with patch('utils.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 13)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert get_current_week() == "2026-W08"

    def test_sunday_targets_next_week(self):
        """Sunday should target the following Monday's week."""
        # Sunday Feb 8, 2026 → should target Monday Feb 9 (W07)
        with patch('utils.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 8)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert get_current_week() == "2026-W07"


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
