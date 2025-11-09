# Story Curation CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interactive CLI tool that loads auto-categorized FTN stories, displays them in rich tables, and allows manual curation (moving stories between days, swapping main/mini assignments) before saving to a new JSON file.

**Architecture:** Wraps existing `ftn_to_json.py` output. Uses `rich` library for table display and prompts. Follows TDD with manual integration testing (no automated tests initially since this is primarily UI). Core logic in `src/curator.py` module, CLI entry point in `code/curate.py`.

**Tech Stack:** Python 3.x, rich library, standard library (json, copy, pathlib)

---

## Task 1: Add rich dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add rich to requirements**

Add this line to `requirements.txt`:
```
rich>=13.0.0
```

**Step 2: Install rich in worktree venv**

Run: `source venv/bin/activate && pip install rich`
Expected: "Successfully installed rich-X.X.X"

**Step 3: Verify import works**

Run: `python -c "from rich.console import Console; Console().print('[green]✓[/green] Rich imported successfully')"`
Expected: Green checkmark with success message

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add rich dependency for CLI tables

Needed for story curation CLI UI.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Create StoryCurator class skeleton

**Files:**
- Create: `code/src/curator.py`

**Step 1: Create curator.py with basic structure**

Create `code/src/curator.py`:

```python
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
        """Show all 4 days in rich tables."""
        console.print("\n[bold cyan]Story Curation Overview[/bold cyan]\n")

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
                title = main.get('title', 'Untitled')[:60]
                length = len(main.get('content', ''))
                table.add_row("1", "[bold]MAIN[/bold]", title, f"{length} chars")

            # Add mini articles
            minis = day_data.get('mini_articles', [])
            for i, mini in enumerate(minis, start=2):
                title = mini.get('title', 'Untitled')[:60]
                length = len(mini.get('content', ''))
                table.add_row(str(i), "mini", title, f"{length} chars")

            console.print(table)
            console.print()  # Blank line between tables

    def save_curated(self, output_file: Path) -> None:
        """
        Save working_data to new JSON file.

        Args:
            output_file: Path to save curated JSON
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.working_data, f, indent=2, ensure_ascii=False)

        console.print(f"\n[green]✓[/green] Saved to: {output_file}")
```

**Step 2: Test import**

Run: `cd /home/louie/Projects/DailyNews/.worktrees/story-curation-cli && python -c "from src.curator import StoryCurator; print('✓ Import successful')"`
Expected: "✓ Import successful"

**Step 3: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add StoryCurator class skeleton

Basic structure for story curation:
- Load/save JSON
- Display overview tables
- Track changes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Create curate.py CLI entry point

**Files:**
- Create: `code/curate.py`

**Step 1: Create curate.py**

Create `code/curate.py`:

```python
#!/usr/bin/env python3
"""
Interactive CLI for curating FTN stories before newspaper generation.

Usage:
    python code/curate.py data/ftn/ftn-316.json
    python code/curate.py data/ftn/ftn-316.json --output data/ftn/custom-name.json
"""

import sys
from pathlib import Path
import click
from src.curator import StoryCurator


@click.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output filename (default: {input}-curated.json)')
@click.option('--dry-run', is_flag=True,
              help='Preview without saving')
def main(json_file, output, dry_run):
    """
    Interactively curate FTN stories.

    Loads auto-categorized JSON from ftn_to_json.py, displays stories
    in tables, and allows manual curation before saving.
    """
    click.echo("📰 News, Fixed - Story Curation Tool\n")

    # Determine output filename
    if output is None:
        input_path = Path(json_file)
        output = input_path.parent / f"{input_path.stem}-curated.json"
    else:
        output = Path(output)

    # Load and display
    try:
        curator = StoryCurator(Path(json_file))
        curator.display_overview()

        if dry_run:
            click.echo("\n[DRY RUN] Not saving changes.")
            return

        # For now, just save (no interactive changes yet)
        click.echo(f"\n💾 Saving to: {output}")
        curator.save_curated(output)

        click.echo(f"\n✨ Next step:")
        click.echo(f"   python code/main.py --input {output} --all")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
```

**Step 2: Make executable**

Run: `chmod +x code/curate.py`
Expected: No output (command succeeds)

**Step 3: Test with sample JSON**

