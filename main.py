#!/usr/bin/env python3
"""
News, Fixed - Main orchestrator for generating daily newspapers.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import click
from src.generator import ContentGenerator
from src.pdf_generator import NewspaperGenerator
from src.utils import get_theme_name


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
def main(input_file, day, generate_all, output, date_str, test, no_rewrite):
    """Generate News, Fixed daily newspaper from Fix The News content."""

    click.echo("📰 News, Fixed - Daily Positive News Generator\n")

    if test:
        # Generate test newspaper with sample data
        generate_test_newspaper(output)
        return

    if not input_file:
        click.echo("❌ Error: Please provide an input file with --input")
        click.echo("   Or use --test to generate a test newspaper")
        sys.exit(1)

    # Load input data
    try:
        with open(input_file, 'r') as f:
            ftn_data = json.load(f)
    except json.JSONDecodeError as e:
        click.echo(f"❌ Error parsing input file: {e}")
        sys.exit(1)

    # Initialize generators
    pdf_gen = NewspaperGenerator()

    # Only initialize AI generator if we need it
    content_gen = None
    if not no_rewrite:
        try:
            content_gen = ContentGenerator()
        except ValueError as e:
            click.echo(f"❌ Error: {e}")
            click.echo("   Make sure ANTHROPIC_API_KEY is set in your .env file")
            click.echo("   Or use --no-rewrite to skip AI generation")
            sys.exit(1)

    # Calculate week dates (Mon-Thu)
    week_dates = calculate_week_dates(date_str)

    # Determine which days to generate
    days_to_generate = range(1, 5) if generate_all else [day]

    for day_num in days_to_generate:
        date_info = week_dates[day_num]
        click.echo(f"\n📅 Generating {date_info['day_name']}, {date_info['formatted_date']} ({get_theme_name(day_num)})...")

        # Get stories for this day
        day_key = f"day_{day_num}"
        if day_key not in ftn_data:
            click.echo(f"⚠️  No data found for {day_key} in input file, skipping...")
            continue

        day_data = ftn_data[day_key]

        try:
            # Use content directly or generate with AI
            if no_rewrite:
                # Use content from JSON as-is
                click.echo("  📝 Using content from JSON...")
                main_story = day_data['main_story']
                mini_articles = day_data['mini_articles']
                statistics = day_data.get('statistics', [])
                tomorrow_teaser = day_data.get('tomorrow_teaser', '')
                feature_box = day_data.get('feature_box')
            else:
                # Generate main story
                click.echo("  ✍️  Generating main story...")
                main_story = content_gen.generate_main_story(
                    original_content=day_data['main_story']['content'],
                    source_url=day_data['main_story']['source_url'],
                    theme=get_theme_name(day_num)
                )
                main_story['source_url'] = day_data['main_story']['source_url']

                # Generate mini articles
                click.echo(f"  ✍️  Generating {len(day_data['mini_articles'])} mini articles...")
                mini_articles = []
                for article_data in day_data['mini_articles']:
                    mini_article = content_gen.generate_mini_article(
                        original_content=article_data['content'],
                        source_url=article_data['source_url']
                    )
                    mini_article['source_url'] = article_data['source_url']
                    mini_articles.append(mini_article)

                # Generate statistics
                click.echo("  📊 Generating statistics...")
                stories_summary = f"Main: {main_story['title']}\n"
                stories_summary += "\n".join([a['title'] for a in mini_articles])
                statistics = content_gen.generate_statistics(
                    stories_summary=stories_summary,
                    theme=get_theme_name(day_num)
                )

                # Generate tomorrow teaser (if not day 4)
                tomorrow_teaser = ""
                feature_box = None
                if day_num < 4:
                    click.echo("  👀 Generating tomorrow teaser...")
                    tomorrow_teaser = content_gen.generate_teaser(
                        tomorrow_theme=get_theme_name(day_num + 1)
                    )

            # Generate PDF
            click.echo("  📄 Generating PDF...")
            output_filename = f"news_fixed_{date_info['day_name'].lower()}.pdf"
            output_path = Path(output) / output_filename

            pdf_gen.generate_pdf(
                day_number=day_num,
                main_story=main_story,
                mini_articles=mini_articles,
                statistics=statistics,
                output_path=str(output_path),
                date_str=date_info['formatted_date'],
                day_of_week=date_info['day_name'],
                feature_box=feature_box,
                tomorrow_teaser=tomorrow_teaser
            )

            click.echo(f"  ✅ Generated: {output_path}")

        except Exception as e:
            click.echo(f"  ❌ Error generating Day {day_num}: {e}")
            continue

    click.echo("\n✨ Done! Your newspapers are ready to print.")


def generate_test_newspaper(output_dir):
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
        mini_articles=mini_articles,
        statistics=statistics,
        output_path=str(output_path),
        feature_box=feature_box,
        tomorrow_teaser=tomorrow_teaser
    )

    click.echo(f"✅ Test newspaper generated: {output_path}")
    click.echo(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
    click.echo(f"\n📄 Open it with: xdg-open {output_path}")


if __name__ == '__main__':
    main()
