#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

# FCIS: Scheduled generation script for automated weekly PDF creation on fly.io.

"""
Scheduled PDF generation for News, Fixed.

This script is designed to run unattended on fly.io's scheduled machines.
It fetches the latest FTN content, generates a combined 4-day PDF, and
caches it for web downloads.

Usage:
    python scheduled_generate.py              # Generate PDF for current week
    python scheduled_generate.py --dry-run    # Test without generating PDF
    python scheduled_generate.py --notify     # Send ntfy.sh notification on completion
"""

import os
import sys
import json
import logging
import tempfile
import httpx
from pathlib import Path
from datetime import datetime
from xml.etree import ElementTree

# Set up logging for unattended operation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cache import PDFCache, get_current_week
from generator import ContentGenerator
from pdf_generator import NewspaperGenerator
from ftn_to_json import create_json_from_ftn
from utils import get_theme_name


# Configuration
FTN_RSS_URL = "https://fixthenews.com/feed"
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "news-fixed")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")


def fetch_latest_ftn_via_rss() -> dict | None:
    """
    Fetch the latest FTN content via RSS feed.

    Returns:
        Dict with 'title', 'content', 'url', 'issue_number' or None if failed
    """
    logger.info(f"Fetching FTN content from RSS: {FTN_RSS_URL}")

    try:
        response = httpx.get(FTN_RSS_URL, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch RSS feed: {e}")
        return None

    try:
        root = ElementTree.fromstring(response.text)
    except ElementTree.ParseError as e:
        logger.error(f"Failed to parse RSS XML: {e}")
        return None

    # Find the latest item
    channel = root.find('channel')
    if channel is None:
        logger.error("No channel element in RSS feed")
        return None

    item = channel.find('item')
    if item is None:
        logger.error("No items in RSS feed")
        return None

    # Extract content
    title = item.findtext('title', '')
    link = item.findtext('link', '')

    # Try content:encoded first (full content), then description
    content = None
    for content_tag in ['content:encoded', '{http://purl.org/rss/1.0/modules/content/}encoded', 'description']:
        content_elem = item.find(content_tag)
        if content_elem is not None and content_elem.text:
            content = content_elem.text
            break

    if not content:
        logger.error("No content found in RSS item")
        return None

    # Extract issue number from title (e.g., "Fix The News #317: ...")
    import re
    issue_match = re.search(r'#(\d+)', title)
    issue_number = issue_match.group(1) if issue_match else datetime.now().strftime("%Y%m%d")

    logger.info(f"Found FTN issue #{issue_number}: {title[:60]}...")

    return {
        'title': title,
        'content': content,
        'url': link,
        'issue_number': issue_number
    }


def parse_ftn_content(ftn_data: dict) -> dict | None:
    """
    Parse FTN content into the 4-day JSON format expected by the generator.

    Args:
        ftn_data: Dict with 'content', 'title', 'url', 'issue_number'

    Returns:
        Dict with 'day_1', 'day_2', 'day_3', 'day_4' structure or None if failed
    """
    logger.info("Parsing FTN content into 4-day format...")

    # Save content to temp file for parser
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(ftn_data['content'])
        temp_html_path = Path(f.name)

    try:
        # Use create_json_from_ftn to parse HTML and create 4-day JSON
        # This handles all the LLM analysis and story grouping
        json_output_path = create_json_from_ftn(
            html_file=str(temp_html_path),
            output_file=str(temp_html_path.with_suffix('.json'))
        )

        # Load the generated JSON
        with open(json_output_path, 'r') as f:
            json_data = json.load(f)

        logger.info(f"Successfully parsed FTN content into 4-day format")
        return json_data

    except Exception as e:
        logger.error(f"Failed to parse FTN content: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        temp_html_path.unlink(missing_ok=True)
        temp_html_path.with_suffix('.json').unlink(missing_ok=True)


def generate_combined_pdf(ftn_json: dict, output_path: Path) -> bool:
    """
    Generate combined 4-day PDF from parsed FTN content.

    Args:
        ftn_json: Dict with 'day_1' through 'day_4' structure
        output_path: Path to save the generated PDF

    Returns:
        True if successful, False otherwise
    """
    logger.info("Initializing generators...")

    try:
        content_gen = ContentGenerator()
    except ValueError as e:
        logger.error(f"Failed to initialize ContentGenerator: {e}")
        logger.error("Make sure ANTHROPIC_API_KEY is set")
        return False

    pdf_gen = NewspaperGenerator()

    # Calculate week dates
    from main import calculate_week_dates
    week_dates = calculate_week_dates()

    days_data = []

    for day_num in range(1, 5):
        day_key = f"day_{day_num}"
        if day_key not in ftn_json:
            logger.warning(f"No data for {day_key}, skipping...")
            continue

        day_data = ftn_json[day_key]
        date_info = week_dates[day_num]

        logger.info(f"Generating content for {date_info['day_name']}...")

        # Generate main story
        main_story = content_gen.generate_main_story(
            original_content=day_data['main_story']['content'],
            source_url=day_data['main_story']['source_url'],
            theme=get_theme_name(day_num),
            original_title=day_data['main_story'].get('title', '')
        )
        main_story['source_url'] = day_data['main_story']['source_url']

        # Generate mini articles
        mini_articles = []
        for article_data in day_data.get('mini_articles', []):
            mini_article = content_gen.generate_mini_article(
                original_content=article_data['content'],
                source_url=article_data['source_url'],
                original_title=article_data.get('title', '')
            )
            mini_article['source_url'] = article_data['source_url']
            mini_articles.append(mini_article)

        # Generate statistics
        stories_summary = f"Main: {main_story['title']}\n"
        stories_summary += "\n".join([a['title'] for a in mini_articles])
        statistics = content_gen.generate_statistics(
            stories_summary=stories_summary,
            theme=get_theme_name(day_num)
        )

        # Generate tomorrow teaser (except for Thursday)
        tomorrow_teaser = ""
        if day_num < 4:
            tomorrow_teaser = content_gen.generate_teaser(
                tomorrow_theme=get_theme_name(day_num + 1)
            )

        # Generate second main story (since personalized features are disabled for web)
        second_main_story = None
        second_story_data = day_data.get('second_story', {})
        if second_story_data and second_story_data.get('content'):
            second_main_story = content_gen.generate_second_main_story(
                original_content=second_story_data['content'],
                source_url=second_story_data['source_url'],
                theme=get_theme_name(day_num),
                original_title=second_story_data.get('title', '')
            )
            second_main_story['source_url'] = second_story_data['source_url']

        days_data.append({
            'day_number': day_num,
            'day_of_week': date_info['day_name'],
            'date': date_info['formatted_date'],
            'theme': get_theme_name(day_num),
            'main_story': main_story,
            'front_page_stories': [],
            'mini_articles': mini_articles,
            'statistics': statistics,
            'feature_box': None,
            'tomorrow_teaser': tomorrow_teaser,
            'xkcd_comic': None,
            'second_main_story': second_main_story,
            'footer_message': "Good news exists, but it travels slowly."
        })

    if not days_data:
        logger.error("No day data generated")
        return False

    logger.info(f"Generating combined PDF: {output_path}")

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_gen.generate_combined_pdf(days_data, str(output_path))
        logger.info(f"PDF generated successfully: {output_path.stat().st_size / 1024:.1f} KB")
        return True
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return False


def send_notification(success: bool, message: str):
    """Send notification via ntfy.sh."""
    if not os.getenv("NTFY_ENABLED", "false").lower() in ("true", "1", "yes"):
        return

    try:
        title = "News Fixed: Generation Complete" if success else "News Fixed: Generation Failed"
        priority = "default" if success else "high"

        httpx.post(
            f"{NTFY_SERVER}/{NTFY_TOPIC}",
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "newspaper" if success else "warning"
            },
            content=message,
            timeout=10.0
        )
        logger.info(f"Notification sent to {NTFY_TOPIC}")
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")


def main():
    """Main entry point for scheduled generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Scheduled PDF generation for News, Fixed")
    parser.add_argument("--dry-run", action="store_true", help="Test without generating PDF")
    parser.add_argument("--notify", action="store_true", help="Send ntfy.sh notification")
    args = parser.parse_args()

    if args.notify:
        os.environ["NTFY_ENABLED"] = "true"

    logger.info("=" * 60)
    logger.info("News, Fixed - Scheduled Generation")
    logger.info("=" * 60)

    # Initialize cache
    cache_dir = Path(os.getenv("CACHE_DIR", "cache"))
    pdf_cache = PDFCache(cache_dir)
    current_week = get_current_week()

    logger.info(f"Current week: {current_week}")
    logger.info(f"Cache directory: {cache_dir}")

    # Check if already cached
    if pdf_cache.is_cached(current_week):
        logger.info(f"PDF already cached for {current_week}")
        send_notification(True, f"PDF for {current_week} already cached, skipping generation.")
        return 0

    if args.dry_run:
        logger.info("Dry run - would generate PDF for this week")
        return 0

    # Fetch FTN content
    ftn_data = fetch_latest_ftn_via_rss()
    if not ftn_data:
        error_msg = "Failed to fetch FTN content via RSS"
        logger.error(error_msg)
        send_notification(False, error_msg)
        return 1

    # Parse content
    ftn_json = parse_ftn_content(ftn_data)
    if not ftn_json:
        error_msg = "Failed to parse FTN content"
        logger.error(error_msg)
        send_notification(False, error_msg)
        return 1

    # Generate PDF to temp location
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        temp_pdf_path = Path(f.name)

    try:
        success = generate_combined_pdf(ftn_json, temp_pdf_path)

        if not success:
            error_msg = "Failed to generate combined PDF"
            logger.error(error_msg)
            send_notification(False, error_msg)
            return 1

        # Cache the PDF
        pdf_cache.cache_pdf(temp_pdf_path, current_week)
        logger.info(f"PDF cached for week {current_week}")

        send_notification(True, f"PDF for {current_week} generated and cached successfully.")
        return 0

    finally:
        temp_pdf_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