Run: `cd /home/louie/Projects/DailyNews/.worktrees/story-curation-cli && python code/curate.py data/ftn/ftn-315.json --dry-run`
Expected: Displays overview tables, prints "DRY RUN" message

**Step 4: Commit**

```bash
git add code/curate.py
git commit -m "feat: add curate.py CLI entry point

Basic CLI that loads JSON, displays overview, and saves.
Interactive curation features to be added in next tasks.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Add view_story method

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add view_story method**

Add this method to `StoryCurator` class in `code/src/curator.py`:

```python
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
```

**Step 2: Test view_story manually**

Create test script `test_view.py`:
```python
from pathlib import Path
from src.curator import StoryCurator

curator = StoryCurator(Path('data/ftn/ftn-315.json'))
curator.view_story(1, 1)  # View Day 1 main story
curator.view_story(1, 2)  # View Day 1 first mini
```

Run: `cd /home/louie/Projects/DailyNews/.worktrees/story-curation-cli && python test_view.py`
Expected: Displays story details in panels

**Step 3: Remove test script**

Run: `rm test_view.py`

**Step 4: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add view_story method

Displays full story details in panel:
- Title, length, source URL, role
- First 500 chars of content

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Add swap_main_story method

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add swap_main_story method**

Add this method to `StoryCurator` class in `code/src/curator.py`:

```python
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
```

**Step 2: Test swap_main_story manually**

Create test script `test_swap.py`:
```python
from pathlib import Path
from src.curator import StoryCurator

curator = StoryCurator(Path('data/ftn/ftn-315.json'))
print("Before swap:")
curator.display_overview()

curator.swap_main_story(1, 2)  # Swap Day 1 main with first mini

print("\nAfter swap:")
curator.display_overview()
```

Run: `cd /home/louie/Projects/DailyNews/.worktrees/story-curation-cli && python test_swap.py`
Expected: Displays tables before/after swap, main story changes

**Step 3: Remove test script**

Run: `rm test_swap.py`

**Step 4: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add swap_main_story method

Swaps main story with mini article:
- Validates indices
- Updates working_data
- Tracks change in changes_made

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Add move_story method (simple case)

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add move_story method (no overflow handling yet)**

Add this method to `StoryCurator` class in `code/src/curator.py`:

```python
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

        if to_count >= 5:
            console.print(f"[yellow]⚠️  Warning: Day {to_day} already has 5 stories[/yellow]")
            console.print("   Overflow handling not yet implemented - move cancelled")
            return False

        # Remove from source day
        if was_main:
            # If moving main story, promote first mini (if exists)
            if from_data.get('mini_articles'):
                from_data['main_story'] = from_data['mini_articles'].pop(0)
            else:
                from_data['main_story'] = {}
        else:
            from_data['mini_articles'].pop(mini_idx)

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
```

**Step 2: Test move_story manually**

Create test script `test_move.py`:
```python
from pathlib import Path
from src.curator import StoryCurator

curator = StoryCurator(Path('data/ftn/ftn-315.json'))
print("Before move:")
curator.display_overview()

curator.move_story(from_day=1, story_index=2, to_day=2)

print("\nAfter move:")
curator.display_overview()
```

Run: `cd /home/louie/Projects/DailyNews/.worktrees/story-curation-cli && python test_move.py`
Expected: Story moves from Day 1 to Day 2 (as mini article)

**Step 3: Remove test script**

Run: `rm test_move.py`

**Step 4: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add move_story method (simple case)

Moves stories between days:
- Removes from source (promotes mini to main if needed)
- Adds to target as mini article
- Warns if target is full (overflow not yet handled)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Add interactive review_day method

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add review_day method**

Add this method to `StoryCurator` class in `code/src/curator.py`:

```python
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

        console.print(f"\n[bold]Review Day {day_num}: {theme}[/bold]")
        console.print("  [A] Accept as-is")
        console.print("  [M] Move stories to different day")
        console.print("  [S] Swap main/mini assignments")
        console.print("  [V] View story details")
        if day_num > 1:
            console.print("  [B] Back to previous day")

        choice = console.input("\n[cyan]Choice:[/cyan] ").strip().lower()

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
```

**Step 2: Add interactive handlers**

Add these helper methods to `StoryCurator` class:

```python
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
        except ValueError:
            console.print("[red]Invalid choice[/red]")

    def _handle_move_action(self, day_num: int) -> None:
        """Handle move story action."""
        day_data = self.working_data[f"day_{day_num}"]
        max_index = 1 + len(day_data.get('mini_articles', []))

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

        target = console.input("\nChoice (1-4, or 'back'): ").strip()

        if target == 'back':
            return

        try:
            to_day = int(target)
            if to_day == day_num:
                console.print("[yellow]Story is already in this day[/yellow]")
                return
            self.move_story(day_num, story_index, to_day)
        except ValueError:
            console.print("[red]Invalid choice[/red]")
