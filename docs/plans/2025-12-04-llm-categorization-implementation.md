# LLM-Based Story Categorization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace keyword-based categorization with two-phase Claude API categorization for better accuracy.

**Architecture:** Phase 1 analyzes each story individually (themes, URL selection, headline). Phase 2 takes all analyzed stories and produces balanced 4-day assignments. JSON parsing includes retry logic with error context.

**Tech Stack:** Python, Anthropic API (claude-sonnet-4-5-20250929), pytest

---

## Task 1: Add `all_urls` Field to FTNStory

**Files:**
- Modify: `code/src/parser.py:17-27` (FTNStory class)
- Test: `code/src/test_parser.py` (new file)

**Step 1: Write the failing test**

Create `code/src/test_parser.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd code/src && python -m pytest test_parser.py -v`

Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'all_urls'`

**Step 3: Write minimal implementation**

Edit `code/src/parser.py` - update FTNStory class:

```python
class FTNStory:
    """Represents a single story from Fix The News."""

    def __init__(self, title: str, content: str, source_url: Optional[str] = None,
                 tui_headline: Optional[str] = None, all_urls: Optional[List[str]] = None):
        self.title = title.strip()
        self.content = content.strip()
        self.source_url = source_url
        self.tui_headline = tui_headline
        self.all_urls = all_urls if all_urls is not None else []

    def __repr__(self):
        return f"FTNStory(title='{self.title[:50]}...', url={self.source_url})"
```

**Step 4: Run test to verify it passes**

Run: `cd code/src && python -m pytest test_parser.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add code/src/parser.py code/src/test_parser.py
git commit -m "feat(parser): add all_urls field to FTNStory"
```

---

## Task 2: Populate `all_urls` During Story Extraction

**Files:**
- Modify: `code/src/parser.py:212-251` (_create_story_from_reader method)
- Test: `code/src/test_parser.py`

**Step 1: Write the failing test**

Add to `code/src/test_parser.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd code/src && python -m pytest test_parser.py::test_create_story_from_reader_populates_all_urls -v`

Expected: FAIL with `assert len(stories[0].all_urls) == 2` (currently empty)

**Step 3: Write minimal implementation**

Edit `code/src/parser.py` - update `_create_story_from_reader` method:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd code/src && python -m pytest test_parser.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add code/src/parser.py code/src/test_parser.py
git commit -m "feat(parser): populate all_urls during story extraction"
```

---

## Task 3: Add JSON Parsing Utility with Retry

**Files:**
- Modify: `code/src/ftn_to_json.py`
- Test: `code/src/test_ftn_to_json.py` (new file)

**Step 1: Write the failing test**

Create `code/src/test_ftn_to_json.py`:

```python
"""Tests for ftn_to_json module."""
import json
import pytest


def test_parse_llm_json_valid():
    """parse_llm_json handles valid JSON."""
    from ftn_to_json import parse_llm_json

    result = parse_llm_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_llm_json_strips_markdown_fences():
    """parse_llm_json strips markdown code fences."""
    from ftn_to_json import parse_llm_json

    result = parse_llm_json('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_llm_json_strips_fences_without_lang():
    """parse_llm_json strips fences without language specifier."""
    from ftn_to_json import parse_llm_json

    result = parse_llm_json('```\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_llm_json_raises_on_invalid():
    """parse_llm_json raises JSONDecodeError on invalid JSON."""
    from ftn_to_json import parse_llm_json

    with pytest.raises(json.JSONDecodeError):
        parse_llm_json('not valid json')
```

**Step 2: Run test to verify it fails**

Run: `cd code/src && python -m pytest test_ftn_to_json.py -v`

Expected: FAIL with `ImportError: cannot import name 'parse_llm_json'`

**Step 3: Write minimal implementation**

Add to `code/src/ftn_to_json.py` after the imports:

```python
def parse_llm_json(response_text: str) -> dict:
    """
    Parse JSON from LLM response, handling common formatting issues.

    Args:
        response_text: Raw response text from LLM

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If JSON is invalid after cleanup
    """
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)
```

**Step 4: Run test to verify it passes**

Run: `cd code/src && python -m pytest test_ftn_to_json.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add code/src/ftn_to_json.py code/src/test_ftn_to_json.py
git commit -m "feat(ftn_to_json): add parse_llm_json utility"
```

---

## Task 4: Add JSON Retry with Error Context

**Files:**
- Modify: `code/src/ftn_to_json.py`
- Test: `code/src/test_ftn_to_json.py`

**Step 1: Write the failing test**

Add to `code/src/test_ftn_to_json.py`:

```python
from unittest.mock import Mock, MagicMock


