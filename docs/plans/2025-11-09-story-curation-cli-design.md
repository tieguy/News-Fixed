# Story Curation CLI Design

**Date:** 2025-11-09
**Issue:** DailyNews-20 - Build CLI UI for story/stat/content selection
**Status:** Design Complete, Ready for Implementation

## Overview

An interactive CLI tool for manually curating FTN stories before newspaper generation. Allows reviewing auto-categorized stories, fixing miscategorizations, and choosing main vs mini story assignments.

## Problem Statement

**Current workflow pain points:**
- All stories auto-categorized by simple keyword matching
- Main story selection is purely by content length
- No way to review or fix categorization mistakes
- No manual control over story assignments before PDF generation

**Desired workflow:**
- Review auto-categorization results visually
- Fix miscategorized stories (move between days/themes)
- Override main story selection when length-based choice is wrong
- Preview story content before finalizing assignments
- Save curated results for reproducibility and testing

## Architecture

### Pipeline Flow

```
fetch_ftn_clean.py → ftn_to_json.py → curate.py → main.py
     (fetch HTML)    (auto-categorize)  (review/fix)  (generate PDFs)
                      outputs JSON      loads JSON     loads JSON
                                       outputs JSON
```

### Concrete Example

```bash
# Step 1: Fetch FTN content (existing)
python code/src/fetch_ftn_clean.py
# → creates data/ftn/FTN-316.html

# Step 2: Auto-categorize (existing)
python code/src/ftn_to_json.py data/ftn/FTN-316.html
# → creates data/ftn/ftn-316.json (with auto-categorization)

# Step 3: Review and fix (NEW TOOL)
python code/curate.py data/ftn/ftn-316.json
# → displays rich tables, prompts for fixes
# → saves to data/ftn/ftn-316-curated.json (new file)

# Step 4: Generate PDFs (existing)
python code/main.py --input data/ftn/ftn-316-curated.json --all
```

### Key Design Decisions

1. **Separate tool, not modification:** `curate.py` is additive, doesn't break existing automation
2. **JSON input/output:** Wraps `ftn_to_json.py`, uses same interchange format
3. **Save to new file:** Preserves original auto-categorized JSON for comparison/testing
4. **FTN-only scope:** Defer Google Sheets integration to DailyNews-19

## File Structure

```
code/
  curate.py          # New CLI tool (main entry point)
  src/
    curator.py       # New module with curation logic
    parser.py        # Existing (no changes)
    ftn_to_json.py   # Existing (no changes)
```

## User Interface Design

### Visual Display (using `rich` library)

**Overview Table** - All stories grouped by day/theme:

```
┌─────────────────────────────────────────────────────────────┐
│ Day 1: Health & Education (5 stories)                      │
├──────┬──────────────────────────────────┬─────────────────┤
│ Role │ Title                            │ Length          │
├──────┼──────────────────────────────────┼─────────────────┤
│ MAIN │ Former USAID chief says...       │ 850 chars       │
│ mini │ Vietnam cuts poverty to 1%       │ 520 chars       │
│ mini │ 325 million students...          │ 480 chars       │
│ mini │ Gen Z turns street power...      │ 390 chars       │
│ mini │ Canada school food programme     │ 350 chars       │
└──────┴──────────────────────────────────┴─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Day 2: Environment & Conservation (4 stories)              │
├──────┬──────────────────────────────────┬─────────────────┤
│ Role │ Title                            │ Length          │
...
```

### Interaction Flow

**1. Day-by-Day Review**

For each day, prompt:
```
Review Day 1 (Health & Education):
  [A] Accept as-is
  [M] Move stories to different day
  [S] Swap main/mini assignments
  [V] View story details
  [B] Back to previous day
Choice:
```

**2. Move Stories**

If user chooses [M]:
```
Which story to move? (1-5, or 'back'):
> 2

Move "Vietnam cuts poverty" to which day?
  [1] Health & Education (current)
  [2] Environment & Conservation
  [3] Technology & Energy
  [4] Society & Youth Movements
Choice: 2
```

**2a. Handle Overflow (if target day already has 5 stories)**