```

**Step 3: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add interactive review_day method

Interactive day review with actions:
- [A]ccept as-is
- [M]ove stories
- [S]wap main/mini
- [V]iew details
- [B]ack to previous

Includes helper methods for each action.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Wire up interactive workflow in curate.py

**Files:**
- Modify: `code/curate.py`

**Step 1: Replace main() in curate.py**

Replace the main() function in `code/curate.py` with this:

```python
@click.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output filename (default: {input}-curated.json)')
@click.option('--dry-run', is_flag=True,
              help='Preview without saving')
def main(json_file, output, dry_run):
    """
    Interactively curate FTN stories.

    Loads auto-categorized JSON from ftn_to_json.py, displays stories
    in tables, and allows manual curation before saving.
    """
    click.echo("📰 News, Fixed - Story Curation Tool\n")

    # Determine output filename
    if output is None:
        input_path = Path(json_file)
        output = input_path.parent / f"{input_path.stem}-curated.json"
    else:
        output = Path(output)

    # Load and display
    try:
        curator = StoryCurator(Path(json_file))
        curator.display_overview()

        # Interactive review
        current_day = 1
        while current_day <= 4:
            choice = curator.review_day(current_day)

            if choice == 'accept':
                current_day += 1
            elif choice == 'move':
                curator._handle_move_action(current_day)
            elif choice == 'swap':
                curator._handle_swap_action(current_day)
            elif choice == 'view':
                curator._handle_view_action(current_day)
            elif choice == 'back':
                current_day = max(1, current_day - 1)

        # Show final summary
        click.echo("\n" + "=" * 60)
        click.echo("✅ Curation complete!\n")

        if curator.changes_made:
            click.echo("Summary of changes:")
            for change in curator.changes_made:
                click.echo(f"  - {change}")
        else:
            click.echo("No changes made.")

        if dry_run:
            click.echo("\n[DRY RUN] Not saving changes.")
            return

        # Save
        click.echo(f"\n💾 Saving to: {output}")
        curator.save_curated(output)

        click.echo(f"\n✨ Next step:")
        click.echo(f"   python code/main.py --input {output} --all")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

**Step 2: Test interactive workflow**

Run: `cd /home/louie/Projects/DailyNews/.worktrees/story-curation-cli && python code/curate.py data/ftn/ftn-315.json --dry-run`

Interact with prompts:
- Day 1: Choose [V]iew, view story 1, then [A]ccept
- Day 2: Choose [A]ccept
- Day 3: Choose [A]ccept
- Day 4: Choose [A]ccept

Expected: Completes full workflow, shows "DRY RUN" message

**Step 3: Commit**

```bash
git add code/curate.py
git commit -m "feat: wire up interactive workflow

Full interactive review loop:
- Review each day 1-4
- Handle all action types
- Show final summary
- Save curated JSON

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Add overflow handling (swap/replace)

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add _handle_overflow method**

Add this method to `StoryCurator` class in `code/src/curator.py`:

```python
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
```

**Step 2: Update move_story to use overflow handling**

Replace the overflow check in `move_story` method:

Change this:
```python
        if to_count >= 5:
            console.print(f"[yellow]⚠️  Warning: Day {to_day} already has 5 stories[/yellow]")
            console.print("   Overflow handling not yet implemented - move cancelled")
            return False
