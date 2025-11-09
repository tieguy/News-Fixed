#!/usr/bin/env python3
"""
Interactive CLI for curating FTN stories before newspaper generation.

Usage:
    python code/curate.py data/processed/ftn-316.json
    python code/curate.py data/processed/ftn-316.json --output data/processed/custom-name.json
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
        python code/curate.py data/processed/ftn-316.json

        # Custom output filename
        python code/curate.py data/processed/ftn-316.json -o data/processed/monday.json

        # Preview without saving
        python code/curate.py data/processed/ftn-316.json --dry-run

    \b
    Next steps after curation:
        python code/main.py --input data/processed/ftn-316-curated.json --all
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

        # Review unused stories
        reviewing_unused = True
        while reviewing_unused:
            choice = curator.review_unused()

            if choice == 'accept':
                reviewing_unused = False
            elif choice == 'move':
                curator._handle_unused_move_action()
            elif choice == 'view':
                curator._handle_unused_view_action()

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

        # Validate before saving
        if not curator.validate_data():
            click.echo("\n❌ Validation failed - cannot save")
            click.echo("   Fix errors and try again")
            sys.exit(1)

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


if __name__ == '__main__':
    main()
