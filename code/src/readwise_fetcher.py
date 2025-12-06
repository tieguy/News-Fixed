#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Fetch SF good news articles from Readwise Reader API."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATA_DIR = Path(__file__).parent.parent.parent / "data"
USED_ARTICLES_FILE = DATA_DIR / "sf_articles_used.json"


class ReadwiseFetcher:
    """Fetch and track SF good news articles from Readwise Reader."""

    def __init__(self, tag: str = "sf-good"):
        self.tag = tag
        self.token = os.getenv("READWISE_TOKEN")
        if not self.token:
            raise ValueError(
                "READWISE_TOKEN not found. Get it from https://readwise.io/access_token"
            )
        self.headers = {"Authorization": f"Token {self.token}"}
        self.used_articles = self._load_used_articles()

    def _load_used_articles(self) -> dict:
        """Load record of previously used articles."""
        if USED_ARTICLES_FILE.exists():
            with open(USED_ARTICLES_FILE) as f:
                return json.load(f)
        return {}

    def _save_used_articles(self):
        """Save record of used articles."""
        USED_ARTICLES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USED_ARTICLES_FILE, "w") as f:
            json.dump(self.used_articles, f, indent=2)

    def test_auth(self) -> bool:
        """Verify the token works."""
        resp = requests.get("https://readwise.io/api/v2/auth/", headers=self.headers)
        return resp.status_code == 204

    def fetch_all_tagged(self, with_content: bool = False) -> list[dict]:
        """Fetch all documents with the configured tag.

        Args:
            with_content: If True, include html_content in response (slower)
        """
        all_results = []
        next_cursor = None

        while True:
            params = {"tag": self.tag}
            if with_content:
                params["withHtmlContent"] = "true"
            if next_cursor:
                params["pageCursor"] = next_cursor

            resp = requests.get(
                "https://readwise.io/api/v3/list/",
                headers=self.headers,
                params=params
            )

            if resp.status_code != 200:
                print(f"Error fetching: {resp.status_code} - {resp.text}")
                break

            data = resp.json()
            all_results.extend(data.get("results", []))

            next_cursor = data.get("nextPageCursor")
            if not next_cursor:
                break

        return all_results

    def get_unused_articles(self, limit: int = 1, with_content: bool = False) -> list[dict]:
        """Get oldest unused articles, up to limit."""
        all_articles = self.fetch_all_tagged(with_content=with_content)

        # Filter out already used
        unused = [
            a for a in all_articles
            if a.get("source_url", a.get("url")) not in self.used_articles
        ]

        # Sort by created date (oldest first - FIFO)
        unused.sort(key=lambda x: x.get("created_at", ""))

        return unused[:limit]

    def mark_as_used(self, article: dict, used_date: str = None):
        """Mark an article as used."""
        url = article.get("source_url", article.get("url"))
        if not url:
            return

        self.used_articles[url] = {
            "title": article.get("title", "Untitled"),
            "used_date": used_date or datetime.now().isoformat(),
            "readwise_id": article.get("id"),
        }
        self._save_used_articles()

    def format_for_newspaper(self, article: dict) -> dict:
        """Format a Readwise article for the newspaper pipeline."""
        # Prefer html_content if available, fall back to summary
        content = article.get("html_content", article.get("summary", ""))
        return {
            "title": article.get("title", "Untitled"),
            "source_url": article.get("source_url", article.get("url", "")),
            "author": article.get("author", ""),
            "summary": article.get("summary", ""),
            "content": content,
            "html_content": article.get("html_content", ""),
            "word_count": article.get("word_count", 0),
            "published_date": article.get("published_date", ""),
        }

    def get_next_article(self, mark_used: bool = False, for_date: str = None, with_content: bool = True) -> Optional[dict]:
        """Get the next unused article, optionally marking it as used."""
        unused = self.get_unused_articles(limit=1, with_content=with_content)
        if not unused:
            return None

        article = unused[0]
        if mark_used:
            self.mark_as_used(article, for_date)

        return self.format_for_newspaper(article)


def main():
    """Test the Readwise fetcher."""
    try:
        fetcher = ReadwiseFetcher()
    except ValueError as e:
        print(f"Error: {e}")
        return

    if not fetcher.test_auth():
        print("Authentication failed")
        return

    print("✓ Authentication successful\n")

    # Show all tagged articles
    all_articles = fetcher.fetch_all_tagged()
    print(f"Found {len(all_articles)} articles tagged '{fetcher.tag}':")
    for a in all_articles:
        url = a.get("source_url", a.get("url", "no url"))
        used = "✓ used" if url in fetcher.used_articles else "○ unused"
        print(f"  [{used}] {a.get('title', 'Untitled')[:50]}")
        print(f"          {url}")

    # Show next unused with content
    print("\n--- Next unused article (with content) ---")
    next_article = fetcher.get_next_article(mark_used=False, with_content=True)
    if next_article:
        print(f"Title: {next_article['title']}")
        print(f"URL: {next_article['source_url']}")
        print(f"Words: {next_article['word_count']}")
        print(f"Has HTML content: {bool(next_article.get('html_content'))}")

        # Test local story generation
        print("\n--- Generating local story via Claude ---")
        try:
            from generator import ContentGenerator
            gen = ContentGenerator()
            local_story = gen.generate_local_story(
                original_content=next_article.get('html_content') or next_article.get('summary', ''),
                source_url=next_article['source_url'],
                original_title=next_article['title']
            )
            print(f"Generated title: {local_story['title']}")
            print(f"Generated content ({len(local_story['content'].split())} words):")
            print(local_story['content'])
        except Exception as e:
            print(f"Error generating: {e}")
    else:
        print("No unused articles available")


if __name__ == "__main__":
    main()
