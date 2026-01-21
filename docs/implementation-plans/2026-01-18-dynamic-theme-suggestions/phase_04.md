# Dynamic Theme Suggestions - Phase 4

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Wire theme analysis into main processing flow

**Architecture:** Insert `analyze_themes()` call between Phase 1 and Phase 2 in `create_json_from_ftn()`. Pass themes through to grouping and structure building functions. Fallback to defaults on error.

**Tech Stack:** Python, Anthropic Claude API

**Scope:** Phase 4 of 6

**Codebase verified:** 2026-01-18

---

## Phase 4: Pipeline Integration

### Task 1: Add DEFAULT_THEMES import and helper

**Files:**
- Modify: `code/src/ftn_to_json.py` (near top, after DEFAULT_THEMES definition around line 35)

**Step 1: Add helper function to convert DEFAULT_THEMES to proposed format**

After the `DEFAULT_THEMES` constant, add:

```python
def _default_theme_proposal() -> dict:
    """Return default themes in the proposal format for fallback."""
    return {
        "proposed_themes": {
            day: {"name": info["name"], "key": info["key"], "source": "default"}
            for day, info in DEFAULT_THEMES.items()
        },
        "theme_health": {
            day: {"status": "unknown", "story_count": 0, "high_strength_count": 0}
            for day in DEFAULT_THEMES.keys()
        },
        "reasoning": "Using default themes (fallback)."
    }
```

**Step 2: Verify module loads**

Run: `uv run python -c "from src.ftn_to_json import _default_theme_proposal; print(_default_theme_proposal())"`
Expected: Dict with proposed_themes, theme_health, reasoning

**Step 3: Commit**

```bash
git add code/src/ftn_to_json.py
git commit -m "feat: add _default_theme_proposal helper for fallback"
```

---

### Task 2: Insert analyze_themes() call in pipeline

**Files:**
- Modify: `code/src/ftn_to_json.py` in `create_json_from_ftn()` function

**Step 1: Add Phase 1.5 theme analysis**

Find the line that prints `"✓ Analyzed {len(stories)} stories"` (around line 453). After that line, add:

```python
        # Phase 1.5: Analyze themes
        print(f"\n🎯 Phase 1.5: Analyzing themes...")
        try:
            theme_proposal = analyze_themes(
                analyzed_stories=analyzed_stories,
                client=anthropic_client
            )
            themes = theme_proposal["proposed_themes"]
            theme_health = theme_proposal.get("theme_health", {})

            # Merge health data into themes for downstream use
            for day in themes:
                if day in theme_health:
                    themes[day]["status"] = theme_health[day].get("status", "unknown")
                    themes[day]["story_count"] = theme_health[day].get("story_count", 0)
                    themes[day]["high_strength_count"] = theme_health[day].get("high_strength_count", 0)

            print(f"   ✓ Theme analysis complete")

            # Show theme health summary
            for day, health in theme_health.items():
                status = health.get("status", "unknown")
                count = health.get("story_count", 0)
                emoji = "✅" if status == "healthy" else "⚠️" if status == "weak" else "📊"
                print(f"   {emoji} Day {day}: {themes[day]['name']} ({status}, {count} stories)")

            if theme_proposal.get("reasoning"):
                print(f"   💡 {theme_proposal['reasoning'][:100]}...")
        except Exception as e:
            print(f"   ⚠️  Error analyzing themes: {e}")
            print(f"   Falling back to default themes...")
            theme_proposal = _default_theme_proposal()
            themes = theme_proposal["proposed_themes"]
            # Merge health data for defaults too
            theme_health = theme_proposal.get("theme_health", {})
            for day in themes:
                if day in theme_health:
                    themes[day]["status"] = theme_health[day].get("status", "unknown")
                    themes[day]["story_count"] = theme_health[day].get("story_count", 0)
                    themes[day]["high_strength_count"] = theme_health[day].get("high_strength_count", 0)
```

**Step 2: Verify syntax**

Run: `uv run python -c "from src.ftn_to_json import create_json_from_ftn; print('OK')"`
Expected: `OK`

---

### Task 3: Update group_stories_into_days() call

**Files:**
- Modify: `code/src/ftn_to_json.py` in `create_json_from_ftn()` function

**Step 1: Pass themes to group_stories_into_days**

Find the `group_stories_into_days()` call (around lines 459-462):
```python
            grouping = group_stories_into_days(
                stories=analyzed_stories,
                blocklisted_ids=blocklisted_ids,
                client=anthropic_client
            )
```

Change to:
```python
            grouping = group_stories_into_days(
                stories=analyzed_stories,
                blocklisted_ids=blocklisted_ids,
                themes=themes,
                client=anthropic_client
            )
```

**Step 2: Update fallback call**

Find the `_fallback_grouping()` call in the except block (around line 470):
```python
            grouping = _fallback_grouping(analyzed_stories, blocklisted_ids)
```

Change to:
```python
            grouping = _fallback_grouping(analyzed_stories, blocklisted_ids, themes)
```

---

### Task 4: Update _build_four_days_from_grouping() call

**Files:**
- Modify: `code/src/ftn_to_json.py` in `create_json_from_ftn()` function

**Step 1: Pass themes to _build_four_days_from_grouping**

Find the `_build_four_days_from_grouping()` call (around line 473):
```python
        four_day_json = _build_four_days_from_grouping(stories, grouping)
```

Change to:
```python
        four_day_json = _build_four_days_from_grouping(stories, grouping, themes)
```

**Step 2: Verify full pipeline loads**

Run: `uv run python -c "from src.ftn_to_json import create_json_from_ftn; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add code/src/ftn_to_json.py
git commit -m "feat: integrate analyze_themes into main pipeline (Phase 1.5)"
```

---

### Task 5: Add integration test

**Files:**
- Modify: `code/src/test_ftn_to_json.py`

**Step 1: Add integration test for full pipeline with themes**

```python
def test_create_json_includes_theme_metadata():
    """Full pipeline produces JSON with theme_metadata."""
    import tempfile
    import json
    from ftn_to_json import create_json_from_ftn

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    # Use existing test fixture FTN-322.html if available
    test_html = Path(__file__).parent.parent / "cache" / "FTN-322.html"
    if not test_html.exists():
        pytest.skip("Test fixture FTN-322.html not found")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        output_file = f.name

    try:
        create_json_from_ftn(str(test_html), output_file)

        with open(output_file) as f:
            result = json.load(f)

        # Verify theme_metadata exists
        assert "theme_metadata" in result
        assert len(result["theme_metadata"]) == 4

        # Verify each day has a theme
        for day_key in ["day_1", "day_2", "day_3", "day_4"]:
            assert "theme" in result[day_key]
            assert result[day_key]["theme"]  # Not empty
    finally:
        if os.path.exists(output_file):
            os.unlink(output_file)
```

**Step 2: Run test**

Run: `uv run pytest code/src/test_ftn_to_json.py::test_create_json_includes_theme_metadata -v`
Expected: PASS (or skip if no API key/fixture)

**Step 3: Commit**

```bash
git add code/src/test_ftn_to_json.py
git commit -m "test: add integration test for theme_metadata in pipeline output"
```