def test_parse_llm_json_with_retry_succeeds_first_try():
    """parse_llm_json_with_retry returns on first successful parse."""
    from ftn_to_json import parse_llm_json_with_retry

    client = Mock()  # Should not be called

    result = parse_llm_json_with_retry('{"key": "value"}', client)
    assert result == {"key": "value"}
    client.messages.create.assert_not_called()


def test_parse_llm_json_with_retry_retries_on_failure():
    """parse_llm_json_with_retry retries with error context."""
    from ftn_to_json import parse_llm_json_with_retry

    # Mock client that returns valid JSON on retry
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"fixed": "json"}')]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    result = parse_llm_json_with_retry('invalid json {', client)

    assert result == {"fixed": "json"}
    client.messages.create.assert_called_once()
    # Check that error context was included in retry prompt
    call_args = client.messages.create.call_args
    prompt = call_args.kwargs['messages'][0]['content']
    assert 'invalid json {' in prompt
    assert 'Parse error' in prompt or 'JSONDecodeError' in prompt


def test_parse_llm_json_with_retry_raises_after_failed_retry():
    """parse_llm_json_with_retry raises if retry also fails."""
    from ftn_to_json import parse_llm_json_with_retry

    # Mock client that returns invalid JSON on retry too
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='still invalid')]

    client = MagicMock()
    client.messages.create.return_value = mock_response

    with pytest.raises(json.JSONDecodeError):
        parse_llm_json_with_retry('invalid json', client)
```

**Step 2: Run test to verify it fails**

Run: `cd code/src && python -m pytest test_ftn_to_json.py::test_parse_llm_json_with_retry_succeeds_first_try -v`

Expected: FAIL with `ImportError: cannot import name 'parse_llm_json_with_retry'`

**Step 3: Write minimal implementation**

Add to `code/src/ftn_to_json.py`:

```python
def parse_llm_json_with_retry(response_text: str, client) -> dict:
    """
    Parse JSON from LLM response, retrying with error context on failure.

    Args:
        response_text: Raw response text from LLM
        client: Anthropic client for retry request

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If JSON is invalid after retry
    """
    try:
        return parse_llm_json(response_text)
    except json.JSONDecodeError as e:
        # Retry with error context
        retry_prompt = f"""Your previous response was not valid JSON.

Your response:
{response_text}

Parse error: {e}

Please return the corrected JSON only, no explanation or markdown."""

        retry_response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": retry_prompt}
            ]
        )

        retry_text = retry_response.content[0].text
        return parse_llm_json(retry_text)  # Let it raise if still invalid
```

**Step 4: Run test to verify it passes**

Run: `cd code/src && python -m pytest test_ftn_to_json.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add code/src/ftn_to_json.py code/src/test_ftn_to_json.py
git commit -m "feat(ftn_to_json): add parse_llm_json_with_retry with error context"
```

---

## Task 5: Add Phase 1 Story Analysis Function

**Files:**
- Modify: `code/src/ftn_to_json.py`
- Test: `code/src/test_ftn_to_json.py`

**Step 1: Write the failing test**

Add to `code/src/test_ftn_to_json.py`:

```python
import os


def test_analyze_story_returns_expected_fields():
    """analyze_story returns all required fields."""
    from ftn_to_json import analyze_story

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    result = analyze_story(
        title="Solar panels bring power to rural villages.",
        content="A new initiative has installed solar panels in 50 villages across Kenya, providing electricity to over 10,000 households for the first time.",
        all_urls=["https://nature.com/solar-study", "https://kenya.gov/energy"],
        content_length=180,
        client=client
    )

    assert "primary_theme" in result
    assert result["primary_theme"] in ["health_education", "environment", "technology_energy", "society"]
    assert "secondary_themes" in result
    assert isinstance(result["secondary_themes"], list)
    assert "age_appropriateness" in result
    assert "story_strength" in result
    assert "suggested_role" in result
    assert result["suggested_role"] in ["main", "mini"]
    assert "primary_source_url" in result
    assert "tui_headline" in result
    assert 30 <= len(result["tui_headline"]) <= 60  # Allow some flexibility