```

To this:
```python
        if to_count >= 5:
            # Handle overflow (swap or replace)
            swapped_story = self._handle_overflow(to_day, story)

            if swapped_story is None:
                # User cancelled or chose replace (no story to add back)
                # Remove from source day (already done above)
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
```

**Step 3: Test overflow handling**

Run: `cd /home/louie/Projects/DailyNews/.worktrees/story-curation-cli && python code/curate.py data/ftn/ftn-315.json --dry-run`

Manually test:
1. Move multiple stories to same day until it has 5
2. Try to move one more → should trigger overflow prompt
3. Test swap option
4. Test replace option
5. Test cancel option

**Step 4: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add overflow handling (swap/replace)

Handle moving stories to full days:
- Prompt for swap, replace, or cancel
- Swap: bidirectional story exchange
- Replace: remove target story from curation
- Cancel: abort move

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Add validation before saving

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add validate_data method**

Add this method to `StoryCurator` class in `code/src/curator.py`:

```python
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
```

**Step 2: Call validation in curate.py before saving**

In `code/curate.py`, add validation check before saving:

Add this after the summary, before saving:
```python
        # Validate before saving
        if not curator.validate_data():
            click.echo("\n[red]❌ Validation failed - cannot save[/red]")
            click.echo("   Fix errors and try again")
            sys.exit(1)
```

**Step 3: Test validation**

Create test with invalid data:
1. Use curate.py to move all stories out of Day 1
2. Try to complete curation
3. Should fail validation with "Day 1 has no main story"

**Step 4: Commit**

```bash
git add code/src/curator.py code/curate.py
git commit -m "feat: add validation before saving

Validates curated data:
- Each day must have main story
- Warns about empty days
- Warns about missing minis
- Warns about >4 minis
- Blocks save if critical errors

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: Add help text and usage examples

**Files:**
- Modify: `code/curate.py`
- Create: `docs/CURATION.md`

**Step 1: Enhance CLI help text**

Update docstring in `code/curate.py` main() function:

```python
def main(json_file, output, dry_run):
    """
    Interactively curate FTN stories before newspaper generation.

    Loads auto-categorized JSON from ftn_to_json.py, displays stories in
    rich tables, and provides an interactive review workflow:

    \b
    1. Review Day 1-4 stories with auto-categorization
    2. Move stories between days to fix miscategorizations
    3. Swap main/mini assignments when length-based choice is wrong
    4. View full story details before making decisions
    5. Save curated results to new JSON file

    \b
    Examples:
        # Basic curation
        python code/curate.py data/ftn/ftn-316.json

        # Custom output filename
        python code/curate.py data/ftn/ftn-316.json -o data/ftn/monday.json

        # Preview without saving
        python code/curate.py data/ftn/ftn-316.json --dry-run

    \b
    Next steps after curation:
        python code/main.py --input data/ftn/ftn-316-curated.json --all
    """
```

**Step 2: Create CURATION.md documentation**

Create `docs/CURATION.md`:

