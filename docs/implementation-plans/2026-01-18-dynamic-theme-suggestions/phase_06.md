# Dynamic Theme Suggestions - Phase 6

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Allow curator to override themes and re-group stories

**Architecture:** Add `edit_themes()` for manual theme editing and `regroup_with_themes()` to call grouping API with new themes. Extend `review_themes()` menu with edit option. Handle regrouping as opt-in to avoid unnecessary API calls.

**Tech Stack:** Python, Anthropic Claude API, Rich

**Scope:** Phase 6 of 6 (final phase)

**Codebase verified:** 2026-01-18

---

## Phase 6: Theme Override Flow

### Task 1: Add edit_themes() method

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add edit_themes() method to StoryCurator**

```python
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
```

**Step 2: Verify method exists**

Run: `uv run python -c "from src.curator import StoryCurator; print(hasattr(StoryCurator, 'edit_themes'))"`
Expected: `True`

**Step 3: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add edit_themes() method for manual theme editing"
```

---

### Task 2: Add regroup_with_themes() method

**Files:**
- Modify: `code/src/curator.py`

**Step 1: Add regroup method**

```python
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
            # _build_four_days_from_grouping expects a list indexed by story ID
            # Sort all_stories by ID to create proper list mapping
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
```

**Step 2: Verify method exists**

Run: `uv run python -c "from src.curator import StoryCurator; print(hasattr(StoryCurator, 'regroup_with_themes'))"`
Expected: `True`

**Step 3: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add regroup_with_themes() for re-grouping with edited themes"
```

---

### Task 3: Extend review_themes() with edit option

**Files:**
- Modify: `code/src/curator.py` (update review_themes() from Phase 5)

**Step 1: Add edit option to menu**

Update the action menu in `review_themes()`:

Change:
```python
        # Show action menu
        console.print("\n[bold]Actions:[/bold]")
        console.print("  [A] Accept themes and continue")
        console.print("  [R] Revert to default themes")
```

To:
```python
        # Show action menu
        console.print("\n[bold]Actions:[/bold]")
        console.print("  [A] Accept themes and continue")
        console.print("  [E] Edit theme names")
        console.print("  [R] Revert to default themes")
```

**Step 2: Handle edit choice**

Update the input loop:

```python
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
```

**Step 3: Commit**

```bash
git add code/src/curator.py
git commit -m "feat: add edit option to theme review menu"
```

---

### Task 4: Update curate.py to handle edit flow

**Files:**
- Modify: `code/src/curate.py`

**Step 1: Add Console import if needed**

At top of curate.py, ensure:
```python
from rich.console import Console
```

**Step 2: Handle edit choice in theme review**

Update the theme review section (added in Phase 5) to handle the full flow:

```python
    # Theme review step
    reviewing_themes = True
    while reviewing_themes:
        theme_choice = curator.review_themes()

        if theme_choice == 'accept':
            reviewing_themes = False
        elif theme_choice == 'revert':
            curator.revert_to_default_themes()
            curator.display_overview()
            reviewing_themes = False
        elif theme_choice == 'edit':
            new_themes = curator.edit_themes()
            if new_themes:
                # Ask if they want to regroup
                console = Console()
                console.print("\n[bold]Regroup stories with new themes?[/bold]")
                console.print("This will call Claude API to reassign stories.")
                console.print("  [Y] Yes, regroup stories")
                console.print("  [N] No, just update theme names")

                regroup_choice = console.input("[bold]Choice: [/bold]").strip().lower()
                if regroup_choice == 'y':
                    if curator.regroup_with_themes(new_themes):
                        curator.display_overview()
                else:
                    # Just update theme names without regrouping
                    curator.working_data["theme_metadata"] = {
                        day: {**new_themes[day], "status": "unknown", "story_count": 0, "high_strength_count": 0}
                        for day in new_themes
                    }
                    for day_num in range(1, 5):
                        day_key = f"day_{day_num}"
                        if day_key in curator.working_data:
                            curator.working_data[day_key]["theme"] = new_themes[day_num]["name"]
                    console.print("[green]✓ Theme names updated[/green]")
                    curator.display_overview()
```

**Step 3: Verify flow loads**

Run: `uv run python -c "from src.curate import main; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add code/src/curate.py
git commit -m "feat: complete theme override flow with edit and regroup options"
```
