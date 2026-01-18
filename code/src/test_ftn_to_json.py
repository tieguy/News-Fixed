"""Tests for ftn_to_json module."""
import json
import os
import pytest
from unittest.mock import Mock, MagicMock
from ftn_to_json import analyze_themes


def test_parse_llm_json_valid():
    """parse_llm_json handles valid JSON."""
    from ftn_to_json import parse_llm_json

    result = parse_llm_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_llm_json_strips_markdown_fences():
    """parse_llm_json strips markdown code fences."""
    from ftn_to_json import parse_llm_json

    result = parse_llm_json('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_llm_json_strips_fences_without_lang():
    """parse_llm_json strips fences without language specifier."""
    from ftn_to_json import parse_llm_json

    result = parse_llm_json('```\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_llm_json_raises_on_invalid():
    """parse_llm_json raises JSONDecodeError on invalid JSON."""
    from ftn_to_json import parse_llm_json

    with pytest.raises(json.JSONDecodeError):
        parse_llm_json('not valid json')


def test_parse_llm_json_with_retry_succeeds_first_try():
    """parse_llm_json_with_retry returns on first successful parse."""
    from ftn_to_json import parse_llm_json_with_retry

    client = Mock()  # Should not be called

    result = parse_llm_json_with_retry('{"key": "value"}', client)
    assert result == {"key": "value"}
    client.messages.create.assert_not_called()


def test_parse_llm_json_with_retry_retries_on_failure():
    """parse_llm_json_with_retry retries with error context."""
    from ftn_to_json import parse_llm_json_with_retry

    # Mock client that returns valid JSON on retry
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"fixed": "json"}')]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    result = parse_llm_json_with_retry('invalid json {', client)

    assert result == {"fixed": "json"}
    client.messages.create.assert_called_once()
    # Check that error context was included in retry prompt
    call_args = client.messages.create.call_args
    prompt = call_args.kwargs['messages'][0]['content']
    assert 'invalid json {' in prompt
    assert 'Parse error' in prompt or 'JSONDecodeError' in prompt


def test_parse_llm_json_with_retry_raises_after_failed_retry():
    """parse_llm_json_with_retry raises if retry also fails."""
    from ftn_to_json import parse_llm_json_with_retry

    # Mock client that returns invalid JSON on retry too
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='still invalid')]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    with pytest.raises(json.JSONDecodeError):
        parse_llm_json_with_retry('invalid json', client)


def test_analyze_story_returns_expected_fields():
    """analyze_story returns all required fields."""
    from ftn_to_json import analyze_story

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    result = analyze_story(
        title="Solar panels bring power to rural villages.",
        content="A new initiative has installed solar panels in 50 villages across Kenya, providing electricity to over 10,000 households for the first time.",
        all_urls=["https://nature.com/solar-study", "https://kenya.gov/energy"],
        content_length=180,
        client=client
    )

    assert "primary_theme" in result
    assert result["primary_theme"] in ["health_education", "environment", "technology_energy", "society"]
    assert "secondary_themes" in result
    assert isinstance(result["secondary_themes"], list)
    assert "age_appropriateness" in result
    assert "story_strength" in result
    assert "suggested_role" in result
    assert result["suggested_role"] in ["main", "mini"]
    assert "primary_source_url" in result
    assert "tui_headline" in result
    assert 30 <= len(result["tui_headline"]) <= 60  # Allow some flexibility


