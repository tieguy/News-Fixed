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
import base64
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()


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

    def select_comic(
        self,
        comic_num: int,
        day: int = 1,
        week_date: Optional[datetime] = None
    ) -> None:
        """
        Mark a comic as selected for a given week and day.

        Args:
            comic_num: Comic number to select
            day: Day number (1-4) to show the comic. Defaults to 1 (Monday).
            week_date: Date within the target week. Defaults to today.
        """
        if week_date is None:
            week_date = datetime.now()

        if day < 1 or day > 4:
            raise ValueError("Day must be between 1 and 4")

        # Get ISO week
        iso_cal = week_date.date().isocalendar()
        week_key = f"{iso_cal.year}-W{iso_cal.week:02d}"

        selected = self.load_selected()
        selected[week_key] = {
            "num": comic_num,
            "day": day,
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

    def get_selected_for_day(
        self,
        day: int,
        week_date: Optional[datetime] = None
    ) -> Optional[int]:
        """
        Get the comic selected for a specific day of a given week.

        Args:
            day: Day number (1-4)
            week_date: Date within the target week. Defaults to today.

        Returns:
            Comic number if selected for this day, None otherwise.
        """
        if week_date is None:
            week_date = datetime.now()

        iso_cal = week_date.date().isocalendar()
        week_key = f"{iso_cal.year}-W{iso_cal.week:02d}"

        selected = self.load_selected()

        if week_key in selected:
            selection = selected[week_key]
            # Check if this selection is for the requested day
            # Default to day 1 for backwards compatibility with old selections
            selected_day = selection.get("day", 1)
            if selected_day == day:
                return selection["num"]
        return None

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
