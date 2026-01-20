#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""
News, Fixed - Main orchestrator for generating daily newspapers.
"""

import sys
import os
import json
import subprocess
import shlex
from pathlib import Path
from datetime import datetime, timedelta
import click
from generator import ContentGenerator
from pdf_generator import NewspaperGenerator
from utils import get_theme_name
from sports_schedule import DukeBasketballSchedule
from xkcd import XkcdManager
from readwise_fetcher import ReadwiseFetcher


def get_feature_flag(name: str, default: bool = True) -> bool:
    """Get a feature flag from environment variable.

    Args:
        name: Feature flag name (e.g., 'FEATURE_DUKE_SPORTS')
        default: Default value if not set (True for local, False for web)

    Returns:
        Boolean indicating if feature is enabled
    """
    value = os.getenv(name, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def preview_and_print(pdf_path: Path) -> None:
    """
    Open PDF in system viewer for preview and optionally print.

    Args:
        pdf_path: Path to the PDF file to preview/print
    """
    # Open in system PDF viewer
    click.echo(f"  👀 Opening preview...")
    try:
        subprocess.Popen(
            ["xdg-open", str(pdf_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        click.echo(f"  ⚠️  Could not open preview (xdg-open not found)")
        click.echo(f"     Open manually: {pdf_path}")
        return

    # Ask if user wants to print
    if click.confirm("  🖨️  Print this newspaper?", default=False):
        print_cmd = os.getenv("PRINT_COMMAND", "lpr")
        # Parse command to handle options like "lpr -P printer"
        cmd_parts = shlex.split(print_cmd) + [str(pdf_path)]

        click.echo(f"  📤 Printing with: {' '.join(cmd_parts)}")
        try:
            result = subprocess.run(cmd_parts, capture_output=True, text=True)
            if result.returncode == 0:
                click.echo(f"  ✅ Sent to printer")
            else:
                click.echo(f"  ❌ Print failed: {result.stderr.strip()}")
        except FileNotFoundError:
            click.echo(f"  ❌ Print command not found: {cmd_parts[0]}")
            click.echo(f"     Set PRINT_COMMAND in .env to configure printing")
    else:
        click.echo(f"  ⏭️  Skipped printing")


def calculate_week_dates(base_date=None):
    """
    Calculate Monday-Thursday dates for the upcoming week.

    If run on Friday, Saturday, or Sunday, calculates for next week's Monday-Thursday.
    Otherwise, calculates for the current week's Monday-Thursday.

    Args:
        base_date: Optional base date (defaults to today)

    Returns:
        dict mapping day_number (1-4) to (date_obj, day_name, formatted_date)
    """
    if base_date is None:
        base_date = datetime.now()
    elif isinstance(base_date, str):
        base_date = datetime.fromisoformat(base_date)

    # Monday=0, Sunday=6
    current_weekday = base_date.weekday()

    # If it's Friday (4), Saturday (5), or Sunday (6), use next week
    if current_weekday >= 4:
        # Calculate next Monday
        days_until_monday = (7 - current_weekday) % 7
        if days_until_monday == 0:  # If somehow we're on Monday and current_weekday >= 4
            days_until_monday = 7
        monday = base_date + timedelta(days=days_until_monday)
    else:
        # Find this week's Monday (Mon-Thu)
        days_since_monday = current_weekday
        monday = base_date - timedelta(days=days_since_monday)

    # Build dict for Mon-Thu (days 1-4)
    week_dates = {}
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday']

    for i in range(4):
        date_obj = monday + timedelta(days=i)
        week_dates[i + 1] = {
            'date_obj': date_obj,
            'day_name': day_names[i],
            'formatted_date': date_obj.strftime('%B %-d, %Y')  # "October 21, 2025"
        }

    return week_dates


def load_ftn_data(input_file: str) -> dict:
    """Load and parse FTN data from JSON file."""
    try:
        with open(input_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        click.echo(f"❌ Error parsing input file: {e}")
        sys.exit(1)


def initialize_generators(no_rewrite: bool) -> tuple:
    """Initialize PDF and optionally AI content generators."""
    pdf_gen = NewspaperGenerator()
    content_gen = None

    if not no_rewrite:
        try:
            content_gen = ContentGenerator()
        except ValueError as e:
            click.echo(f"❌ Error: {e}")
            click.echo("   Make sure ANTHROPIC_API_KEY is set in your .env file")
            click.echo("   Or use --no-rewrite to skip AI generation")
            sys.exit(1)

    return pdf_gen, content_gen


def generate_content_with_ai(content_gen, day_data: dict, day_num: int) -> tuple:
    """Generate content using AI."""
    click.echo("  ✍️  Generating main story...")
    main_story = content_gen.generate_main_story(
        original_content=day_data['main_story']['content'],
        source_url=day_data['main_story']['source_url'],
        theme=get_theme_name(day_num),
        original_title=day_data['main_story'].get('title', '')
    )
    main_story['source_url'] = day_data['main_story']['source_url']

    front_page_stories = day_data.get('front_page_stories', [])

    click.echo(f"  ✍️  Generating {len(day_data['mini_articles'])} mini articles...")
    mini_articles = []
    for article_data in day_data['mini_articles']:
        mini_article = content_gen.generate_mini_article(
            original_content=article_data['content'],
            source_url=article_data['source_url'],
            original_title=article_data.get('title', '')
        )
        mini_article['source_url'] = article_data['source_url']
        mini_articles.append(mini_article)

    click.echo("  📊 Generating statistics...")
    stories_summary = f"Main: {main_story['title']}\n"
    stories_summary += "\n".join([a['title'] for a in mini_articles])
    statistics = content_gen.generate_statistics(
        stories_summary=stories_summary,
        theme=get_theme_name(day_num)
    )

    tomorrow_teaser = ""
    if day_num < 4:
        click.echo("  👀 Generating tomorrow teaser...")
        tomorrow_teaser = content_gen.generate_teaser(
            tomorrow_theme=get_theme_name(day_num + 1)
        )

    return main_story, front_page_stories, mini_articles, statistics, tomorrow_teaser


def use_content_from_json(day_data: dict) -> tuple:
    """Use content from JSON file without AI rewriting."""
    click.echo("  📝 Using content from JSON...")
    main_story = day_data['main_story']
    front_page_stories = day_data.get('front_page_stories', [])
    mini_articles = day_data['mini_articles']
    statistics = day_data.get('statistics', [])
    tomorrow_teaser = day_data.get('tomorrow_teaser', '')

    return main_story, front_page_stories, mini_articles, statistics, tomorrow_teaser


def fetch_local_story(content_gen, date_str: str) -> dict | None:
    """Fetch and generate a local SF story from Readwise Reader.

    Args:
        content_gen: ContentGenerator instance for rewriting
        date_str: Date string for the edition (YYYY-MM-DD format)

    Returns:
        Dict with 'title', 'content', 'source_url' or None if no articles
    """
    try:
        fetcher = ReadwiseFetcher(tag="sf-good")
    except ValueError as e:
        click.echo(f"  ⚠️  Readwise not configured: {e}")
        return None

    # Get article for this date (reuses if already assigned, else picks next unused)
    article = fetcher.get_article_for_date(date_str, with_content=True)
    if not article:
        click.echo("  ℹ️  No unused local articles available")
        return None

    click.echo(f"  🏠 Generating local story: {article['title'][:50]}...")

    # Generate the local story
    local_story = content_gen.generate_local_story(
        original_content=article.get('html_content') or article.get('summary', ''),
        source_url=article['source_url'],
        original_title=article['title']
    )
    local_story['source_url'] = article['source_url']

    return local_story


def check_for_sports_games(date_info: dict) -> dict | None:
    """Check for Duke basketball games and return feature box if found."""
    sports_schedule = DukeBasketballSchedule()
    games = []

    if date_info['day_name'] == 'Thursday':
        # For Thursday, check Fri-Sun for weekend games
        for days_ahead in range(1, 4):
            weekend_date = date_info['date_obj'].date() + timedelta(days=days_ahead)
            weekend_games = sports_schedule.get_games_for_date(weekend_date)
            if weekend_games:
                games.extend(weekend_games)
    else:
        # For Mon-Wed, check the actual day
        games = sports_schedule.get_games_for_date(date_info['date_obj'].date())

    if games:
        click.echo(f"  🏀 Adding {games[0]['team']} game to feature box")
        return sports_schedule.format_game_box(games[0])

    return None


def generate_day_newspaper(
    day_num: int,
    day_data: dict,
    date_info: dict,
    pdf_gen,
    content_gen,
    output: str,
    no_rewrite: bool,
    ftn_number: str = None
) -> None:
    """Generate newspaper for a single day."""
    click.echo(f"\n📅 Generating {date_info['day_name']}, {date_info['formatted_date']} ({get_theme_name(day_num)})...")

    # Generate or load content
    if no_rewrite:
        main_story, front_page_stories, mini_articles, statistics, tomorrow_teaser = \
            use_content_from_json(day_data)
        feature_box = day_data.get('feature_box')
    else:
        main_story, front_page_stories, mini_articles, statistics, tomorrow_teaser = \
            generate_content_with_ai(content_gen, day_data, day_num)
        feature_box = None

    # Check for sports games if feature enabled (takes priority for feature box)
    if get_feature_flag('FEATURE_DUKE_SPORTS', default=True):
        sports_feature = check_for_sports_games(date_info)
        if sports_feature:
            feature_box = sports_feature

    # Fetch local SF story if feature enabled (add to front page stories)
    if content_gen and get_feature_flag('FEATURE_SF_LOCAL', default=True):
        local_story = fetch_local_story(content_gen, date_info['date_obj'].strftime('%Y-%m-%d'))
        if local_story:
            front_page_stories = [local_story] + list(front_page_stories or [])

    # Load xkcd comic if selected for the newspaper's week
    xkcd_manager = XkcdManager()
    xkcd_comic = None
    selected_num = xkcd_manager.get_selected_for_day(day_num, date_info['date_obj'])
    if selected_num:
        cache = xkcd_manager.load_cache()
        if str(selected_num) in cache:
            xkcd_comic = cache[str(selected_num)]

    # Generate PDF
    click.echo("  📄 Generating PDF...")
    date_str_iso = date_info['date_obj'].strftime('%Y-%m-%d')

    # Build filename: news_fixed_NNN_YYYY-MM-DD.pdf
    if ftn_number:
        output_filename = f"news_fixed_{ftn_number}_{date_str_iso}.pdf"
    else:
        output_filename = f"news_fixed_{date_str_iso}.pdf"

    output_path = Path(output) / output_filename

    pdf_gen.generate_pdf(
        day_number=day_num,
        main_story=main_story,
        front_page_stories=front_page_stories,
        mini_articles=mini_articles,
        statistics=statistics,
        output_path=str(output_path),
        date_str=date_info['formatted_date'],
        day_of_week=date_info['day_name'],
        feature_box=feature_box,
        tomorrow_teaser=tomorrow_teaser,
        xkcd_comic=xkcd_comic
    )

    click.echo(f"  ✅ Generated: {output_path}")
    return output_path


@click.command()
@click.option('--input', '-i', 'input_file', type=click.Path(exists=True),
              help='Input file with Fix The News content (JSON format)')
@click.option('--day', '-d', type=click.IntRange(1, 4), default=1,
              help='Day number to generate (1-4)')
@click.option('--all', 'generate_all', is_flag=True,
              help='Generate all 4 days')
@click.option('--output', '-o', type=click.Path(),
              default='output',
              help='Output directory for PDFs')
@click.option('--date', 'date_str',
              help='Date for the newspaper (YYYY-MM-DD), defaults to today')
@click.option('--test', is_flag=True,
              help='Generate test newspaper with sample data (no API calls)')
@click.option('--no-rewrite', is_flag=True,
              help='Use content from JSON as-is without AI rewriting')
@click.option('--no-preview', is_flag=True,
              help='Skip PDF preview and print prompt')
def main(input_file, day, generate_all, output, date_str, test, no_rewrite, no_preview):
    """Generate News, Fixed daily newspaper from Fix The News content."""

    click.echo("📰 News, Fixed - Daily Positive News Generator\n")

    if test:
        generate_test_newspaper(output, no_preview)
        return

    if not input_file:
        click.echo("❌ Error: Please provide an input file with --input")
        click.echo("   Or use --test to generate a test newspaper")
        sys.exit(1)

    ftn_data = load_ftn_data(input_file)
    pdf_gen, content_gen = initialize_generators(no_rewrite)
    week_dates = calculate_week_dates(date_str)
    days_to_generate = range(1, 5) if generate_all else [day]

    # Extract FTN issue number from input filename (e.g., "ftn-316.json" -> "316")
    import re
    ftn_number = None
    if input_file:
        match = re.search(r'ftn-?(\d+)', Path(input_file).name, re.IGNORECASE)
        if match:
            ftn_number = match.group(1)

    for day_num in days_to_generate:
        day_key = f"day_{day_num}"
        if day_key not in ftn_data:
            click.echo(f"⚠️  No data found for {day_key} in input file, skipping...")
            continue

        try:
            output_path = generate_day_newspaper(
                day_num=day_num,
                day_data=ftn_data[day_key],
                date_info=week_dates[day_num],
                pdf_gen=pdf_gen,
                content_gen=content_gen,
                output=output,
                no_rewrite=no_rewrite,
                ftn_number=ftn_number
            )
            if not no_preview:
                preview_and_print(output_path)
        except Exception as e:
            click.echo(f"  ❌ Error generating Day {day_num}: {e}")
            import traceback
            traceback.print_exc()
            continue

    click.echo("\n✨ Done!")


def generate_test_newspaper(output_dir, no_preview=False):
    """Generate a test newspaper with sample data (no API calls)."""

    click.echo("🧪 Generating test newspaper with sample data...\n")

    pdf_gen = NewspaperGenerator()

    # Sample data
    main_story = {
        "title": "Scientists Discover Ocean Bacteria That Eat Plastic",
        "content": """Imagine if nature had its own cleanup crew for pollution. Well, scientists just found one! A team of researchers discovered bacteria living in coastal waters that can actually eat plastic waste.

