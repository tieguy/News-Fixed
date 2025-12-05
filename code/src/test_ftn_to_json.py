"""Tests for ftn_to_json module."""
import json
import pytest


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
