# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Tests for tomorrow teaser generation with specific story content."""

import pytest
from unittest.mock import patch, MagicMock


class TestGenerateTeaser:
    """Tests for ContentGenerator.generate_teaser with story-specific content."""

    def test_generate_teaser_accepts_story_titles(self):
        """generate_teaser should accept main_title and secondary_title parameters."""
        from generator import ContentGenerator

        with patch.object(ContentGenerator, '__init__', lambda self, **kwargs: None):
            generator = ContentGenerator()
            generator.client = MagicMock()
            generator.model = "test-model"
            generator.prompts_dir = MagicMock()

            # Mock _load_prompt to return a template with story placeholders
            generator._load_prompt = MagicMock(return_value="""
TOMORROW'S THEME: {tomorrow_theme}
MAIN STORY: {main_title}
SECONDARY STORY: {secondary_title}
""")

            # Mock _call_claude to return a teaser
            generator._call_claude = MagicMock(return_value="Tomorrow: Sea otters save kelp, plus solar breakthrough.")

            # Call with new signature - this should work
            teaser = generator.generate_teaser(
                tomorrow_theme="Environment & Conservation",
                main_title="Sea Otters Become Unlikely Ecosystem Heroes",
                secondary_title="Solar Panel Recycling Gets Major Boost"
            )

            # Verify the prompt was formatted with story titles
            prompt_arg = generator._call_claude.call_args[0][0]
            assert "Sea Otters Become Unlikely Ecosystem Heroes" in prompt_arg
            assert "Solar Panel Recycling Gets Major Boost" in prompt_arg
            assert teaser == "Tomorrow: Sea otters save kelp, plus solar breakthrough."

    def test_generate_teaser_backward_compatible_theme_only(self):
        """generate_teaser should still work with just tomorrow_theme for backward compatibility."""
        from generator import ContentGenerator

        with patch.object(ContentGenerator, '__init__', lambda self, **kwargs: None):
            generator = ContentGenerator()
            generator.client = MagicMock()
            generator.model = "test-model"
            generator.prompts_dir = MagicMock()

            # Mock _load_prompt with template including all placeholders
            generator._load_prompt = MagicMock(return_value="""
TOMORROW'S THEME: {tomorrow_theme}
MAIN STORY: {main_title}
SECONDARY STORY: {secondary_title}
""")
            generator._call_claude = MagicMock(return_value="Tomorrow: Environment stories await!")

            # Call with just theme (backward compatible)
            teaser = generator.generate_teaser(tomorrow_theme="Environment & Conservation")

            # Verify placeholder defaults were used
            prompt_arg = generator._call_claude.call_args[0][0]
            assert "(not specified)" in prompt_arg
            assert teaser == "Tomorrow: Environment stories await!"


class TestGenerateTeasersForCuratedData:
    """Tests for generate_teasers_for_curated_data function."""

    def test_generates_teasers_for_days_1_through_3(self):
        """Should generate teasers for days 1-3 using tomorrow's story titles."""
        from curator import generate_teasers_for_curated_data

        # Sample curated data with 4 days
        curated_data = {
            "day_1": {
                "theme": "Health & Education",
                "main_story": {"title": "Day 1 Main", "tui_headline": "Day 1 Headline"},
                "front_page_stories": [],
                "mini_articles": [],
                "tomorrow_teaser": ""
            },
            "day_2": {
                "theme": "Environment & Conservation",
                "main_story": {"title": "Sea Otters Save Kelp Forests", "tui_headline": "Sea Otters Save Kelp"},
                "front_page_stories": [{"title": "Solar Recycling Breakthrough"}],
                "mini_articles": [],
                "tomorrow_teaser": ""
            },
            "day_3": {
                "theme": "Technology & Energy",
                "main_story": {"title": "New Battery Tech", "tui_headline": "Battery Revolution"},
                "front_page_stories": [],
                "mini_articles": [{"title": "AI Helps Farmers"}],
                "tomorrow_teaser": ""
            },
            "day_4": {
                "theme": "Society & Youth Movements",
                "main_story": {"title": "Youth Climate March", "tui_headline": "Youth March"},
                "front_page_stories": [{"title": "Community Gardens Bloom"}],
                "mini_articles": [],
                "tomorrow_teaser": ""
            }
        }

        # Mock the generator
        with patch('curator.ContentGenerator') as MockGenerator:
            mock_gen = MagicMock()
            mock_gen.generate_teaser.return_value = "Generated teaser text"
            MockGenerator.return_value = mock_gen

            result = generate_teasers_for_curated_data(curated_data)

            # Days 1-3 should have teasers
            assert result["day_1"]["tomorrow_teaser"] == "Generated teaser text"
            assert result["day_2"]["tomorrow_teaser"] == "Generated teaser text"
            assert result["day_3"]["tomorrow_teaser"] == "Generated teaser text"

            # Day 4 should NOT have a teaser (no tomorrow)
            assert result["day_4"]["tomorrow_teaser"] == ""

            # Verify generator was called with correct story titles
            calls = mock_gen.generate_teaser.call_args_list
            assert len(calls) == 3

            # Day 1's teaser uses Day 2's stories
            assert calls[0].kwargs["main_title"] == "Sea Otters Save Kelp"
            assert calls[0].kwargs["secondary_title"] == "Solar Recycling Breakthrough"

    def test_skips_day_when_tomorrow_has_no_main_story(self):
        """Should skip teaser generation if tomorrow has no main story."""
        from curator import generate_teasers_for_curated_data

        curated_data = {
            "day_1": {
                "theme": "Health & Education",
                "main_story": {"title": "Day 1 Main"},
                "front_page_stories": [],
                "mini_articles": [],
                "tomorrow_teaser": ""
            },
            "day_2": {
                "theme": "Environment",
                "main_story": {},  # No main story
                "front_page_stories": [],
                "mini_articles": [],
                "tomorrow_teaser": ""
            }
        }

        with patch('curator.ContentGenerator') as MockGenerator:
            mock_gen = MagicMock()
            MockGenerator.return_value = mock_gen

            result = generate_teasers_for_curated_data(curated_data)

            # Day 1 should NOT get a teaser since Day 2 has no main story
            assert result["day_1"]["tomorrow_teaser"] == ""
            mock_gen.generate_teaser.assert_not_called()
