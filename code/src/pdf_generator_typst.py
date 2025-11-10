#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Typst-based PDF generator for News, Fixed newspaper."""

import subprocess
from pathlib import Path
from typing import Dict, List
from utils import generate_qr_code_file, format_date, extract_source_name


class TypstNewspaperGenerator:
    """Generate newspaper PDFs using Typst for reliable print layouts."""

    def __init__(self):
        """Initialize the generator."""
        self.template_path = Path(__file__).parent.parent / "templates" / "newspaper.typ"
        self.typst_bin = Path.home() / ".local" / "bin" / "typst"

        if not self.typst_bin.exists():
            # Try system path
            result = subprocess.run(["which", "typst"], capture_output=True, text=True)
            if result.returncode == 0:
                self.typst_bin = Path(result.stdout.strip())
            else:
                raise RuntimeError("Typst not found. Install from https://typst.app")

    def generate_pdf(
        self,
        day_number: int,
        main_story: Dict,
        front_page_stories: List[Dict],
        mini_articles: List[Dict],
        statistics: List[Dict],
        output_path: str,
        date_str: str = "",
        day_of_week: str = "",
        theme: str = "",
        feature_box: Dict = None,
        tomorrow_teaser: str = ""
    ):
        """
        Generate a 2-page newspaper PDF using Typst.

        Args:
            day_number: Day number (1-4)
            main_story: Main story dict with title, content, source_url
            front_page_stories: List of secondary stories
            mini_articles: List of mini articles for page 2
            statistics: List of statistics dicts
            output_path: Output PDF path
            date_str: Formatted date string
            day_of_week: Day name (e.g., "Monday")
            theme: Theme name
            feature_box: Feature box content dict
            tomorrow_teaser: Tomorrow's teaser text
        """
        # Generate QR codes
        main_qr = self._generate_qr(main_story.get('source_url', ''))
        main_source = extract_source_name(main_story.get('source_url', ''))

        # Build secondary stories
        secondary_stories_text = self._build_secondary_stories(front_page_stories)

        # Build mini articles
        mini_articles_text = self._build_mini_articles(mini_articles)

        # Build statistics
        statistics_text = self._build_statistics(statistics)

        # Feature box
        if feature_box:
            feature_title = feature_box.get('title', 'COMING UP')
            feature_content = feature_box.get('content', '')
        else:
            feature_title = "Quick Win"
            feature_content = "Good news is happening every day. Keep reading to discover how the world is getting better!"

        # Tomorrow teaser
        if tomorrow_teaser:
            teaser_text = f"""#box(
  width: 100%,
  stroke: 2pt + black,
  fill: white,
  inset: 8pt,
)[
  #text(size: 10pt, weight: "bold")[TOMORROW]
  #v(4pt)
  #text(size: 8.5pt, style: "italic")[{tomorrow_teaser}]
]"""
        else:
            teaser_text = ""

        # Footer message
        footer_message = f"Day {day_number} of 4 • {theme}"

        # Load template
        with open(self.template_path, 'r') as f:
            template = f.read()

        # Replace placeholders
        typst_content = template.replace('{{DAY_OF_WEEK}}', day_of_week)
        typst_content = typst_content.replace('{{DATE}}', date_str)
        typst_content = typst_content.replace('{{THEME}}', theme)
        typst_content = typst_content.replace('{{MAIN_TITLE}}', self._escape_typst(main_story.get('title', '')))
        typst_content = typst_content.replace('{{MAIN_CONTENT}}', self._escape_typst(main_story.get('content', '')))
        typst_content = typst_content.replace('{{MAIN_QR}}', str(main_qr) if main_qr else '')
        typst_content = typst_content.replace('{{MAIN_SOURCE}}', main_source)
        typst_content = typst_content.replace('{{SECONDARY_STORIES}}', secondary_stories_text)
        typst_content = typst_content.replace('{{FEATURE_TITLE}}', self._escape_typst(feature_title))
        typst_content = typst_content.replace('{{FEATURE_CONTENT}}', self._escape_typst(feature_content))
        typst_content = typst_content.replace('{{TOMORROW_TEASER}}', teaser_text)
        typst_content = typst_content.replace('{{MINI_ARTICLES}}', mini_articles_text)
        typst_content = typst_content.replace('{{STATISTICS}}', statistics_text)
        typst_content = typst_content.replace('{{FOOTER_MESSAGE}}', footer_message)

        # Write temporary .typ file in code directory so paths work
        temp_typ = Path(__file__).parent.parent / "temp_newspaper.typ"
        output_path_abs = Path(output_path).resolve()

        with open(temp_typ, 'w') as f:
            f.write(typst_content)

        # Compile with Typst
        try:
            subprocess.run(
                [str(self.typst_bin), "compile", str(temp_typ), str(output_path_abs)],
                capture_output=True,
                text=True,
                check=True
            )
            return str(output_path_abs)
        except subprocess.CalledProcessError as e:
            print(f"Typst compilation error:\n{e.stderr}")
            raise
        finally:
            # Clean up temp file
            # Commented out for debugging - keep temp file to inspect
            # if temp_typ.exists():
            #     temp_typ.unlink()
            pass

    def _build_secondary_stories(self, stories: List[Dict]) -> str:
        """Build Typst markup for secondary stories."""
        if not stories:
            return ""

        parts = []
        for story in stories[:3]:  # Max 3 secondary stories
            qr_path = self._generate_qr(story.get('source_url', ''))
            source_name = extract_source_name(story.get('source_url', ''))

            title = self._escape_typst(story.get('title', ''))
            content = self._escape_typst(story.get('content', ''))

            story_text = f"""#line(length: 100%, stroke: 1pt + black)
#v(6pt)
#text(size: 12pt, weight: "bold")[{title}]
#v(4pt)
#text(size: 9pt)[{content}]
#v(4pt)
"""
            if qr_path:
                story_text += f'#box(image("{qr_path}", width: 0.25in, height: 0.25in)) '
            story_text += f'#text(size: 7pt, style: "italic")[{source_name}]\n#v(8pt)\n'

            parts.append(story_text)

        return "\n".join(parts)

    def _build_mini_articles(self, articles: List[Dict]) -> str:
        """Build Typst markup for mini articles."""
        if not articles:
            return ""

        parts = []
        for i, article in enumerate(articles):
            qr_path = self._generate_qr(article.get('source_url', ''))
            source_name = extract_source_name(article.get('source_url', ''))

            title = self._escape_typst(article.get('title', ''))
            content = self._escape_typst(article.get('content', ''))

            article_text = f"""#box(
  width: 100%,
  stroke: 2pt + black,
  fill: white,
  inset: 8pt,
)[
  #text(size: 10pt, weight: "bold")[{title}]
  #v(4pt)
  #line(length: 100%, stroke: 1pt + black)
  #v(6pt)

  #grid(
    columns: (5.8in, 0.8in),
    column-gutter: 8pt,
    align: (left, center + top),
    [
      #text(size: 8.5pt)[{content}]
    ],
    [
      #box(image("{qr_path}", width: 0.6in, height: 0.6in))
      #v(2pt)
      #text(size: 6pt)[{source_name}]
    ]
  )
]
"""
            parts.append(article_text)

            if i < len(articles) - 1:
                parts.append("#v(10pt)\n")

        return "\n".join(parts)

    def _build_statistics(self, stats: List[Dict]) -> str:
        """Build Typst markup for statistics."""
        if not stats:
            # Default stats if none provided
            stats = [
                {"number": "∞", "description": "Possibilities"},
                {"number": "100%", "description": "Effort"},
                {"number": "1", "description": "World"}
            ]

        parts = []
        for i, stat in enumerate(stats[:6]):  # Max 6 stats (2 rows × 3 cols)
            number = self._escape_typst(stat.get('number', ''))
            desc = self._escape_typst(stat.get('description', ''))

            stat_text = f"""#box(
  width: 100%,
  stroke: 1pt + black,
  fill: white,
  inset: 6pt,
)[
  #align(center)[
    #text(size: 14pt, weight: "bold")[{number}]
    #v(3pt)
    #text(size: 7.5pt)[{desc}]
  ]
]"""
            parts.append(stat_text)
            # Add spacing between stats
            if i < len(stats[:6]) - 1:
                parts.append("")

        return "\n".join(parts)

    def _escape_typst(self, text: str) -> str:
        """Escape special characters for Typst."""
        if not text:
            return ""

        # Escape backslashes first
        text = text.replace('\\', '\\\\')
        # Escape special Typst characters
        text = text.replace('#', '\\#')
        text = text.replace('[', '\\[')
        text = text.replace(']', '\\]')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        text = text.replace('<', '\\<')
        text = text.replace('>', '\\>')
        text = text.replace('$', '\\$')
        text = text.replace('*', '\\*')
        text = text.replace('_', '\\_')
        text = text.replace('`', '\\`')

        return text

    def _generate_qr(self, url: str) -> str | None:
        """Generate QR code file and return relative path, or None if generation fails."""
        if not url:
            return None
        try:
            abs_path = generate_qr_code_file(url)
            # Convert to relative path from code directory
            code_dir = Path(__file__).parent.parent
            rel_path = Path(abs_path).relative_to(code_dir)
            return str(rel_path)
        except Exception as e:
            print(f"Warning: Could not generate QR code for {url}: {e}")
            return None


