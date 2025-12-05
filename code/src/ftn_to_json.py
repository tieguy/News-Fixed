#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Convert fetched FTN HTML into a 4-day JSON file for News, Fixed."""

import sys
import json
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path so we can import src modules
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent.parent))

# Use relative import to avoid conflict with built-in parser module
from src.parser import FTNParser

# Constants
FTN_BASE_URL = "https://fixthenews.com"


def parse_llm_json(response_text: str) -> dict:
    """
    Parse JSON from LLM response, handling common formatting issues.

    Args:
        response_text: Raw response text from LLM

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If JSON is invalid after cleanup
    """
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)


def parse_llm_json_with_retry(response_text: str, client) -> dict:
    """
    Parse JSON from LLM response, retrying with error context on failure.

    Args:
        response_text: Raw response text from LLM
        client: Anthropic client for retry request

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If JSON is invalid after retry
    """
    try:
        return parse_llm_json(response_text)
    except json.JSONDecodeError as e:
        # Retry with error context
        retry_prompt = f"""Your previous response was not valid JSON.

Your response:
{response_text}

Parse error: {e}

Please return the corrected JSON only, no explanation or markdown."""

        retry_response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": retry_prompt}
            ]
        )

        retry_text = retry_response.content[0].text
        return parse_llm_json(retry_text)  # Let it raise if still invalid


def analyze_story(title: str, content: str, all_urls: list, content_length: int, client) -> dict:
    """
    Analyze a story using Claude API (Phase 1).

    Extracts themes, selects primary URL, generates headline.

    Args:
        title: Story title
        content: Story content
        all_urls: List of all URLs found in story
        content_length: Character count of content
        client: Anthropic client

    Returns:
        Dict with analysis results
    """
    urls_str = "\n".join(f"- {url}" for url in all_urls) if all_urls else "None"

    prompt = f"""You are helping categorize news stories for a children's newspaper (ages 10-14).

Analyze this story and return JSON:

STORY:
Title: {title}
Content: {content}
URLs found:
{urls_str}
Length: {content_length} characters

Return ONLY valid JSON (no markdown fences):
{{
  "primary_theme": "one of: health_education, environment, technology_energy, society",
  "secondary_themes": ["other relevant themes as free-form tags"],
  "age_appropriateness": "high, medium, or low - is this suitable for 10-14 year olds?",
  "story_strength": "high, medium, or low - how compelling and well-sourced is this?",
  "suggested_role": "main or mini - main needs 600+ chars and depth",
  "primary_source_url": "the best URL for attribution from the list above, or null if none suitable",
  "tui_headline": "40-50 character engaging headline for display"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return parse_llm_json_with_retry(response.content[0].text, client)


def generate_tui_headline(story_title: str, story_content: str, anthropic_client: Anthropic) -> str:
    """
    Generate a concise 40-50 character headline for TUI display.

    Args:
        story_title: The story title (first sentence)
        story_content: The story content (remaining text)
        anthropic_client: Initialized Anthropic client

    Returns:
        40-50 character headline
    """
    # Combine title and content for context
    full_text = f"{story_title} {story_content}".strip()

    prompt = f"""Generate a concise, informative headline of exactly 40-50 characters (including spaces) for this news story. The headline should be suitable for display in a text user interface.

Story:
{full_text[:500]}

Return ONLY the headline, nothing else. Make it engaging and clear."""

    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        headline = message.content[0].text.strip()

        # Ensure it's within length limits
        if len(headline) > 50:
            headline = headline[:47] + "..."
        elif len(headline) < 40:
            # Pad with spaces if too short (shouldn't happen, but just in case)
            headline = headline.ljust(40)

        return headline
    except Exception as e:
        print(f"   ⚠️  Error generating headline: {e}")
        # Fallback to truncated title
        fallback = full_text[:47]
        return fallback + "..." if len(full_text) > 47 else fallback


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

    # Initialize Anthropic client for headline generation
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("   ⚠️  Warning: ANTHROPIC_API_KEY not found - using truncated titles for TUI")
        anthropic_client = None
    else:
        anthropic_client = Anthropic(api_key=api_key)
        print(f"   Generating TUI headlines for {len(stories)} stories...")

    # Generate TUI headlines for each story
    for i, story in enumerate(stories, 1):
        if anthropic_client:
            print(f"   [{i}/{len(stories)}] Generating headline...", end="\r")
            story.tui_headline = generate_tui_headline(story.title, story.content, anthropic_client)
        else:
            # Fallback: use truncated title + content
            full_text = f"{story.title} {story.content}".strip()
            story.tui_headline = full_text[:47] + ("..." if len(full_text) > 47 else "")

    if anthropic_client:
        print(f"   ✓ Generated {len(stories)} headlines" + " " * 20)

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
                    "source_url": story.source_url or FTN_BASE_URL,
                    "tui_headline": story.tui_headline or story.content[:47] + "..."
                }
                for story in unused_stories
            ]
        }

    for day_num, category_key in day_mapping.items():
        category_stories = categories.get(category_key, [])

        if not category_stories:
            print(f"\n⚠️  Warning: No stories found for day {day_num} ({category_key})")
            # Still create the day structure (empty) so TUI can display it
            four_days[f"day_{day_num}"] = {
                "theme": get_theme_name(day_num),
                "main_story": {},
                "front_page_stories": [],
                "mini_articles": [],
                "statistics": [],
                "tomorrow_teaser": ""
            }
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
                "source_url": main_story.source_url or FTN_BASE_URL,
                "tui_headline": main_story.tui_headline or main_story.content[:47] + "..."
            },
            "front_page_stories": [
                {
                    "title": story.title,
                    "content": story.content,
                    "source_url": story.source_url or FTN_BASE_URL,
                    "tui_headline": story.tui_headline or story.content[:47] + "..."
                }
                for story in front_page_stories
            ],
            "mini_articles": [
                {
                    "title": story.title,
                    "content": story.content,
                    "source_url": story.source_url or FTN_BASE_URL,
                    "tui_headline": story.tui_headline or story.content[:47] + "..."
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
