# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Tests for ContentGenerator.generate_second_main_story() method."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestGenerateSecondMainStory:
    """Tests for ContentGenerator.generate_second_main_story method."""

    def test_loads_correct_prompt_template(self):
        """Should load the second_main_story.txt prompt template."""
        from generator import ContentGenerator

        with patch.object(ContentGenerator, '__init__', lambda self, **kwargs: None):
            generator = ContentGenerator()
            generator.client = MagicMock()
            generator.model = "test-model"
            generator.prompts_dir = Path("/fake/prompts")

            # Mock _load_prompt to track which template is requested
            generator._load_prompt = MagicMock(return_value="Template: {original_content}\n{source_url}\n{theme}")
            generator._call_claude = MagicMock(return_value="Generated content for second story")
            generator.generate_headline = MagicMock(return_value="Generated Headline")

            # Call generate_second_main_story
            result = generator.generate_second_main_story(
                original_content="Test story content",
                source_url="https://example.com/story",
                theme="Health & Education",
                original_title="Original Title"
            )

            # Verify _load_prompt was called with "second_main_story"
            generator._load_prompt.assert_called_once_with("second_main_story")

    def test_calls_claude_with_max_tokens_500(self):
        """Should call Claude with max_tokens=500 for second main story."""
        from generator import ContentGenerator

        with patch.object(ContentGenerator, '__init__', lambda self, **kwargs: None):
            generator = ContentGenerator()
            generator.client = MagicMock()
            generator.model = "test-model"
            generator.prompts_dir = Path("/fake/prompts")

            # Mock methods
            generator._load_prompt = MagicMock(return_value="Template: {original_content}\n{source_url}\n{theme}")
            generator._call_claude = MagicMock(return_value="Generated content")
            generator.generate_headline = MagicMock(return_value="Generated Headline")

            # Call generate_second_main_story
            result = generator.generate_second_main_story(
                original_content="Test story content",
                source_url="https://example.com/story",
                theme="Health & Education"
            )

            # Verify _call_claude was called with max_tokens=500
            # It's called once for the story content generation
            generator._call_claude.assert_called_once()
            call_args = generator._call_claude.call_args
            assert call_args[1]['max_tokens'] == 500

    def test_returns_dict_with_title_and_content_keys(self):
        """Should return a dict with 'title' and 'content' keys."""
        from generator import ContentGenerator

        with patch.object(ContentGenerator, '__init__', lambda self, **kwargs: None):
            generator = ContentGenerator()
            generator.client = MagicMock()
            generator.model = "test-model"
            generator.prompts_dir = Path("/fake/prompts")

            # Mock methods
            generator._load_prompt = MagicMock(return_value="Template: {original_content}\n{source_url}\n{theme}")
            generator._call_claude = MagicMock(return_value="Generated story content")
            generator.generate_headline = MagicMock(return_value="Great News About Science")

            # Call generate_second_main_story
            result = generator.generate_second_main_story(
                original_content="Test story content",
                source_url="https://example.com/story",
                theme="Technology & Energy"
            )

            # Verify result structure
            assert isinstance(result, dict)
            assert 'title' in result
            assert 'content' in result
            assert result['title'] == "Great News About Science"
            assert result['content'] == "Generated story content"

    def test_formats_prompt_with_full_text_and_url_and_theme(self):
        """Should format prompt with original_title + content, source_url, and theme."""
        from generator import ContentGenerator

        with patch.object(ContentGenerator, '__init__', lambda self, **kwargs: None):
            generator = ContentGenerator()
            generator.client = MagicMock()
            generator.model = "test-model"
            generator.prompts_dir = Path("/fake/prompts")

            # Mock _load_prompt to return a template
            template = "Original: {original_content}\nURL: {source_url}\nTheme: {theme}"
            generator._load_prompt = MagicMock(return_value=template)
            generator._call_claude = MagicMock(return_value="Generated content")
            generator.generate_headline = MagicMock(return_value="Headline")

            # Call with title and content
            result = generator.generate_second_main_story(
                original_content="The story body",
                source_url="https://fixthe.news/story",
                theme="Environment & Conservation",
                original_title="First Sentence"
            )

            # Verify the prompt was formatted correctly
            call_args = generator._call_claude.call_args_list[0]
            prompt = call_args[0][0]
            assert "First Sentence The story body" in prompt
            assert "https://fixthe.news/story" in prompt
            assert "Environment & Conservation" in prompt

    def test_handles_missing_original_title(self):
        """Should handle case where original_title is not provided."""
        from generator import ContentGenerator

        with patch.object(ContentGenerator, '__init__', lambda self, **kwargs: None):
            generator = ContentGenerator()
            generator.client = MagicMock()
            generator.model = "test-model"
            generator.prompts_dir = Path("/fake/prompts")

            template = "Content: {original_content}\nURL: {source_url}\nTheme: {theme}"
            generator._load_prompt = MagicMock(return_value=template)
            generator._call_claude = MagicMock(return_value="Generated content")
            generator.generate_headline = MagicMock(return_value="Headline")

            # Call without title
            result = generator.generate_second_main_story(
                original_content="The story body",
                source_url="https://fixthe.news/story",
                theme="Society & Youth Movements"
            )

            # Verify only content is used (no title prefix)
            call_args = generator._call_claude.call_args_list[0]
            prompt = call_args[0][0]
            assert "The story body" in prompt
            # Should not have double spaces or empty title prefix
            assert prompt.count("  ") == 0 or "Content: The story body" in prompt

    def test_calls_generate_headline_for_title(self):
        """Should call generate_headline to create the title from generated content."""
        from generator import ContentGenerator

        with patch.object(ContentGenerator, '__init__', lambda self, **kwargs: None):
            generator = ContentGenerator()
            generator.client = MagicMock()
            generator.model = "test-model"
            generator.prompts_dir = Path("/fake/prompts")

            generator._load_prompt = MagicMock(return_value="Template: {original_content}\n{source_url}\n{theme}")
            generator._call_claude = MagicMock(return_value="Generated story content")
            generator.generate_headline = MagicMock(return_value="Generated Headline")

            # Call generate_second_main_story
            result = generator.generate_second_main_story(
                original_content="Test content",
                source_url="https://example.com",
                theme="Health & Education"
            )

            # Verify generate_headline was called with the generated content
            generator.generate_headline.assert_called_once_with("Generated story content")
            assert result['title'] == "Generated Headline"