```

**Step 2: Run test to verify it fails**

Run: `cd code/src && python -m pytest test_ftn_to_json.py::test_analyze_story_returns_expected_fields -v`

Expected: FAIL with `ImportError: cannot import name 'analyze_story'`

**Step 3: Write minimal implementation**

Add to `code/src/ftn_to_json.py`:

```python
def analyze_story(title: str, content: str, all_urls: list, content_length: int, client) -> dict:
    """
    Analyze a story using Claude API (Phase 1).

    Extracts themes, selects primary URL, generates headline.

    Args:
        title: Story title
        content: Story content
        all_urls: List of all URLs found in story
        content_length: Character count of content
        client: Anthropic client

    Returns:
        Dict with analysis results
    """
    urls_str = "\n".join(f"- {url}" for url in all_urls) if all_urls else "None"

    prompt = f"""You are helping categorize news stories for a children's newspaper (ages 10-14).

Analyze this story and return JSON:

STORY:
Title: {title}
Content: {content}
URLs found:
{urls_str}
Length: {content_length} characters

Return ONLY valid JSON (no markdown fences):
{{
  "primary_theme": "one of: health_education, environment, technology_energy, society",
  "secondary_themes": ["other relevant themes as free-form tags"],
  "age_appropriateness": "high, medium, or low - is this suitable for 10-14 year olds?",
  "story_strength": "high, medium, or low - how compelling and well-sourced is this?",
  "suggested_role": "main or mini - main needs 600+ chars and depth",
  "primary_source_url": "the best URL for attribution from the list above, or null if none suitable",
  "tui_headline": "40-50 character engaging headline for display"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return parse_llm_json_with_retry(response.content[0].text, client)
```

**Step 4: Run test to verify it passes**

Run: `cd code/src && python -m pytest test_ftn_to_json.py::test_analyze_story_returns_expected_fields -v`

Expected: PASS

**Step 5: Commit**

```bash
git add code/src/ftn_to_json.py code/src/test_ftn_to_json.py
git commit -m "feat(ftn_to_json): add analyze_story for Phase 1 categorization"
```

---

## Task 6: Add Phase 2 Story Grouping Function

**Files:**
- Modify: `code/src/ftn_to_json.py`
- Test: `code/src/test_ftn_to_json.py`

**Step 1: Write the failing test**

Add to `code/src/test_ftn_to_json.py`:

```python
def test_group_stories_into_days_returns_expected_structure():
    """group_stories_into_days returns proper day assignments."""
    from ftn_to_json import group_stories_into_days

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    # Create mock analyzed stories
    stories = [
        {"id": 0, "headline": "Solar farms expand", "primary_theme": "technology_energy", "secondary_themes": ["africa"], "story_strength": "high", "length": 800},
        {"id": 1, "headline": "New literacy program", "primary_theme": "health_education", "secondary_themes": ["youth"], "story_strength": "medium", "length": 400},
        {"id": 2, "headline": "Ocean cleanup success", "primary_theme": "environment", "secondary_themes": ["technology"], "story_strength": "high", "length": 600},
        {"id": 3, "headline": "Youth voting rights", "primary_theme": "society", "secondary_themes": ["democracy"], "story_strength": "medium", "length": 350},
    ]

    result = group_stories_into_days(stories, blocklisted_ids=[], client=client)

    # Check structure
    assert "day_1" in result
    assert "day_2" in result
    assert "day_3" in result
    assert "day_4" in result
    assert "main" in result["day_1"]
    assert "minis" in result["day_1"]
    assert isinstance(result["day_1"]["minis"], list)

    # Check all story IDs are accounted for
    all_assigned = set()
    for day_key in ["day_1", "day_2", "day_3", "day_4"]:
        if result[day_key]["main"] is not None:
            all_assigned.add(result[day_key]["main"])
        all_assigned.update(result[day_key]["minis"])
    all_assigned.update(result.get("unused", []))

    assert all_assigned == {0, 1, 2, 3}
```

**Step 2: Run test to verify it fails**

Run: `cd code/src && python -m pytest test_ftn_to_json.py::test_group_stories_into_days_returns_expected_structure -v`

Expected: FAIL with `ImportError: cannot import name 'group_stories_into_days'`

**Step 3: Write minimal implementation**

Add to `code/src/ftn_to_json.py`:

```python
def group_stories_into_days(stories: list, blocklisted_ids: list, client) -> dict:
    """
    Group analyzed stories into 4 days using Claude API (Phase 2).

    Args:
        stories: List of analyzed story dicts with id, headline, themes, strength, length
        blocklisted_ids: List of story IDs to exclude
        client: Anthropic client

    Returns:
        Dict with day assignments: {day_1: {main: id, minis: [ids]}, ...}
    """
    stories_str = json.dumps(stories, indent=2)
    blocklist_str = json.dumps(blocklisted_ids) if blocklisted_ids else "[]"

    prompt = f"""You are organizing stories for a 4-day children's newspaper (ages 10-14).

