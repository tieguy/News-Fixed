# Dynamic Theme Suggestions - Phase 3

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Add theme metadata to output JSON structure to track theme sources

**Architecture:** Modify `_build_four_days_from_grouping()` to accept themes parameter, use dynamic theme names, and include `theme_metadata` field in output.

**Tech Stack:** Python

**Scope:** Phase 3 of 6

**Codebase verified:** 2026-01-18

---

## Phase 3: JSON Structure Update

### Task 1: Modify _build_four_days_from_grouping() to accept themes

**Files:**
- Modify: `code/src/ftn_to_json.py:248-309`

**Step 1: Update function signature**

Change line 248 from:
```python
def _build_four_days_from_grouping(stories: list, grouping: dict) -> dict:
```

To:
```python
def _build_four_days_from_grouping(stories: list, grouping: dict, themes: dict) -> dict:
```

**Step 2: Update docstring**

```python
def _build_four_days_from_grouping(stories: list, grouping: dict, themes: dict) -> dict:
    """
    Build final 4-day JSON structure from grouped stories.

    Args:
        stories: List of analyzed story dicts
        grouping: Day assignments from group_stories_into_days
        themes: Dict mapping day (1-4) to theme info with:
            - name: display name
            - key: internal key
            - source: "default", "generated", or "split_from_<theme>"

    Returns:
        Dict with day_1-day_4 structures, theme_metadata, and unused stories
    """
```

**Step 3: Replace hardcoded theme with dynamic theme**

Find line 278 (approximately):
```python
"theme": get_theme_name(day_num),
```

Replace with:
```python
"theme": themes[day_num]["name"],
```

**Step 4: Add theme_metadata to output**

At the end of the function, before the return statement (around line 305), add theme_metadata. Include health data if available (passed from Phase 4):

```python
    # Add theme metadata (includes health info if available)
    result["theme_metadata"] = {
        day: {
            "name": themes[day]["name"],
            "key": themes[day]["key"],
            "source": themes[day]["source"],
            "status": themes[day].get("status", "unknown"),
            "story_count": themes[day].get("story_count", 0),
            "high_strength_count": themes[day].get("high_strength_count", 0)
        }
        for day in themes.keys()
    }

    return result
```

**Step 5: Verify module loads**

Run: `uv run python -c "from src.ftn_to_json import _build_four_days_from_grouping; print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add code/src/ftn_to_json.py
git commit -m "feat: add theme_metadata to JSON output structure"
```

---

### Task 2: Add test for theme_metadata in output

**Files:**
- Modify: `code/src/test_ftn_to_json.py`

**Step 1: Add test for theme_metadata**

```python
def test_build_four_days_includes_theme_metadata():
    """_build_four_days_from_grouping includes theme_metadata in output."""
    from ftn_to_json import _build_four_days_from_grouping

    stories = [
        {"id": 0, "title": "Story 1", "content": "Content 1", "source_url": "https://example.com/1", "tui_headline": "Headline 1"},
        {"id": 1, "title": "Story 2", "content": "Content 2", "source_url": "https://example.com/2", "tui_headline": "Headline 2"},
    ]

    grouping = {
        "day_1": {"main": 0, "minis": []},
        "day_2": {"main": 1, "minis": []},
        "day_3": {"main": None, "minis": []},
        "day_4": {"main": None, "minis": []},
        "unused": []
    }

    themes = {
        1: {"name": "Health & Education", "key": "health_education", "source": "default"},
        2: {"name": "AI & Robotics", "key": "ai_robotics", "source": "generated"},
        3: {"name": "Environment & Conservation", "key": "environment", "source": "default"},
        4: {"name": "Society & Youth Movements", "key": "society", "source": "default"},
    }

    result = _build_four_days_from_grouping(stories, grouping, themes)

    # Verify theme_metadata exists
    assert "theme_metadata" in result
    assert len(result["theme_metadata"]) == 4

    # Verify day themes match
    assert result["day_1"]["theme"] == "Health & Education"
    assert result["day_2"]["theme"] == "AI & Robotics"

    # Verify metadata structure
    assert result["theme_metadata"][1]["source"] == "default"
    assert result["theme_metadata"][2]["source"] == "generated"
    assert result["theme_metadata"][2]["key"] == "ai_robotics"
```

**Step 2: Run test**

Run: `uv run pytest code/src/test_ftn_to_json.py::test_build_four_days_includes_theme_metadata -v`
Expected: PASS

**Step 3: Commit**

```bash
git add code/src/test_ftn_to_json.py
git commit -m "test: add test for theme_metadata in JSON output"
```