def test_group_stories_into_days_returns_expected_structure():
    """group_stories_into_days returns proper day assignments."""
    from ftn_to_json import group_stories_into_days, DEFAULT_THEMES

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    # Convert DEFAULT_THEMES to the expected format
    themes = {
        day: {"name": info["name"], "key": info["key"], "source": "default"}
        for day, info in DEFAULT_THEMES.items()
    }

    # Create mock analyzed stories
    stories = [
        {"id": 0, "headline": "Solar farms expand", "primary_theme": "technology_energy", "secondary_themes": ["africa"], "story_strength": "high", "length": 800},
        {"id": 1, "headline": "New literacy program", "primary_theme": "health_education", "secondary_themes": ["youth"], "story_strength": "medium", "length": 400},
        {"id": 2, "headline": "Ocean cleanup success", "primary_theme": "environment", "secondary_themes": ["technology"], "story_strength": "high", "length": 600},
        {"id": 3, "headline": "Youth voting rights", "primary_theme": "society", "secondary_themes": ["democracy"], "story_strength": "medium", "length": 350},
    ]

    result = group_stories_into_days(stories, blocklisted_ids=[], themes=themes, client=client)

    # Check structure
    assert "day_1" in result
    assert "day_2" in result
    assert "day_3" in result
    assert "day_4" in result
    assert "main" in result["day_1"]
    assert "minis" in result["day_1"]
    assert isinstance(result["day_1"]["minis"], list)

    # Check all story IDs are accounted for
    all_assigned = set()
    for day_key in ["day_1", "day_2", "day_3", "day_4"]:
        if result[day_key]["main"] is not None:
            all_assigned.add(result[day_key]["main"])
        all_assigned.update(result[day_key]["minis"])
    all_assigned.update(result.get("unused", []))

    assert all_assigned == {0, 1, 2, 3}


