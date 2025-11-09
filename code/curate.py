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
