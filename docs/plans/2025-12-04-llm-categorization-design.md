# LLM-Based Story Categorization - Design Document

**Date:** 2025-12-04

**Goal:** Replace keyword-based story categorization with Claude API-powered two-phase categorization for better accuracy and balanced day assignments.

## Problem

Current keyword matching in `parser.py` has two issues:
1. Stories end up in "unused" when they clearly fit a category (narrow keyword lists)
2. Stories get assigned to wrong categories (no semantic understanding)

## Solution

Two-phase Claude API approach:

### Phase 1: Per-Story Analysis
For each story, Claude extracts:
- Primary theme (health_education, environment, technology_energy, society)
- Secondary themes (free-form tags)
- Age appropriateness (high/medium/low)
- Story strength (high/medium/low)
- Suggested role (main/mini)
- Primary source URL (best attribution from all URLs)
- TUI headline (40-50 chars)

### Phase 2: Holistic Grouping
One API call with all stories produces complete 4-day assignment:
- Balances story count across days (aim for 4-5 per day)
- Assigns main (longest/strongest) and minis per day
- Considers both primary and secondary themes
- Respects blocklist
- Returns reasoning for key decisions

## Files Changed

| File | Change |
|------|--------|
| `code/src/parser.py` | Add `all_urls` field to FTNStory; remove `categorize_stories()` |
| `code/src/ftn_to_json.py` | Add `analyze_story()`, `group_stories_into_days()`, `parse_llm_json()` |

## Error Handling

- JSON parsing: Strip markdown fences, retry with error context on failure
- Phase 1 failure: Mark story as unused with warning
- Phase 2 failure: Fall back to length-based assignment

## Future Work

- `News-Fixed-4cg`: Allow LLM to suggest/adjust day themes based on content