These tiny organisms can break down certain types of plastic in just a few weeks—compare that to the hundreds of years it normally takes plastic to decompose naturally. Think of it like having a recycling system that works at super speed.

What's really cool is that these bacteria weren't created in a lab. They've been living in the ocean all along, quietly doing their job. Scientists just had to figure out what they were up to. It's like finding out your backyard has been home to superheroes this whole time.

The research team estimates that with some help, these bacteria could clean up millions of tons of plastic from our oceans. They're now working on ways to boost the bacteria's abilities and use them safely in polluted areas.

This discovery matters because it shows that solutions to big problems can come from unexpected places. While we still need to use less plastic and recycle more, it's encouraging to know that nature might help us fix past mistakes.

For anyone who cares about the environment, this is a powerful reminder: nature has been solving problems for billions of years. Sometimes our job is just to pay attention and learn from it. Those tiny bacteria might be small, but they could make a huge difference in keeping our oceans clean for generations to come.""",
        "source_url": "https://www.nature.com/articles/s41586-023-06000-0"
    }

    mini_articles = [
        {
            "title": "Solar Power Costs Drop 90% in a Decade",
            "content": "Solar energy is now cheaper than fossil fuels in most countries, thanks to a 90% price drop over the past ten years. More than 100 countries now get at least 10% of their electricity from solar and wind. This means cleaner air for everyone and lower energy bills for millions of families. The falling costs prove that switching to renewable energy isn't just good for the planet—it makes economic sense too.",
            "source_url": "https://www.iea.org/reports/solar-pv"
        },
        {
            "title": "Kenyan Teens Invent $5 Water Filter",
            "content": "Three high school students in Kenya created a water filter that costs less than $5 and uses only local materials. It can clean 20 liters of water per hour and removes 99% of harmful bacteria. The invention is already helping communities access clean drinking water. The students say they wanted to solve a problem they saw in their own neighborhoods—proving that you don't need to be an adult or have fancy equipment to make a real difference.",
            "source_url": "https://www.unicef.org/innovation/stories/water-filter-innovation"
        },
        {
            "title": "Forests Bounce Back Faster Than Expected",
            "content": "Satellite data reveals that reforested areas are recovering much faster than scientists predicted. Places that were cleared 20 years ago now have thriving forests with diverse wildlife. The findings show that when we give nature the chance, it can heal remarkably quickly. This is great news for climate change efforts, since growing forests absorb carbon dioxide and provide homes for countless species.",
            "source_url": "https://www.conservation.org/blog/forest-restoration-success"
        },
        {
            "title": "Girls' School Enrollment Hits Record High",
            "content": "For the first time ever, more than 90% of girls worldwide are enrolled in primary school. Countries that invested in girls' education are seeing major benefits in health, economy, and innovation. Education experts call it 'the most powerful investment any society can make.' When girls get education, entire communities benefit for generations. This milestone represents millions of individual success stories.",
            "source_url": "https://www.unesco.org/reports/gem/2023/en"
        }
    ]

    statistics = [
        {"number": "90%", "description": "drop in solar panel costs"},
        {"number": "100+", "description": "countries using clean energy"},
        {"number": "$5", "description": "cost of new water filter"},
        {"number": "99%", "description": "harmful bacteria removed"},
        {"number": "20 yrs", "description": "for forests to recover"},
        {"number": "90%", "description": "of girls in school"}
    ]

    feature_box = {
        "title": "Quick Win",
        "content": "Over 50 countries have banned single-use plastic bags, reducing ocean plastic pollution by millions of tons each year. Small policy changes can have massive impacts!"
    }

    tomorrow_teaser = "Tomorrow: Discover how young climate activists are changing the world, plus a major breakthrough in clean energy storage."

    output_path = Path(output_dir) / "test_newspaper.pdf"

    pdf_gen.generate_pdf(
        day_number=1,
        main_story=main_story,
        front_page_stories=[],  # No secondary stories for test
        mini_articles=mini_articles,
        statistics=statistics,
        output_path=str(output_path),
        date_str="Monday, October 20, 2025",
        day_of_week="Monday",
        feature_box=feature_box,
        tomorrow_teaser=tomorrow_teaser,
        xkcd_comic=None
    )

    click.echo(f"✅ Test newspaper generated: {output_path}")
    click.echo(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")

    if not no_preview:
        preview_and_print(output_path)
    else:
        click.echo(f"\n📄 Open it with: xdg-open {output_path}")


if __name__ == '__main__':
    main()
