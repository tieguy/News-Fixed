# Dynamic Theme Suggestions Design

## Summary

This design introduces intelligent theme selection for the News, Fixed daily newspaper. Currently, articles from Fix The News are assigned to four hardcoded daily themes (Health & Education, Environment & Conservation, Technology & Energy, Society & Youth Movements). This works adequately when content aligns with these categories, but breaks down when a week's stories cluster around different topics—resulting in weak themes with insufficient stories or overloaded themes forcing unrelated articles together.

The solution adds a new "Phase 1.5" analysis step between story analysis and grouping. After Claude analyzes each story individually (existing behavior), a new `analyze_themes()` function examines all stories collectively to assess whether the default themes work well for this week's content. If themes are weak (< 2 stories) or overloaded (> 6 stories), the LLM proposes substitute or split themes based on natural content clusters. The curator TUI gains a new review step displaying the proposed themes with health indicators, allowing acceptance or manual override before story grouping proceeds. This preserves the existing two-phase LLM architecture while making the newspaper adapt intelligently to each week's content distribution.

## Definition of Done

1. LLM analyzes week's content and proposes 4 themes (may differ from hardcoded defaults)
2. Weak theme detection: flags themes with insufficient count/quality
3. Substitute theme generation: proposes replacement themes from clustered content
4. Theme splitting: detects overloaded themes and proposes splits
5. Curator TUI shows suggested themes with option to accept/reject/modify

## Glossary

- **Fix The News (FTN)**: Weekly newsletter aggregating positive news stories about human progress; the primary content source for News, Fixed
- **Story strength**: Quality rating assigned during individual story analysis (low/medium/high) based on verifiability, impact, and relevance to target audience
- **Primary/secondary themes**: Tags assigned to each story during Phase 1 analysis indicating main topic and alternate categorization options
- **Curator TUI**: Terminal user interface that allows interactive review and manual adjustment of story assignments before PDF generation
- **Theme health**: Assessment of whether a theme has sufficient/appropriate story count (weak: < 2 stories, healthy: 2-6, overloaded: > 6)
- **Story grouping**: Process of assigning analyzed stories to specific daily editions (Days 1-4) based on theme alignment
- **Phase 1/Phase 2 processing**: Existing two-stage Claude API architecture: Phase 1 analyzes stories individually, Phase 2 groups all stories collectively
- **Rich tables**: Terminal UI library (Rich) used for formatted table display in the curator interface
- **Fallback grouping**: Simple round-robin story assignment used when LLM grouping fails or returns invalid data

## Architecture

Dynamic theme suggestion via a dedicated analysis step inserted between story analysis and story grouping.

**Pipeline flow:**

```
Phase 1: Story Analysis (existing)
    - Per-story: primary_theme, secondary_themes, story_strength
    ↓
Phase 1.5: Theme Analysis (NEW)
    - Input: All analyzed stories
    - Output: 4 proposed themes + health assessment
    ↓
Phase 2: Story Grouping (modified)
    - Uses proposed themes instead of hardcoded defaults
    - Assigns stories to proposed day-theme slots
    ↓
Curator TUI (modified)
    - Shows proposed themes automatically
    - Override action triggers re-grouping
```

**Key components:**

- `analyze_themes()` in `src/ftn_to_json.py` — clusters stories, assesses default theme health, proposes substitutes/splits
- `group_stories_into_days(themes)` in `src/ftn_to_json.py` — modified to accept themes parameter
- `review_themes()` in `src/curator.py` — new TUI step for theme review/override
- `theme_metadata` in output JSON — tracks theme source (default/generated/split)

**Theme health assessment:**

| Status | Criteria |
|--------|----------|
| Weak | < 2 stories OR 0 high-strength stories |
| Healthy | 2-6 stories with at least 1 high-strength |
| Overloaded | > 6 stories with 2+ high-strength (split candidate) |

**Theme sources:**

- `default` — kept from original 4 themes (Health & Education, Environment & Conservation, Technology & Energy, Society & Youth Movements)
- `generated` — LLM-proposed substitute based on content clusters
- `split_from_<theme>` — split from overloaded default theme

## Existing Patterns

