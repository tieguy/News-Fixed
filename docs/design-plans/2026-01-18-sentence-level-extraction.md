# Sentence-Level Story Extraction Design

## Summary

The News Fixed application currently extracts one story per paragraph from Fix The News content, even when a single paragraph contains multiple distinct topics each with their own source link. This design adds sentence-level story extraction to split these multi-link paragraphs into separate stories, increasing the total story count from ~22 to an estimated 50-60 per newsletter issue.

The approach inserts a new "Story Splitter" processing step between the existing HTML parser and the story analysis phase. When the parser encounters paragraphs containing 2+ external links, the splitter sends them to Claude API to identify topic boundaries within the paragraph. Claude returns each distinct topic as a separate split with its associated URL and a classification of whether it elaborates on the paragraph's introduction or stands alone. These splits are then converted into individual FTNStory objects and flow through the existing pipeline unchanged, providing more content options for theme assignment and daily edition curation.

## Definition of Done

1. Parser identifies multi-link paragraphs (2+ external links)
2. Multi-link paragraphs sent to Claude for story boundary detection
3. Claude returns distinct stories with: content, primary URL, relationship to intro (standalone/elaboration)
4. Single-link paragraphs extracted as before (no change)
5. Output: More stories per newsletter (estimated 50-60 vs current ~22)

## Glossary

- **Fix The News (FTN)**: A weekly positive news newsletter that serves as the source content for News Fixed. Each newsletter contains dozens of brief stories about human progress.
- **FTNStory**: The core data structure representing a single story extracted from Fix The News HTML. Contains title, content, source_url (primary attribution link), and all_urls (all links found in the story span).
- **Multi-link paragraph**: A paragraph from FTN content containing 2 or more external source URLs, often indicating multiple distinct stories condensed into one paragraph.
- **Story Splitter**: The new processing component that identifies multi-link paragraphs and uses Claude API to split them into separate stories at sentence boundaries.
- **Phase 1/Phase 2**: The existing two-stage LLM processing pipeline. Phase 1 analyzes individual stories for theme/audience fit. Phase 2 groups all stories into daily theme buckets.
- **Standalone vs Elaboration**: The relationship classification for split stories. "Standalone" stories have their own context; "elaboration" stories depend on the paragraph's introductory sentence for full meaning.

## Architecture

Post-parse story splitting via a dedicated processing step between HTML parsing and story analysis.

**Pipeline flow:**

```
FTN HTML
    ↓
Parser (unchanged)
    - extract_stories() returns List[FTNStory]
    - Multi-link stories pass through unmodified
    ↓
Story Splitter (NEW)
    - Identifies stories with 2+ URLs in all_urls
    - Sends to Claude for boundary detection
    - Returns expanded List[FTNStory]
    ↓
Phase 1: Story Analysis (unchanged)
    - Now processes more stories (~50-60 vs ~22)
    ↓
Phase 2: Story Grouping (unchanged)
    - More stories available for theme assignment
```

**Key components:**

- `split_multi_link_stories()` in `src/ftn_to_json.py` — filters stories by URL count, sends multi-link stories to Claude, returns expanded list
- Splitting prompt — instructs Claude to identify distinct topics, assign URLs, determine relationship to intro
- No changes to `parser.py` — parser stays pure (HTML → data)
- No changes to `FTNStory` data structure — title, content, source_url, all_urls all still apply

**Split decision criteria:**

| URL count | Action |
|-----------|--------|
| 0-1 URLs | Pass through unchanged |
| 2+ URLs | Send to Claude for splitting |

**Claude split output per story:**

```python
{
  "splits": [
    {
      "content": "Sentence(s) about this topic...",
      "primary_url": "https://source.com/...",
      "relationship": "standalone"  # or "elaboration"
    }
  ],
  "reasoning": "Brief explanation of split decision"
}
```

## Existing Patterns

Investigation found two-phase LLM processing in `src/ftn_to_json.py`:
- Phase 1: `analyze_story()` — per-story Claude API call returning structured JSON
- Phase 2: `group_stories_into_days()` — single Claude API call for all-story grouping

This design follows the same pattern:
- `split_multi_link_stories()` — per-multi-link-story Claude API call
- Uses "Return ONLY valid JSON" instruction per existing pattern
- Uses same model (Claude Sonnet) as existing phases

Investigation found `FTNStory` data structure in `src/parser.py`:
- `title`: First sentence extracted via regex
- `content`: Remaining text after title removed
- `source_url`: First valid URL for attribution
- `all_urls`: All filtered URLs from story span

Split stories use identical structure — each split becomes a new `FTNStory` with its own title/content/source_url derived from the split content.

## Implementation Phases

### Phase 1: Story Splitter Function

**Goal:** Add `split_multi_link_stories()` function that identifies and splits multi-link stories

**Components:**
- `split_multi_link_stories(stories, client)` in `src/ftn_to_json.py` — main entry point
- `_split_single_story(story, client)` in `src/ftn_to_json.py` — Claude API call for one story
- `_convert_splits_to_stories(splits, original_story)` in `src/ftn_to_json.py` — creates FTNStory objects from splits

**Dependencies:** None (new function, no existing code modified yet)

**Done when:** Function can take a list of stories, identify multi-link ones, call Claude for splitting, and return expanded list

### Phase 2: Splitting Prompt

**Goal:** Create Claude prompt that reliably identifies story boundaries within multi-link paragraphs

**Components:**
- Prompt template for splitting — input: story content + all_urls, output: JSON with splits array
- JSON schema validation — ensures required fields present in each split
- Relationship classification — standalone vs elaboration logic

**Dependencies:** Phase 1 (function structure exists)

**Done when:** Prompt reliably splits test cases from FTN-322 (the 5 multi-link paragraphs identified in investigation)

### Phase 3: Pipeline Integration

**Goal:** Wire splitting into main processing flow

**Components:**
- Modified `process_ftn_content()` in `src/ftn_to_json.py` — calls `split_multi_link_stories()` after parsing, before Phase 1 analysis
- Logging for split metrics — stories before/after, splits per story

**Dependencies:** Phases 1-2 (splitter function and prompt work)

**Done when:** Full pipeline produces expanded story list when run on FTN content

### Phase 4: Error Handling and Fallbacks

**Goal:** Graceful degradation when splitting fails

**Components:**
- API failure handling — keep original story on failure, log warning
- Invalid JSON handling — retry once, then keep original
- Validation — splits must have non-empty content and valid URL from original all_urls

**Dependencies:** Phase 3 (pipeline integration complete)

**Done when:** Pipeline continues successfully even when individual splits fail; metrics show which stories couldn't be split

## Additional Considerations

**API call budget:** Splitting adds ~5 API calls (one per multi-link story). Phase 1 analysis then processes ~50-60 stories instead of ~22. Total API calls roughly 2.5x current, but yields 2.5x more content.

**Relationship handling:** Stories marked "elaboration" inherit bold intro as context. Stories marked "standalone" extract title from their own first sentence. This preserves editorial coherence where appropriate.

**Downstream impact:** Issue #8 (dynamic theme suggestions) benefits directly — more stories means better theme clustering and more options for substitution/splitting of themes.