def test_group_stories_with_custom_themes():
    """group_stories_into_days works with custom (non-default) themes."""
    from ftn_to_json import group_stories_into_days

    stories = [
        {"id": 0, "headline": "AI discovery", "primary_theme": "ai_robotics", "secondary_themes": [], "story_strength": "high", "length": 800},
        {"id": 1, "headline": "Clean energy win", "primary_theme": "clean_energy", "secondary_themes": [], "story_strength": "medium", "length": 400},
    ]

    # Custom themes (simulating generated/split themes)
    custom_themes = {
        1: {"name": "AI & Robotics", "key": "ai_robotics", "source": "split_from_technology_energy"},
        2: {"name": "Environment & Conservation", "key": "environment", "source": "default"},
        3: {"name": "Clean Energy", "key": "clean_energy", "source": "split_from_technology_energy"},
        4: {"name": "Society & Youth Movements", "key": "society", "source": "default"},
    }

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "day_1": {"main": 0, "minis": []},
        "day_2": {"main": null, "minis": []},
        "day_3": {"main": 1, "minis": []},
        "day_4": {"main": null, "minis": []},
        "unused": []
    }''')]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = group_stories_into_days(stories, blocklisted_ids=[], themes=custom_themes, client=mock_client)

    # Verify custom theme names appear in prompt
    call_args = mock_client.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "AI & Robotics" in prompt
    assert "Clean Energy" in prompt

    # Verify structure
    assert result["day_1"]["main"] == 0
    assert result["day_3"]["main"] == 1


def test_fallback_grouping_with_custom_themes():
    """_fallback_grouping works with custom themes."""
    from ftn_to_json import _fallback_grouping

    stories = [
        {"id": 0, "primary_theme": "ai_robotics", "story_strength": "high", "length": 800},
        {"id": 1, "primary_theme": "clean_energy", "story_strength": "medium", "length": 400},
        {"id": 2, "primary_theme": "environment", "story_strength": "high", "length": 600},
    ]

    custom_themes = {
        1: {"name": "AI & Robotics", "key": "ai_robotics", "source": "generated"},
        2: {"name": "Environment & Conservation", "key": "environment", "source": "default"},
        3: {"name": "Clean Energy", "key": "clean_energy", "source": "generated"},
        4: {"name": "Society & Youth Movements", "key": "society", "source": "default"},
    }

    result = _fallback_grouping(stories, blocklisted_ids=[], themes=custom_themes)

    # Verify all days exist
    assert "day_1" in result
    assert "day_2" in result
    assert "day_3" in result
    assert "day_4" in result

    # Story 0 (ai_robotics) should go to day_1
    assert result["day_1"]["main"] == 0, "Story 0 (ai_robotics) should be main story in day_1"

    # Story 2 (environment) should go to day_2
    assert result["day_2"]["main"] == 2, "Story 2 (environment) should be main story in day_2"

    # Story 1 (clean_energy) should go to day_3
    assert result["day_3"]["main"] == 1, "Story 1 (clean_energy) should be main story in day_3"

    # Day 4 (society) should have no stories assigned (no matching primary_theme)
    assert result["day_4"]["main"] is None, "Day 4 (society) should have no main story"
    assert result["day_4"]["minis"] == [], "Day 4 (society) should have no mini stories"


# Tests for split_multi_link_stories

def test_split_multi_link_stories_passes_through_single_url_stories():
    """Stories with 0-1 URLs pass through unchanged."""
    from ftn_to_json import split_multi_link_stories
    from parser import FTNStory

    stories = [
        FTNStory("Title one.", "Content one.", source_url="https://example.com/1", all_urls=["https://example.com/1"]),
        FTNStory("Title two.", "Content two.", source_url=None, all_urls=[]),
    ]

    client = Mock()  # Should not be called

    result = split_multi_link_stories(stories, client)

    assert len(result) == 2
    assert result[0].title == "Title one."
    assert result[1].title == "Title two."
    client.messages.create.assert_not_called()


def test_split_multi_link_stories_splits_multi_url_story():
    """Stories with 2+ URLs are sent to Claude and split."""
    from ftn_to_json import split_multi_link_stories
    from parser import FTNStory

    # Multi-URL story (2 URLs)
    multi_url_story = FTNStory(
        "Intro sentence.",
        "Topic A is great. Topic B is also great.",
        source_url="https://example.com/a",
        all_urls=["https://example.com/a", "https://example.com/b"]
    )

    # Mock Claude response with splits
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "splits": [
            {"content": "Topic A is great.", "primary_url": "https://example.com/a", "relationship": "standalone"},
            {"content": "Topic B is also great.", "primary_url": "https://example.com/b", "relationship": "standalone"}
        ],
        "reasoning": "Two distinct topics"
    }))]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    result = split_multi_link_stories([multi_url_story], client)

    # Should have 2 stories instead of 1
    assert len(result) == 2
    client.messages.create.assert_called_once()
    # Check split stories have correct content
    assert result[0].content == "Topic A is great."
    assert result[0].source_url == "https://example.com/a"
    assert result[1].content == "Topic B is also great."
    assert result[1].source_url == "https://example.com/b"


def test_split_multi_link_stories_mixed_list():
    """Mixed list: single-URL stories pass through, multi-URL stories split."""
    from ftn_to_json import split_multi_link_stories
    from parser import FTNStory

    # Single-URL story (should pass through)
    single_story = FTNStory(
        "Single topic.",
        "Just one thing here.",
        source_url="https://single.com",
        all_urls=["https://single.com"]
    )

    # Multi-URL story (should split into 2)
    multi_story = FTNStory(
        "Intro.",
        "First topic. Second topic.",
        source_url="https://multi.com/a",
        all_urls=["https://multi.com/a", "https://multi.com/b"]
    )

    # Mock Claude response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "splits": [
            {"content": "First topic.", "primary_url": "https://multi.com/a", "relationship": "standalone"},
            {"content": "Second topic.", "primary_url": "https://multi.com/b", "relationship": "standalone"}
        ],
        "reasoning": "Two topics"
    }))]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    result = split_multi_link_stories([single_story, multi_story], client)

    # Should have 3 stories: 1 passthrough + 2 splits
    assert len(result) == 3
    # First is unchanged passthrough
    assert result[0].title == "Single topic."
    assert result[0].content == "Just one thing here."
    # Second and third are splits
    assert result[1].source_url == "https://multi.com/a"
    assert result[2].source_url == "https://multi.com/b"
    # Only called once (for the multi-URL story)
    client.messages.create.assert_called_once()


# Phase 2 tests: Real FTN-322 data

# Test fixture: Story 0 from FTN-322 - two distinct topics in one paragraph
FTN_322_STORY_0_TITLE = "Humanity's fight against measles in three charts."
FTN_322_STORY_0_CONTENT = """A new report from the WHO reveals that annual measles deaths fell by 88% between 2000 and 2024, from 777,000 to 95,000 a year. Vaccinations have prevented an estimated 58 million deaths over this period, one of our species' greatest ever achievements. Routine immunisation, including a second-dose surge from 17% to 76%, has reshaped our collective immunity, particularly in Africa, yet there is still so much work to be done: 20.6 million children missed their first dose last year, driving outbreaks in 59 countries. Gavi Energy analysts say electricity demand in the United States is about to skyrocket. And they really do mean skyrocket — predicted to grow 25% by 2030, which would be the largest increase in electricity demand in US history. It's mostly being blamed on generative AI: data centres are already driving up electricity prices around the country."""
FTN_322_STORY_0_URLS = [
    'https://www.who.int/news/item/28-11-2025-measles-deaths-down-88--since-2000--but-cases-surge',
    'https://www.gavi.org/vaccineswork/winning-against-measles-five-charts-tell-remarkable-24-year-story',
    'https://www.icf.com/insights/energy/electricity-demand-expected-to-grow',
    'https://www.bloomberg.com/graphics/2025-ai-data-centers-electricity-prices/?sref=B9VwE2e5'
]


def test_split_prompt_identifies_distinct_topics_in_ftn322_story0():
    """Prompt correctly identifies that FTN-322 Story 0 contains two distinct topics."""
    from ftn_to_json import _split_single_story
    from parser import FTNStory

    story = FTNStory(
        FTN_322_STORY_0_TITLE,
        FTN_322_STORY_0_CONTENT,
        source_url=FTN_322_STORY_0_URLS[0],
        all_urls=FTN_322_STORY_0_URLS
    )

    # Use real API if available, otherwise skip
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    splits = _split_single_story(story, client)

    # Should identify at least 2 distinct topics
    assert len(splits) >= 2, f"Expected at least 2 splits, got {len(splits)}"

    # One split should be about measles/health
    split_contents = [s.get("content", "").lower() for s in splits]
    measles_split = any("measles" in c or "vaccination" in c for c in split_contents)
    assert measles_split, "Expected a split about measles/vaccination"

    # One split should be about electricity/AI
    electricity_split = any("electricity" in c or "data centre" in c or "data center" in c for c in split_contents)
    assert electricity_split, "Expected a split about electricity/AI"

    # Each split should have a URL from the provided list
    for split in splits:
        assert split.get("primary_url") in FTN_322_STORY_0_URLS, f"URL {split.get('primary_url')} not in original URLs"


# Test fixture: Story 8 from FTN-322 - ONE topic with two sources (should not split)
FTN_322_STORY_8_TITLE = "Centuries ago, a lot of people from Africa were taken as slaves to South America, and a lot of those people fled to the forests (for a fascinating history of this check out National Geographic's article on Brazilian quilimbos)."
FTN_322_STORY_8_CONTENT = """Today, many of their descendants live on what are now protected lands, and a new study shows that these places have also seen lower levels of deforestation and greater biodiversity conservation than protected areas that are free of people. It appears that humans can live in harmony with nature even if their ancestors haven't been in the same place for millennia, so… let's do it?"""
FTN_322_STORY_8_URLS = [
    'https://archive.is/C9ZbP',
    'https://news.mongabay.com/2025/11/afro-descendant-territories-slash-deforestation-lock-in-carbon-study-shows/'
]


def test_split_prompt_keeps_single_topic_together_ftn322_story8():
    """Prompt correctly identifies that FTN-322 Story 8 is ONE topic (should not split)."""
    from ftn_to_json import _split_single_story
    from parser import FTNStory

    story = FTNStory(
        FTN_322_STORY_8_TITLE,
        FTN_322_STORY_8_CONTENT,
        source_url=FTN_322_STORY_8_URLS[0],
        all_urls=FTN_322_STORY_8_URLS
    )

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    splits = _split_single_story(story, client)

    # This story is about ONE topic with two sources
    # It should either return 1 split, or if it returns 2, they should both be
    # about the same topic (descendants, protected lands, deforestation)
    if len(splits) == 1:
        # Good - recognized as single topic
        assert True
    else:
        # If split, both should be about the same core topic
        split_contents = [s.get("content", "").lower() for s in splits]
        # All splits should mention descendants, protected lands, or deforestation
        for content in split_contents:
            related_to_topic = any(term in content for term in [
                "descendant", "protected", "deforestation", "biodiversity", "forest", "slave"
            ])
            assert related_to_topic, f"Split '{content[:50]}...' doesn't seem related to the main topic"


# Phase 3 tests: Pipeline integration

def test_pipeline_expands_multi_link_stories():
    """Pipeline integration: split_multi_link_stories is called and expands story count."""
    from ftn_to_json import split_multi_link_stories
    from parser import FTNParser
    from pathlib import Path

    # Parse FTN-322 raw (without splitting)
    test_file = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'FTN-322.html'
    parser = FTNParser(str(test_file))
    raw_stories = parser.extract_stories()
    raw_count = len(raw_stories)

    # Count how many have 2+ URLs (candidates for splitting)
    multi_link_count = sum(1 for s in raw_stories if len(s.all_urls) >= 2)

    # Now run through splitter with mock that always splits multi-URL stories into 2
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "splits": [
            {"content": "First topic.", "primary_url": "https://example.com/a", "relationship": "standalone"},
            {"content": "Second topic.", "primary_url": "https://example.com/b", "relationship": "standalone"}
        ],
        "reasoning": "Split into two"
    }))]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    expanded_stories = split_multi_link_stories(raw_stories, client)

    # Should have more stories after splitting
    # Each multi-link story becomes 2, so: raw_count - multi_link_count + (multi_link_count * 2)
    expected_count = raw_count - multi_link_count + (multi_link_count * 2)
    assert len(expanded_stories) == expected_count
    assert len(expanded_stories) > raw_count


# Phase 4 tests: Error handling and fallbacks

def test_split_multi_link_stories_keeps_original_on_api_failure():
    """When API call fails, keep the original story instead of crashing."""
    from ftn_to_json import split_multi_link_stories
    from parser import FTNStory

    multi_url_story = FTNStory(
        "Title.",
        "Content about multiple topics.",
        source_url="https://example.com/a",
        all_urls=["https://example.com/a", "https://example.com/b"]
    )

    # Mock client that raises an exception
    client = MagicMock()
    client.messages.create.side_effect = Exception("API error")

    result = split_multi_link_stories([multi_url_story], client)

    # Should return original story, not crash
    assert len(result) == 1
    assert result[0].title == "Title."
    assert result[0].source_url == "https://example.com/a"


def test_split_multi_link_stories_keeps_original_on_invalid_json():
    """When API returns invalid JSON after retry, keep original story."""
    from ftn_to_json import split_multi_link_stories
    from parser import FTNStory

    multi_url_story = FTNStory(
        "Title.",
        "Content about multiple topics.",
        source_url="https://example.com/a",
        all_urls=["https://example.com/a", "https://example.com/b"]
    )

    # Mock client that returns invalid JSON both times
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json at all")]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    result = split_multi_link_stories([multi_url_story], client)

    # Should return original story after JSON parse fails
    assert len(result) == 1
    assert result[0].title == "Title."


def test_split_multi_link_stories_filters_empty_splits():
    """Splits with empty content should be filtered out."""
    from ftn_to_json import split_multi_link_stories
    from parser import FTNStory

    multi_url_story = FTNStory(
        "Title.",
        "Content about multiple topics.",
        source_url="https://example.com/a",
        all_urls=["https://example.com/a", "https://example.com/b"]
    )

    # Mock response where one split has empty content
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "splits": [
            {"content": "Valid content here.", "primary_url": "https://example.com/a", "relationship": "standalone"},
            {"content": "", "primary_url": "https://example.com/b", "relationship": "standalone"}  # Empty
        ],
        "reasoning": "Split"
    }))]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    result = split_multi_link_stories([multi_url_story], client)

    # Should only have the non-empty split
    assert len(result) == 1
    assert result[0].content == "Valid content here."


# Phase 1 tests: Theme analysis (dynamic theme suggestions)


def test_analyze_themes_healthy_returns_defaults():
    """analyze_themes returns default themes when all are healthy."""
    # Create stories with healthy distribution (2-6 per theme, at least 1 high)
    stories = [
        {"id": 1, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Health Story 1"},
        {"id": 2, "primary_theme": "health_education", "story_strength": "medium", "tui_headline": "Health Story 2"},
        {"id": 3, "primary_theme": "environment", "story_strength": "high", "tui_headline": "Environment Story 1"},
        {"id": 4, "primary_theme": "environment", "story_strength": "medium", "tui_headline": "Environment Story 2"},
        {"id": 5, "primary_theme": "technology_energy", "story_strength": "high", "tui_headline": "Tech Story 1"},
        {"id": 6, "primary_theme": "technology_energy", "story_strength": "low", "tui_headline": "Tech Story 2"},
        {"id": 7, "primary_theme": "society", "story_strength": "high", "tui_headline": "Society Story 1"},
        {"id": 8, "primary_theme": "society", "story_strength": "medium", "tui_headline": "Society Story 2"},
    ]

    # Mock client - should NOT be called for healthy themes
    mock_client = MagicMock()

    result = analyze_themes(stories, mock_client)

    # Should return defaults without calling API
    mock_client.messages.create.assert_not_called()
    assert result["proposed_themes"][1]["source"] == "default"
    assert result["proposed_themes"][1]["name"] == "Health & Education"
    assert result["theme_health"][1]["status"] == "healthy"
    assert "healthy" in result["reasoning"].lower()


def test_analyze_themes_detects_weak_themes():
    """analyze_themes detects weak themes (< 2 stories or no high-strength)."""
    # Create stories with one weak theme (society has only 1 story)
    stories = [
        {"id": 1, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Health 1"},
        {"id": 2, "primary_theme": "health_education", "story_strength": "medium", "tui_headline": "Health 2"},
        {"id": 3, "primary_theme": "environment", "story_strength": "high", "tui_headline": "Env 1"},
        {"id": 4, "primary_theme": "environment", "story_strength": "medium", "tui_headline": "Env 2"},
        {"id": 5, "primary_theme": "technology_energy", "story_strength": "high", "tui_headline": "Tech 1"},
        {"id": 6, "primary_theme": "technology_energy", "story_strength": "low", "tui_headline": "Tech 2"},
        {"id": 7, "primary_theme": "society", "story_strength": "medium", "tui_headline": "Society 1"},  # Only 1, no high
    ]

    # Mock LLM response for theme proposal
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "proposed_themes": {
            "1": {"name": "Health & Education", "key": "health_education", "source": "default"},
            "2": {"name": "Environment & Conservation", "key": "environment", "source": "default"},
            "3": {"name": "Technology & Energy", "key": "technology_energy", "source": "default"},
            "4": {"name": "Youth Leadership", "key": "youth_leadership", "source": "generated"}
        },
        "reasoning": "Society theme was weak, replaced with Youth Leadership based on story clusters."
    }''')]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = analyze_themes(stories, mock_client)

    # Should call API for theme proposals
    mock_client.messages.create.assert_called_once()
    assert result["theme_health"][4]["status"] == "weak"
    assert result["proposed_themes"][4]["source"] == "generated"


