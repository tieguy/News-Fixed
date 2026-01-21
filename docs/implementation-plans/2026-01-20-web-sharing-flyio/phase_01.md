# Web Sharing via fly.io Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

**Goal:** Deploy News Fixed as a public-facing web application on fly.io serving weekly combined PDFs.

**Architecture:** Flask web app with cached PDF generation, deployed on fly.io with persistent storage and scheduled weekly regeneration. Reuses all existing content pipeline components.

**Tech Stack:** Python 3.11+, Flask, Gunicorn, WeasyPrint, fly.io

**Scope:** 7 phases from original design (phases 1-7)

**Codebase verified:** 2026-01-20

---

## Phase 1: Feature Flag Configuration

**Goal:** Make Duke/SF/XKCD features configurable via environment variables so they can be disabled for the public web version.

**Done when:** Running with `FEATURE_DUKE_SPORTS=false` skips Duke basketball integration; same for other features.

---

### Task 1: Add Feature Flag Environment Variables

**Files:**
- Modify: `code/src/main.py:10-23` (imports section)
- Modify: `code/.env.example`

**Step 1: Add feature flag helper function to main.py**

Add after the imports section (after line 23):

```python
def get_feature_flag(name: str, default: bool = True) -> bool:
    """Get a feature flag from environment variable.

    Args:
        name: Feature flag name (e.g., 'FEATURE_DUKE_SPORTS')
        default: Default value if not set (True for local, False for web)

    Returns:
        Boolean indicating if feature is enabled
    """
    value = os.getenv(name, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')
```

**Step 2: Update .env.example with feature flags**

Add to `code/.env.example`:

```bash
# Feature flags (default: true for local, false for web deployment)
FEATURE_DUKE_SPORTS=true
FEATURE_SF_LOCAL=true
FEATURE_XKCD=true
```

**Step 3: Verify changes**

Run: `python -c "import sys; sys.path.insert(0, 'code/src'); from main import get_feature_flag; print(get_feature_flag('FEATURE_TEST', True))"`
Expected: `True`

Run: `FEATURE_TEST=false python -c "import sys; sys.path.insert(0, 'code/src'); from main import get_feature_flag; print(get_feature_flag('FEATURE_TEST', True))"`
Expected: `False`

**Step 4: Commit**

```bash
git add code/src/main.py code/.env.example
git commit -m "feat: add feature flag helper function

Adds get_feature_flag() to read boolean flags from environment.
Prepares for configurable Duke/SF/XKCD features."
```

---

### Task 2: Wrap Duke Basketball Feature in Flag

**Files:**
- Modify: `code/src/main.py:276-279` (sports feature section in generate_day_newspaper)

**Step 1: Add flag check around sports feature**

Replace lines 276-279 in `generate_day_newspaper()`:

```python
    # Check for sports games (always takes priority for feature box)
    sports_feature = check_for_sports_games(date_info)
    if sports_feature:
        feature_box = sports_feature
```

With:

```python
    # Check for sports games if feature enabled (takes priority for feature box)
    if get_feature_flag('FEATURE_DUKE_SPORTS', default=True):
        sports_feature = check_for_sports_games(date_info)
        if sports_feature:
            feature_box = sports_feature
```

**Step 2: Verify feature flag works**

Run: `cd code && FEATURE_DUKE_SPORTS=false python -c "from main import get_feature_flag; print('Duke disabled:', not get_feature_flag('FEATURE_DUKE_SPORTS', True))"`
Expected: `Duke disabled: True`

**Step 3: Commit**

```bash
git add code/src/main.py
git commit -m "feat: wrap Duke basketball feature in FEATURE_DUKE_SPORTS flag

When FEATURE_DUKE_SPORTS=false, skips basketball game detection."
```

---

### Task 3: Wrap SF Local News Feature in Flag

**Files:**
- Modify: `code/src/main.py:281-285` (local story section in generate_day_newspaper)

**Step 1: Add flag check around SF local news**

Replace lines 281-285 in `generate_day_newspaper()`:

```python
    # Fetch local SF story if available (add to front page stories)
    if content_gen:
        local_story = fetch_local_story(content_gen, date_info['date_obj'].strftime('%Y-%m-%d'))
        if local_story:
            front_page_stories = [local_story] + list(front_page_stories or [])
```

With:

```python
    # Fetch local SF story if feature enabled (add to front page stories)
    if content_gen and get_feature_flag('FEATURE_SF_LOCAL', default=True):
        local_story = fetch_local_story(content_gen, date_info['date_obj'].strftime('%Y-%m-%d'))
        if local_story:
            front_page_stories = [local_story] + list(front_page_stories or [])
```

**Step 2: Verify feature flag works**

Run: `cd code && FEATURE_SF_LOCAL=false python -c "from main import get_feature_flag; print('SF disabled:', not get_feature_flag('FEATURE_SF_LOCAL', True))"`
Expected: `SF disabled: True`

**Step 3: Commit**

```bash
git add code/src/main.py
git commit -m "feat: wrap SF local news feature in FEATURE_SF_LOCAL flag

When FEATURE_SF_LOCAL=false, skips Readwise/SF article fetching."
```

---

### Task 4: Wrap XKCD Comic Feature in Flag

**Files:**
- Modify: `code/src/main.py:287-294` (xkcd section in generate_day_newspaper)

**Step 1: Add flag check around XKCD**

Replace lines 287-294 in `generate_day_newspaper()`:

```python
    # Load xkcd comic if selected for the newspaper's week
    xkcd_manager = XkcdManager()
    xkcd_comic = None
    selected_num = xkcd_manager.get_selected_for_day(day_num, date_info['date_obj'])
    if selected_num:
        cache = xkcd_manager.load_cache()
        if str(selected_num) in cache:
            xkcd_comic = cache[str(selected_num)]
```

With:

```python
    # Load xkcd comic if feature enabled and selected for the newspaper's week
    xkcd_comic = None
    if get_feature_flag('FEATURE_XKCD', default=True):
        xkcd_manager = XkcdManager()
        selected_num = xkcd_manager.get_selected_for_day(day_num, date_info['date_obj'])
        if selected_num:
            cache = xkcd_manager.load_cache()
            if str(selected_num) in cache:
                xkcd_comic = cache[str(selected_num)]
```

**Step 2: Verify feature flag works**

Run: `cd code && FEATURE_XKCD=false python -c "from main import get_feature_flag; print('XKCD disabled:', not get_feature_flag('FEATURE_XKCD', True))"`
Expected: `XKCD disabled: True`

**Step 3: Commit**

```bash
git add code/src/main.py
git commit -m "feat: wrap XKCD comic feature in FEATURE_XKCD flag

When FEATURE_XKCD=false, skips XKCD comic selection and display."
```

---

### Task 5: Integration Test - All Features Disabled

**Files:**
- None (verification only)

**Step 1: Test with all features disabled**

Run:
```bash
cd /var/home/louie/Projects/family/News-Fixed
FEATURE_DUKE_SPORTS=false FEATURE_SF_LOCAL=false FEATURE_XKCD=false \
  ./news-fixed --test --no-preview
```

Expected: Test newspaper generates successfully without Duke/SF/XKCD content.

**Step 2: Verify no errors in output**

The output should show:
- No "Adding Duke game" messages
- No "Generating local story" messages
- No XKCD-related messages
- "Test newspaper generated" success message

**Step 3: Commit documentation update**

```bash
git add code/.env.example
git commit -m "docs: document feature flags in .env.example

Phase 1 complete: All three features (Duke, SF, XKCD) now configurable via environment variables."
```

---

## Phase 1 Verification

After completing all tasks:

1. Run `./news-fixed --test --no-preview` - should work with defaults (all features enabled)
2. Run with `FEATURE_DUKE_SPORTS=false FEATURE_SF_LOCAL=false FEATURE_XKCD=false ./news-fixed --test --no-preview` - should work with all features disabled
3. All commits should be in git log

Phase 1 is complete when feature flags control all three optional features.
