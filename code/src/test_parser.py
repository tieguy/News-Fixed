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


def test_create_story_from_reader_populates_all_urls():
    """_create_story_from_reader stores all URLs in all_urls field."""
    from parser import FTNParser

    # Create minimal HTML with multiple URLs in a story
    html_content = '''
    <html>
    <body>
    <div class="moz-reader-content">
        <p><strong>Solar panels are transforming energy.</strong>
        A new <a href="https://nature.com/study">study</a> shows
        <a href="https://gov.uk/report">government data</a> supports this.
        </p>
    </div>
    </body>
    </html>
    '''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        f.flush()

        parser = FTNParser(f.name)
        stories = parser.extract_stories()

        assert len(stories) == 1
        assert len(stories[0].all_urls) == 2
        assert "https://nature.com/study" in stories[0].all_urls
        assert "https://gov.uk/report" in stories[0].all_urls
