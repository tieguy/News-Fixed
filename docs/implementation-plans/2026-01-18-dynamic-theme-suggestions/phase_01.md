# Dynamic Theme Suggestions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Add `analyze_themes()` function that assesses theme health and proposes dynamic themes

**Architecture:** New "Phase 1.5" analysis step between story analysis and grouping. Function examines all stories collectively, counts per-theme distribution, assesses health (weak/healthy/overloaded), and uses LLM to propose substitutes for problematic themes.

**Tech Stack:** Python, Anthropic Claude API (claude-sonnet-4-5-20250929), pytest

**Scope:** 6 phases from original design (Phase 1 of 6)

**Codebase verified:** 2026-01-18

---

## Phase 1: Theme Analysis Function

### Task 1: Add DEFAULT_THEMES constant

**Files:**
- Modify: `code/src/ftn_to_json.py:26-28`

**Step 1: Add constant after FTN_BASE_URL**

```python
# Constants
FTN_BASE_URL = "https://fixthenews.com"

# Default themes mapped to days and their internal keys
DEFAULT_THEMES = {
    1: {"name": "Health & Education", "key": "health_education"},
    2: {"name": "Environment & Conservation", "key": "environment"},
    3: {"name": "Technology & Energy", "key": "technology_energy"},
    4: {"name": "Society & Youth Movements", "key": "society"},
}
```

**Step 2: Update get_theme_name() to use DEFAULT_THEMES**

Replace the function at lines 629-637:
```python
def get_theme_name(day_number: int) -> str:
    """Get theme name for a day number."""
    theme = DEFAULT_THEMES.get(day_number)
    return theme["name"] if theme else "General"
```

**Step 3: Verify no regressions**

Run: `uv run pytest code/src/test_ftn_to_json.py -v`
Expected: All existing tests pass

**Step 4: Commit**

```bash
git add code/src/ftn_to_json.py
git commit -m "refactor: add DEFAULT_THEMES constant for theme unification"
```

---

### Task 2: Add analyze_themes() function

**Files:**
- Modify: `code/src/ftn_to_json.py` (add after `group_stories_into_days()`, around line 205)

**Step 1: Add the analyze_themes() function**

