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