STORIES:
{stories_str}

BLOCKLISTED STORY IDs (exclude these):
{blocklist_str}

DAY THEMES:
- Day 1: Health & Education
- Day 2: Environment & Conservation
- Day 3: Technology & Energy
- Day 4: Society & Youth Movements

RULES:
- Each day needs 1 main story (longest/strongest fit) + up to 4 minis
- Balance story count across days (aim for 4-5 per day)
- Main stories should be 600+ characters when possible
- Consider both primary and secondary themes for placement
- Stories can fit multiple days - pick best overall balance
- Blocklisted stories go in "unused"

Return ONLY valid JSON (no markdown fences):
{{
  "day_1": {{"main": <story_id or null>, "minis": [<story_ids>]}},
  "day_2": {{"main": <story_id or null>, "minis": [<story_ids>]}},
  "day_3": {{"main": <story_id or null>, "minis": [<story_ids>]}},
  "day_4": {{"main": <story_id or null>, "minis": [<story_ids>]}},
  "unused": [<story_ids>],
  "reasoning": "brief explanation of key placement decisions"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return parse_llm_json_with_retry(response.content[0].text, client)
```

**Step 4: Run test to verify it passes**

Run: `cd code/src && python -m pytest test_ftn_to_json.py::test_group_stories_into_days_returns_expected_structure -v`

Expected: PASS

**Step 5: Commit**

```bash
git add code/src/ftn_to_json.py code/src/test_ftn_to_json.py
git commit -m "feat(ftn_to_json): add group_stories_into_days for Phase 2 grouping"
```

---

## Task 7: Integrate New Functions into create_json_from_ftn

**Files:**
- Modify: `code/src/ftn_to_json.py:76-228` (create_json_from_ftn function)
- Test: Manual integration test

**Step 1: Update create_json_from_ftn to use new functions**

Replace the categorization and headline generation logic in `create_json_from_ftn`:

```python
def create_json_from_ftn(html_file: str, output_file: str = None):
    """
    Parse FTN HTML and create a 4-day JSON file.

    Args:
        html_file: Path to FTN HTML file
        output_file: Output JSON file path (defaults to ftn-{issue}.json)

    Returns:
        Path to created JSON file
    """
    print(f"📖 Parsing {html_file}...")

    # Parse the HTML
    parser = FTNParser(html_file)
    stories = parser.extract_stories()

    print(f"   Found {len(stories)} stories")

    # Initialize Anthropic client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found")
        print("   Set it in .env or environment to use LLM categorization")
        sys.exit(1)

    anthropic_client = Anthropic(api_key=api_key)

    # Load blocklist
    blocklist = parser._load_blocklist()

    # Phase 1: Analyze each story
    print(f"\n🔍 Phase 1: Analyzing {len(stories)} stories...")
    analyzed_stories = []
    blocklisted_ids = []

    for i, story in enumerate(stories):
        print(f"   [{i+1}/{len(stories)}] Analyzing...", end="\r")

        # Check blocklist first
        if parser._is_blocklisted(story, blocklist):
            blocklisted_ids.append(i)
            analyzed_stories.append({
                "id": i,
                "headline": story.title[:50],
                "primary_theme": "unused",
                "secondary_themes": [],
                "story_strength": "low",
                "length": len(story.content),
                "blocklisted": True
            })
            continue

        try:
            analysis = analyze_story(
                title=story.title,
                content=story.content,
                all_urls=story.all_urls,
                content_length=len(story.content),
                client=anthropic_client
            )

            # Store analysis results back on story object
            story.tui_headline = analysis.get("tui_headline", story.title[:47] + "...")
            story.source_url = analysis.get("primary_source_url") or story.source_url

            analyzed_stories.append({
                "id": i,
                "headline": analysis.get("tui_headline", story.title[:50]),
                "primary_theme": analysis.get("primary_theme", "society"),
                "secondary_themes": analysis.get("secondary_themes", []),
                "story_strength": analysis.get("story_strength", "medium"),
                "length": len(story.content)
            })
        except Exception as e:
            print(f"\n   ⚠️  Error analyzing story {i}: {e}")
            analyzed_stories.append({
                "id": i,
                "headline": story.title[:50],
                "primary_theme": "society",
                "secondary_themes": [],
                "story_strength": "medium",
                "length": len(story.content)
            })

    print(f"   ✓ Analyzed {len(stories)} stories" + " " * 20)

    # Phase 2: Group stories into days
    print(f"\n📊 Phase 2: Grouping stories into days...")

    try:
        grouping = group_stories_into_days(
            stories=analyzed_stories,
            blocklisted_ids=blocklisted_ids,
            client=anthropic_client
        )
        print(f"   ✓ Grouped stories")
        if grouping.get("reasoning"):
            print(f"   Reasoning: {grouping['reasoning'][:100]}...")
    except Exception as e:
        print(f"   ⚠️  Error grouping stories: {e}")
        print(f"   Falling back to length-based assignment...")
        grouping = _fallback_grouping(analyzed_stories, blocklisted_ids)

    # Build 4-day structure from grouping
    four_days = _build_four_days_from_grouping(stories, grouping)

    # Determine output filename
    if output_file is None:
        html_path = Path(html_file)
        if 'FTN-' in html_path.name:
            issue = html_path.name.split('FTN-')[1].split('.')[0]
            output_file = f"ftn-{issue}.json"
        else:
            output_file = "ftn-content.json"

    # Write JSON file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(four_days, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Created {output_path}")

    # Print summary
    for day_num in range(1, 5):
        day_key = f"day_{day_num}"
        if day_key in four_days:
            main = 1 if four_days[day_key].get("main_story") else 0
            minis = len(four_days[day_key].get("mini_articles", []))
            print(f"   Day {day_num}: {main} main + {minis} minis")

    if "unused" in four_days:
        unused_count = len(four_days["unused"].get("stories", []))
        if unused_count:
            print(f"   Unused: {unused_count} stories")

    return output_path
```

**Step 2: Add helper functions**

Add these helper functions to `code/src/ftn_to_json.py`:

```python
def _fallback_grouping(analyzed_stories: list, blocklisted_ids: list) -> dict:
    """
    Fallback grouping using simple length-based assignment.

    Used when Phase 2 API call fails.
    """
    # Group by primary theme
    theme_map = {
        "health_education": "day_1",
        "environment": "day_2",
        "technology_energy": "day_3",
        "society": "day_4"
    }

    days = {
        "day_1": {"main": None, "minis": []},
        "day_2": {"main": None, "minis": []},
        "day_3": {"main": None, "minis": []},
        "day_4": {"main": None, "minis": []},
        "unused": blocklisted_ids.copy()
    }

    # Sort by length descending
    sorted_stories = sorted(
        [s for s in analyzed_stories if s["id"] not in blocklisted_ids],
        key=lambda s: s["length"],
        reverse=True
    )

    for story in sorted_stories:
        day_key = theme_map.get(story["primary_theme"], "day_4")

        if days[day_key]["main"] is None:
            days[day_key]["main"] = story["id"]
        elif len(days[day_key]["minis"]) < 4:
            days[day_key]["minis"].append(story["id"])
        else:
            days["unused"].append(story["id"])

    return days


def _build_four_days_from_grouping(stories: list, grouping: dict) -> dict:
    """
    Build the final 4-day JSON structure from grouping results.
    """
    four_days = {}

    # Add unused stories first
    unused_ids = grouping.get("unused", [])
    if unused_ids:
        four_days["unused"] = {
            "stories": [
                {
                    "title": stories[i].title,
                    "content": stories[i].content,
                    "source_url": stories[i].source_url or FTN_BASE_URL,
                    "tui_headline": stories[i].tui_headline or stories[i].title[:47] + "..."
                }
                for i in unused_ids if i < len(stories)
            ]
        }

    # Build each day
    for day_num in range(1, 5):
        day_key = f"day_{day_num}"
        day_grouping = grouping.get(day_key, {"main": None, "minis": []})

        main_id = day_grouping.get("main")
        mini_ids = day_grouping.get("minis", [])

        day_data = {
            "theme": get_theme_name(day_num),
            "main_story": {},
            "front_page_stories": [],
            "mini_articles": [],
            "statistics": [],
            "tomorrow_teaser": ""
        }

        # Add main story
        if main_id is not None and main_id < len(stories):
            story = stories[main_id]
            day_data["main_story"] = {
                "title": story.title,
                "content": story.content,
                "source_url": story.source_url or FTN_BASE_URL,
                "tui_headline": story.tui_headline or story.title[:47] + "..."
            }

        # Add mini articles
        for mini_id in mini_ids:
            if mini_id < len(stories):
                story = stories[mini_id]
                day_data["mini_articles"].append({
                    "title": story.title,
                    "content": story.content,
                    "source_url": story.source_url or FTN_BASE_URL,
                    "tui_headline": story.tui_headline or story.title[:47] + "..."
                })

        four_days[day_key] = day_data

    return four_days
```

**Step 3: Run integration test**

Run manually with a real FTN file:
```bash
cd code/src && python ftn_to_json.py ../../data/raw/FTN-318.html -o /tmp/test-output.json
```

Expected: Should see Phase 1 and Phase 2 output, create valid JSON

**Step 4: Commit**

```bash
git add code/src/ftn_to_json.py
git commit -m "feat(ftn_to_json): integrate LLM categorization into main pipeline"
```

---

## Task 8: Remove Old Keyword Categorization

**Files:**
- Modify: `code/src/parser.py` (remove categorize_stories method)

**Step 1: Verify categorize_stories is no longer called**

Search for usages:
```bash
grep -r "categorize_stories" code/src/
```

Expected: Only definition in parser.py (no longer called from ftn_to_json.py)

**Step 2: Remove the method**

Delete `categorize_stories` method from `code/src/parser.py` (lines 332-385).

Also remove the keywords dict since it's no longer needed.

**Step 3: Run all tests**

```bash
cd code/src && python -m pytest test_parser.py test_ftn_to_json.py -v
```

Expected: All PASS

**Step 4: Commit**

```bash
git add code/src/parser.py
git commit -m "refactor(parser): remove deprecated keyword categorization"
```

---

## Task 9: Final Integration Test

**Step 1: Run full pipeline**

```bash
./news-fixed process data/raw/FTN-318.html
```

**Step 2: Verify output**

Check that:
- Stories are distributed across all 4 days
- Main stories are appropriately selected
- TUI headlines are generated
- Source URLs are selected from all_urls

**Step 3: Run curation TUI**

```bash
./news-fixed curate data/processed/ftn-318.json
```

Verify:
- All days show stories
- Unused section contains blocklisted/unfit stories
- Moving stories between days works

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete LLM-based story categorization

Replaces keyword-based categorization with two-phase Claude API approach:
- Phase 1: Per-story analysis (themes, URL selection, headline)
- Phase 2: Holistic grouping across 4 days

Closes categorization issues with unused stories and misclassification."
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add all_urls field to FTNStory | parser.py, test_parser.py |
| 2 | Populate all_urls during extraction | parser.py, test_parser.py |
| 3 | Add JSON parsing utility | ftn_to_json.py, test_ftn_to_json.py |
| 4 | Add JSON retry with error context | ftn_to_json.py, test_ftn_to_json.py |
| 5 | Add Phase 1 analyze_story | ftn_to_json.py, test_ftn_to_json.py |
| 6 | Add Phase 2 group_stories_into_days | ftn_to_json.py, test_ftn_to_json.py |
| 7 | Integrate into create_json_from_ftn | ftn_to_json.py |
| 8 | Remove old keyword categorization | parser.py |
| 9 | Final integration test | - |