```python
def analyze_themes(analyzed_stories: list, client) -> dict:
    """
    Analyze all stories collectively to assess theme health and propose themes (Phase 1.5).

    Examines story distribution across default themes. If themes are weak (< 2 stories
    or no high-strength stories) or overloaded (> 6 stories with 2+ high-strength),
    proposes substitute or split themes.

    Args:
        analyzed_stories: List of dicts from analyze_story(), each with:
            - id: story index
            - primary_theme: one of health_education, environment, technology_energy, society
            - secondary_themes: list of tags
            - story_strength: high, medium, or low
            - headline: display headline
        client: Anthropic client

    Returns:
        Dict with:
            - proposed_themes: dict mapping day (1-4) to theme info:
                - name: display name (e.g., "Health & Education")
                - key: internal key for grouping (e.g., "health_education")
                - source: "default", "generated", or "split_from_<theme>"
            - theme_health: dict mapping day (1-4) to health info:
                - status: "weak", "healthy", or "overloaded"
                - story_count: number of stories
                - high_strength_count: number of high-strength stories
            - reasoning: explanation of theme choices
    """
    # Count stories per default theme
    theme_counts = {key: {"total": 0, "high": 0} for key in ["health_education", "environment", "technology_energy", "society"]}

    for story in analyzed_stories:
        theme = story.get("primary_theme")
        if theme in theme_counts:
            theme_counts[theme]["total"] += 1
            if story.get("story_strength") == "high":
                theme_counts[theme]["high"] += 1

    # Assess health of each default theme
    theme_health = {}
    weak_themes = []
    overloaded_themes = []

    for day, theme_info in DEFAULT_THEMES.items():
        key = theme_info["key"]
        counts = theme_counts.get(key, {"total": 0, "high": 0})

        if counts["total"] < 2 or counts["high"] == 0:
            status = "weak"
            weak_themes.append(day)
        elif counts["total"] > 6 and counts["high"] >= 2:
            status = "overloaded"
            overloaded_themes.append(day)
        else:
            status = "healthy"

        theme_health[day] = {
            "status": status,
            "story_count": counts["total"],
            "high_strength_count": counts["high"]
        }

    # If all themes are healthy, use defaults
    if not weak_themes and not overloaded_themes:
        return {
            "proposed_themes": {
                day: {"name": info["name"], "key": info["key"], "source": "default"}
                for day, info in DEFAULT_THEMES.items()
            },
            "theme_health": theme_health,
            "reasoning": "All default themes have healthy story counts."
        }

    # Need LLM to propose substitutes/splits
    stories_summary = []
    for story in analyzed_stories:
        stories_summary.append({
            "id": story.get("id"),
            "headline": story.get("headline") or story.get("tui_headline", "")[:50],
            "primary_theme": story.get("primary_theme"),
            "secondary_themes": story.get("secondary_themes", []),
            "strength": story.get("story_strength")
        })

    prompt = f"""You are helping organize a children's newspaper (ages 10-14).

We have {len(analyzed_stories)} stories that need to be organized into 4 daily themes.

CURRENT THEME ASSESSMENT:
{json.dumps(theme_health, indent=2)}

WEAK THEMES (need substitutes): {[DEFAULT_THEMES[d]["name"] for d in weak_themes] if weak_themes else "None"}
OVERLOADED THEMES (candidates for splitting): {[DEFAULT_THEMES[d]["name"] for d in overloaded_themes] if overloaded_themes else "None"}

STORIES:
{json.dumps(stories_summary, indent=2)}

Based on the stories' secondary_themes and content, propose 4 themes for the newspaper.

Rules:
1. Keep healthy default themes unchanged
2. Replace weak themes with generated themes based on story clusters
3. Split overloaded themes into two related sub-themes
4. Every theme needs a clear, kid-friendly name
5. Generate a unique key for non-default themes (lowercase, underscores)

Return ONLY valid JSON (no markdown fences):
{{
  "proposed_themes": {{
    "1": {{"name": "Theme Name", "key": "theme_key", "source": "default|generated|split_from_X"}},
    "2": {{"name": "Theme Name", "key": "theme_key", "source": "default|generated|split_from_X"}},
    "3": {{"name": "Theme Name", "key": "theme_key", "source": "default|generated|split_from_X"}},
    "4": {{"name": "Theme Name", "key": "theme_key", "source": "default|generated|split_from_X"}}
  }},
  "reasoning": "Brief explanation of theme choices"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    result = parse_llm_json_with_retry(response.content[0].text, client)

    # Convert string keys to int and add theme_health
    proposed = {}
    for day_str, theme_info in result.get("proposed_themes", {}).items():
        proposed[int(day_str)] = theme_info

    return {
        "proposed_themes": proposed,
        "theme_health": theme_health,
        "reasoning": result.get("reasoning", "")
    }
```

**Step 2: Verify module still loads**

Run: `uv run python -c "from src.ftn_to_json import analyze_themes; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add code/src/ftn_to_json.py
git commit -m "feat: add analyze_themes() for dynamic theme suggestions (Phase 1.5)"
```

---

### Task 3: Write tests for analyze_themes()

**Files:**
- Modify: `code/src/test_ftn_to_json.py`

**Step 1: Add unit test for healthy themes (no API call)**

Add to end of file:
```python
def test_analyze_themes_healthy_returns_defaults():
    """analyze_themes returns default themes when all are healthy."""
    from ftn_to_json import analyze_themes
    from unittest.mock import MagicMock

    # Create stories with healthy distribution (2-6 per theme, at least 1 high)
    stories = [
        {"id": 1, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Health Story 1"},
        {"id": 2, "primary_theme": "health_education", "story_strength": "medium", "tui_headline": "Health Story 2"},
        {"id": 3, "primary_theme": "environment", "story_strength": "high", "tui_headline": "Environment Story 1"},
        {"id": 4, "primary_theme": "environment", "story_strength": "medium", "tui_headline": "Environment Story 2"},
        {"id": 5, "primary_theme": "technology_energy", "story_strength": "high", "tui_headline": "Tech Story 1"},
        {"id": 6, "primary_theme": "technology_energy", "story_strength": "low", "tui_headline": "Tech Story 2"},
        {"id": 7, "primary_theme": "society", "story_strength": "high", "tui_headline": "Society Story 1"},
        {"id": 8, "primary_theme": "society", "story_strength": "medium", "tui_headline": "Society Story 2"},
    ]

    # Mock client - should NOT be called for healthy themes
    mock_client = MagicMock()

    result = analyze_themes(stories, mock_client)

    # Should return defaults without calling API
    mock_client.messages.create.assert_not_called()
    assert result["proposed_themes"][1]["source"] == "default"
    assert result["proposed_themes"][1]["name"] == "Health & Education"
    assert result["theme_health"][1]["status"] == "healthy"
    assert "healthy" in result["reasoning"].lower()
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest code/src/test_ftn_to_json.py::test_analyze_themes_healthy_returns_defaults -v`
Expected: PASS