```markdown
# Story Curation Guide

## Overview

The story curation CLI (`code/curate.py`) provides an interactive workflow for manually reviewing and organizing FTN stories before newspaper generation.

## Workflow

### 1. Auto-Categorization

First, run `ftn_to_json.py` to parse FTN HTML and auto-categorize stories:

```bash
python code/src/ftn_to_json.py data/ftn/FTN-316.html
```

This creates `data/ftn/ftn-316.json` with stories assigned to days based on keyword matching.

### 2. Interactive Curation

Run the curation tool to review and fix categorization:

```bash
python code/curate.py data/ftn/ftn-316.json
```

You'll see an overview table showing all 4 days with their stories, then review each day interactively.

### 3. Review Actions

For each day, you can:

- **[A]ccept as-is** - Move to next day
- **[M]ove stories** - Reassign stories to different days
- **[S]wap main/mini** - Change which story is the main feature
- **[V]iew details** - Read full story content before deciding
- **[B]ack** - Return to previous day to revise

### 4. Moving Stories

When moving a story:

1. Select story number (1 = main, 2+ = minis)
2. Choose target day (1-4)
3. If target day is full (5 stories), choose:
   - **Swap** - Exchange with a story from target day
   - **Replace** - Remove a story from target day
   - **Cancel** - Abort the move

### 5. Save and Generate

After reviewing all 4 days:

1. Review summary of changes
2. Validate data (checks for missing main stories, etc.)
3. Save to `{original}-curated.json`
4. Run main.py to generate PDFs

## Tips

- **Length matters**: Main stories should be 400-500 words, minis 100-150 words
- **Theme alignment**: Day 1 = Health/Education, Day 2 = Environment, Day 3 = Technology, Day 4 = Society
- **View before moving**: Use [V]iew to check story content when unsure about categorization
- **Dry run first**: Use `--dry-run` to preview without saving changes

## Common Scenarios

### Story in wrong day

Day 3 has a health story that belongs in Day 1:

1. Review Day 3
2. Choose [M]ove stories
3. Select the misplaced story
4. Choose Day 1 as target

### Wrong main story

Day 2's longest story is boring, but mini #2 is more compelling:

1. Review Day 2
2. Choose [S]wap main/mini
3. Select mini #2 as new main

### Too many stories in one day

Day 1 has 7 stories, Day 2 has only 3:

1. Review Day 1
2. Move 2-3 stories to Day 2
3. Keep best 5 in Day 1

## Output Format

Curated JSON has same structure as input:

```json
{
  "day_1": {
    "theme": "Health & Education",
    "main_story": { "title": "...", "content": "...", "source_url": "..." },
    "mini_articles": [
      { "title": "...", "content": "...", "source_url": "..." },
      ...
    ],
    "statistics": [],
    "tomorrow_teaser": ""
  },
  ...
}
```

Compatible with `main.py --input`.

## Troubleshooting

**"Day X has no main story"**
- You moved all stories out of a day
- Solution: Move at least one story back, or delete the empty day from JSON manually

**"Overflow handling" message**
- Target day already has 5 stories (max)
- Solution: Swap/replace an existing story, or move to a different day

**Changes not saving**
- Using `--dry-run` flag
- Solution: Remove flag to save changes
```

**Step 3: Commit**

```bash
git add code/curate.py docs/CURATION.md
git commit -m "docs: add help text and curation guide

Enhanced CLI help with examples.
Created comprehensive CURATION.md guide:
- Workflow overview
- Review actions
- Common scenarios
- Troubleshooting

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 12: Manual integration testing

**Files:**
- None (testing only)

**Step 1: Test full workflow with real data**

Run complete workflow:

```bash
cd /home/louie/Projects/DailyNews/.worktrees/story-curation-cli

# 1. Ensure sample data exists
ls -la data/ftn/ftn-315.json

# 2. Run curation with real interactions
python code/curate.py data/ftn/ftn-315.json

# Interact with all features:
# Day 1: View story 1, Accept
# Day 2: Move story 2 to Day 3, Accept
# Day 3: Swap main story with mini 2, Accept
# Day 4: Accept
# Complete and save
```

**Step 2: Verify output**

```bash
# Check output file was created
ls -la data/ftn/ftn-315-curated.json

# Verify JSON structure
python -c "import json; data = json.load(open('data/ftn/ftn-315-curated.json')); print(f'Days: {list(data.keys())}'); print(f'Day 1 main: {data[\"day_1\"][\"main_story\"][\"title\"]}')"
```

Expected: Valid JSON with day_1 through day_4 keys

**Step 3: Test edge cases**

Test overflow handling:
1. Run curate.py again
2. Move 5 stories into one day
3. Try to move a 6th → should trigger overflow prompt
4. Test swap option
5. Test replace option
6. Test cancel option

Test validation:
1. Move all stories out of Day 1
2. Try to save → should fail validation
3. Move one story back to Day 1
4. Save should succeed

**Step 4: Test with main.py**

```bash
# Generate PDFs from curated JSON
python code/main.py --input data/ftn/ftn-315-curated.json --day 1 --no-rewrite

# Check PDF was created
ls -la output/news_fixed_*.pdf
```

Expected: PDF generated successfully from curated data

**Step 5: Document test results**

Create `TESTING.md` with results:

```markdown
# Testing Results - Story Curation CLI

## Test Date: 2025-11-09

### Functional Tests

✅ Load JSON - Loads ftn-315.json successfully
✅ Display overview - Shows all 4 days in tables
✅ View story - Displays full content in panel
✅ Swap main story - Demotes main to mini, promotes mini to main
✅ Move story (simple) - Moves between days successfully
✅ Move story (overflow/swap) - Swaps stories when target full
✅ Move story (overflow/replace) - Removes target story
✅ Move story (overflow/cancel) - Aborts move
✅ Validation (empty day) - Warns about empty days
✅ Validation (no main) - Blocks save when day missing main
✅ Save curated JSON - Creates {input}-curated.json
✅ Integration with main.py - Generated PDF from curated JSON