```
Move "Vietnam cuts poverty" to Day 2?

⚠️  Warning: Day 2 already has 5 stories (1 main + 4 minis)
   Moving this story would exceed the limit.

Options:
  [S] Swap with an existing mini article in Day 2
  [R] Replace an existing mini article in Day 2
  [C] Cancel move
Choice: S

Swap "Vietnam cuts poverty" with which Day 2 mini article?
  [1] China's clean-air drive... (520 chars)
  [2] Next up for the Pacific... (480 chars)
  [3] Green sea turtles comeback... (390 chars)
  [4] Humpback whales recovery... (350 chars)
Choice: 2

✓ Swapped: "Vietnam cuts poverty" ↔ "Next up for Pacific"
  - "Vietnam" moved to Day 2 (mini)
  - "Next up" moved to Day 1 (mini)
```

**3. Swap Main/Mini Assignments**

If user chooses [S]:
```
Pick new main story for Day 1:
  [1] Former USAID chief... (currently MAIN) (850 chars)
  [2] Vietnam cuts poverty (520 chars)
  [3] 325 million students (480 chars)
  [4] Gen Z turns street power (390 chars)
  [5] Canada school food programme (350 chars)
Choice: 2

✓ "Vietnam cuts poverty" is now the main story for Day 1
  "Former USAID chief" demoted to mini article
```

**4. View Story Details**

If user chooses [V]:
```
Which story? (1-5):
> 2

─────────────────────────────────────────────────────
Title: Vietnam cuts poverty to 1%
Length: 520 characters
Source: https://borgenproject.org/education-in-vietnam/
Role: mini article

Content:
Case in point: Vietnam, where the government cut
extreme poverty from around 50% in the early '90s
to approximately 1% by 2022. The government's
playbook was education-centred...
─────────────────────────────────────────────────────

Press Enter to continue...
```

**5. Final Confirmation**

After reviewing all 4 days:
```
✅ Curation complete!

Summary of changes:
  - Day 1: Swapped main story
  - Day 2: Moved 1 story from Day 1
  - Day 3: No changes
  - Day 4: No changes

Save curated JSON? [Y/n]: Y

Saved to: data/ftn/ftn-316-curated.json

Next step:
  python code/main.py --input data/ftn/ftn-316-curated.json --all
```

## Technical Implementation

### Dependencies

- `rich` - Tables, panels, pretty terminal output
- Standard library: `json`, `copy`, `pathlib`
- Reuses existing: `src/parser.py`, `src/ftn_to_json.py`

### Core Classes

```python
# src/curator.py

class StoryCurator:
    """Manages interactive story curation workflow."""

    def __init__(self, json_file: Path):
        """Load auto-categorized JSON from ftn_to_json.py"""
        self.json_file = json_file
        self.original_data = self._load_json(json_file)
        self.working_data = copy.deepcopy(self.original_data)
        self.changes_made = []

    def display_overview(self) -> None:
        """Show all 4 days in rich tables"""
        # Uses rich.table.Table for each day

    def review_day(self, day_num: int) -> bool:
        """Interactive review for one day. Returns True if changes made."""
        # Menu: Accept/Move/Swap/View/Back

    def move_story(self, from_day: int, story_index: int, to_day: int) -> None:
        """Move a story between days, handling overflow"""

    def swap_main_story(self, day_num: int, new_main_index: int) -> None:
        """Change which story is main vs mini"""

    def view_story(self, day_num: int, story_index: int) -> None:
        """Display full story details"""

    def save_curated(self, output_file: Path) -> None:
        """Save working_data to new JSON file"""

    def _handle_overflow(self, target_day: int, incoming_story: dict) -> dict | None:
        """Handle adding story to a full day. Returns story to swap back, or None if cancelled."""
```

### Key Implementation Choices

- **Immutability:** Keep `original_data` unchanged, work on `working_data` copy
- **Change tracking:** Record all moves/swaps in `changes_made` list for final summary
- **Validation:** Check that each day has 1 main + at least 1 mini before saving
- **Output filename:** Default to `{original}-curated.json` (e.g., `ftn-316-curated.json`)

