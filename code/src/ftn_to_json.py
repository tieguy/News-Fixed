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


def group_stories_into_days(stories: list, blocklisted_ids: list, client) -> dict:
    """
    Group analyzed stories into 4 days using Claude API (Phase 2).

    Args:
        stories: List of analyzed story dicts with id, headline, themes, strength, length
        blocklisted_ids: List of story IDs to exclude
        client: Anthropic client

    Returns:
        Dict with day assignments: {day_1: {main: id, minis: [ids]}, ...}
    """
    stories_str = json.dumps(stories, indent=2)
    blocklist_str = json.dumps(blocklisted_ids) if blocklisted_ids else "[]"

    prompt = f"""You are organizing stories for a 4-day children's newspaper (ages 10-14).

STORIES:
{stories_str}

BLOCKLISTED STORY IDs (exclude these):
{blocklist_str}

DAY THEMES:
- Day 1: Health & Education
- Day 2: Environment & Conservation
- Day 3: Technology & Energy
- Day 4: Society & Youth Movements

RULES:
- Each day needs 1 main story (longest/strongest fit) + up to 4 minis
- Balance story count across days (aim for 4-5 per day)
- Main stories should be 600+ characters when possible
- Consider both primary and secondary themes for placement
- Stories can fit multiple days - pick best overall balance
- Blocklisted stories go in "unused"

Return ONLY valid JSON (no markdown fences):
{{
  "day_1": {{"main": <story_id or null>, "minis": [<story_ids>]}},
  "day_2": {{"main": <story_id or null>, "minis": [<story_ids>]}},
  "day_3": {{"main": <story_id or null>, "minis": [<story_ids>]}},
  "day_4": {{"main": <story_id or null>, "minis": [<story_ids>]}},
  "unused": [<story_ids>],
  "reasoning": "brief explanation of key placement decisions"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return parse_llm_json_with_retry(response.content[0].text, client)


def _fallback_grouping(analyzed_stories: list, blocklisted_ids: list) -> dict:
    """
    Fallback grouping using simple length-based assignment.

    Used when Phase 2 API call fails.
    """
    # Group by primary theme
    theme_map = {
        "health_education": "day_1",
        "environment": "day_2",
        "technology_energy": "day_3",
        "society": "day_4"
    }

    days = {
        "day_1": {"main": None, "minis": []},
        "day_2": {"main": None, "minis": []},
        "day_3": {"main": None, "minis": []},
        "day_4": {"main": None, "minis": []},
        "unused": blocklisted_ids.copy()
    }

    # Sort by length descending
    sorted_stories = sorted(
        [s for s in analyzed_stories if s["id"] not in blocklisted_ids],
        key=lambda s: s["length"],
        reverse=True
    )

    for story in sorted_stories:
        day_key = theme_map.get(story["primary_theme"], "day_4")

        if days[day_key]["main"] is None:
            days[day_key]["main"] = story["id"]
        elif len(days[day_key]["minis"]) < 4:
            days[day_key]["minis"].append(story["id"])
        else:
            days["unused"].append(story["id"])

    return days


def _build_four_days_from_grouping(stories: list, grouping: dict) -> dict:
    """
    Build the final 4-day JSON structure from grouping results.
    """
    four_days = {}

    # Add unused stories first
    unused_ids = grouping.get("unused", [])
    if unused_ids:
        four_days["unused"] = {
            "stories": [
                {
                    "title": stories[i].title,
                    "content": stories[i].content,
                    "source_url": stories[i].source_url or FTN_BASE_URL,
                    "tui_headline": stories[i].tui_headline or stories[i].title[:47] + "..."
                }
                for i in unused_ids if i < len(stories)
            ]
        }

    # Build each day
    for day_num in range(1, 5):
        day_key = f"day_{day_num}"
        day_grouping = grouping.get(day_key, {"main": None, "minis": []})

        main_id = day_grouping.get("main")
        mini_ids = day_grouping.get("minis", [])

        day_data = {
            "theme": get_theme_name(day_num),
            "main_story": {},
            "front_page_stories": [],
            "mini_articles": [],
            "statistics": [],
            "tomorrow_teaser": ""
        }

        # Add main story
        if main_id is not None and main_id < len(stories):
            story = stories[main_id]
            day_data["main_story"] = {
                "title": story.title,
                "content": story.content,
                "source_url": story.source_url or FTN_BASE_URL,
                "tui_headline": story.tui_headline or story.title[:47] + "..."
            }

        # Add mini articles
        for mini_id in mini_ids:
            if mini_id < len(stories):
                story = stories[mini_id]
                day_data["mini_articles"].append({
                    "title": story.title,
                    "content": story.content,
                    "source_url": story.source_url or FTN_BASE_URL,
                    "tui_headline": story.tui_headline or story.title[:47] + "..."
                })

        four_days[day_key] = day_data

    return four_days


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

    # Initialize Anthropic client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found")
        print("   Set it in .env or environment to use LLM categorization")
        sys.exit(1)

    anthropic_client = Anthropic(api_key=api_key)

    # Load blocklist
    blocklist = parser._load_blocklist()

    # Phase 1: Analyze each story
    print(f"\n🔍 Phase 1: Analyzing {len(stories)} stories...")
    analyzed_stories = []
    blocklisted_ids = []

    for i, story in enumerate(stories):
        print(f"   [{i+1}/{len(stories)}] Analyzing...", end="\r")

        # Check blocklist first
        if parser._is_blocklisted(story, blocklist):
            blocklisted_ids.append(i)
            analyzed_stories.append({
                "id": i,
                "headline": story.title[:50],
                "primary_theme": "unused",
                "secondary_themes": [],
                "story_strength": "low",
                "length": len(story.content),
                "blocklisted": True
            })
            continue

        try:
            analysis = analyze_story(
                title=story.title,
                content=story.content,
                all_urls=story.all_urls,
                content_length=len(story.content),
                client=anthropic_client
            )

            # Store analysis results back on story object
            story.tui_headline = analysis.get("tui_headline", story.title[:47] + "...")
            story.source_url = analysis.get("primary_source_url") or story.source_url

            analyzed_stories.append({
                "id": i,
                "headline": analysis.get("tui_headline", story.title[:50]),
                "primary_theme": analysis.get("primary_theme", "society"),
                "secondary_themes": analysis.get("secondary_themes", []),
                "story_strength": analysis.get("story_strength", "medium"),
                "length": len(story.content)
            })
        except Exception as e:
            print(f"\n   ⚠️  Error analyzing story {i}: {e}")
            story.tui_headline = story.title[:47] + ("..." if len(story.title) > 47 else "")
            analyzed_stories.append({
                "id": i,
                "headline": story.title[:50],
                "primary_theme": "society",
                "secondary_themes": [],
                "story_strength": "medium",
                "length": len(story.content)
            })

    print(f"   ✓ Analyzed {len(stories)} stories" + " " * 20)

    # Phase 2: Group stories into days
    print(f"\n📊 Phase 2: Grouping stories into days...")

    try:
        grouping = group_stories_into_days(
            stories=analyzed_stories,
            blocklisted_ids=blocklisted_ids,
            client=anthropic_client
        )
        print(f"   ✓ Grouped stories")
        if grouping.get("reasoning"):
            print(f"   Reasoning: {grouping['reasoning'][:100]}...")
    except Exception as e:
        print(f"   ⚠️  Error grouping stories: {e}")
        print(f"   Falling back to length-based assignment...")
        grouping = _fallback_grouping(analyzed_stories, blocklisted_ids)

    # Build 4-day structure from grouping
    four_days = _build_four_days_from_grouping(stories, grouping)

    # Determine output filename
    if output_file is None:
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

    # Print summary
    for day_num in range(1, 5):
        day_key = f"day_{day_num}"
        if day_key in four_days:
            main = 1 if four_days[day_key].get("main_story") else 0
            minis = len(four_days[day_key].get("mini_articles", []))
            print(f"   Day {day_num}: {main} main + {minis} minis")

    if "unused" in four_days:
        unused_count = len(four_days["unused"].get("stories", []))
        if unused_count:
            print(f"   Unused: {unused_count} stories")

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