**Step 3: Add unit test for weak theme detection**

```python
def test_analyze_themes_detects_weak_themes():
    """analyze_themes detects weak themes (< 2 stories or no high-strength)."""
    from ftn_to_json import analyze_themes
    from unittest.mock import MagicMock

    # Create stories with one weak theme (society has only 1 story)
    stories = [
        {"id": 1, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Health 1"},
        {"id": 2, "primary_theme": "health_education", "story_strength": "medium", "tui_headline": "Health 2"},
        {"id": 3, "primary_theme": "environment", "story_strength": "high", "tui_headline": "Env 1"},
        {"id": 4, "primary_theme": "environment", "story_strength": "medium", "tui_headline": "Env 2"},
        {"id": 5, "primary_theme": "technology_energy", "story_strength": "high", "tui_headline": "Tech 1"},
        {"id": 6, "primary_theme": "technology_energy", "story_strength": "low", "tui_headline": "Tech 2"},
        {"id": 7, "primary_theme": "society", "story_strength": "medium", "tui_headline": "Society 1"},  # Only 1, no high
    ]

    # Mock LLM response for theme proposal
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "proposed_themes": {
            "1": {"name": "Health & Education", "key": "health_education", "source": "default"},
            "2": {"name": "Environment & Conservation", "key": "environment", "source": "default"},
            "3": {"name": "Technology & Energy", "key": "technology_energy", "source": "default"},
            "4": {"name": "Youth Leadership", "key": "youth_leadership", "source": "generated"}
        },
        "reasoning": "Society theme was weak, replaced with Youth Leadership based on story clusters."
    }''')]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = analyze_themes(stories, mock_client)

    # Should call API for theme proposals
    mock_client.messages.create.assert_called_once()
    assert result["theme_health"][4]["status"] == "weak"
    assert result["proposed_themes"][4]["source"] == "generated"
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest code/src/test_ftn_to_json.py::test_analyze_themes_detects_weak_themes -v`
Expected: PASS

**Step 5: Add integration test (requires API key)**

```python
def test_analyze_themes_integration():
    """Integration test for analyze_themes with real API."""
    from ftn_to_json import analyze_themes

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic
    client = Anthropic()

    # Stories with intentionally weak society theme
    stories = [
        {"id": 1, "primary_theme": "health_education", "story_strength": "high", "tui_headline": "Medical breakthrough", "secondary_themes": ["science"]},
        {"id": 2, "primary_theme": "health_education", "story_strength": "medium", "tui_headline": "School program", "secondary_themes": ["education"]},
        {"id": 3, "primary_theme": "environment", "story_strength": "high", "tui_headline": "Ocean cleanup", "secondary_themes": ["conservation"]},
        {"id": 4, "primary_theme": "environment", "story_strength": "medium", "tui_headline": "Forest growth", "secondary_themes": ["nature"]},
        {"id": 5, "primary_theme": "technology_energy", "story_strength": "high", "tui_headline": "Solar power", "secondary_themes": ["renewable"]},
        {"id": 6, "primary_theme": "technology_energy", "story_strength": "medium", "tui_headline": "AI helps", "secondary_themes": ["ai"]},
        {"id": 7, "primary_theme": "society", "story_strength": "low", "tui_headline": "Community event", "secondary_themes": ["local"]},
    ]

    result = analyze_themes(stories, client)

    # Verify structure
    assert "proposed_themes" in result
    assert "theme_health" in result
    assert "reasoning" in result
    assert len(result["proposed_themes"]) == 4

    # Society should be marked weak
    assert result["theme_health"][4]["status"] == "weak"
```

**Step 6: Run all new tests**

Run: `uv run pytest code/src/test_ftn_to_json.py -k "analyze_themes" -v`
Expected: All tests pass (integration test may skip without API key)

**Step 7: Commit**

```bash
git add code/src/test_ftn_to_json.py
git commit -m "test: add tests for analyze_themes() function"
```
