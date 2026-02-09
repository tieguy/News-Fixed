# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Data model layer for story curation.

Contains StoryCuratorData — the pure data operations for loading,
mutating, validating, and saving curated story data. TUI/interactive
methods are in curator.py (StoryCurator subclass).
"""

import json
import copy
import os
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from utils import get_theme_name


def _get_secondary_story_title(day_data: Dict) -> Optional[str]:
    """Get a secondary story title from front_page_stories or mini_articles."""
    # Try front_page_stories first
    front_page = day_data.get("front_page_stories", [])
    if front_page and front_page[0].get("title"):
        return front_page[0]["title"]

    # Fall back to mini_articles
    mini = day_data.get("mini_articles", [])
    if mini and mini[0].get("title"):
        return mini[0]["title"]

    return None


def generate_teasers_for_curated_data(curated_data: Dict, console: Console = None) -> Dict:
    """
    Generate tomorrow teasers for days 1-3 based on next day's content.

    Args:
        curated_data: Dict with day_1 through day_4 keys
        console: Optional Rich Console for output

    Returns:
        Modified curated_data with populated tomorrow_teaser fields
    """
    from generator import ContentGenerator

    if console is None:
        console = Console()

    generator = ContentGenerator()

    for day_num in [1, 2, 3]:
        current_day = f"day_{day_num}"
        tomorrow_day = f"day_{day_num + 1}"

        # Skip if current day doesn't exist
        if current_day not in curated_data:
            continue

        # Skip if tomorrow doesn't exist or has no main story
        tomorrow = curated_data.get(tomorrow_day, {})
        main_story = tomorrow.get("main_story", {})
        if not main_story.get("title") and not main_story.get("tui_headline"):
            continue

        # Get story titles from tomorrow
        main_title = main_story.get("tui_headline") or main_story.get("title")
        secondary_title = _get_secondary_story_title(tomorrow)

        # Generate teaser
        try:
            teaser = generator.generate_teaser(
                tomorrow_theme=tomorrow.get("theme", get_theme_name(day_num + 1)),
                main_title=main_title,
                secondary_title=secondary_title
            )
            curated_data[current_day]["tomorrow_teaser"] = teaser
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to generate teaser for day {day_num}: {e}[/yellow]")
            # Leave teaser empty on failure

    return curated_data


class StoryCuratorData:
    """Data model for story curation — loading, mutation, validation, saving.

    This class handles all non-interactive data operations. Interactive
    TUI methods are in StoryCurator (curator.py) which subclasses this.

    Args:
        json_file: Path to JSON file with day_1/day_2/day_3/day_4 structure
        output_file: Path where curated JSON will be saved (for auto-save)
        console: Optional Rich Console for status output (default: new Console)
    """

    def __init__(self, json_file: Path, output_file: Path = None, console: Console = None):
        self.json_file = Path(json_file)
        self.output_file = output_file
        self.console = console or Console()
        self.original_data = self._load_json(self.json_file)
        self.working_data = copy.deepcopy(self.original_data)
        self.changes_made = []

    def _load_json(self, json_file: Path) -> Dict:
        """Load JSON file and validate structure."""
        if not json_file.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        for day_num in range(1, 5):
            day_key = f"day_{day_num}"
            if day_key not in data:
                self.console.print(f"[yellow]Warning: {day_key} not found in JSON[/yellow]")

        return data

    def _day_theme(self, day_num: int) -> str:
        """Get the live theme name for a day from working data."""
        day_key = f"day_{day_num}"
        if day_key in self.working_data:
            return self.working_data[day_key].get('theme', get_theme_name(day_num))
        return get_theme_name(day_num)

    def _has_second_story(self, day_data: Dict) -> bool:
        """Check if a day has a second main story."""
        second = day_data.get('second_story', {})
        return bool(second and second.get('title'))

    def _mini_start_index(self, day_data: Dict) -> int:
        """Get the 1-based index where mini articles start for a day."""
        return 3 if self._has_second_story(day_data) else 2

    def _total_stories(self, day_data: Dict) -> int:
        """Get total number of stories in a day (main + optional second + minis)."""
        count = 1  # main
        if self._has_second_story(day_data):
            count += 1
        count += len(day_data.get('mini_articles', []))
        return count

    def _auto_save(self) -> None:
        """Auto-save working data after each change (if output file is set)."""
        if self.output_file is None:
            return

        # Create output data without unused category
        output_data = {k: v for k, v in self.working_data.items() if k != 'unused'}

        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.console.print(f"[dim][Auto-save failed: {e}][/dim]")

    def _get_story_by_index(self, day_data: Dict, index: int):
        """
        Get a story from a day by its 1-based display index.

        Returns:
            (story_dict, slot_type) where slot_type is 'main', 'second', or 'mini'
            or (None, None) if index is invalid
        """
        has_second = self._has_second_story(day_data)
        mini_start = self._mini_start_index(day_data)

        if index == 1:
            return day_data.get('main_story', {}), 'main'
        elif index == 2 and has_second:
            return day_data.get('second_story', {}), 'second'
        else:
            minis = day_data.get('mini_articles', [])
            mini_idx = index - mini_start
            if 0 <= mini_idx < len(minis):
                return minis[mini_idx], 'mini'
        return None, None

    def swap_main_story(self, day_num: int, new_main_index: int) -> None:
        """
        Change which story is main vs mini.

        Args:
            day_num: Day number (1-4)
            new_main_index: Story index to make main (1-based, 2+ = currently minis)
        """
        day_key = f"day_{day_num}"
        if day_key not in self.working_data:
            self.console.print(f"[red]Error: {day_key} not found[/red]")
            return

        day_data = self.working_data[day_key]
        has_second = self._has_second_story(day_data)
        mini_start = self._mini_start_index(day_data)

        # Can't swap with itself
        if new_main_index == 1:
            self.console.print("[yellow]Story 1 is already the main story[/yellow]")
            return

        current_main = day_data.get('main_story', {})

        # Swap main with second story
        if new_main_index == 2 and has_second:
            new_main = day_data['second_story']
            day_data['main_story'] = new_main
            day_data['second_story'] = current_main
        else:
            # Swap main with a mini article
            minis = day_data.get('mini_articles', [])
            mini_idx = new_main_index - mini_start
            if mini_idx < 0 or mini_idx >= len(minis):
                self.console.print(f"[red]Error: Story {new_main_index} not found[/red]")
                return
            new_main = minis[mini_idx]
            day_data['main_story'] = new_main
            minis[mini_idx] = current_main

        # Record change
        change_msg = f"Day {day_num}: Swapped main story"
        self.changes_made.append(change_msg)

        self.console.print(f"[green]✓[/green] {change_msg}")
        self.console.print(f"  New main: {new_main.get('title', 'Untitled')[:50]}...")
        self.console.print(f"  Demoted: {current_main.get('title', 'Untitled')[:50]}...")

        # Auto-save after change
        self._auto_save()

    def _remove_story_from_day(self, from_data: Dict, story_index: int, from_day: int) -> tuple:
        """
        Remove a story from a day by index, handling promotions.

        Args:
            from_data: The day data dict
            story_index: 1-based story index
            from_day: Day number (for warning messages)

        Returns:
            (story, slot_type) tuple, or (None, None) if invalid
        """
        has_second = self._has_second_story(from_data)
        mini_start = self._mini_start_index(from_data)

        # Determine slot type
        if story_index == 1:
            story = from_data.get('main_story', {})
            slot_type = 'main'
        elif story_index == 2 and has_second:
            story = from_data.get('second_story', {})
            slot_type = 'second'
        else:
            minis = from_data.get('mini_articles', [])
            mini_idx = story_index - mini_start
            if mini_idx < 0 or mini_idx >= len(minis):
                self.console.print(f"[red]Error: Story {story_index} not found[/red]")
                return None, None
            story = minis[mini_idx]
            slot_type = 'mini'

        # Remove from source day
        if slot_type == 'main':
            if has_second:
                from_data['main_story'] = from_data.pop('second_story')
            elif from_data.get('mini_articles'):
                from_data['main_story'] = from_data['mini_articles'].pop(0)
            else:
                self.console.print(f"[yellow]⚠️  Warning: Day {from_day} will have no main story after this move[/yellow]")
                self.console.print(f"[dim]   (This will cause validation to fail when saving)[/dim]")
                from_data['main_story'] = {}
        elif slot_type == 'second':
            from_data['second_story'] = {}
        else:
            mini_idx = story_index - mini_start
            from_data['mini_articles'].pop(mini_idx)

        return story, slot_type

    def move_story(self, from_day: int, story_index: int, to_day: int) -> bool:
        """
        Move a story between days.

        Args:
            from_day: Source day number (1-4)
            story_index: Story index in source day (1-based)
            to_day: Destination day number (1-4)

        Returns:
            True if move succeeded, False if cancelled/failed
        """
        from_key = f"day_{from_day}"
        to_key = f"day_{to_day}"

        if from_key not in self.working_data or to_key not in self.working_data:
            self.console.print("[red]Error: Invalid day number[/red]")
            return False

        from_data = self.working_data[from_key]
        to_data = self.working_data[to_key]
        has_second = self._has_second_story(from_data)
        mini_start = self._mini_start_index(from_data)

        # Get story to move and determine its slot type
        slot_type = None  # 'main', 'second', or 'mini'
        if story_index == 1:
            story = from_data.get('main_story', {})
            slot_type = 'main'
        elif story_index == 2 and has_second:
            story = from_data.get('second_story', {})
            slot_type = 'second'
        else:
            minis = from_data.get('mini_articles', [])
            mini_idx = story_index - mini_start
            if mini_idx < 0 or mini_idx >= len(minis):
                self.console.print(f"[red]Error: Story {story_index} not found[/red]")
                return False
            story = minis[mini_idx]
            slot_type = 'mini'

        # Check if target day is full (up to 2 main + 4 minis = 6 total)
        to_minis = to_data.get('mini_articles', [])
        to_has_main = bool(to_data.get('main_story'))
        to_has_second = self._has_second_story(to_data)
        to_count = len(to_minis) + (1 if to_has_main else 0) + (1 if to_has_second else 0)
        to_max = 6 if to_has_second else 5

        # Remove from source day first
        if slot_type == 'main':
            # If moving main story, promote second story or first mini
            if has_second:
                from_data['main_story'] = from_data.pop('second_story')
            elif from_data.get('mini_articles'):
                from_data['main_story'] = from_data['mini_articles'].pop(0)
            else:
                self.console.print(f"[yellow]⚠️  Warning: Day {from_day} will have no main story after this move[/yellow]")
                self.console.print(f"[dim]   (This will cause validation to fail when saving)[/dim]")
                from_data['main_story'] = {}
        elif slot_type == 'second':
            from_data['second_story'] = {}
        else:
            from_data['mini_articles'].pop(mini_idx)

        if to_count >= to_max:
            # Handle overflow (swap or replace) — delegated to TUI layer
            swapped_story = self._handle_overflow(to_day, story)

            if swapped_story is None:
                # User cancelled or chose replace (no story to add back)
                # Story removed from source day (already done above)
                return True

            # User chose swap - add swapped story to source day
            if slot_type == 'main':
                # Source lost its main, make swapped story the main
                from_data['main_story'] = swapped_story
            elif slot_type == 'second':
                # Source lost its second story, put swapped story there
                from_data['second_story'] = swapped_story
            else:
                # Add swapped story as mini
                if 'mini_articles' not in from_data:
                    from_data['mini_articles'] = []
                from_data['mini_articles'].insert(mini_idx, swapped_story)

            return True

        # Add to target day as mini article
        if 'mini_articles' not in to_data:
            to_data['mini_articles'] = []
        to_data['mini_articles'].append(story)

        # Record change
        story_title = story.get('tui_headline') or story.get('title', 'Untitled')[:40]
        change_msg = f"Day {from_day} → Day {to_day}: {story_title}"
        self.changes_made.append(change_msg)

        self.console.print(f"[green]✓[/green] Moved: {story_title}")
        self.console.print(f"  From: Day {from_day} → To: Day {to_day} (mini)")

        # Auto-save after change
        self._auto_save()

        return True

    def _handle_overflow(self, to_day: int, incoming_story: dict) -> Optional[dict]:
        """
        Handle adding story to a full day (5 stories already).

        Default implementation prints a warning and returns None (cancel).
        Override in TUI subclass for interactive swap/replace behavior.

        Args:
            to_day: Target day number
            incoming_story: Story being moved

        Returns:
            Story to swap back to source day, or None if cancelled/replaced
        """
        self.console.print(f"[yellow]⚠️  Day {to_day} is full. Move cancelled.[/yellow]")
        return None

    def move_to_unused(self, from_day: int, story_index: int) -> None:
        """
        Move a story from a day to unused (delete from newspaper).

        Args:
            from_day: Source day number (1-4)
            story_index: Story index in source day (1-based)
        """
        from_key = f"day_{from_day}"
        if from_key not in self.working_data:
            self.console.print("[red]Error: Invalid day number[/red]")
            return

        from_data = self.working_data[from_key]
        has_second = self._has_second_story(from_data)
        mini_start = self._mini_start_index(from_data)

        # Get story to move
        slot_type = None
        if story_index == 1:
            story = from_data.get('main_story', {})
            slot_type = 'main'
        elif story_index == 2 and has_second:
            story = from_data.get('second_story', {})
            slot_type = 'second'
        else:
            minis = from_data.get('mini_articles', [])
            mini_idx = story_index - mini_start
            if mini_idx < 0 or mini_idx >= len(minis):
                self.console.print(f"[red]Error: Story {story_index} not found[/red]")
                return
            story = minis[mini_idx]
            slot_type = 'mini'

        # Remove from source day
        if slot_type == 'main':
            if has_second:
                from_data['main_story'] = from_data.pop('second_story')
            elif from_data.get('mini_articles'):
                from_data['main_story'] = from_data['mini_articles'].pop(0)
            else:
                self.console.print(f"[yellow]⚠️  Warning: Day {from_day} will have no main story after this move[/yellow]")
                self.console.print(f"[dim]   (This will cause validation to fail when saving)[/dim]")
                from_data['main_story'] = {}
        elif slot_type == 'second':
            from_data['second_story'] = {}
        else:
            from_data['mini_articles'].pop(mini_idx)

        # Add to unused
        if 'unused' not in self.working_data:
            self.working_data['unused'] = {'stories': []}
        self.working_data['unused']['stories'].append(story)

        story_title = story.get('tui_headline') or story.get('title', 'Untitled')[:40]
        change_msg = f"Day {from_day} → Unused: {story_title}"
        self.changes_made.append(change_msg)

        self.console.print(f"[green]✓[/green] Moved to unused: {story_title}")
        self.console.print(f"  Story removed from newspaper")

        # Auto-save after change
        self._auto_save()

    def move_from_unused(self, story_index: int, to_day: int) -> None:
        """
        Move a story from unused to a day.

        Args:
            story_index: Story index in unused (1-based)
            to_day: Target day number (1-4)
        """
        if 'unused' not in self.working_data:
            self.console.print("[red]Error: No unused stories[/red]")
            return

        unused_stories = self.working_data['unused'].get('stories', [])
        if story_index < 1 or story_index > len(unused_stories):
            self.console.print(f"[red]Error: Story {story_index} not found in unused[/red]")
            return

        # Validate target day before removing from unused
        if to_day < 1 or to_day > 4:
            self.console.print(f"[red]Error: Invalid day number {to_day}[/red]")
            return

        to_key = f"day_{to_day}"

        # Create target day if it doesn't exist
        if to_key not in self.working_data:
            self.working_data[to_key] = {
                "theme": get_theme_name(to_day),
                "main_story": {},
                "front_page_stories": [],
                "mini_articles": [],
                "statistics": [],
                "tomorrow_teaser": ""
            }

        # Now safe to remove from unused
        story = unused_stories.pop(story_index - 1)

        to_data = self.working_data[to_key]

        # Check if target day is full - warn but allow
        to_minis = to_data.get('mini_articles', [])
        to_has_main = bool(to_data.get('main_story'))
        to_has_second = self._has_second_story(to_data)
        to_count = len(to_minis) + (1 if to_has_main else 0) + (1 if to_has_second else 0)
        to_max = 6 if to_has_second else 5

        # Add to target day as mini article
        if 'mini_articles' not in to_data:
            to_data['mini_articles'] = []
        to_data['mini_articles'].append(story)

        story_title = story.get('tui_headline') or story.get('title', 'Untitled')[:40]
        change_msg = f"Unused → Day {to_day}: {story_title}"
        self.changes_made.append(change_msg)

        self.console.print(f"[green]✓[/green] Moved from unused: {story_title}")
        self.console.print(f"  Added to Day {to_day} (mini)")

        # Warn if day now exceeds capacity
        new_count = to_count + 1
        if new_count > to_max:
            self.console.print(f"[yellow]⚠️  Day {to_day} now has {new_count} stories (over capacity)[/yellow]")
            self.console.print(f"[dim]   You'll need to remove {new_count - to_max} during day review[/dim]")

        # Auto-save after change
        self._auto_save()

    def validate_data(self) -> bool:
        """
        Validate working_data before saving.

        Returns:
            True if valid, False if critical errors found
        """
        valid = True
        warnings = []

        for day_num in range(1, 5):
            day_key = f"day_{day_num}"
            if day_key not in self.working_data:
                warnings.append(f"Day {day_num} not found in data")
                continue

            day_data = self.working_data[day_key]
            main_story = day_data.get('main_story', {})
            mini_articles = day_data.get('mini_articles', [])

            # Check for empty day
            if not main_story and not mini_articles:
                warnings.append(f"Day {day_num} is empty")
                continue

            # Check for missing main story
            if not main_story or not main_story.get('title'):
                self.console.print(f"[red]Error: Day {day_num} has no main story[/red]")
                valid = False

            # Check for no mini articles
            if not mini_articles:
                warnings.append(f"Day {day_num} has no mini articles (only main story)")

            # Check for too many mini articles
            if len(mini_articles) > 4:
                warnings.append(f"Day {day_num} has {len(mini_articles)} mini articles (recommended max: 4)")

        # Show warnings
        if warnings:
            self.console.print("\n[yellow]Validation warnings:[/yellow]")
            for warning in warnings:
                self.console.print(f"  ⚠️  {warning}")

        return valid

    def save_curated(self, output_file: Path, generate_teasers: bool = True) -> None:
        """
        Save working_data to new JSON file (excluding unused stories).

        Args:
            output_file: Path to save curated JSON
            generate_teasers: Whether to generate tomorrow teasers (default True)
        """
        # Create output data without unused category
        output_data = {k: v for k, v in self.working_data.items() if k != 'unused'}

        # Generate teasers for days 1-3 using tomorrow's content
        if generate_teasers:
            self.console.print("\n[cyan]Generating tomorrow teasers...[/cyan]")
            try:
                output_data = generate_teasers_for_curated_data(output_data, console=self.console)
                for day_num in [1, 2, 3]:
                    day_key = f"day_{day_num}"
                    if day_key in output_data and output_data[day_key].get("tomorrow_teaser"):
                        self.console.print(f"  [green]✨[/green] Day {day_num}: teaser generated")
                    else:
                        self.console.print(f"  [dim]⏭️  Day {day_num}: skipped (no tomorrow content)[/dim]")
            except Exception as e:
                self.console.print(f"  [yellow]⚠️  Teaser generation failed: {e}[/yellow]")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        self.console.print(f"\n[green]✓[/green] Saved to: {output_file}")

        # Report unused stories count if any
        if 'unused' in self.working_data:
            unused_count = len(self.working_data['unused'].get('stories', []))
            if unused_count > 0:
                self.console.print(f"[dim]  ({unused_count} unused stories excluded from newspaper)[/dim]")

    def revert_to_default_themes(self):
        """Revert working_data to use default themes."""
        from ftn_to_json import DEFAULT_THEMES

        # Update theme_metadata to defaults
        self.working_data["theme_metadata"] = {
            day: {
                "name": info["name"],
                "key": info["key"],
                "source": "default",
                "status": "unknown",
                "story_count": 0,
                "high_strength_count": 0
            }
            for day, info in DEFAULT_THEMES.items()
        }

        # Update day themes
        for day_num in range(1, 5):
            day_key = f"day_{day_num}"
            if day_key in self.working_data:
                self.working_data[day_key]["theme"] = DEFAULT_THEMES[day_num]["name"]

        self.console.print("[green]✓ Reverted to default themes[/green]")

    def regroup_with_themes(self, themes: dict) -> bool:
        """
        Re-group stories using new theme assignments.

        Args:
            themes: Dict mapping day (1-4) to theme info with name, key, source

        Returns:
            True if regrouping succeeded, False otherwise
        """
        from anthropic import Anthropic
        from ftn_to_json import group_stories_into_days, _build_four_days_from_grouping

        # Check for API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            self.console.print("[red]Error: ANTHROPIC_API_KEY not set. Cannot regroup.[/red]")
            return False

        self.console.print("\n[dim]Regrouping stories with new themes...[/dim]")

        try:
            client = Anthropic()

            # Collect all stories from current working_data
            all_stories = []
            story_id = 0
            for day_num in range(1, 5):
                day_key = f"day_{day_num}"
                day_data = self.working_data.get(day_key, {})

                # Main story
                main = day_data.get("main_story")
                if main and main.get("title"):
                    all_stories.append({
                        "id": story_id,
                        "headline": main.get("tui_headline") or main.get("title", "")[:50],
                        "primary_theme": themes[day_num]["key"],
                        "secondary_themes": [],
                        "story_strength": "medium",
                        "length": len(main.get("content", "")),
                        "_story_data": main
                    })
                    story_id += 1

                # Second story
                second = day_data.get("second_story")
                if second and second.get("title"):
                    all_stories.append({
                        "id": story_id,
                        "headline": second.get("tui_headline") or second.get("title", "")[:50],
                        "primary_theme": themes[day_num]["key"],
                        "secondary_themes": [],
                        "story_strength": "medium",
                        "length": len(second.get("content", "")),
                        "_story_data": second
                    })
                    story_id += 1

                # Mini articles
                for mini in day_data.get("mini_articles", []):
                    if mini and mini.get("title"):
                        all_stories.append({
                            "id": story_id,
                            "headline": mini.get("tui_headline") or mini.get("title", "")[:50],
                            "primary_theme": themes[day_num]["key"],
                            "secondary_themes": [],
                            "story_strength": "medium",
                            "length": len(mini.get("content", "")),
                            "_story_data": mini
                        })
                        story_id += 1

            # Add unused stories
            unused = self.working_data.get("unused", {}).get("stories", [])
            for story in unused:
                if story and story.get("title"):
                    all_stories.append({
                        "id": story_id,
                        "headline": story.get("tui_headline") or story.get("title", "")[:50],
                        "primary_theme": "society",  # Default
                        "secondary_themes": [],
                        "story_strength": "low",
                        "length": len(story.get("content", "")),
                        "_story_data": story
                    })
                    story_id += 1

            if not all_stories:
                self.console.print("[yellow]No stories to regroup.[/yellow]")
                return False

            # Call grouping function
            grouping = group_stories_into_days(
                stories=all_stories,
                blocklisted_ids=[],
                themes=themes,
                client=client
            )

            # Build new structure
            story_list = [s["_story_data"] for s in sorted(all_stories, key=lambda x: x["id"])]
            new_data = _build_four_days_from_grouping(
                stories=story_list,
                grouping=grouping,
                themes=themes
            )

            # Update working_data
            for day_key in ["day_1", "day_2", "day_3", "day_4"]:
                if day_key in new_data:
                    self.working_data[day_key] = new_data[day_key]
            if "unused" in new_data:
                self.working_data["unused"] = new_data["unused"]
            if "theme_metadata" in new_data:
                self.working_data["theme_metadata"] = new_data["theme_metadata"]

            self.console.print("[green]✓ Stories regrouped successfully[/green]")
            return True

        except Exception as e:
            self.console.print(f"[red]Error regrouping: {e}[/red]")
            self.console.print("[yellow]Keeping current assignments.[/yellow]")
            return False
