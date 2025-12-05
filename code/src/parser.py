# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Parse Fix The News HTML content into structured stories."""

import re
from pathlib import Path
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Constants
FTN_DOMAIN = 'fixthenews.com'


class FTNStory:
    """Represents a single story from Fix The News."""

    def __init__(self, title: str, content: str, source_url: Optional[str] = None,
                 tui_headline: Optional[str] = None, all_urls: Optional[List[str]] = None):
        self.title = title.strip()
        self.content = content.strip()
        self.source_url = source_url
        self.tui_headline = tui_headline  # 40-50 char headline for TUI display
        self.all_urls = all_urls if all_urls is not None else []

    def __repr__(self):
        return f"FTNStory(title='{self.title[:50]}...', url={self.source_url})"


class FTNParser:
    """Parser for Fix The News HTML content."""

    def __init__(self, html_file: str):
        """
        Initialize parser with HTML file.

        Args:
            html_file: Path to FTN HTML file
        """
        self.html_file = Path(html_file)
        with open(self.html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.soup = BeautifulSoup(content, 'html.parser')
            # Also keep raw text for pattern matching
            self.text = self.soup.get_text()

    def extract_all_urls(self) -> List[str]:
        """Extract all URLs from the HTML."""
        urls = []

        # Find URLs in angle brackets in text (common in FTN)
        url_pattern = r'<(https?://[^>]+)>'
        urls.extend(re.findall(url_pattern, self.text))

        # Also get from href attributes
        for link in self.soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http') and 'substackcdn' not in href and FTN_DOMAIN not in href:
                urls.append(href)

        return list(dict.fromkeys(urls))  # Remove duplicates, preserve order

    def _should_skip_paragraph(self, text: str) -> bool:
        """Check if paragraph should be skipped (footer/subscription content)."""
        if not text:
            return True
        skip_phrases = [
            "you're reading the free version",
            "if someone forwarded this",
            "institutional subscriptions",
            "get in touch",
            "profit-driven organisations"
        ]
        return any(skip in text.lower() for skip in skip_phrases)

    def _extract_urls_from_paragraph(self, para) -> List[str]:
        """Extract valid URLs from a paragraph."""
        urls = []
        for link in para.find_all('a', href=True):
            href = link['href']
            if href.startswith('http') and 'substackcdn' not in href:
                urls.append(href)
        return urls

    def _save_current_story(
        self,
        stories: List[FTNStory],
        story_text: List[str],
        story_urls: List[str]
    ) -> None:
        """Save current story if it has content."""
        if story_text:
            story = self._create_story_from_reader(story_text, story_urls)
            if story:
                stories.append(story)

    def extract_stories(self) -> List[FTNStory]:
        """
        Extract stories from FTN content (now works with reader mode HTML).

        Returns:
            List of FTNStory objects
        """
        stories = []

        # Find the main content div in reader mode HTML
        content_div = self.soup.find('div', class_='moz-reader-content')
        if not content_div:
            # Fallback to old text-based parsing
            return self._extract_stories_from_text()

        # Get all paragraphs
        paragraphs = content_div.find_all('p')

        current_story_text = []
        current_urls = []

        for para in paragraphs:
            text = para.get_text().strip()

            if self._should_skip_paragraph(text):
                continue

            # Check if this paragraph starts a story (has bold/strong tag)
            strong_tag = para.find(['strong', 'b'])

            if strong_tag:
                # Save previous story if exists
                self._save_current_story(stories, current_story_text, current_urls)

                # Start new story
                current_story_text = [text]
                current_urls = self._extract_urls_from_paragraph(para)

            elif current_story_text:
                # Continue current story
                current_story_text.append(text)
                current_urls.extend(self._extract_urls_from_paragraph(para))

        # Add last story
        self._save_current_story(stories, current_story_text, current_urls)

        return stories

    def _should_save_story(self, story_lines: List[str]) -> bool:
        """Check if accumulated story lines are long enough to save."""
        return len(story_lines) > 0 and len(' '.join(story_lines)) > 100

    def _save_story_if_valid(
        self,
        stories: List[FTNStory],
        story_lines: List[str],
        urls: List[str]
    ) -> None:
        """Save story if it meets minimum requirements."""
        if self._should_save_story(story_lines):
            story = self._create_story(story_lines, urls)
            if story:
                stories.append(story)

    def _is_story_start(self, line: str) -> bool:
        """Check if line starts a new story."""
        return line.startswith('*') and len(line) > 50

    def _is_story_end(self, lines: List[str], current_index: int) -> bool:
        """Check if current position is the end of a story."""
        next_index = current_index + 1
        if next_index >= len(lines):
            return False
        next_line = lines[next_index].strip()
        return not next_line or next_line.startswith('*')

    def _extract_stories_from_text(self) -> List[FTNStory]:
        """Fallback text-based extraction for non-reader-mode HTML."""
        stories = []
        lines = self.text.split('\n')

        current_story_lines = []
        current_urls = []
        in_story = False

        for i, line in enumerate(lines):
            line = line.strip()

            if not line:
                continue

            # Check if line starts a story
            if self._is_story_start(line):
                self._save_story_if_valid(stories, current_story_lines, current_urls)

                current_story_lines = [line]
                current_urls = []
                in_story = True

            elif in_story:
                urls_in_line = re.findall(r'<(https?://[^>]+)>', line)
                current_urls.extend(urls_in_line)
                current_story_lines.append(line)

                if self._is_story_end(lines, i):
                    self._save_story_if_valid(stories, current_story_lines, current_urls)
                    current_story_lines = []
                    current_urls = []
                    in_story = False

        # Save final story if exists
        self._save_story_if_valid(stories, current_story_lines, current_urls)

        return stories

    def _create_story_from_reader(self, text_paragraphs: List[str], urls: List[str]) -> Optional[FTNStory]:
        """
        Create a story from reader mode paragraphs and URLs.

        Args:
            text_paragraphs: List of paragraph texts
            urls: URLs found in the story

        Returns:
            FTNStory object or None
        """
        if not text_paragraphs:
            return None

        # Join paragraphs into content
        full_content = ' '.join(text_paragraphs)

        # Extract title (first sentence)
        title_match = re.match(r'^([^.!?]+[.!?])', full_content)
        if title_match:
            title = title_match.group(1).strip()
            # Remove the title from the content to avoid repetition
            content = full_content[len(title_match.group(1)):].strip()
        else:
            # Fallback: first 100 chars
            title = full_content[:100].strip()
            content = full_content

        # Filter URLs - remove FTN, Substack CDN, and tinyurl
        filtered_urls = [
            url for url in urls
            if FTN_DOMAIN not in url and 'substackcdn' not in url and 'tinyurl' not in url
        ]

        # Get source URL (first filtered URL, or first URL if none pass filter)
        source_url = filtered_urls[0] if filtered_urls else (urls[0] if urls else None)

        return FTNStory(
            title=title,
            content=content,
            source_url=source_url,
            all_urls=filtered_urls
        )

    def _create_story(self, lines: List[str], urls: List[str]) -> Optional[FTNStory]:
        """
        Create a story from lines and URLs (fallback for non-reader mode).

        Args:
            lines: Lines of text
            urls: URLs found in the story

        Returns:
            FTNStory object or None
        """
        if not lines:
            return None

        # Join lines into content
        content = ' '.join(lines)

        # Clean up asterisks and URLs from content
        content = re.sub(r'\*+', '', content)
        content = re.sub(r'<https?://[^>]+>', '', content)

        # Extract title (first sentence or first bold section)
        title_match = re.match(r'^([^.!?]+[.!?])', content)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Fallback: first 100 chars
            title = content[:100].strip()

        # Clean title
        title = title.replace('*', '').strip()

        # Filter URLs - remove FTN, Substack CDN, and tinyurl
        filtered_urls = [
            url for url in urls
            if FTN_DOMAIN not in url and 'substackcdn' not in url and 'tinyurl' not in url
        ]

        # Get source URL (first filtered URL, or first URL if none pass filter)
        source_url = filtered_urls[0] if filtered_urls else (urls[0] if urls else None)

        return FTNStory(title=title, content=content, source_url=source_url, all_urls=filtered_urls)

    def _load_blocklist(self) -> List[str]:
        """
        Load blocklist keywords from config/blocklist.txt.

        Returns:
            List of lowercase blocklist keywords
        """
        blocklist_path = Path(__file__).parent.parent.parent / 'config' / 'blocklist.txt'
        blocklist = []

        if blocklist_path.exists():
            with open(blocklist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        blocklist.append(line.lower())

        return blocklist

    def _is_blocklisted(self, story: 'FTNStory', blocklist: List[str]) -> bool:
        """
        Check if story matches any blocklist keywords.

        Args:
            story: FTNStory to check
            blocklist: List of blocklist keywords

        Returns:
            True if story matches blocklist, False otherwise
        """
        text = (story.title + ' ' + story.content).lower()
        return any(keyword in text for keyword in blocklist)

    def categorize_stories(self, stories: List[FTNStory]) -> Dict[str, List[FTNStory]]:
        """
        Categorize stories by theme.

        Args:
            stories: List of FTNStory objects

        Returns:
            Dict mapping theme names to story lists (includes 'unused' category)
        """
        categories = {
            'health_education': [],
            'environment': [],
            'technology_energy': [],
            'society': [],
            'unused': []
        }

        # Load blocklist
        blocklist = self._load_blocklist()

        # Keywords for each category
        keywords = {
            'health_education': ['health', 'education', 'school', 'student', 'vaccine', 'hospital', 'literacy', 'teaching'],
            'environment': ['climate', 'environment', 'conservation', 'wildlife', 'species', 'ocean', 'forest', 'pollution'],
            'technology_energy': ['solar', 'battery', 'energy', 'technology', 'renewable', 'power', 'data', 'AI'],
            'society': ['democracy', 'rights', 'community', 'social', 'poverty', 'inequality', 'justice']
        }

        for story in stories:
            # Check blocklist first
            if self._is_blocklisted(story, blocklist):
                categories['unused'].append(story)
                continue

            text = (story.title + ' ' + story.content).lower()
            scores = {}

            for category, terms in keywords.items():
                if category == 'unused':
                    continue
                score = sum(1 for term in terms if term in text)
                scores[category] = score

            # Assign to category with highest score
            if scores:
                best_category = max(scores, key=scores.get)
                if scores[best_category] > 0:
                    categories[best_category].append(story)
                else:
                    # No clear match - move to unused
                    categories['unused'].append(story)

        return categories


def main():
    """Test the parser."""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python -m src.parser <html_file>")
        sys.exit(1)

    parser = FTNParser(sys.argv[1])

    print("=" * 80)
    print("EXTRACTING STORIES FROM FTN")
    print("=" * 80)

    stories = parser.extract_stories()
    print(f"\nFound {len(stories)} stories\n")

    for i, story in enumerate(stories[:10], 1):  # Show first 10
        print(f"{i}. {story.title}")
        print(f"   URL: {story.source_url}")
        print(f"   Content length: {len(story.content)} chars")
        print()

    # Categorize
    print("\n" + "=" * 80)
    print("CATEGORIZED BY THEME")
    print("=" * 80)

    categories = parser.categorize_stories(stories)
    for theme, theme_stories in categories.items():
        print(f"\n{theme.upper()}: {len(theme_stories)} stories")
        for story in theme_stories[:3]:  # Show first 3 in each category
            print(f"  - {story.title[:80]}...")


if __name__ == '__main__':
    main()
