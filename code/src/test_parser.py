"""Tests for parser module."""
import tempfile
from pathlib import Path


def test_ftnstory_has_all_urls_field():
    """FTNStory stores all_urls as a list."""
    from parser import FTNStory

    story = FTNStory(
        title="Test title",
        content="Test content",
        source_url="https://example.com",
        all_urls=["https://example.com", "https://other.com"]
    )

    assert story.all_urls == ["https://example.com", "https://other.com"]


def test_ftnstory_all_urls_defaults_to_empty():
    """FTNStory.all_urls defaults to empty list."""
    from parser import FTNStory

    story = FTNStory(title="Test", content="Content")

    assert story.all_urls == []
