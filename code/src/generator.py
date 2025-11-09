"""Claude API integration for content generation."""

import os
import json
from pathlib import Path
from typing import Dict, List
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ContentGenerator:
    """Generates newspaper content using Claude API."""

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-5-20250929"):
        """
        Initialize the content generator.

        Args:
            api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or provided")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"

    def _load_prompt(self, prompt_name: str) -> str:
        """Load a prompt template from the prompts directory."""
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        with open(prompt_path, 'r') as f:
            return f.read()

    def _call_claude(self, prompt: str, max_tokens: int = 2000) -> str:
        """Make a call to Claude API."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text

    def generate_headline(self, story_content: str) -> str:
        """
        Generate a headline for a story.

        Args:
            story_content: The story text

        Returns:
            Headline text
        """
        template = self._load_prompt("headline")
        prompt = template.format(story_content=story_content)
        return self._call_claude(prompt, max_tokens=100).strip()

    def generate_main_story(
        self,
        original_content: str,
        source_url: str,
        theme: str,
        original_title: str = ""
    ) -> Dict[str, str]:
        """
        Generate main story content (400-500 words).

        Args:
            original_content: Original news story text
            source_url: Source URL
            theme: Today's theme
            original_title: Original story title (first sentence)

        Returns:
            Dict with 'title' and 'content' keys
        """
        # Combine title and content for full context
        full_text = f"{original_title} {original_content}".strip() if original_title else original_content

        template = self._load_prompt("main_story")
        prompt = template.format(
            original_content=full_text,
            source_url=source_url,
            theme=theme
        )

        content = self._call_claude(prompt, max_tokens=1500)
        title = self.generate_headline(content)

        return {
            "title": title,
            "content": content
        }

    def generate_mini_article(
        self,
        original_content: str,
        source_url: str,
        original_title: str = ""
    ) -> Dict[str, str]:
        """
        Generate a mini article (100-150 words).

        Args:
            original_content: Original news story text
            source_url: Source URL
            original_title: Original story title (first sentence)

        Returns:
            Dict with 'title' and 'content' keys
        """
        # Combine title and content for full context
        full_text = f"{original_title} {original_content}".strip() if original_title else original_content

        template = self._load_prompt("mini_article")
        prompt = template.format(
            original_content=full_text,
            source_url=source_url
        )

        content = self._call_claude(prompt, max_tokens=500)
        title = self.generate_headline(content)

        return {
            "title": title,
            "content": content
        }

    def generate_statistics(
        self,
        stories_summary: str,
        theme: str
    ) -> List[Dict[str, str]]:
        """
        Generate "By The Numbers" statistics.

        Args:
            stories_summary: Summary of all today's stories
            theme: Today's theme

        Returns:
            List of stat dicts with 'number' and 'description' keys
        """
        template = self._load_prompt("statistics")
        prompt = template.format(
            stories_summary=stories_summary,
            theme=theme
        )

        response = self._call_claude(prompt, max_tokens=500)

        # Parse JSON response
        try:
            # Extract JSON from response (might have extra text)
            start = response.find('[')
            end = response.rfind(']') + 1
            json_str = response[start:end]
            stats = json.loads(json_str)
            return stats
        except json.JSONDecodeError as e:
            print(f"Error parsing statistics JSON: {e}")
            # Return dummy stats as fallback
            return [
                {"number": "N/A", "description": "Data processing error"}
                for _ in range(6)
            ]

    def generate_teaser(self, tomorrow_theme: str) -> str:
        """
        Generate tomorrow teaser text.

        Args:
            tomorrow_theme: Tomorrow's theme name

        Returns:
            Teaser text
        """
        template = self._load_prompt("teaser")
        prompt = template.format(tomorrow_theme=tomorrow_theme)
        return self._call_claude(prompt, max_tokens=150).strip()


if __name__ == "__main__":
    # Test the generator
    print("Testing ContentGenerator...")

    try:
        generator = ContentGenerator()

        # Test headline generation
        print("\n1. Testing headline generation...")
        test_story = "Scientists have discovered a new way to clean ocean plastic using naturally occurring bacteria. This breakthrough could help remove millions of tons of plastic from our oceans."
        headline = generator.generate_headline(test_story)
        print(f"   Headline: {headline}")

        # Test teaser generation
        print("\n2. Testing teaser generation...")
        teaser = generator.generate_teaser("Environment & Conservation")
        print(f"   Teaser: {teaser}")

        print("\n✓ Generator tests passed!")

    except ValueError as e:
        print(f"\n✗ Error: {e}")
        print("   Make sure to set ANTHROPIC_API_KEY in your .env file")
