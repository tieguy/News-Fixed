# Dynamic Theme Suggestions - Phase 2

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Modify `group_stories_into_days()` to accept dynamic themes instead of hardcoded defaults

**Architecture:** Add `themes` parameter to grouping function and fallback. Prompt dynamically inserts theme names. Fallback builds theme_map from passed themes.

**Tech Stack:** Python, Anthropic Claude API

**Scope:** Phase 2 of 6

**Codebase verified:** 2026-01-18

---

## Phase 2: Grouping Function Modification

### Task 1: Modify group_stories_into_days() signature and prompt

**Files:**
- Modify: `code/src/ftn_to_json.py:148-203`

**Step 1: Update function signature**

Change line 148 from:
```python
def group_stories_into_days(stories: list, blocklisted_ids: list, client) -> dict:
```

To:
```python
def group_stories_into_days(stories: list, blocklisted_ids: list, themes: dict, client) -> dict:
```

**Step 2: Update docstring**

Update the docstring (lines 149-161) to document the `themes` parameter:
```python
def group_stories_into_days(stories: list, blocklisted_ids: list, themes: dict, client) -> dict:
    """
    Group analyzed stories into 4 days using Claude API (Phase 2).

    Args:
        stories: List of analyzed story dicts with id, headline, themes, strength, length
        blocklisted_ids: List of story IDs to exclude
        themes: Dict mapping day (1-4) to theme info with keys:
            - name: display name (e.g., "Health & Education")
            - key: internal key (e.g., "health_education")
            - source: "default", "generated", or "split_from_<theme>"
        client: Anthropic client

    Returns:
        Dict with day_1 through day_4, each containing:
            - main: ID of main story or None
            - minis: list of mini story IDs
        Plus unused: list of story IDs not assigned
    """
```

**Step 3: Replace hardcoded themes in prompt**

Before the prompt definition (around line 163), add theme list construction:
```python
    # Build dynamic theme list for prompt
    theme_lines = "\n".join(
        f"- Day {day}: {themes[day]['name']}"
        for day in sorted(themes.keys())
    )
```

Then in the prompt string, replace the hardcoded DAY THEMES section (lines 171-175):

From:
```
DAY THEMES:
- Day 1: Health & Education
- Day 2: Environment & Conservation
- Day 3: Technology & Energy
- Day 4: Society & Youth Movements
```

To:
```
DAY THEMES:
{theme_lines}
```

**Step 4: Update fallback call**

Find the call to `_fallback_grouping` (around line 201-202) and update it to pass themes:

From:
```python
return _fallback_grouping(stories, blocklisted_ids)
```

To:
```python
return _fallback_grouping(stories, blocklisted_ids, themes)
```

**Step 5: Verify module loads**

