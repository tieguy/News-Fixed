#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""
Shared content generation logic for News, Fixed.

This module contains the core content generation functions used by both
the interactive CLI (main.py) and the unattended web generator (scheduled_generate.py).
"""

import os
from utils import get_theme_name


# =============================================================================
# Mode Detection
# =============================================================================

def get_news_mode(default: str = 'family') -> str:
    """Get the current news mode from environment.

    Args:
        default: Default mode if NEWS_MODE not set ('family' or 'friends')

    Returns:
        'family' or 'friends'
    """
    mode = os.getenv('NEWS_MODE', default).lower()
    if mode not in ('family', 'friends'):
        mode = default
    return mode


def is_family_mode(default: str = 'family') -> bool:
    """Check if running in family mode (personalized content enabled)."""
    return get_news_mode(default) == 'family'


def is_friends_mode(default: str = 'family') -> bool:
    """Check if running in friends mode (generic content only)."""
    return get_news_mode(default) == 'friends'


# =============================================================================
# Content Generation
# =============================================================================

def generate_day_content(
    content_gen,
    day_data: dict,
    day_num: int,
    mode_default: str = 'family',
    on_progress=None
) -> dict:
    """
    Generate all content for a single day's newspaper.

    This is the shared content generation logic used by both the interactive
    CLI and the unattended web generator.

    Args:
        content_gen: ContentGenerator instance
        day_data: Dict with 'main_story', 'mini_articles', optionally 'second_story'
        day_num: Day number (1-4)
        mode_default: Default mode for this context ('family' for CLI, 'friends' for web)
        on_progress: Optional callback for progress messages, e.g. click.echo or logger.info

    Returns:
        Dict with all generated content:
        - main_story: Dict with title, content, source_url
        - mini_articles: List of dicts
        - statistics: List of stat strings
        - tomorrow_teaser: String (empty for day 4)
        - second_main_story: Dict or None (friends mode only)
    """
    def log(msg):
        if on_progress:
            on_progress(msg)

    # Generate main story
    log(f"Generating main story...")
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

    # Generate second main story for friends mode
    second_main_story = None
    if is_friends_mode(mode_default):
        second_story_data = day_data.get('second_story', {})
        if second_story_data and second_story_data.get('content'):
            second_main_story = content_gen.generate_second_main_story(
                original_content=second_story_data['content'],
                source_url=second_story_data['source_url'],
                theme=get_theme_name(day_num),
                original_title=second_story_data.get('title', '')
            )
            second_main_story['source_url'] = second_story_data['source_url']

    return {
        'main_story': main_story,
        'mini_articles': mini_articles,
        'statistics': statistics,
        'tomorrow_teaser': tomorrow_teaser,
        'second_main_story': second_main_story,
    }
