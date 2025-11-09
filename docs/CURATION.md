# Story Curation Guide

## Overview

The story curation CLI (`code/curate.py`) provides an interactive workflow for manually reviewing and organizing FTN stories before newspaper generation.

## Workflow

### 1. Auto-Categorization

First, run `ftn_to_json.py` to parse FTN HTML and auto-categorize stories:

```bash
python code/src/ftn_to_json.py data/ftn/FTN-316.html
```

This creates `data/ftn/ftn-316.json` with stories assigned to days based on keyword matching.

### 2. Interactive Curation

Run the curation tool to review and fix categorization:

```bash
python code/curate.py data/ftn/ftn-316.json
```

You'll see an overview table showing all 4 days with their stories, then review each day interactively.

### 3. Review Actions

For each day, you can:

- **[A]ccept as-is** - Move to next day
- **[M]ove stories** - Reassign stories to different days
- **[S]wap main/mini** - Change which story is the main feature
- **[V]iew details** - Read full story content before deciding
- **[B]ack** - Return to previous day to revise

### 4. Moving Stories

When moving a story:

1. Select story number (1 = main, 2+ = minis)
2. Choose target day (1-4)
3. If target day is full (5 stories), choose:
   - **Swap** - Exchange with a story from target day
   - **Replace** - Remove a story from target day
   - **Cancel** - Abort the move

### 5. Save and Generate

After reviewing all 4 days:

1. Review summary of changes
2. Validate data (checks for missing main stories, etc.)
3. Save to `{original}-curated.json`
4. Run main.py to generate PDFs

## Tips

- **Length matters**: Main stories should be 400-500 words, minis 100-150 words
- **Theme alignment**: Day 1 = Health/Education, Day 2 = Environment, Day 3 = Technology, Day 4 = Society
- **View before moving**: Use [V]iew to check story content when unsure about categorization
- **Dry run first**: Use `--dry-run` to preview without saving changes

## Common Scenarios

### Story in wrong day

Day 3 has a health story that belongs in Day 1:

1. Review Day 3
2. Choose [M]ove stories
3. Select the misplaced story
4. Choose Day 1 as target

### Wrong main story

Day 2's longest story is boring, but mini #2 is more compelling:

1. Review Day 2
2. Choose [S]wap main/mini
3. Select mini #2 as new main

### Too many stories in one day

Day 1 has 7 stories, Day 2 has only 3:

1. Review Day 1
2. Move 2-3 stories to Day 2
3. Keep best 5 in Day 1

## Output Format

Curated JSON has same structure as input:

```json
{
  "day_1": {
    "theme": "Health & Education",
    "main_story": { "title": "...", "content": "...", "source_url": "..." },
    "mini_articles": [
      { "title": "...", "content": "...", "source_url": "..." },
      ...
    ],
    "statistics": [],
    "tomorrow_teaser": ""
  },
  ...
}
```

Compatible with `main.py --input`.

## Troubleshooting

**"Day X has no main story"**
- You moved all stories out of a day
- Solution: Move at least one story back, or delete the empty day from JSON manually

**"Overflow handling" message**
- Target day already has 5 stories (max)
- Solution: Swap/replace an existing story, or move to a different day

**Changes not saving**
- Using `--dry-run` flag
- Solution: Remove flag to save changes
