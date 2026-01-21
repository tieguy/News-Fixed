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
