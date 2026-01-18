"""Tests for ftn_to_json module."""
import json
import os
import pytest
from unittest.mock import Mock, MagicMock


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
    from ftn_to_json import group_stories_into_days

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    # Create mock analyzed stories
    stories = [
        {"id": 0, "headline": "Solar farms expand", "primary_theme": "technology_energy", "secondary_themes": ["africa"], "story_strength": "high", "length": 800},
        {"id": 1, "headline": "New literacy program", "primary_theme": "health_education", "secondary_themes": ["youth"], "story_strength": "medium", "length": 400},
        {"id": 2, "headline": "Ocean cleanup success", "primary_theme": "environment", "secondary_themes": ["technology"], "story_strength": "high", "length": 600},
        {"id": 3, "headline": "Youth voting rights", "primary_theme": "society", "secondary_themes": ["democracy"], "story_strength": "medium", "length": 350},
    ]

    result = group_stories_into_days(stories, blocklisted_ids=[], client=client)

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
