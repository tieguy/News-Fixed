#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""xkcd comic management for News, Fixed newspaper."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import httpx


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