def main():
    """Test the Typst generator."""
    import json

    # Load test data
    with open('ftn-315.json', 'r') as f:
        data = json.load(f)

    # Generate for day 2 (has basketball feature box)
    day_data = data.get('day_2', {})

    # Add feature box for testing
    from sports_schedule import DukeBasketballSchedule
    from datetime import datetime, timedelta

    sports_schedule = DukeBasketballSchedule()
    tuesday = datetime(2025, 10, 21).date()
    games = sports_schedule.get_games_for_date(tuesday)

    feature_box = None
    if games:
        feature_box = sports_schedule.format_game_box(games[0])

    generator = TypstNewspaperGenerator()
    output_path = '../output/news_fixed_typst_poc.pdf'

    date_str = format_date('2025-10-21')
    generator.generate_pdf(
        day_number=2,
        main_story=day_data['main_story'],
        front_page_stories=day_data.get('front_page_stories', []),
        mini_articles=day_data['mini_articles'],
        statistics=day_data.get('statistics', []),
        output_path=output_path,
        date_str=date_str,
        day_of_week='Tuesday',
        theme='Environment & Conservation',
        feature_box=feature_box,
        tomorrow_teaser=''
    )

    print(f"✅ Generated Typst POC: {output_path}")


if __name__ == '__main__':
    main()
