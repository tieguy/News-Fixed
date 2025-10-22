"""Fix The News content fetcher and parser."""

import re
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote


class FTNParser:
    """Parser for Fix The News HTML content."""

    def __init__(self, html_file: str):
        """
        Initialize parser with HTML file.

        Args:
            html_file: Path to the FTN HTML file
        """
        self.html_file = Path(html_file)
        with open(self.html_file, 'r', encoding='utf-8') as f:
            self.soup = BeautifulSoup(f.read(), 'html.parser')

    def extract_links(self) -> List[str]:
        """Extract all links from the HTML."""
        links = []
        for a_tag in self.soup.find_all('a', href=True):
            href = a_tag['href']
            # Clean up Substack CDN image links and get actual URLs
            if 'tinyurl.com' in href or not href.startswith('https://substackcdn'):
                if not href.startswith('mailto:'):
                    links.append(href)
        return links

    def get_text_content(self) -> str:
        """Get all text content from the HTML."""
        # Remove script and style elements
        for script in self.soup(["script", "style"]):
            script.decompose()

        text = self.soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    def extract_stories(self) -> List[Dict[str, str]]:
        """
        Extract stories from FTN content.

        Returns:
            List of story dicts with 'content' and 'source_url'
        """
        text = self.get_text_content()
        links = self.extract_links()

        # Split by story markers (sentences starting with *)
        # This is a rough heuristic - stories often start with bold text
        stories = []

        # Find paragraphs that look like stories
        # Pattern: Look for substantial paragraphs with URLs nearby
        paragraphs = text.split('\n\n')

        current_story = []
        current_links = []

        for i, para in enumerate(paragraphs):
            para = para.strip()

            # Skip empty or very short paragraphs
            if not para or len(para) < 50:
                continue

            # Skip navigation/UI elements
            if any(skip in para.lower() for skip in [
                'close reader view', 'text and layout', 'theme', 'read aloud',
                'reset defaults', 'font', 'alignment'
            ]):
                continue

            # A story typically has multiple sentences
            sentences = para.split('.')
            if len(sentences) >= 2:
                # Check if this looks like a story opening (starts with *)
                if para.startswith('*') or para.startswith('•'):
                    # Save previous story if exists
                    if current_story:
                        stories.append({
                            'content': ' '.join(current_story),
                            'potential_links': current_links
                        })
                        current_story = []
                        current_links = []

                # Add to current story
                current_story.append(para)

        # Add last story
        if current_story:
            stories.append({
                'content': ' '.join(current_story),
                'potential_links': current_links
            })

        # Match stories with links
        # For MVP, we'll extract links from the text manually
        all_links = self.extract_links()

        for story in stories:
            # Try to find a link mentioned in the story
            story['source_url'] = self._find_best_link(story['content'], all_links)

        return stories

    def _find_best_link(self, content: str, all_links: List[str]) -> str:
        """
        Find the most relevant link for a story.

        Args:
            content: Story content
            all_links: All available links

        Returns:
            Best matching URL or a placeholder
        """
        # For now, return first non-FTN, non-tinyurl link
        # In future, we could use fuzzy matching or AI to find the right link
        for link in all_links:
            if 'fixthenews.com' not in link and 'substackcdn' not in link:
                return link

        return "https://example.com/source"

    def extract_manual_stories(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Manual extraction helper - prints text for human review.

        This is a temporary function for the MVP - we can extract stories
        manually and create a JSON file.

        Returns:
            Empty dict (use this function for debugging/manual extraction)
        """
        text = self.get_text_content()

        # Find the main content area (after UI cruft)
        start_markers = ['World Bank', 'Electricity access', 'students']
        for marker in start_markers:
            if marker in text:
                idx = text.find(marker)
                text = text[max(0, idx-100):]
                break

        print("=" * 80)
        print("FTN CONTENT PREVIEW")
        print("=" * 80)
        print(text[:3000])
        print("\n" + "=" * 80)
        print("ALL LINKS")
        print("=" * 80)
        links = self.extract_links()
        for i, link in enumerate(links[:30], 1):
            print(f"{i}. {link}")

        return {}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.fetcher <html_file>")
        sys.exit(1)

    parser = FTNParser(sys.argv[1])

    print("Extracting stories from FTN HTML...\n")

    # For MVP, let's just print what we find for manual review
    parser.extract_manual_stories()