Investigation found two-phase LLM processing in `src/ftn_to_json.py`:
- Phase 1: `analyze_story()` — per-story Claude API call returning structured JSON
- Phase 2: `group_stories_into_days()` — single Claude API call for all-story grouping

This design follows the same pattern:
- Phase 1.5: `analyze_themes()` — single Claude API call analyzing all stories for theme health
- All prompts use "Return ONLY valid JSON" instruction per existing pattern
- Uses same model (Claude Sonnet) as existing phases

Investigation found curator TUI in `src/curator.py`:
- Interactive menu pattern with `[A]ccept`, `[M]ove`, `[S]wap`, `[V]iew` actions
- Rich tables for day-by-day display
- Step-by-step review flow: unused stories → days 1-4 → xkcd

New `review_themes()` step follows existing TUI patterns and inserts before `review_unused()`.

## Implementation Phases

### Phase 1: Theme Analysis Function

**Goal:** Add `analyze_themes()` function that assesses theme health and proposes themes

**Components:**
- `analyze_themes()` in `src/ftn_to_json.py` — takes analyzed stories, returns proposed themes with health assessment
- Prompt template for theme analysis — follows existing JSON-output pattern
- `ThemeProposal` data structure — proposed_themes dict, theme_health dict, reasoning string

**Dependencies:** None (new function, no existing code modified)

**Done when:** Function can analyze a list of stories and return theme proposals with health assessment

### Phase 2: Grouping Function Modification

**Goal:** Modify `group_stories_into_days()` to accept dynamic themes

**Components:**
- Modified `group_stories_into_days(analyzed_stories, themes)` in `src/ftn_to_json.py` — themes parameter replaces hardcoded dict
- Modified prompt template — uses passed theme names instead of hardcoded
- Modified `_fallback_grouping()` — uses passed themes for fallback mapping

**Dependencies:** Phase 1 (theme analysis function exists)

**Done when:** Grouping function works with arbitrary theme names passed as parameter

### Phase 3: JSON Structure Update

**Goal:** Add theme metadata to output JSON structure

**Components:**
- `theme_metadata` field in `build_4day_structure()` output — tracks source of each theme
- Modified `day_N.theme` values — populated from proposed themes instead of hardcoded

**Dependencies:** Phase 2 (grouping accepts dynamic themes)

**Done when:** Output JSON includes theme_metadata and dynamic theme names in day structures

### Phase 4: Pipeline Integration

**Goal:** Wire theme analysis into main processing flow

**Components:**
- Modified `process_ftn_content()` in `src/ftn_to_json.py` — calls analyze_themes() after story analysis, passes result to grouping
- Error handling for theme analysis failures — falls back to default themes

**Dependencies:** Phases 1-3 (all components exist)

**Done when:** Full pipeline produces JSON with dynamic themes when run on FTN content

### Phase 5: Curator Theme Review UI

**Goal:** Add theme review step to curator TUI

**Components:**
- `review_themes()` in `src/curator.py` — displays proposed themes, health summary, accept/override options
- Theme display using Rich tables — matches existing day display pattern
- Integration into main review flow — called before `review_unused()`

**Dependencies:** Phase 4 (pipeline produces theme metadata)

**Done when:** Curator shows theme summary at start and allows acceptance

### Phase 6: Theme Override Flow

**Goal:** Allow curator to override themes and re-group stories

**Components:**
- Override menu in `review_themes()` — edit theme names, revert to defaults
- `regroup_with_themes()` in `src/curator.py` — calls grouping function with new themes, updates working_data
- Re-display after override — shows updated assignments

**Dependencies:** Phase 5 (theme review UI exists)

**Done when:** Curator can override themes and see updated story assignments

## Additional Considerations

**Error handling:** Theme analysis LLM failures fall back to 4 default themes with logged warning. Invalid JSON responses retry once before fallback. Theme count != 4 triggers fallback.

**Soft dependency on issue #14:** This design assumes current paragraph-level story extraction. With sentence-level extraction (#14), theme clustering will have more content to work with, improving substitute theme quality. Implementation can proceed before #14 but will benefit from it.

**Thresholds are configurable:** Health thresholds (weak < 2 stories, overloaded > 6 stories) are initial values. May need tuning based on typical FTN newsletter content volume.
