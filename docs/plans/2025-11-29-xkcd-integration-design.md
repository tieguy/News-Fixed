# xkcd Integration Design

**Date:** 2025-11-29
**Status:** Approved
**Goal:** Add weekly xkcd comic to the newspaper, with human-in-the-loop selection and persistent rejection tracking.

## Overview

Include one xkcd comic per week in the newspaper. The system fetches recent comics, uses Claude vision to analyze them for age-appropriateness and panel count, presents 2-3 candidates for human selection, and stores rejection decisions persistently to avoid re-evaluating unsuitable comics.

## Requirements

- Target audience: ages 10-14
- Only single-panel comics (multi-panel won't fit the layout)
- Human makes final selection from AI-curated candidates
- Rejected comics are stored with reason category, never shown again
- Cache comic metadata and analysis to avoid redundant API calls
- Works as standalone CLI command or integrated into newspaper generation

## Data Model

### data/xkcd_cache.json

Comic metadata and AI analysis results. Keyed by comic number.

```json
{
  "3174": {
    "num": 3174,
    "title": "Example Comic",
    "alt": "The alt text hover...",
    "img": "https://imgs.xkcd.com/comics/example.png",
    "date": "2025-11-28",
    "fetched_at": "2025-11-29T10:00:00Z",
    "analysis": {
      "panel_count": 1,
      "age_appropriate": true,
      "requires_specialized_knowledge": false,
      "knowledge_domains": [],
      "topic_tags": ["science", "humor"],
      "brief_summary": "A joke about...",
      "analyzed_at": "2025-11-29T10:00:05Z"
    }
  }
}
```

### data/xkcd_rejected.json

Blocklist of comics marked as unsuitable. Never shown as candidates again.

```json
{
  "3150": {"reason": "too_complex", "rejected_at": "2025-11-20"},
  "3145": {"reason": "adult_humor", "rejected_at": "2025-11-19"}
}
```

**Rejection categories:**
- `too_complex` - Joke is too sophisticated for target age
- `adult_humor` - Mature themes or innuendo
- `too_dark` - Morbid or disturbing content
- `multi_panel` - Not single-panel (if AI miscounted)
- `requires_context` - Needs knowledge of current events or xkcd lore
- `other` - Catch-all

### data/xkcd_selected.json

Record of which comics were used in which week's paper.

```json
{
  "2025-W48": {"num": 3170, "selected_at": "2025-11-25"},
  "2025-W47": {"num": 3165, "selected_at": "2025-11-18"}
}
```

## CLI Interface

```bash
./news-fixed xkcd [subcommand]
```

### Subcommands

| Command | Description |
|---------|-------------|
| `fetch` | Fetch last 10 comics from xkcd API, analyze any not in cache |
| `candidates` | Show 2-3 recommended candidates for this week |
| `select <num>` | Mark comic as selected for current week |
| `reject <num> <reason>` | Add comic to rejection list |
| `show <num>` | Display comic details and analysis |

### Integration with Newspaper Generation

When generating a newspaper, if no comic selected for current week:
1. Check for viable candidates in cache
2. If insufficient, fetch and analyze recent comics
3. Present candidates, prompt for selection
4. Include selected comic in PDF

## Candidate Selection Logic

Applied in order:

1. **Not rejected** - Filter out comics in rejection list
2. **Not recently used** - Filter out comics used in last 8 weeks
3. **Single-panel** - Only `panel_count == 1`
4. **Age-appropriate** - `age_appropriate == true`
5. **Accessible humor** - `requires_specialized_knowledge == false`
6. **Sort by recency** - Prefer newer comics
7. **Return top 3** - Present as candidates

## AI Analysis

One Claude API call per comic (cached forever):

**Input:** Comic image + metadata (title, alt text)

**Prompt:**
```
Analyze this xkcd comic for use in a children's newspaper (ages 10-14).

Return JSON:
{
  "panel_count": <int>,
  "age_appropriate": <bool>,
  "requires_specialized_knowledge": <bool>,
  "knowledge_domains": [<strings if applicable>],
  "topic_tags": [<strings>],
  "brief_summary": "<1-2 sentences explaining the joke>"
}

Age-appropriate means: no adult themes, violence, or mature humor.
Specialized knowledge means: requires understanding of programming,
advanced math, obscure science, or niche internet culture to get the joke.
```

**Output:** Cached in `xkcd_cache.json` under `analysis` key.

## Template Integration

Add to `newspaper.typ` on page 2, above the footer:

```typst
// === XKCD COMIC ===
#v(10pt)
#line(length: 100%, stroke: 1pt + black)
#v(6pt)
#grid(
  columns: (auto, 1fr),
  column-gutter: 12pt,
  [#image("{{XKCD_IMAGE}}", width: 2in)],
  [
    #text(size: 10pt, weight: "bold")[xkcd: {{XKCD_TITLE}}]
    #v(4pt)
    #text(size: 8pt, style: "italic")[{{XKCD_ALT}}]
  ]
)
```

Comic image is downloaded locally for Typst inclusion.

## Module Structure

**New file:** `code/src/xkcd.py`

### Functions

| Function | Description |
|----------|-------------|
| `fetch_recent_comics(count=10)` | Fetch metadata from xkcd API |
| `analyze_comic(comic_data)` | Claude vision API call, returns analysis |
| `get_candidates()` | Apply selection logic, return top 3 |
| `select_comic(num)` | Record selection for current week |
| `reject_comic(num, reason)` | Add to rejection list |
| `get_selected_for_week(week_date)` | Check if comic already selected |
| `download_comic_image(num, dest_path)` | Download image for PDF |
| `load_cache()` / `save_cache()` | JSON file I/O |
| `load_rejected()` / `save_rejected()` | JSON file I/O |
| `load_selected()` / `save_selected()` | JSON file I/O |

### Integration Points

- **CLI:** Add `xkcd` subcommand to `news-fixed` script
- **PDF generator:** Modify `pdf_generator_typst.py` to accept xkcd data and substitute template variables

## File Changes Summary

| File | Change |
|------|--------|
| `code/src/xkcd.py` | New file - xkcd module |
| `code/templates/newspaper.typ` | Add xkcd section on page 2 |
| `code/src/pdf_generator_typst.py` | Accept xkcd data, download image |
| `news-fixed` | Add xkcd subcommand |
| `data/xkcd_cache.json` | New file - created at runtime |
| `data/xkcd_rejected.json` | New file - created at runtime |
| `data/xkcd_selected.json` | New file - created at runtime |