Run: `uv run python -c "from src.ftn_to_json import group_stories_into_days; print('OK')"`
Expected: Error (fallback function signature doesn't match yet) - this is expected, fixed in Task 2

---

### Task 2: Modify _fallback_grouping() to accept themes

**Files:**
- Modify: `code/src/ftn_to_json.py:206-245`

**Step 1: Update function signature**

Change line 206 from:
```python
def _fallback_grouping(analyzed_stories: list, blocklisted_ids: list) -> dict:
```

To:
```python
def _fallback_grouping(analyzed_stories: list, blocklisted_ids: list, themes: dict) -> dict:
```

**Step 2: Update docstring**

```python
def _fallback_grouping(analyzed_stories: list, blocklisted_ids: list, themes: dict) -> dict:
    """
    Fallback grouping using simple length-based assignment.

    Used when Phase 2 API call fails.

    Args:
        analyzed_stories: List of analyzed story dicts
        blocklisted_ids: List of story IDs to exclude
        themes: Dict mapping day (1-4) to theme info with key field
    """
```

**Step 3: Replace hardcoded theme_map**

Replace lines 213-218:
```python
    theme_map = {
        "health_education": "day_1",
        "environment": "day_2",
        "technology_energy": "day_3",
        "society": "day_4"
    }
```

With dynamic construction:
```python
    # Build theme_map from passed themes
    theme_map = {
        themes[day]["key"]: f"day_{day}"
        for day in themes.keys()
    }
```

**Step 4: Verify module loads**

Run: `uv run python -c "from src.ftn_to_json import group_stories_into_days, _fallback_grouping; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add code/src/ftn_to_json.py
git commit -m "feat: modify group_stories_into_days to accept dynamic themes"
```

---

### Task 3: Update existing tests

**Files:**
- Modify: `code/src/test_ftn_to_json.py:119-156`

**Step 1: Update test to pass themes**

The existing test `test_group_stories_into_days_returns_expected_structure` needs to pass the themes parameter. After the `client = Anthropic()` line, add:
```python
    from ftn_to_json import DEFAULT_THEMES

    # Convert DEFAULT_THEMES to the expected format
    themes = {
        day: {"name": info["name"], "key": info["key"], "source": "default"}
        for day, info in DEFAULT_THEMES.items()
    }
```

Then update the function call from:
```python
    result = group_stories_into_days(stories, blocklisted_ids=[], client=client)
```

To:
```python
    result = group_stories_into_days(stories, blocklisted_ids=[], themes=themes, client=client)
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest code/src/test_ftn_to_json.py::test_group_stories_into_days_returns_expected_structure -v`
Expected: PASS (or skip if no API key)

**Step 3: Commit**

```bash
git add code/src/test_ftn_to_json.py
git commit -m "test: update group_stories_into_days test for themes parameter"
```

---

### Task 4: Add unit test for dynamic themes

**Files:**
- Modify: `code/src/test_ftn_to_json.py`

**Step 1: Add test for custom themes**

```python
def test_group_stories_with_custom_themes():
    """group_stories_into_days works with custom (non-default) themes."""
    from ftn_to_json import group_stories_into_days
    from unittest.mock import MagicMock

    stories = [
        {"id": 0, "headline": "AI discovery", "primary_theme": "ai_robotics", "secondary_themes": [], "story_strength": "high", "length": 800},
        {"id": 1, "headline": "Clean energy win", "primary_theme": "clean_energy", "secondary_themes": [], "story_strength": "medium", "length": 400},
    ]

    # Custom themes (simulating generated/split themes)
    custom_themes = {
        1: {"name": "AI & Robotics", "key": "ai_robotics", "source": "split_from_technology_energy"},
        2: {"name": "Environment & Conservation", "key": "environment", "source": "default"},
        3: {"name": "Clean Energy", "key": "clean_energy", "source": "split_from_technology_energy"},
        4: {"name": "Society & Youth Movements", "key": "society", "source": "default"},
    }

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "day_1": {"main": 0, "minis": []},
        "day_2": {"main": null, "minis": []},
        "day_3": {"main": 1, "minis": []},
        "day_4": {"main": null, "minis": []},
        "unused": []
    }''')]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = group_stories_into_days(stories, blocklisted_ids=[], themes=custom_themes, client=mock_client)

    # Verify custom theme names appear in prompt
    call_args = mock_client.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "AI & Robotics" in prompt
    assert "Clean Energy" in prompt

    # Verify structure
    assert result["day_1"]["main"] == 0
    assert result["day_3"]["main"] == 1
```

**Step 2: Run test**

Run: `uv run pytest code/src/test_ftn_to_json.py::test_group_stories_with_custom_themes -v`
Expected: PASS

**Step 3: Add test for fallback with custom themes**

```python
def test_fallback_grouping_with_custom_themes():
    """_fallback_grouping works with custom themes."""
    from ftn_to_json import _fallback_grouping

    stories = [
        {"id": 0, "primary_theme": "ai_robotics", "story_strength": "high", "length": 800},
        {"id": 1, "primary_theme": "clean_energy", "story_strength": "medium", "length": 400},
        {"id": 2, "primary_theme": "environment", "story_strength": "high", "length": 600},
    ]

    custom_themes = {
        1: {"name": "AI & Robotics", "key": "ai_robotics", "source": "generated"},
        2: {"name": "Environment & Conservation", "key": "environment", "source": "default"},
        3: {"name": "Clean Energy", "key": "clean_energy", "source": "generated"},
        4: {"name": "Society & Youth Movements", "key": "society", "source": "default"},
    }

    result = _fallback_grouping(stories, blocklisted_ids=[], themes=custom_themes)

    # Story 0 (ai_robotics) should go to day_1
    # Story 1 (clean_energy) should go to day_3
    # Story 2 (environment) should go to day_2
    assert "day_1" in result
    assert "day_2" in result
    assert "day_3" in result
    assert "day_4" in result
```

**Step 4: Run all Phase 2 tests**

Run: `uv run pytest code/src/test_ftn_to_json.py -k "group_stories" -v`
Expected: All pass

**Step 5: Commit**

```bash
git add code/src/test_ftn_to_json.py
git commit -m "test: add tests for dynamic themes in grouping functions"
```