### Edge Cases

✅ Back navigation - Returns to previous day
✅ Invalid choices - Handles gracefully with warnings
✅ Keyboard interrupt - Exits cleanly with message
✅ Missing JSON file - Clear error message
✅ Dry run mode - Previews without saving

### Known Limitations

- No automated tests (manual testing only)
- No undo within a session (restart to undo)
- No autosave (must complete full workflow)
- Cannot edit story content inline (only move/swap)

## Next Steps

- Consider adding automated integration tests
- Add undo/redo functionality
- Add session save/resume capability
```

**Step 6: Commit test documentation**

```bash
git add TESTING.md
git commit -m "test: document manual integration testing

Completed full workflow testing:
- All features tested and working
- Edge cases handled correctly
- Integration with main.py verified
- Documented known limitations

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 13: Final cleanup and merge preparation

**Files:**
- Update: `README.md` (add curation step to workflow)
- Update: `.beads/issues.jsonl` (close bead 20)

**Step 1: Update README workflow section**

Add curation step to workflow in README.md (find the "Running the Application" section):

```markdown
## Running the Application

**Workflow:**

1. **Fetch FTN content**
   ```bash
   python code/src/fetch_ftn_clean.py
   # Creates data/ftn/FTN-XXX.html
   ```

2. **Parse and auto-categorize**
   ```bash
   python code/src/ftn_to_json.py data/ftn/FTN-XXX.html
   # Creates data/ftn/ftn-XXX.json
   ```

3. **Curate stories (NEW)**
   ```bash
   python code/curate.py data/ftn/ftn-XXX.json
   # Creates data/ftn/ftn-XXX-curated.json
   # Interactive review to fix categorization
   ```

4. **Generate newspapers**
   ```bash
   # Generate all 4 days
   python code/main.py --input data/ftn/ftn-XXX-curated.json --all

   # Or single day
   python code/main.py --input data/ftn/ftn-XXX-curated.json --day 1
   ```

See `docs/CURATION.md` for detailed curation guide.
```

**Step 2: Close bead 20**

```bash
bd close DailyNews-20 --reason "Completed - story curation CLI implemented" --json
```

Expected: Bead marked as closed

**Step 3: Create comprehensive commit**

```bash
git add README.md
git commit -m "docs: update README with curation workflow

Added step 3 (curation) to workflow documentation.
Points to docs/CURATION.md for details.

Closes DailyNews-20

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Step 4: Verify branch is ready for review**

```bash
# Check all commits
git log --oneline main..feature/story-curation-cli

# Check files changed
git diff main --stat

# Verify tests (manual verification since no automated tests)
python code/curate.py data/ftn/ftn-315.json --dry-run
```

Expected: Clean history, all features working

---

## Summary

This plan implements the story curation CLI in 13 tasks:

1. ✅ Add rich dependency
2. ✅ Create StoryCurator class skeleton
3. ✅ Create curate.py CLI entry point
4. ✅ Add view_story method
5. ✅ Add swap_main_story method
6. ✅ Add move_story method (simple case)
7. ✅ Add interactive review_day method
8. ✅ Wire up interactive workflow
9. ✅ Add overflow handling (swap/replace)
10. ✅ Add validation before saving
11. ✅ Add help text and documentation
12. ✅ Manual integration testing
13. ✅ Final cleanup and merge preparation

**Total estimated time:** 2-3 hours for experienced developer

**Key files created:**
- `code/curate.py` - CLI entry point
- `code/src/curator.py` - Core curation logic
- `docs/CURATION.md` - User guide
- `docs/plans/2025-11-09-story-curation-cli.md` - This plan

**Key files modified:**
- `requirements.txt` - Added rich
- `README.md` - Updated workflow

**Testing approach:**
- Manual integration testing (no automated tests initially)
- Test with real ftn-315.json data
- Verify all features work end-to-end
- Verify integration with main.py

**Future enhancements (out of scope):**
- Automated integration tests
- Undo/redo functionality
- Session save/resume
- Inline content editing
- Statistics/teaser review (separate feature)
