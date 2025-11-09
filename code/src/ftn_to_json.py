#!/usr/bin/env python3
"""Convert fetched FTN HTML into a 4-day JSON file for News, Fixed."""

import sys
import json
from pathlib import Path

# Add parent directory to path so we can import src modules
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import FTNParser

# Constants
FTN_BASE_URL = "https://fixthenews.com"


def create_json_from_ftn(html_file: str, output_file: str = None):
    """
    Parse FTN HTML and create a 4-day JSON file.

    Args:
        html_file: Path to FTN HTML file
        output_file: Output JSON file path (defaults to ftn-{issue}.json)

    Returns:
        Path to created JSON file
    """
    print(f"📖 Parsing {html_file}...")

    # Parse the HTML
    parser = FTNParser(html_file)
    stories = parser.extract_stories()

    print(f"   Found {len(stories)} stories")

    # Categorize stories
    categories = parser.categorize_stories(stories)

    print("\n📊 Stories by category:")
    for category, cat_stories in categories.items():
        print(f"   {category}: {len(cat_stories)} stories")

    # Map categories to days
    day_mapping = {
        1: 'health_education',
        2: 'environment',
        3: 'technology_energy',
        4: 'society'
    }

    # Build 4-day structure + unused
    four_days = {}

    # Add unused stories
    unused_stories = categories.get('unused', [])
    if unused_stories:
        four_days['unused'] = {
            "stories": [
                {
                    "title": story.title,
                    "content": story.content,
                    "source_url": story.source_url or FTN_BASE_URL
                }
                for story in unused_stories
            ]
        }

    for day_num, category_key in day_mapping.items():
        category_stories = categories.get(category_key, [])

        if not category_stories:
            print(f"\n⚠️  Warning: No stories found for day {day_num} ({category_key})")
            continue

        # Select stories for front page and back page
        # Sort by content length to get the most substantial stories
        sorted_stories = sorted(category_stories, key=lambda s: len(s.content), reverse=True)

        # Front page: 1 lead story ONLY (to fit on 2 pages)
        main_story = sorted_stories[0]
        front_page_stories = []  # No secondary stories - they take too much space

        # Back page: mini articles (max 4 for 2-page fit)
        mini_stories = sorted_stories[1:5]  # Up to 4 mini articles for back page

        # Build day structure
        day_data = {
            "theme": get_theme_name(day_num),
            "main_story": {
                "title": main_story.title,
                "content": main_story.content,
                "source_url": main_story.source_url or FTN_BASE_URL
            },
            "front_page_stories": [
                {
                    "title": story.title,
                    "content": story.content,
                    "source_url": story.source_url or FTN_BASE_URL
                }
                for story in front_page_stories
            ],
            "mini_articles": [
                {
                    "title": story.title,
                    "content": story.content,
                    "source_url": story.source_url or FTN_BASE_URL
                }
                for story in mini_stories
            ],
            "statistics": [],  # Can be filled in manually or generated later
            "tomorrow_teaser": ""  # Can be filled in manually
        }

        four_days[f"day_{day_num}"] = day_data

    # Determine output filename
    if output_file is None:
        # Extract issue number from HTML filename
        html_path = Path(html_file)
        if 'FTN-' in html_path.name:
            issue = html_path.name.split('FTN-')[1].split('.')[0]
            output_file = f"ftn-{issue}.json"
        else:
            output_file = "ftn-content.json"

    # Write JSON file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(four_days, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Created {output_path}")
    print(f"   Contains {len(four_days)} days")

    return output_path


def get_theme_name(day_number: int) -> str:
    """Get theme name for a day number."""
    themes = {
        1: "Health & Education",
        2: "Environment & Conservation",
        3: "Technology & Energy",
        4: "Society & Youth Movements"
    }
    return themes.get(day_number, "General")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert FTN HTML to 4-day JSON for News, Fixed'
    )
    parser.add_argument(
        'html_file',
        help='FTN HTML file to parse'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output JSON file (default: ftn-{issue}.json)'
    )

    args = parser.parse_args()

    try:
        create_json_from_ftn(args.html_file, args.output)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {args.html_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