## Validation Rules

**Story Limits:**
- Each day: exactly 1 main story
- Each day: 1-4 mini articles (warn if <1 or >4)
- Total per day: 2-5 stories (1 main + 1-4 minis)

**Pre-Save Validation:**
- Can't save if any day has 0 stories
- Can't save if any day is missing main story
- Warn (but allow) if day has 0 mini articles
- Warn (but allow) if day has >4 mini articles

**Overflow Handling:**
- Moving story to full day (5 stories) triggers swap/replace prompt
- Swapping moves story bidirectionally (safe, preserves total count)
- Replacing removes target story from curation entirely

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Too few stories for 4 days | Warn user, allow proceeding with empty days (main.py will skip them) |
| Story matches multiple categories | Auto-categorization picks highest keyword score; user can reassign |
| No clear category match | Parser defaults to "Society"; user can fix in curate.py |
| Interrupted session | No autosave - changes lost (acceptable for MVP) |
| Invalid JSON input | Error message with clear explanation, exit gracefully |
| Empty day after moves | Warn before saving, require at least 1 story per day with content |

## User Experience Features

- **Preview stories:** [V]iew option shows full title + first 200 chars of content + source URL
- **Character counts:** Show content length to help judge main vs mini suitability
- **Progress indicator:** "Reviewing Day 2 of 4" at top of each review screen
- **Final summary:** Before saving, show table of all changes made
- **Navigation:** Can go back to previous days to revise earlier decisions
- **Clear prompts:** All choices numbered/lettered, "back" option always available

## CLI Options

```bash
python code/curate.py <json_file> [options]

Arguments:
  json_file           Auto-categorized JSON from ftn_to_json.py

Options:
  -o, --output FILE   Output filename (default: {input}-curated.json)
  --dry-run          Preview without saving
  -h, --help         Show help message
```

## Future Enhancements (Out of Scope for DailyNews-20)

- **Statistics review:** After story curation, review/edit AI-generated statistics (mentioned in original bead notes)
- **Teaser review:** Review/edit tomorrow's teaser before PDF generation
- **Inline editing:** Edit headlines/content directly in CLI (currently can only assign/move)
- **Google Sheets integration:** Add stories from external URLs (deferred to DailyNews-19)
- **Autosave/resume:** Save session state to allow resuming interrupted curation
- **Full pipeline mode:** Continue directly to AI generation + PDF creation after curation
- **Undo/redo stack:** More sophisticated change history with granular undo

## Testing Strategy

**Manual Testing:**
1. Run `ftn_to_json.py` on sample FTN HTML
2. Run `curate.py` on resulting JSON
3. Test each operation: move, swap, view, back navigation
4. Test overflow scenarios (moving to full day)
5. Verify output JSON is valid and loads in `main.py`
6. Compare auto vs curated output side-by-side

**Test Cases:**
- Move story between days (normal case)
- Move story to full day → trigger swap
- Move story to full day → trigger replace
- Swap main/mini assignments
- Navigate back/forward through days
- Cancel operations at various points
- Empty day handling
- Save and verify JSON structure

## Success Criteria

- ✅ Loads auto-categorized JSON from `ftn_to_json.py`
- ✅ Displays all 4 days with stories in rich tables
- ✅ Allows moving stories between days
- ✅ Handles overflow with swap/replace prompts
- ✅ Allows changing main story selection
- ✅ Shows story previews on demand
- ✅ Saves curated results to new JSON file
- ✅ Output JSON works with existing `main.py`
- ✅ Preserves original auto-categorized JSON for comparison
- ✅ Provides clear summary of changes made

## Non-Goals (Explicitly Out of Scope)

- ❌ Modifying existing `ftn_to_json.py` or `main.py`
- ❌ AI/LLM-based categorization improvements
- ❌ Google Sheets URL fetching (DailyNews-19)
- ❌ Statistics/teaser review (future enhancement)
- ❌ Direct PDF generation from curate.py
- ❌ Web-based UI or GUI
- ❌ Multi-user collaboration features
