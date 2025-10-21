"""Parse Fix The News HTML content into structured stories."""

import re
from pathlib import Path
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class FTNStory:
    """Represents a single story from Fix The News."""

    def __init__(self, title: str, content: str, source_url: Optional[str] = None):
        self.title = title.strip()
        self.content = content.strip()
        self.source_url = source_url

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
            if href.startswith('http') and 'substackcdn' not in href and 'fixthenews.com' not in href:
                urls.append(href)

        return list(dict.fromkeys(urls))  # Remove duplicates, preserve order

    def extract_stories(self) -> List[FTNStory]:
        """
        Extract stories from FTN content.

        Returns:
            List of FTNStory objects
        """
        stories = []

        # Pattern: Stories often start with *text* or bold text
        # and are followed by URLs
        lines = self.text.split('\n')

        current_story_lines = []
        current_urls = []
        in_story = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Skip empty lines and UI cruft
            if not line or any(skip in line.lower() for skip in [
                'close reader', 'text and layout', 'theme', 'read aloud',
                'reset defaults', 'font', 'default', 'voice'
            ]):
                continue

            # Check if line starts a story (contains * and meaningful content)
            if line.startswith('*') and len(line) > 50:
                # Save previous story if exists
                if current_story_lines and len(' '.join(current_story_lines)) > 100:
                    story = self._create_story(current_story_lines, current_urls)
                    if story:
                        stories.append(story)

                # Start new story
                current_story_lines = [line]
                current_urls = []
                in_story = True

            elif in_story:
                # Extract URLs from this line
                urls_in_line = re.findall(r'<(https?://[^>]+)>', line)
                current_urls.extend(urls_in_line)

                # Add to current story
                current_story_lines.append(line)

                # End story if we hit a blank line or new story marker
                if i + 1 < len(lines) and (not lines[i + 1].strip() or lines[i + 1].strip().startswith('*')):
                    if len(' '.join(current_story_lines)) > 100:
                        story = self._create_story(current_story_lines, current_urls)
                        if story:
                            stories.append(story)
                    current_story_lines = []
                    current_urls = []
                    in_story = False

        # Add last story
        if current_story_lines and len(' '.join(current_story_lines)) > 100:
            story = self._create_story(current_story_lines, current_urls)
            if story:
                stories.append(story)

        return stories

    def _create_story(self, lines: List[str], urls: List[str]) -> Optional[FTNStory]:
        """
        Create a story from lines and URLs.

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

        # Get source URL (first non-FTN URL)
        source_url = None
        for url in urls:
            if 'fixthenews.com' not in url and 'substackcdn' not in url and 'tinyurl' not in url:
                source_url = url
                break

        # If no direct URL, take any URL
        if not source_url and urls:
            source_url = urls[0]

        return FTNStory(title=title, content=content, source_url=source_url)

    def categorize_stories(self, stories: List[FTNStory]) -> Dict[str, List[FTNStory]]:
        """
        Categorize stories by theme.

        Args:
            stories: List of FTNStory objects

        Returns:
            Dict mapping theme names to story lists
        """
        categories = {
            'health_education': [],
            'environment': [],
            'technology_energy': [],
            'society': []
        }

        # Keywords for each category
        keywords = {
            'health_education': ['health', 'education', 'school', 'student', 'vaccine', 'hospital', 'literacy', 'teaching'],
            'environment': ['climate', 'environment', 'conservation', 'wildlife', 'species', 'ocean', 'forest', 'pollution'],
            'technology_energy': ['solar', 'battery', 'energy', 'technology', 'renewable', 'power', 'data', 'AI'],
            'society': ['democracy', 'rights', 'community', 'social', 'poverty', 'inequality', 'justice']
        }

        for story in stories:
            text = (story.title + ' ' + story.content).lower()
            scores = {}

            for category, terms in keywords.items():
                score = sum(1 for term in terms if term in text)
                scores[category] = score

            # Assign to category with highest score
            if scores:
                best_category = max(scores, key=scores.get)
                if scores[best_category] > 0:
                    categories[best_category].append(story)
                else:
                    # Default to society if no clear match
                    categories['society'].append(story)

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
