"""Interactive story curation for News, Fixed."""

import json
import copy
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class StoryCurator:
    """Manages interactive story curation workflow."""

    def __init__(self, json_file: Path):
        """
        Load auto-categorized JSON from ftn_to_json.py.

        Args:
            json_file: Path to JSON file with day_1/day_2/day_3/day_4 structure
        """
        self.json_file = Path(json_file)
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

    def display_overview(self) -> None:
        """Show unused stories first, then all 4 days in rich tables."""
        console.print("\n[bold cyan]Story Curation Overview[/bold cyan]\n")

        # Display unused stories FIRST
        if 'unused' in self.working_data:
            unused_data = self.working_data['unused']
            unused_stories = unused_data.get('stories', [])

            if unused_stories:
                table = Table(title="Unused Stories (Blocklisted or Uncategorized)")
                table.add_column("#", style="dim", width=3)
                table.add_column("Title", style="yellow")
                table.add_column("Length", justify="right", width=10)

                for i, story in enumerate(unused_stories, start=1):
                    title = story.get('tui_headline') or story.get('title', 'Untitled')[:60]
                    # Calculate full length: title + content
                    full_length = len(story.get('title', '')) + len(story.get('content', ''))
                    table.add_row(str(i), title, f"{full_length} chars")

                console.print(table)
                console.print()

        # Then display day tables
        for day_num in range(1, 5):
            day_key = f"day_{day_num}"
            if day_key not in self.working_data:
                continue

            day_data = self.working_data[day_key]
            theme = day_data.get('theme', 'Unknown Theme')

            # Create table for this day
            table = Table(title=f"Day {day_num}: {theme}")
            table.add_column("#", style="dim", width=3)
            table.add_column("Role", width=6)
            table.add_column("Title", style="cyan")
            table.add_column("Length", justify="right", width=10)

            # Add main story
            main = day_data.get('main_story', {})
            if main:
                title = main.get('tui_headline') or main.get('title', 'Untitled')[:60]
                # Calculate full length: title + content
                full_length = len(main.get('title', '')) + len(main.get('content', ''))
                table.add_row("1", "[bold]MAIN[/bold]", title, f"{full_length} chars")

            # Add mini articles
            minis = day_data.get('mini_articles', [])
            for i, mini in enumerate(minis, start=2):
                title = mini.get('tui_headline') or mini.get('title', 'Untitled')[:60]
                # Calculate full length: title + content
                full_length = len(mini.get('title', '')) + len(mini.get('content', ''))
                table.add_row(str(i), "mini", title, f"{full_length} chars")

            console.print(table)
            console.print()  # Blank line between tables

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

        # Get the story
        if story_index == 1:
            story = day_data.get('main_story', {})
            role = "MAIN story"
        else:
            minis = day_data.get('mini_articles', [])
            mini_idx = story_index - 2
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

        # Can't swap with itself
        if new_main_index == 1:
            console.print("[yellow]Story 1 is already the main story[/yellow]")
            return

        # Get current main and target mini
        current_main = day_data.get('main_story', {})
        minis = day_data.get('mini_articles', [])

        mini_idx = new_main_index - 2
        if mini_idx < 0 or mini_idx >= len(minis):
            console.print(f"[red]Error: Story {new_main_index} not found[/red]")
            return

        new_main = minis[mini_idx]

        # Swap
        day_data['main_story'] = new_main
        minis[mini_idx] = current_main

        # Record change
        change_msg = f"Day {day_num}: Swapped main story"
        self.changes_made.append(change_msg)

        console.print(f"[green]✓[/green] {change_msg}")
        console.print(f"  New main: {new_main.get('title', 'Untitled')[:50]}...")
        console.print(f"  Demoted: {current_main.get('title', 'Untitled')[:50]}...")

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

        console.print(f"\n[yellow]⚠️  Warning: Day {to_day} already has 5 stories (1 main + 4 minis)[/yellow]")
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

        # Get story to move
        if story_index == 1:
            story = from_data.get('main_story', {})
            was_main = True
        else:
            minis = from_data.get('mini_articles', [])
            mini_idx = story_index - 2
            if mini_idx < 0 or mini_idx >= len(minis):
                console.print(f"[red]Error: Story {story_index} not found[/red]")
                return False
            story = minis[mini_idx]
            was_main = False

        # Check if target day is full (1 main + 4 minis = 5 total)
        to_minis = to_data.get('mini_articles', [])
        to_has_main = bool(to_data.get('main_story'))
        to_count = len(to_minis) + (1 if to_has_main else 0)

        # Remove from source day first
        if was_main:
            # If moving main story, promote first mini (if exists)
            if from_data.get('mini_articles'):
                from_data['main_story'] = from_data['mini_articles'].pop(0)
            else:
                # No mini to promote - day will have no main story
                console.print(f"[yellow]⚠️  Warning: Day {from_day} will have no main story after this move[/yellow]")
                console.print(f"[dim]   (This will cause validation to fail when saving)[/dim]")
                from_data['main_story'] = {}
        else:
            from_data['mini_articles'].pop(mini_idx)

        if to_count >= 5:
            # Handle overflow (swap or replace)
            swapped_story = self._handle_overflow(to_day, story)

            if swapped_story is None:
                # User cancelled or chose replace (no story to add back)
                # Story removed from source day (already done above)
                return True

            # User chose swap - add swapped story to source day
            if was_main:
                # Source lost its main, make swapped story the main
                from_data['main_story'] = swapped_story
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
        story_title = story.get('title', 'Untitled')[:40]
        change_msg = f"Day {from_day} → Day {to_day}: {story_title}"
        self.changes_made.append(change_msg)

        console.print(f"[green]✓[/green] Moved: {story_title}")
        console.print(f"  From: Day {from_day} → To: Day {to_day} (mini)")

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

        # Get story to move
        if story_index == 1:
            story = from_data.get('main_story', {})
            was_main = True
        else:
            minis = from_data.get('mini_articles', [])
            mini_idx = story_index - 2
            if mini_idx < 0 or mini_idx >= len(minis):
                console.print(f"[red]Error: Story {story_index} not found[/red]")
                return
            story = minis[mini_idx]
            was_main = False

        # Remove from source day
        if was_main:
            if from_data.get('mini_articles'):
                from_data['main_story'] = from_data['mini_articles'].pop(0)
            else:
                console.print(f"[yellow]⚠️  Warning: Day {from_day} will have no main story after this move[/yellow]")
                console.print(f"[dim]   (This will cause validation to fail when saving)[/dim]")
                from_data['main_story'] = {}
        else:
            from_data['mini_articles'].pop(mini_idx)

        # Add to unused
        if 'unused' not in self.working_data:
            self.working_data['unused'] = {'stories': []}
        self.working_data['unused']['stories'].append(story)

        story_title = story.get('title', 'Untitled')[:40]
        change_msg = f"Day {from_day} → Unused: {story_title}"
        self.changes_made.append(change_msg)

        console.print(f"[green]✓[/green] Moved to unused: {story_title}")
        console.print(f"  Story removed from newspaper")

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

        story = unused_stories.pop(story_index - 1)

        to_key = f"day_{to_day}"
        if to_key not in self.working_data:
            console.print(f"[red]Error: Day {to_day} not found[/red]")
            return

        to_data = self.working_data[to_key]

        # Check if target day is full - warn but allow
        to_minis = to_data.get('mini_articles', [])
        to_has_main = bool(to_data.get('main_story'))
        to_count = len(to_minis) + (1 if to_has_main else 0)

        # Add to target day as mini article
        if 'mini_articles' not in to_data:
            to_data['mini_articles'] = []
        to_data['mini_articles'].append(story)

        story_title = story.get('title', 'Untitled')[:40]
        change_msg = f"Unused → Day {to_day}: {story_title}"
        self.changes_made.append(change_msg)

        console.print(f"[green]✓[/green] Moved from unused: {story_title}")
        console.print(f"  Added to Day {to_day} (mini)")

        # Warn if day now exceeds capacity
        new_count = to_count + 1
        if new_count > 5:
            console.print(f"[yellow]⚠️  Day {to_day} now has {new_count} stories (over capacity)[/yellow]")
            console.print(f"[dim]   You'll need to remove {new_count - 5} during day review[/dim]")

    def review_unused(self) -> str:
        """
        Interactive review for unused stories.

        Returns:
            User's choice: 'accept', 'move', 'view'
        """
        if 'unused' not in self.working_data:
            return 'accept'

        unused_stories = self.working_data['unused'].get('stories', [])
        if not unused_stories:
            return 'accept'

        max_index = len(unused_stories)

        console.print(f"\n[bold]Review Unused Stories ({max_index} total)[/bold]")
        console.print("  [A] Accept as-is (keep all unused)")
        console.print("  [M] Move story to a day")
        console.print("  [V] View story details")
        console.print(f"  [1-{max_index}] Quick move story # to a day")

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
        console.print("  [1] Health & Education")
        console.print("  [2] Environment & Conservation")
        console.print("  [3] Technology & Energy")
        console.print("  [4] Society & Youth Movements")

        target = console.input("\nChoice (1-4, or 'back'): ").strip()

        if target == 'back':
            return

        try:
            to_day = int(target)
            if to_day < 1 or to_day > 4:
                console.print("[red]Invalid day number[/red]")
                return
            self.move_from_unused(story_index, to_day)
            # Refresh display after move from unused
            console.print("\n" + "=" * 60)
            self.display_overview()
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
        minis = day_data.get('mini_articles', [])
        total_stories = 1 + len(minis)  # 1 main + N minis
        max_index = total_stories

        # Auto-prompt if day has 6+ stories
        if total_stories >= 6:
            console.print(f"\n[yellow]⚠️  Day {day_num} has {total_stories} stories (capacity exceeded!)[/yellow]")
            console.print(f"[dim]   Maximum is 1 main + 4 minis = 5 total stories[/dim]")
            console.print(f"[dim]   You need to remove at least {total_stories - 5} stories[/dim]\n")

        console.print(f"\n[bold]Review Day {day_num}: {theme}[/bold]")
        console.print("  [A] Accept as-is")
        console.print("  [M] Move stories to different day")
        console.print("  [S] Swap main/mini assignments")
        console.print("  [V] View story details")
        console.print(f"  [1-{max_index}] Quick move story # to another day")
        if day_num > 1:
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
        elif choice == 'v':
            return 'view'
        elif choice == 'b' and day_num > 1:
            return 'back'
        else:
            console.print("[yellow]Invalid choice, treating as 'accept'[/yellow]")
            return 'accept'

    def _handle_view_action(self, day_num: int) -> None:
        """Handle view story action."""
        day_data = self.working_data[f"day_{day_num}"]
        max_index = 1 + len(day_data.get('mini_articles', []))

        story_num = console.input(f"Which story? (1-{max_index}, or 'back'): ").strip()

        if story_num == 'back':
            return

        try:
            self.view_story(day_num, int(story_num))
            console.input("\nPress Enter to continue...")
        except ValueError:
            console.print("[red]Invalid story number[/red]")

    def _handle_swap_action(self, day_num: int) -> None:
        """Handle swap main story action."""
        day_data = self.working_data[f"day_{day_num}"]
        minis = day_data.get('mini_articles', [])

        if not minis:
            console.print("[yellow]No mini articles to swap with[/yellow]")
            return

        console.print("\nPick new main story:")
        console.print(f"  [1] {day_data.get('main_story', {}).get('title', 'Untitled')[:50]} (currently MAIN)")

        for i, mini in enumerate(minis, start=2):
            title = mini.get('title', 'Untitled')[:50]
            length = len(mini.get('content', ''))
            console.print(f"  [{i}] {title} ({length} chars)")

        choice = console.input(f"\nChoice (2-{len(minis)+1}, or 'back'): ").strip()

        if choice == 'back':
            return

        try:
            self.swap_main_story(day_num, int(choice))
            # Refresh display after swap
            console.print("\n" + "=" * 60)
            self.display_overview()
        except ValueError:
            console.print("[red]Invalid choice[/red]")

    def _handle_move_action(self, day_num: int, preselected_story: int = None) -> None:
        """Handle move story action.

        Args:
            day_num: Day number (1-4)
            preselected_story: If provided, skip asking which story to move
        """
        day_data = self.working_data[f"day_{day_num}"]
        max_index = 1 + len(day_data.get('mini_articles', []))

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
        console.print(f"  [1] Health & Education (current)" if day_num == 1 else "  [1] Health & Education")
        console.print(f"  [2] Environment & Conservation (current)" if day_num == 2 else "  [2] Environment & Conservation")
        console.print(f"  [3] Technology & Energy (current)" if day_num == 3 else "  [3] Technology & Energy")
        console.print(f"  [4] Society & Youth Movements (current)" if day_num == 4 else "  [4] Society & Youth Movements")
        console.print(f"  [U] Unused (delete from newspaper)")

        target = console.input("\nChoice (1-4, U, or 'back'): ").strip().lower()

        if target == 'back':
            return

        if target == 'u':
            self.move_to_unused(day_num, story_index)
            # Refresh display after move to unused
            console.print("\n" + "=" * 60)
            self.display_overview()
            return

        try:
            to_day = int(target)
            if to_day == day_num:
                console.print("[yellow]Story is already in this day[/yellow]")
                return
            self.move_story(day_num, story_index, to_day)
            # Refresh display after move
            console.print("\n" + "=" * 60)
            self.display_overview()
        except ValueError:
            console.print("[red]Invalid choice[/red]")

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

    def save_curated(self, output_file: Path) -> None:
        """
        Save working_data to new JSON file (excluding unused stories).

        Args:
            output_file: Path to save curated JSON
        """
        # Create output data without unused category
        output_data = {k: v for k, v in self.working_data.items() if k != 'unused'}

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        console.print(f"\n[green]✓[/green] Saved to: {output_file}")

        # Report unused stories count if any
        if 'unused' in self.working_data:
            unused_count = len(self.working_data['unused'].get('stories', []))
            if unused_count > 0:
                console.print(f"[dim]  ({unused_count} unused stories excluded from newspaper)[/dim]")
