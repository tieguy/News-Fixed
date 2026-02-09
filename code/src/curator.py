# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Interactive story curation for News, Fixed."""

import json
import copy
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from xkcd import XkcdManager
from generator import ContentGenerator

console = Console()

# Theme names for each day
_DAY_THEMES = {
    1: "Health & Education",
    2: "Environment & Conservation",
    3: "Technology & Energy",
    4: "Society & Youth Movements"
}


def _get_theme_name(day_num: int) -> str:
    """Get theme name for a day number."""
    return _DAY_THEMES.get(day_num, "General")


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


def generate_teasers_for_curated_data(curated_data: Dict) -> Dict:
    """
    Generate tomorrow teasers for days 1-3 based on next day's content.

    Args:
        curated_data: Dict with day_1 through day_4 keys

    Returns:
        Modified curated_data with populated tomorrow_teaser fields
    """
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
                tomorrow_theme=tomorrow.get("theme", _get_theme_name(day_num + 1)),
                main_title=main_title,
                secondary_title=secondary_title
            )
            curated_data[current_day]["tomorrow_teaser"] = teaser
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to generate teaser for day {day_num}: {e}[/yellow]")
            # Leave teaser empty on failure

    return curated_data


class StoryCurator:
    """Manages interactive story curation workflow."""

    def __init__(self, json_file: Path, output_file: Path = None):
        """
        Load auto-categorized JSON from ftn_to_json.py.

        Args:
            json_file: Path to JSON file with day_1/day_2/day_3/day_4 structure
            output_file: Path where curated JSON will be saved (for auto-save)
        """
        self.json_file = Path(json_file)
        self.output_file = output_file
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
                console.print(f"[yellow]Warning: {day_key} not found in JSON[/yellow]")

        return data

    def _day_theme(self, day_num: int) -> str:
        """Get the live theme name for a day from working data."""
        day_key = f"day_{day_num}"
        if day_key in self.working_data:
            return self.working_data[day_key].get('theme', _get_theme_name(day_num))
        return _get_theme_name(day_num)

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
            console.print(f"[dim][Auto-save failed: {e}][/dim]")

    def display_unused_table(self, page: int = 0, page_size: int = 10) -> tuple:
        """
        Show one page of unused stories in a Rich table.

        Args:
            page: 0-based page number
            page_size: Stories per page (0 = show all)

        Returns:
            (total_stories, total_pages) tuple
        """
        unused_stories = []
        if 'unused' in self.working_data:
            unused_stories = self.working_data['unused'].get('stories', [])

        total = len(unused_stories)
        if total == 0:
            return (0, 0)

        if page_size <= 0:
            # Show all
            start, end = 0, total
            total_pages = 1
        else:
            total_pages = (total + page_size - 1) // page_size
            page = max(0, min(page, total_pages - 1))
            start = page * page_size
            end = min(start + page_size, total)

        title = "Unused Stories (Blocklisted or Uncategorized)"
        if total_pages > 1:
            title += f" — Page {page + 1}/{total_pages}"

        table = Table(title=title)
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="yellow")
        table.add_column("Length", justify="right", width=10)

        for i in range(start, end):
            story = unused_stories[i]
            story_title = story.get('tui_headline') or story.get('title', 'Untitled')[:60]
            full_length = len(story.get('title', '')) + len(story.get('content', ''))
            table.add_row(str(i + 1), story_title, f"{full_length} chars")

        console.print(table)
        console.print()
        return (total, total_pages)

    def display_day_table(self, day_num: int) -> None:
        """
        Show a single day's table.

        Args:
            day_num: Day number (1-4)
        """
        day_key = f"day_{day_num}"
        if day_key not in self.working_data:
            return

        day_data = self.working_data[day_key]
        theme = day_data.get('theme', 'Unknown Theme')

        table = Table(title=f"Day {day_num}: {theme}")
        table.add_column("#", style="dim", width=3)
        table.add_column("Role", width=6)
        table.add_column("Title", style="cyan")
        table.add_column("Length", justify="right", width=10)

        # Add main story
        main = day_data.get('main_story', {})
        if main:
            title = main.get('tui_headline') or main.get('title', 'Untitled')[:60]
            full_length = len(main.get('title', '')) + len(main.get('content', ''))
            table.add_row("1", "[bold]MAIN[/bold]", title, f"{full_length} chars")

        # Add second main story (if present)
        second = day_data.get('second_story', {})
        has_second = bool(second and second.get('title'))
        if has_second:
            title = second.get('tui_headline') or second.get('title', 'Untitled')[:60]
            full_length = len(second.get('title', '')) + len(second.get('content', ''))
            table.add_row("2", "[bold]MAIN2[/bold]", title, f"{full_length} chars")

        # Add mini articles
        mini_start = 3 if has_second else 2
        minis = day_data.get('mini_articles', [])
        for i, mini in enumerate(minis, start=mini_start):
            title = mini.get('tui_headline') or mini.get('title', 'Untitled')[:60]
            full_length = len(mini.get('title', '')) + len(mini.get('content', ''))
            table.add_row(str(i), "mini", title, f"{full_length} chars")

        console.print(table)
        console.print()

    def display_overview(self) -> None:
        """Show unused stories first, then all 4 days in rich tables."""
        console.print("\n[bold cyan]Story Curation Overview[/bold cyan]\n")

        # Display unused stories FIRST (all at once in overview)
        self.display_unused_table(page_size=0)

        # Then display day tables
        for day_num in range(1, 5):
            self.display_day_table(day_num)

    def review_themes(self) -> str:
        """
        Display and review proposed themes.

        Returns:
            'accept' to proceed with current themes
            'revert' to switch to default themes
        """
        console = Console()

        # Get theme_metadata from working data
        theme_metadata = self.working_data.get("theme_metadata", {})

        if not theme_metadata:
            console.print("\n[yellow]No theme metadata found. Using default themes.[/yellow]")
            return 'accept'

        console.print("\n[bold]🎯 Theme Review[/bold]\n")

        # Create theme summary table
        table = Table(title="Proposed Daily Themes")
        table.add_column("Day", style="dim", width=4)
        table.add_column("Theme", style="cyan")
        table.add_column("Source", style="magenta", width=20)
        table.add_column("Status", width=12)
        table.add_column("Stories", justify="right", width=8)

        for day in sorted(theme_metadata.keys(), key=lambda x: int(x) if isinstance(x, str) else x):
            day_int = int(day) if isinstance(day, str) else day
            meta = theme_metadata[day]

            # Get theme health if available
            status = meta.get("status", "unknown")
            story_count = meta.get("story_count", "?")
            high_count = meta.get("high_strength_count", "?")

            # Format status with color
            if status == "healthy":
                status_display = "[green]✓ Healthy[/green]"
            elif status == "weak":
                status_display = "[yellow]⚠️ Weak[/yellow]"
            elif status == "overloaded":
                status_display = "[red]⚠️ Overloaded[/red]"
            else:
                status_display = "[dim]Unknown[/dim]"

            # Format source
            source = meta.get("source", "unknown")
            if source == "default":
                source_display = "[dim]default[/dim]"
            elif source == "generated":
                source_display = "[cyan]generated[/cyan]"
            elif source.startswith("split_from_"):
                source_display = f"[magenta]split[/magenta]"
            else:
                source_display = source

            table.add_row(
                str(day_int),
                meta.get("name", "Unknown"),
                source_display,
                status_display,
                f"{story_count} ({high_count} high)"
            )

        console.print(table)

        # Show any non-default themes prominently
        non_defaults = [
            (day, meta) for day, meta in theme_metadata.items()
            if meta.get("source") != "default"
        ]

        if non_defaults:
            console.print("\n[bold yellow]Note:[/bold yellow] Some themes were dynamically generated:")
            for day, meta in non_defaults:
                day_int = int(day) if isinstance(day, str) else day
                console.print(f"  • Day {day_int}: [cyan]{meta.get('name')}[/cyan] ({meta.get('source')})")

        # Show action menu
        console.print("\n[bold]Actions:[/bold]")
        console.print("  [A] Accept themes and continue")
        console.print("  [E] Edit theme names")
        console.print("  [R] Revert to default themes")
        console.print()

        while True:
            choice = console.input("[bold]Choose action: [/bold]").strip().lower()

            if choice == 'a':
                return 'accept'
            elif choice == 'e':
                return 'edit'
            elif choice == 'r':
                return 'revert'
            else:
                console.print("[red]Invalid choice. Use A, E, or R.[/red]")

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

        Console().print("[green]✓ Reverted to default themes[/green]")

    def edit_themes(self) -> dict:
        """
        Allow user to edit individual theme names.

        Returns:
            Updated themes dict mapping day (1-4) to theme info
        """
        console = Console()
        theme_metadata = self.working_data.get("theme_metadata", {})

        if not theme_metadata:
            console.print("[yellow]No theme metadata to edit.[/yellow]")
            return None

        console.print("\n[bold]Edit Theme Names[/bold]")
        console.print("[dim]Press Enter to keep current name, or type new name[/dim]\n")

        updated_themes = {}
        for day in sorted(theme_metadata.keys(), key=lambda x: int(x) if isinstance(x, str) else x):
            day_int = int(day) if isinstance(day, str) else day
            meta = theme_metadata[day]
            current_name = meta.get("name", "Unknown")

            new_name = console.input(f"Day {day_int} [{current_name}]: ").strip()

            if new_name:
                updated_themes[day_int] = {
                    "name": new_name,
                    "key": new_name.lower().replace(" ", "_").replace("&", "and"),
                    "source": "edited"
                }
            else:
                updated_themes[day_int] = {
                    "name": current_name,
                    "key": meta.get("key", current_name.lower().replace(" ", "_")),
                    "source": meta.get("source", "default")
                }

        return updated_themes

    def regroup_with_themes(self, themes: dict) -> bool:
        """
        Re-group stories using new theme assignments.

        Args:
            themes: Dict mapping day (1-4) to theme info with name, key, source

        Returns:
            True if regrouping succeeded, False otherwise
        """
        import os
        from anthropic import Anthropic
        from ftn_to_json import group_stories_into_days, _build_four_days_from_grouping

        console = Console()

        # Check for API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            console.print("[red]Error: ANTHROPIC_API_KEY not set. Cannot regroup.[/red]")
            return False

        console.print("\n[dim]Regrouping stories with new themes...[/dim]")

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
                console.print("[yellow]No stories to regroup.[/yellow]")
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

            console.print("[green]✓ Stories regrouped successfully[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Error regrouping: {e}[/red]")
            console.print("[yellow]Keeping current assignments.[/yellow]")
            return False

    def view_story(self, day_num: int, story_index: int) -> None:
        """
        Display full story details.

        Args:
            day_num: Day number (1-4)
            story_index: Story index (1-based, 1=main, 2+=minis)
        """
        day_key = f"day_{day_num}"
        if day_key not in self.working_data:
            console.print(f"[red]Error: {day_key} not found[/red]")
            return

        day_data = self.working_data[day_key]
        has_second = self._has_second_story(day_data)
        mini_start = self._mini_start_index(day_data)

        # Get the story
        if story_index == 1:
            story = day_data.get('main_story', {})
            role = "MAIN story"
        elif story_index == 2 and has_second:
            story = day_data.get('second_story', {})
            role = "second main story"
        else:
            minis = day_data.get('mini_articles', [])
            mini_idx = story_index - mini_start
            if mini_idx < 0 or mini_idx >= len(minis):
                console.print(f"[red]Error: Story {story_index} not found[/red]")
                return
            story = minis[mini_idx]
            role = "mini article"

        # Display story details
        title = story.get('title', 'Untitled')
        content = story.get('content', '')
        source_url = story.get('source_url', 'No URL')

        panel_content = f"""[bold]Title:[/bold] {title}
[bold]Length:[/bold] {len(content)} characters
[bold]Source:[/bold] {source_url}
[bold]Role:[/bold] {role}

[bold]Content:[/bold]
{content[:500]}{'...' if len(content) > 500 else ''}"""

        console.print(Panel(panel_content, title=f"Day {day_num} - Story {story_index}"))

    def swap_main_story(self, day_num: int, new_main_index: int) -> None:
        """
        Change which story is main vs mini.

        Args:
            day_num: Day number (1-4)
            new_main_index: Story index to make main (1-based, 2+ = currently minis)
        """
        day_key = f"day_{day_num}"
        if day_key not in self.working_data:
            console.print(f"[red]Error: {day_key} not found[/red]")
            return

        day_data = self.working_data[day_key]
        has_second = self._has_second_story(day_data)
        mini_start = self._mini_start_index(day_data)

        # Can't swap with itself
        if new_main_index == 1:
            console.print("[yellow]Story 1 is already the main story[/yellow]")
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
                console.print(f"[red]Error: Story {new_main_index} not found[/red]")
                return
            new_main = minis[mini_idx]
            day_data['main_story'] = new_main
            minis[mini_idx] = current_main

        # Record change
        change_msg = f"Day {day_num}: Swapped main story"
        self.changes_made.append(change_msg)

        console.print(f"[green]✓[/green] {change_msg}")
        console.print(f"  New main: {new_main.get('title', 'Untitled')[:50]}...")
        console.print(f"  Demoted: {current_main.get('title', 'Untitled')[:50]}...")

        # Auto-save after change
        self._auto_save()

    def _handle_overflow(self, to_day: int, incoming_story: dict) -> Optional[dict]:
        """
        Handle adding story to a full day (5 stories already).

        Args:
            to_day: Target day number
            incoming_story: Story being moved

        Returns:
            Story to swap back to source day, or None if cancelled/replaced
        """
        to_data = self.working_data[f"day_{to_day}"]
        minis = to_data.get('mini_articles', [])

        incoming_title = incoming_story.get('title', 'Untitled')[:40]

        to_has_second = self._has_second_story(to_data)
        max_capacity = 6 if to_has_second else 5
        capacity_desc = "2 main + 4 minis" if to_has_second else "1 main + 4 minis"
        console.print(f"\n[yellow]⚠️  Warning: Day {to_day} already has {max_capacity} stories ({capacity_desc})[/yellow]")
        console.print(f"   Moving '{incoming_title}' would exceed the limit.\n")
        console.print("Options:")
        console.print("  [S] Swap with an existing mini article")
        console.print("  [R] Replace an existing mini article")
        console.print("  [C] Cancel move")

        choice = console.input("\nChoice: ").strip().lower()

        if choice == 'c':
            console.print("[yellow]Move cancelled[/yellow]")
            return None

        if choice not in ['s', 'r']:
            console.print("[yellow]Invalid choice, cancelling move[/yellow]")
            return None

        # Show mini articles to swap/replace
        console.print(f"\n{'Swap' if choice == 's' else 'Replace'} with which Day {to_day} mini article?")
        for i, mini in enumerate(minis, start=1):
            title = mini.get('title', 'Untitled')[:50]
            length = len(mini.get('content', ''))
            console.print(f"  [{i}] {title} ({length} chars)")

        target = console.input(f"\nChoice (1-{len(minis)}, or 'back'): ").strip()

        if target == 'back':
            console.print("[yellow]Move cancelled[/yellow]")
            return None

        try:
            target_idx = int(target) - 1
            if target_idx < 0 or target_idx >= len(minis):
                console.print("[red]Invalid choice, cancelling move[/red]")
                return None

            target_story = minis[target_idx]
            target_title = target_story.get('title', 'Untitled')[:40]

            # Add incoming story to target day
            minis[target_idx] = incoming_story

            if choice == 's':
                # Swap: return target story to source day
                console.print(f"[green]✓[/green] Swapped: {incoming_title} ↔ {target_title}")
                return target_story
            else:
                # Replace: target story is removed
                console.print(f"[green]✓[/green] Replaced {target_title} with {incoming_title}")
                console.print(f"[dim]  ({target_title} removed from curation)[/dim]")
                return None

        except ValueError:
            console.print("[red]Invalid choice, cancelling move[/red]")
            return None

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
            console.print("[red]Error: Invalid day number[/red]")
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
                console.print(f"[red]Error: Story {story_index} not found[/red]")
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
                console.print(f"[yellow]⚠️  Warning: Day {from_day} will have no main story after this move[/yellow]")
                console.print(f"[dim]   (This will cause validation to fail when saving)[/dim]")
                from_data['main_story'] = {}
        elif slot_type == 'second':
            from_data['second_story'] = {}
        else:
            from_data['mini_articles'].pop(mini_idx)

        if to_count >= to_max:
            # Handle overflow (swap or replace)
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

        console.print(f"[green]✓[/green] Moved: {story_title}")
        console.print(f"  From: Day {from_day} → To: Day {to_day} (mini)")

        # Auto-save after change
        self._auto_save()

        return True

    def move_to_unused(self, from_day: int, story_index: int) -> None:
        """
        Move a story from a day to unused (delete from newspaper).

        Args:
            from_day: Source day number (1-4)
            story_index: Story index in source day (1-based)
        """
        from_key = f"day_{from_day}"
        if from_key not in self.working_data:
            console.print("[red]Error: Invalid day number[/red]")
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
                console.print(f"[red]Error: Story {story_index} not found[/red]")
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
                console.print(f"[yellow]⚠️  Warning: Day {from_day} will have no main story after this move[/yellow]")
                console.print(f"[dim]   (This will cause validation to fail when saving)[/dim]")
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

        console.print(f"[green]✓[/green] Moved to unused: {story_title}")
        console.print(f"  Story removed from newspaper")

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
            console.print("[red]Error: No unused stories[/red]")
            return

        unused_stories = self.working_data['unused'].get('stories', [])
        if story_index < 1 or story_index > len(unused_stories):
            console.print(f"[red]Error: Story {story_index} not found in unused[/red]")
            return

        # Validate target day before removing from unused
        if to_day < 1 or to_day > 4:
            console.print(f"[red]Error: Invalid day number {to_day}[/red]")
            return

        to_key = f"day_{to_day}"

        # Create target day if it doesn't exist
        if to_key not in self.working_data:
            self.working_data[to_key] = {
                "theme": _get_theme_name(to_day),
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

        console.print(f"[green]✓[/green] Moved from unused: {story_title}")
        console.print(f"  Added to Day {to_day} (mini)")

        # Warn if day now exceeds capacity
        new_count = to_count + 1
        if new_count > to_max:
            console.print(f"[yellow]⚠️  Day {to_day} now has {new_count} stories (over capacity)[/yellow]")
            console.print(f"[dim]   You'll need to remove {new_count - to_max} during day review[/dim]")

        # Auto-save after change
        self._auto_save()

    def review_unused(self, page: int = 0) -> str:
        """
        Interactive review for unused stories with pagination.

        Args:
            page: 0-based page number for pagination

        Returns:
            User's choice: 'accept', 'move', 'view', 'next_page', 'prev_page'
        """
        if 'unused' not in self.working_data:
            return 'accept'

        unused_stories = self.working_data['unused'].get('stories', [])
        if not unused_stories:
            return 'accept'

        max_index = len(unused_stories)

        # Show the table for the current page
        total, total_pages = self.display_unused_table(page=page, page_size=10)

        # Show which range is visible
        if total_pages > 1:
            start = page * 10 + 1
            end = min((page + 1) * 10, total)
            console.print(f"[dim]Showing stories {start}-{end} of {total}[/dim]")

        console.print(f"\n[bold]Review Unused Stories ({max_index} total)[/bold]")
        console.print("  [A] Accept as-is (keep all unused)")
        console.print("  [M] Move story to a day")
        console.print("  [V] View story details")
        console.print(f"  [1-{max_index}] Quick move story # to a day")
        if total_pages > 1:
            if page < total_pages - 1:
                console.print("  [N] Next page")
            if page > 0:
                console.print("  [P] Previous page")

        choice = console.input("\n[cyan]Choice:[/cyan] ").strip().lower()

        # Check for numeric shortcut (e.g., "3" means move unused story 3)
        if choice.isdigit():
            story_num = int(choice)
            if 1 <= story_num <= max_index:
                # Trigger move action with this story number pre-selected
                self._handle_unused_move_action(story_num)
                return 'move'  # Signal that we handled a move
            else:
                console.print(f"[red]Invalid story number (must be 1-{max_index})[/red]")
                return 'accept'

        if choice == 'a':
            return 'accept'
        elif choice == 'm':
            return 'move'
        elif choice == 'v':
            return 'view'
        elif choice == 'n' and total_pages > 1 and page < total_pages - 1:
            return 'next_page'
        elif choice == 'p' and total_pages > 1 and page > 0:
            return 'prev_page'
        else:
            console.print("[yellow]Invalid choice, treating as 'accept'[/yellow]")
            return 'accept'

    def _handle_unused_move_action(self, preselected_story: int = None) -> None:
        """Handle moving a story from unused to a day.

        Args:
            preselected_story: If provided, skip asking which story to move
        """
        unused_stories = self.working_data['unused'].get('stories', [])
        max_index = len(unused_stories)

        if preselected_story is not None:
            story_index = preselected_story
        else:
            story_num = console.input(f"\nWhich unused story to move? (1-{max_index}, or 'back'): ").strip()

            if story_num == 'back':
                return

            try:
                story_index = int(story_num)
            except ValueError:
                console.print("[red]Invalid story number[/red]")
                return

        console.print(f"\nMove story to which day?")
        for d in range(1, 5):
            console.print(f"  [{d}] {self._day_theme(d)}")

        target = console.input("\nChoice (1-4, or 'back'): ").strip()

        if target == 'back':
            return

        try:
            to_day = int(target)
            if to_day < 1 or to_day > 4:
                console.print("[red]Invalid day number[/red]")
                return
            self.move_from_unused(story_index, to_day)
        except ValueError:
            console.print("[red]Invalid choice[/red]")

    def _handle_unused_view_action(self) -> None:
        """Handle viewing an unused story."""
        unused_stories = self.working_data['unused'].get('stories', [])
        max_index = len(unused_stories)

        story_num = console.input(f"Which story? (1-{max_index}, or 'back'): ").strip()

        if story_num == 'back':
            return

        try:
            story_index = int(story_num)
            if story_index < 1 or story_index > max_index:
                console.print(f"[red]Invalid story number[/red]")
                return

            story = unused_stories[story_index - 1]
            title = story.get('title', 'Untitled')
            content = story.get('content', '')
            source_url = story.get('source_url', 'No URL')

            panel_content = f"""[bold]Title:[/bold] {title}
[bold]Length:[/bold] {len(content)} characters
[bold]Source:[/bold] {source_url}
[bold]Status:[/bold] Unused (will not appear in newspaper)

[bold]Content:[/bold]
{content[:500]}{'...' if len(content) > 500 else ''}"""

            console.print(Panel(panel_content, title=f"Unused Story {story_index}"))
            console.input("\nPress Enter to continue...")
        except ValueError:
            console.print("[red]Invalid story number[/red]")

    def review_day(self, day_num: int) -> str:
        """
        Interactive review for one day.

        Args:
            day_num: Day number (1-4)

        Returns:
            User's choice: 'accept', 'move', 'swap', 'view', 'back'
        """
        day_key = f"day_{day_num}"
        if day_key not in self.working_data:
            console.print(f"[red]Error: {day_key} not found[/red]")
            return 'accept'

        day_data = self.working_data[day_key]
        theme = day_data.get('theme', 'Unknown Theme')
        total_stories = self._total_stories(day_data)
        max_index = total_stories

        # Show the day's table before the menu
        self.display_day_table(day_num)

        # Auto-prompt if day exceeds capacity
        has_second = self._has_second_story(day_data)
        max_capacity = 6 if has_second else 5
        capacity_desc = "2 main + 4 minis" if has_second else "1 main + 4 minis"
        if total_stories > max_capacity:
            console.print(f"\n[yellow]⚠️  Day {day_num} has {total_stories} stories (capacity exceeded!)[/yellow]")
            console.print(f"[dim]   Maximum is {capacity_desc} = {max_capacity} total stories[/dim]")
            console.print(f"[dim]   You need to remove at least {total_stories - max_capacity} stories[/dim]\n")

        console.print(f"\n[bold]Review Day {day_num}: {theme}[/bold]")
        console.print("  [A] Accept as-is")
        console.print("  [M] Move stories to different day")
        console.print("  [S] Swap main/mini assignments")
        console.print("  [C] Combine 2+ stories into one")
        console.print("  [V] View story details")
        console.print(f"  [1-{max_index}] Quick move story # to another day")
        if day_num == 1:
            console.print("  [B] Back to unused stories")
        else:
            console.print("  [B] Back to previous day")

        choice = console.input("\n[cyan]Choice:[/cyan] ").strip().lower()

        # Check for numeric shortcut (e.g., "3" means move story 3)
        if choice.isdigit():
            story_num = int(choice)
            if 1 <= story_num <= max_index:
                # Trigger move action with this story number pre-selected
                self._handle_move_action(day_num, story_num)
                return 'move'  # Signal that we handled a move
            else:
                console.print(f"[red]Invalid story number (must be 1-{max_index})[/red]")
                return 'accept'

        if choice == 'a':
            return 'accept'
        elif choice == 'm':
            return 'move'
        elif choice == 's':
            return 'swap'
        elif choice == 'c':
            return 'combine'
        elif choice == 'v':
            return 'view'
        elif choice == 'b':
            return 'back'
        else:
            console.print("[yellow]Invalid choice, treating as 'accept'[/yellow]")
            return 'accept'

    def _handle_view_action(self, day_num: int) -> None:
        """Handle view story action."""
        day_data = self.working_data[f"day_{day_num}"]
        max_index = self._total_stories(day_data)

        story_num = console.input(f"Which story? (1-{max_index}, or 'back'): ").strip()

        if story_num == 'back':
            return

        try:
            self.view_story(day_num, int(story_num))
            console.input("\nPress Enter to continue...")
        except ValueError:
            console.print("[red]Invalid story number[/red]")

    def _handle_swap_action(self, day_num: int) -> None:
        """Handle swap/promote story roles."""
        day_data = self.working_data[f"day_{day_num}"]
        has_second = self._has_second_story(day_data)
        mini_start = self._mini_start_index(day_data)
        minis = day_data.get('mini_articles', [])

        if not minis and not has_second:
            console.print("[yellow]No other stories to swap with[/yellow]")
            return

        # Offer promote option when second main slot is empty and minis exist
        can_promote = not has_second and len(minis) > 0

        console.print("\n[bold]Reassign story roles:[/bold]")
        console.print("  [S] Swap main story with another")
        if can_promote:
            console.print("  [P] Promote a mini to second main story")
        if has_second:
            console.print("  [D] Demote second main to mini")

        sub_choice = console.input("\nChoice (or 'back'): ").strip().lower()

        if sub_choice == 'back':
            return

        if sub_choice == 's':
            self._swap_main_submenu(day_num)
        elif sub_choice == 'p' and can_promote:
            self._promote_to_second_main(day_num)
        elif sub_choice == 'd' and has_second:
            self._demote_second_main(day_num)
        else:
            console.print("[yellow]Invalid choice[/yellow]")

    def _swap_main_submenu(self, day_num: int) -> None:
        """Show the swap-main-story submenu."""
        day_data = self.working_data[f"day_{day_num}"]
        has_second = self._has_second_story(day_data)
        mini_start = self._mini_start_index(day_data)
        minis = day_data.get('mini_articles', [])

        console.print("\nPick new main story:")
        console.print(f"  [1] {day_data.get('main_story', {}).get('title', 'Untitled')[:50]} (currently MAIN)")

        if has_second:
            second = day_data.get('second_story', {})
            title = second.get('title', 'Untitled')[:50]
            length = len(second.get('content', ''))
            console.print(f"  [2] {title} ({length} chars) (currently MAIN2)")

        for i, mini in enumerate(minis, start=mini_start):
            title = mini.get('title', 'Untitled')[:50]
            length = len(mini.get('content', ''))
            console.print(f"  [{i}] {title} ({length} chars)")

        max_choice = self._total_stories(day_data)
        choice = console.input(f"\nChoice (2-{max_choice}, or 'back'): ").strip()

        if choice == 'back':
            return

        try:
            self.swap_main_story(day_num, int(choice))
        except ValueError:
            console.print("[red]Invalid choice[/red]")

    def _promote_to_second_main(self, day_num: int) -> None:
        """Promote a mini article to the second main story slot."""
        day_key = f"day_{day_num}"
        day_data = self.working_data[day_key]
        mini_start = self._mini_start_index(day_data)
        minis = day_data.get('mini_articles', [])

        if not minis:
            console.print("[yellow]No mini articles to promote[/yellow]")
            return

        console.print("\nPromote which mini to second main story?")
        for i, mini in enumerate(minis, start=mini_start):
            title = mini.get('title', 'Untitled')[:50]
            length = len(mini.get('content', ''))
            console.print(f"  [{i}] {title} ({length} chars)")

        choice = console.input(f"\nChoice ({mini_start}-{mini_start + len(minis) - 1}, or 'back'): ").strip()

        if choice == 'back':
            return

        try:
            idx = int(choice)
            mini_idx = idx - mini_start
            if mini_idx < 0 or mini_idx >= len(minis):
                console.print(f"[red]Invalid choice[/red]")
                return

            promoted = minis.pop(mini_idx)
            day_data['second_story'] = promoted

            title = promoted.get('title', 'Untitled')[:50]
            change_msg = f"Day {day_num}: Promoted '{title}' to second main story"
            self.changes_made.append(change_msg)
            console.print(f"[green]✓[/green] {change_msg}")

            self._auto_save()
        except ValueError:
            console.print("[red]Invalid choice[/red]")

    def _demote_second_main(self, day_num: int) -> None:
        """Demote the second main story back to a mini article."""
        day_key = f"day_{day_num}"
        day_data = self.working_data[day_key]

        second = day_data.get('second_story', {})
        if not second or not second.get('title'):
            console.print("[yellow]No second main story to demote[/yellow]")
            return

        title = second.get('title', 'Untitled')[:50]
        minis = day_data.get('mini_articles', [])
        minis.insert(0, second)
        day_data['second_story'] = {}

        change_msg = f"Day {day_num}: Demoted '{title}' from second main to mini"
        self.changes_made.append(change_msg)
        console.print(f"[green]✓[/green] {change_msg}")

        self._auto_save()

    def _handle_move_action(self, day_num: int, preselected_story: int = None) -> None:
        """Handle move story action.

        Args:
            day_num: Day number (1-4)
            preselected_story: If provided, skip asking which story to move
        """
        day_data = self.working_data[f"day_{day_num}"]
        max_index = self._total_stories(day_data)

        if preselected_story is not None:
            story_index = preselected_story
        else:
            story_num = console.input(f"\nWhich story to move? (1-{max_index}, or 'back'): ").strip()

            if story_num == 'back':
                return

            try:
                story_index = int(story_num)
            except ValueError:
                console.print("[red]Invalid story number[/red]")
                return

        console.print(f"\nMove story to which day?")
        for d in range(1, 5):
            label = self._day_theme(d)
            suffix = " (current)" if d == day_num else ""
            console.print(f"  [{d}] {label}{suffix}")
        console.print(f"  [U] Unused (delete from newspaper)")

        target = console.input("\nChoice (1-4, U, or 'back'): ").strip().lower()

        if target == 'back':
            return

        if target == 'u':
            self.move_to_unused(day_num, story_index)
            return

        try:
            to_day = int(target)
            if to_day == day_num:
                console.print("[yellow]Story is already in this day[/yellow]")
                return
            self.move_story(day_num, story_index, to_day)
        except ValueError:
            console.print("[red]Invalid choice[/red]")

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

    def _handle_combine_action(self, day_num: int) -> None:
        """
        Handle combining 2+ same-day stories into one.

        Merges raw content (no Claude API call). The generator rewrites later.
        Preserves all source URLs for multi-QR-code rendering.
        """
        day_key = f"day_{day_num}"
        day_data = self.working_data[day_key]
        max_index = self._total_stories(day_data)

        if max_index < 2:
            console.print("[yellow]Need at least 2 stories to combine[/yellow]")
            return

        # Prompt for indices
        raw = console.input(
            f"\nWhich stories to combine? (e.g. '3,5' or '2 4 6', or 'back'): "
        ).strip()

        if raw.lower() == 'back':
            return

        # Parse comma or space separated indices
        parts = raw.replace(',', ' ').split()
        try:
            indices = [int(p) for p in parts]
        except ValueError:
            console.print("[red]Invalid input — enter numbers separated by commas or spaces[/red]")
            return

        if len(indices) < 2:
            console.print("[red]Need at least 2 stories to combine[/red]")
            return

        # Validate indices
        for idx in indices:
            if idx < 1 or idx > max_index:
                console.print(f"[red]Story {idx} not found (valid: 1-{max_index})[/red]")
                return

        if len(set(indices)) != len(indices):
            console.print("[red]Duplicate story numbers[/red]")
            return

        # Gather selected stories
        selected = []
        for idx in indices:
            story, slot_type = self._get_story_by_index(day_data, idx)
            if story is None:
                console.print(f"[red]Story {idx} not found[/red]")
                return
            selected.append((idx, story, slot_type))

        # Confirm
        console.print("\n[bold]Combine these stories?[/bold]")
        for idx, story, slot_type in selected:
            title = story.get('tui_headline') or story.get('title', 'Untitled')[:60]
            console.print(f"  [{idx}] {title}")

        confirm = console.input("\nCombine? [Y/n]: ").strip().lower()
        if confirm not in ('', 'y', 'yes'):
            console.print("[dim]Cancelled[/dim]")
            return

        # Build combined story
        titles = [s.get('title', '') for _, s, _ in selected]
        contents = [s.get('content', '') for _, s, _ in selected]

        # Collect all source URLs (deduped, order-preserving)
        all_source_urls = []
        seen_urls = set()
        for _, s, _ in selected:
            url = s.get('source_url', '')
            if url and url not in seen_urls:
                all_source_urls.append(url)
                seen_urls.add(url)

        # Merge all_urls from each story
        merged_all_urls = []
        seen_all = set()
        for _, s, _ in selected:
            for u in s.get('all_urls', []):
                if u not in seen_all:
                    merged_all_urls.append(u)
                    seen_all.add(u)

        first_title_short = (selected[0][1].get('tui_headline')
                             or selected[0][1].get('title', 'Story'))[:30]
        others_count = len(selected) - 1

        combined = {
            'title': '\n\n'.join(t for t in titles if t),
            'content': '\n\n'.join(c for c in contents if c),
            'source_url': all_source_urls[0] if all_source_urls else '',
            'source_urls': all_source_urls,
            'tui_headline': f"Combined: {first_title_short} + {others_count} more",
            'all_urls': merged_all_urls if merged_all_urls else all_source_urls,
        }

        # Determine where to place the combined story
        has_main_selected = any(st == 'main' for _, _, st in selected)
        first_idx = indices[0]

        # Remove originals in reverse index order to avoid shift issues
        has_second = self._has_second_story(day_data)
        mini_start = self._mini_start_index(day_data)

        for idx, _, slot_type in sorted(selected, key=lambda x: x[0], reverse=True):
            if slot_type == 'main':
                day_data['main_story'] = {}
            elif slot_type == 'second':
                day_data['second_story'] = {}
            else:
                mini_idx = idx - mini_start
                if 0 <= mini_idx < len(day_data.get('mini_articles', [])):
                    day_data['mini_articles'].pop(mini_idx)

        # Insert combined story
        if has_main_selected:
            day_data['main_story'] = combined
        else:
            # Insert at position of first selected story (as a mini)
            # Recalculate mini position after removals
            minis = day_data.get('mini_articles', [])
            # Place at start of minis if first_idx was near the top, else append
            new_mini_start = self._mini_start_index(day_data)
            insert_pos = max(0, first_idx - new_mini_start)
            insert_pos = min(insert_pos, len(minis))
            minis.insert(insert_pos, combined)

        # Clean up empty second_story if it was combined away
        if 'second_story' in day_data and not day_data['second_story'].get('title'):
            # If second_story is now empty, promote first mini if available
            if day_data.get('mini_articles'):
                day_data['second_story'] = day_data['mini_articles'].pop(0)
            else:
                del day_data['second_story']

        # Record change
        change_msg = f"Day {day_num}: Combined {len(selected)} stories → '{combined['tui_headline']}'"
        self.changes_made.append(change_msg)
        console.print(f"\n[green]✓[/green] {change_msg}")

        # Auto-save
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
                console.print(f"[red]Error: Day {day_num} has no main story[/red]")
                valid = False

            # Check for no mini articles
            if not mini_articles:
                warnings.append(f"Day {day_num} has no mini articles (only main story)")

            # Check for too many mini articles
            if len(mini_articles) > 4:
                warnings.append(f"Day {day_num} has {len(mini_articles)} mini articles (recommended max: 4)")

        # Show warnings
        if warnings:
            console.print("\n[yellow]Validation warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  ⚠️  {warning}")

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
            console.print("\n[cyan]Generating tomorrow teasers...[/cyan]")
            try:
                output_data = generate_teasers_for_curated_data(output_data)
                for day_num in [1, 2, 3]:
                    day_key = f"day_{day_num}"
                    if day_key in output_data and output_data[day_key].get("tomorrow_teaser"):
                        console.print(f"  [green]✨[/green] Day {day_num}: teaser generated")
                    else:
                        console.print(f"  [dim]⏭️  Day {day_num}: skipped (no tomorrow content)[/dim]")
            except Exception as e:
                console.print(f"  [yellow]⚠️  Teaser generation failed: {e}[/yellow]")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        console.print(f"\n[green]✓[/green] Saved to: {output_file}")

        # Report unused stories count if any
        if 'unused' in self.working_data:
            unused_count = len(self.working_data['unused'].get('stories', []))
            if unused_count > 0:
                console.print(f"[dim]  ({unused_count} unused stories excluded from newspaper)[/dim]")

    def review_xkcd(self) -> None:
        """
        Interactive xkcd comic selection for the newspaper.

        Auto-selects 4 comics (one per day), then lets user review and veto.
        """
        console.print("\n[bold cyan]xkcd Comic Selection (4 comics for the week)[/bold cyan]\n")

        xkcd_manager = XkcdManager()
        cache = xkcd_manager.load_cache()

        # Check if already selected for this week
        existing = xkcd_manager.get_week_selections()
        has_existing = any(existing.values())

        if has_existing:
            console.print("[bold]Current selections:[/bold]")
            for day in range(1, 5):
                comic_num = existing.get(day)
                if comic_num:
                    comic = cache.get(str(comic_num), {})
                    title = comic.get("title", "Unknown")
                    console.print(f"  Day {day} ({_get_theme_name(day)}): #{comic_num} \"{title}\"")
                else:
                    console.print(f"  Day {day} ({_get_theme_name(day)}): [dim]not selected[/dim]")
            console.print()

            choice = console.input("Keep current selections? [Y/n]: ").strip().lower()
            if choice in ['', 'y', 'yes']:
                console.print("[dim]Keeping current selections[/dim]")
                return
            # Otherwise, fall through to new selection

        # Get candidates - need at least 4
        candidates = xkcd_manager.get_candidates(max_count=20)

        # If not enough candidates, try fetching more
        if len(candidates) < 4:
            console.print(f"[yellow]Only {len(candidates)} comics available, need 4. Fetching more...[/yellow]")
            self._fetch_more_comics(xkcd_manager)
            candidates = xkcd_manager.get_candidates(max_count=20)

        if len(candidates) < 4:
            console.print(f"[red]Still only {len(candidates)} candidates after fetching.[/red]")
            console.print("[dim]Try again later or adjust filter criteria.[/dim]")
            return

        # Auto-select 4 comics
        try:
            auto_selections = xkcd_manager.auto_select_for_week()
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return

        # Build dict of day -> comic data for review
        selections = {}
        for day, comic_num in auto_selections.items():
            comic = cache.get(str(comic_num), {})
            selections[day] = {
                "num": comic_num,
                "title": comic.get("title", "Unknown"),
                "summary": comic.get("analysis", {}).get("brief_summary", ""),
                "url": f"https://xkcd.com/{comic_num}/"
            }

        # Review loop - let user approve or veto each
        console.print("[bold]Computer picked these 4 comics:[/bold]\n")

        reviewing = True
        while reviewing:
            # Display all 4
            for day in range(1, 5):
                sel = selections[day]
                console.print(f"  Day {day} ({_get_theme_name(day)}): #{sel['num']} \"{sel['title']}\"")
                if sel['summary']:
                    console.print(f"         [dim]{sel['summary']}[/dim]")
                console.print(f"         [dim]{sel['url']}[/dim]")
            console.print()

            console.print("[bold]Options:[/bold]")
            console.print("  [A] Accept all - looks good!")
            console.print("  [1-4] Veto comic for that day (pick a different one)")
            console.print("  [S] Skip xkcd for this week")
            console.print()

            choice = console.input("[cyan]Choice:[/cyan] ").strip().lower()

            if choice == 'a':
                # Save all selections
                final_selections = {day: sel["num"] for day, sel in selections.items()}
                xkcd_manager.save_week_selections(final_selections)
                console.print("\n[green]✓[/green] Saved all 4 comics!")
                for day in range(1, 5):
                    self.changes_made.append(
                        f"xkcd #{selections[day]['num']} selected for Day {day}"
                    )
                reviewing = False

            elif choice == 's':
                console.print("[dim]Skipping xkcd for this week[/dim]")
                reviewing = False

            elif choice in ['1', '2', '3', '4']:
                veto_day = int(choice)
                vetoed_num = selections[veto_day]["num"]
                console.print(f"\n[yellow]Vetoed #{vetoed_num} for Day {veto_day}[/yellow]")

                # Get replacement options (exclude already selected comics)
                used_nums = {sel["num"] for sel in selections.values()}
                replacement_candidates = [
                    c for c in candidates
                    if c["num"] not in used_nums
                ]

                if not replacement_candidates:
                    console.print("[red]No more candidates available![/red]")
                    continue

                # Show options: auto-pick or manual pick
                auto_pick = replacement_candidates[0]
                console.print(f"\n  [A] Auto-pick: #{auto_pick['num']} \"{auto_pick.get('title', 'Unknown')}\"")
                console.print(f"  [M] Pick manually from {len(replacement_candidates)} options")
                console.print(f"  [R] Reject #{vetoed_num} (mark as bad for future)")
                console.print()

                replace_choice = console.input("[cyan]Choice:[/cyan] ").strip().lower()

                if replace_choice == 'a':
                    # Use auto-pick
                    selections[veto_day] = {
                        "num": auto_pick["num"],
                        "title": auto_pick.get("title", "Unknown"),
                        "summary": auto_pick.get("analysis", {}).get("brief_summary", ""),
                        "url": f"https://xkcd.com/{auto_pick['num']}/"
                    }
                    console.print(f"[green]✓[/green] Replaced with #{auto_pick['num']}\n")

                elif replace_choice == 'm':
                    # Show all candidates for manual pick
                    console.print("\n[bold]Available comics:[/bold]")
                    for i, c in enumerate(replacement_candidates[:10], 1):
                        title = c.get("title", "Unknown")
                        summary = c.get("analysis", {}).get("brief_summary", "")
                        console.print(f"  [{i}] #{c['num']}: {title}")
                        if summary:
                            console.print(f"      [dim]{summary}[/dim]")

                    pick = console.input(f"\nPick (1-{min(10, len(replacement_candidates))}): ").strip()
                    try:
                        pick_idx = int(pick) - 1
                        if 0 <= pick_idx < len(replacement_candidates):
                            picked = replacement_candidates[pick_idx]
                            selections[veto_day] = {
                                "num": picked["num"],
                                "title": picked.get("title", "Unknown"),
                                "summary": picked.get("analysis", {}).get("brief_summary", ""),
                                "url": f"https://xkcd.com/{picked['num']}/"
                            }
                            console.print(f"[green]✓[/green] Selected #{picked['num']}\n")
                        else:
                            console.print("[yellow]Invalid choice, keeping auto-pick[/yellow]")
                            selections[veto_day] = {
                                "num": auto_pick["num"],
                                "title": auto_pick.get("title", "Unknown"),
                                "summary": auto_pick.get("analysis", {}).get("brief_summary", ""),
                                "url": f"https://xkcd.com/{auto_pick['num']}/"
                            }
                    except ValueError:
                        console.print("[yellow]Invalid input, keeping auto-pick[/yellow]")
                        selections[veto_day] = {
                            "num": auto_pick["num"],
                            "title": auto_pick.get("title", "Unknown"),
                            "summary": auto_pick.get("analysis", {}).get("brief_summary", ""),
                            "url": f"https://xkcd.com/{auto_pick['num']}/"
                        }

                elif replace_choice == 'r':
                    # Reject the comic and use auto-pick
                    self._handle_single_reject(xkcd_manager, vetoed_num)
                    selections[veto_day] = {
                        "num": auto_pick["num"],
                        "title": auto_pick.get("title", "Unknown"),
                        "summary": auto_pick.get("analysis", {}).get("brief_summary", ""),
                        "url": f"https://xkcd.com/{auto_pick['num']}/"
                    }
                    console.print(f"[green]✓[/green] Rejected #{vetoed_num}, replaced with #{auto_pick['num']}\n")

                else:
                    console.print("[dim]Cancelled veto[/dim]\n")

            else:
                console.print("[yellow]Invalid choice[/yellow]\n")

    def _fetch_more_comics(self, xkcd_manager: XkcdManager) -> None:
        """Fetch and analyze more comics (recent + random old ones)."""
        console.print("[dim]Fetching recent comics...[/dim]")
        try:
            recent = xkcd_manager.fetch_recent_comics(count=15)
            console.print(f"[dim]  Got {len(recent)} recent comics[/dim]")
        except Exception as e:
            console.print(f"[red]  Error fetching recent: {e}[/red]")
            recent = []

        console.print("[dim]Fetching random old comics...[/dim]")
        try:
            old = xkcd_manager.fetch_random_comics(count=15)
            console.print(f"[dim]  Got {len(old)} random old comics[/dim]")
        except Exception as e:
            console.print(f"[red]  Error fetching old: {e}[/red]")
            old = []

        # Analyze any new comics
        all_comics = recent + old
        rejected = xkcd_manager.load_rejected()
        analyzed_count = 0

        for comic in all_comics:
            comic_num = str(comic["num"])
            if comic_num in rejected:
                continue
            cache = xkcd_manager.load_cache()
            if comic_num in cache and "analysis" in cache[comic_num]:
                continue
            console.print(f"[dim]  Analyzing #{comic['num']}: {comic['title']}...[/dim]")
            try:
                xkcd_manager.analyze_comic(comic)
                analyzed_count += 1
            except Exception as e:
                console.print(f"[red]    Error: {e}[/red]")

        if analyzed_count > 0:
            console.print(f"[dim]Analyzed {analyzed_count} new comics[/dim]")

    def _handle_single_reject(self, xkcd_manager: XkcdManager, comic_num: int) -> None:
        """Quick reject a single comic with reason prompt."""
        console.print("\nRejection reason:")
        console.print("  [1] too_complex")
        console.print("  [2] adult_humor")
        console.print("  [3] too_dark")
        console.print("  [4] multi_panel")
        console.print("  [5] requires_context")
        console.print("  [6] other")

        reason_choice = console.input("\nReason (1-6): ").strip()

        reasons = ["too_complex", "adult_humor", "too_dark", "multi_panel", "requires_context", "other"]
        try:
            reason_idx = int(reason_choice) - 1
            if 0 <= reason_idx < len(reasons):
                reason = reasons[reason_idx]
                xkcd_manager.reject_comic(comic_num, reason)
                self.changes_made.append(f"xkcd #{comic_num} rejected ({reason})")
            else:
                console.print("[dim]Invalid reason, skipping rejection[/dim]")
        except ValueError:
            console.print("[dim]Invalid input, skipping rejection[/dim]")

