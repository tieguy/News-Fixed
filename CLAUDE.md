# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**News, Fixed** is a Python application that transforms positive news content from Fix The News (https://fixthe.news) into a daily 2-page newspaper for children ages 10-14. The goal is to counter ambient negative news with evidence of human progress, formatted as a traditional black-and-white newspaper optimized for home printing.

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**
```bash
bd ready --json
```

**Create new issues:**
```bash
bd create "Issue title" -t bug|feature|task -p 0-4 --json
bd create "Issue title" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**
```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**
```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs with git:
- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python dependency management.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv automatically)
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

The `./news-fixed` script automatically uses `uv run` to execute commands in the managed environment, so you don't need to manually activate the virtual environment.

## Architecture

### Core Pipeline

1. **Input**: Fix The News content (via manual file, URL, or RSS feed)
2. **Processing**: Parse and categorize articles by theme
3. **Generation**: Use Claude API to rewrite content for target audience
4. **Output**: Generate 2-page PDF newspaper

### Module Structure

- `src/fetcher.py` - Fetch and parse Fix The News content
- `src/processor.py` - Categorize articles into daily themes (Health/Education, Environment, Technology, Society)
- `src/generator.py` - Claude API integration for content generation
- `src/pdf_generator.py` - Generate print-ready PDFs from HTML template
- `src/utils.py` - QR code generation and other utilities
- `main.py` - CLI orchestrator

### Content Flow

- One Fix The News weekly issue → 4 daily editions (Monday-Thursday)
- Each daily edition contains:
  - **Page 1**: Main story (400-500 words), feature box, tomorrow teaser
  - **Page 2**: 4-6 mini articles (100-150 words each), "By The Numbers" statistics section

### Templates

- `templates/newspaper.html` - Jinja2 template for newspaper layout
- `templates/styles.css` - High-contrast black & white styling for printing
- `prompts/*.txt` - Claude API prompt templates for different content types

## Running the Application

**Note**: FTN content input is flexible - no issue numbers required. Accept content via:
- Local file: `--input ftn_content.txt`
- URL: `--url https://fixthe.news/...`
- Stdin: `cat content.txt | python main.py`

```bash
# Generate a single day edition from FTN content file
python main.py --input ftn_content.txt --day 1 --output ./output/

# Generate all 4 days from FTN content
python main.py --input ftn_content.txt --all

# Specify output directory
python main.py --input ftn_content.txt --day 1 --output ~/Desktop/
```

## Testing

```bash
# Test PDF generation with sample data
python main.py --test

# Test parser
python -m src.parser FTN-315.html

# Test QR code generation
python -m src.utils
```

## Documentation

- **User Guide:** README.md (root)
- **Design & Technical:** docs/ directory
  - docs/design-spec.md - Original project requirements
  - docs/FETCHING.md - How to fetch FTN content

## Key Design Principles

1. **MVP First**: Prioritize getting a working newspaper on the breakfast table. Iterate on quality.
2. **Flexible Input**: Don't rely on FTN issue numbers - accept whatever FTN content is provided.
3. **Print Optimization**: All output must be high-contrast black & white for home printing/photocopying.
4. **Source Attribution**: Every article includes a QR code linking to the original source (not FTN, but the actual study/organization/news outlet).
5. **Age-Appropriate**: Write for bright 10-14 year olds - accessible but not patronizing.

## Content Guidelines

### Writing Style
- Target audience: Bright 10-14 year olds
- Use analogies (e.g., "like leveling up in a video game")
- Explain why news matters to young readers
- Emphasize youth agency and possibility
- No condescension

### Daily Themes
- Day 1: Health & Education
- Day 2: Environment & Conservation
- Day 3: Technology & Energy
- Day 4: Society & Youth Movements

## Configuration

- `config.py` - Configuration constants (newspaper dimensions, fonts, colors, API settings)
- `.env` - Environment variables (ANTHROPIC_API_KEY)

## Caching

The `cache/` directory stores:
- Fetched FTN content to avoid re-fetching
- Claude API responses to save costs during development
- Intermediate processed data

Cache files are JSON format and ignored by git.

## Future Enhancements

(Tracked in beads, not implemented yet)
- Family calendar integration
- Rotating single-panel cartoons
- "Dinner Table Question" section
- Weekend edition with puzzles
- Email subscription for automated delivery
