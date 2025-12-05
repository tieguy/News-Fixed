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
