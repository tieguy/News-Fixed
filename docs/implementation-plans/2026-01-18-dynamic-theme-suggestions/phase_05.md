# Dynamic Theme Suggestions - Phase 5

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Add theme review step to curator TUI

**Architecture:** New `review_themes()` method displays theme health in Rich table, allows acceptance or revert to defaults. Integrates into `curate.py` flow after `display_overview()` and before `review_unused()`.

**Tech Stack:** Python, Rich (Console, Table)

**Scope:** Phase 5 of 6

**Codebase verified:** 2026-01-18

---

## Phase 5: Curator Theme Review UI

### Task 1: Add review_themes() method to StoryCurator

**Files:**
- Modify: `code/src/curator.py` (add method to StoryCurator class, around line 150)

**Step 1: Add review_themes() method**

Add this method to the `StoryCurator` class (after `display_overview()`):

```python
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
        console.print("  [R] Revert to default themes")
        console.print()

        while True:
            choice = console.input("[bold]Choose action: [/bold]").strip().lower()

            if choice == 'a':
                return 'accept'
            elif choice == 'r':
                return 'revert'
            else:
                console.print("[red]Invalid choice. Use A or R.[/red]")
```

**Step 2: Verify method exists**

Run: `uv run python -c "from src.curator import StoryCurator; print(hasattr(StoryCurator, 'review_themes'))"`
Expected: `True`

**Step 3: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add review_themes() method to StoryCurator"
```

---

### Task 2: Add revert_to_default_themes() method

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add revert method after review_themes()**

```python
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
```

**Step 2: Verify method exists**

Run: `uv run python -c "from src.curator import StoryCurator; print(hasattr(StoryCurator, 'revert_to_default_themes'))"`
Expected: `True`

**Step 3: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add revert_to_default_themes() method"
```

---

### Task 3: Integrate review_themes() into curate.py flow

**Files:**
- Modify: `code/src/curate.py` (around lines 67-70)

**Step 1: Add theme review step**

Find the section after `display_overview()` (around line 67). Insert theme review:

After:
```python
    curator.display_overview()
```

Add:
```python
    # Theme review step
    theme_choice = curator.review_themes()
    if theme_choice == 'revert':
        curator.revert_to_default_themes()
        curator.display_overview()  # Re-display with default themes
```

Before:
```python
    # Review unused stories first
    reviewing_unused = True
```

**Step 2: Verify curate.py loads**

Run: `uv run python -c "from src.curate import main; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add code/src/curate.py
git commit -m "feat: integrate theme review into curator flow"
```

---

### Task 4: Handle missing theme_metadata gracefully

**Files:**
- Modify: `code/src/curator.py` (if needed)

**Step 1: Verify display_overview() handles old JSON**

The `review_themes()` method already handles missing `theme_metadata` gracefully (returns 'accept' early). Verify that `display_overview()` continues working since it reads theme from `day_data.get('theme')`, which is still populated.

**Step 2: Run existing tests**

Run: `uv run pytest code/src/ -v`
Expected: All existing tests pass

**Step 3: Commit (if any changes were needed)**

```bash
git add code/src/curator.py
git commit -m "fix: handle missing theme_metadata gracefully in curator"
```