def test_analyze_themes_integration():
    """Integration test for analyze_themes with real API."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    # Stories with intentionally weak society theme
    stories = [
        {"id": 1, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Medical breakthrough", "secondary_themes": ["science"]},
        {"id": 2, "primary_theme": "health_education", "story_strength": "medium", "tui_headline": "School program", "secondary_themes": ["education"]},
        {"id": 3, "primary_theme": "environment", "story_strength": "high", "tui_headline": "Ocean cleanup", "secondary_themes": ["conservation"]},
        {"id": 4, "primary_theme": "environment", "story_strength": "medium", "tui_headline": "Forest growth", "secondary_themes": ["nature"]},
        {"id": 5, "primary_theme": "technology_energy", "story_strength": "high", "tui_headline": "Solar power", "secondary_themes": ["renewable"]},
        {"id": 6, "primary_theme": "technology_energy", "story_strength": "medium", "tui_headline": "AI helps", "secondary_themes": ["ai"]},
        {"id": 7, "primary_theme": "society", "story_strength": "low", "tui_headline": "Community event", "secondary_themes": ["local"]},
    ]

    result = analyze_themes(stories, client)

    # Verify structure
    assert "proposed_themes" in result
    assert "theme_health" in result
    assert "reasoning" in result
    assert len(result["proposed_themes"]) == 4

    # Society should be marked weak
    assert result["theme_health"][4]["status"] == "weak"


def test_analyze_themes_detects_overloaded_themes():
    """analyze_themes detects overloaded themes (> 6 stories with 2+ high-strength)."""
    # Create stories with one overloaded theme (health_education has 7 stories with 3 high-strength)
    stories = [
        {"id": 1, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Health 1"},
        {"id": 2, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Health 2"},
        {"id": 3, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Health 3"},
        {"id": 4, "primary_theme": "health_education", "story_strength": "medium", "tui_headline": "Health 4"},
        {"id": 5, "primary_theme": "health_education", "story_strength": "medium", "tui_headline": "Health 5"},
        {"id": 6, "primary_theme": "health_education", "story_strength": "low", "tui_headline": "Health 6"},
        {"id": 7, "primary_theme": "health_education", "story_strength": "low", "tui_headline": "Health 7"},
        {"id": 8, "primary_theme": "environment", "story_strength": "high", "tui_headline": "Env 1"},
        {"id": 9, "primary_theme": "environment", "story_strength": "medium", "tui_headline": "Env 2"},
        {"id": 10, "primary_theme": "technology_energy", "story_strength": "high", "tui_headline": "Tech 1"},
        {"id": 11, "primary_theme": "technology_energy", "story_strength": "medium", "tui_headline": "Tech 2"},
        {"id": 12, "primary_theme": "society", "story_strength": "high", "tui_headline": "Society 1"},
        {"id": 13, "primary_theme": "society", "story_strength": "medium", "tui_headline": "Society 2"},
    ]

    # Mock LLM response for theme split proposal
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "proposed_themes": {
            "1": {"name": "Health & Education", "key": "health_education", "source": "default"},
            "2": {"name": "Environment & Conservation", "key": "environment", "source": "default"},
            "3": {"name": "Technology & Energy", "key": "technology_energy", "source": "default"},
            "4": {"name": "Health Policy", "key": "health_policy", "source": "split_from_health_education"}
        },
        "reasoning": "Health theme was overloaded with 7 stories and 3 high-strength. Split into Health & Education and Health Policy."
    }''')]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = analyze_themes(stories, mock_client)

    # Should call API for theme split proposal
    mock_client.messages.create.assert_called_once()
    assert result["theme_health"][1]["status"] == "overloaded"
    assert result["theme_health"][1]["story_count"] == 7
    assert result["theme_health"][1]["high_strength_count"] == 3
