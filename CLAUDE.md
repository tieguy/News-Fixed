# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**News, Fixed** is a Python application that transforms positive news content from Fix The News (https://fixthe.news) into a daily 2-page newspaper for children ages 10-14. The goal is to counter ambient negative news with evidence of human progress, formatted as a traditional black-and-white newspaper optimized for home printing.

## Issue Tracking with Chainlink

**IMPORTANT**: This project uses **chainlink** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why Chainlink?

- Local-first: SQLite storage in `.chainlink/issues.db`, no external dependencies
- Session management: Preserves context across AI coding sessions with handoff notes
- Dependency-aware: Track blockers and relationships between issues
- Smart recommendations: `chainlink next` suggests prioritized work based on blockers
- Hierarchical: Support for subissues, milestones, and related issue linking

### Quick Start

**Check for ready work:**
```bash
chainlink ready      # Show unblocked issues
chainlink next       # Get recommended next task
```

**Create new issues:**
```bash
chainlink create "Issue title" -p high|medium|low
chainlink create "Issue title" -p high -d "Description here"
```

**Manage issues:**
```bash
chainlink show <id>       # View issue details
chainlink list            # List all open issues
chainlink close <id>      # Mark complete
chainlink update <id> -p medium  # Change priority
```

**Dependencies:**
```bash
chainlink block <id> <blocker_id>  # Mark as blocked by another issue
chainlink blocked                   # Show all blocked issues
```

### Session Workflow (AI Agent Handoffs)

```bash
chainlink session start          # Begin work, shows prior handoff notes
chainlink session work <id>      # Set current focus
chainlink session end --notes "Progress made, next steps..."
```

### Priorities

- `critical` - Security, data loss, broken builds
- `high` - Major features, important bugs
- `medium` - Default, nice-to-have
- `low` - Polish, optimization, backlog

### Workflow for AI Agents

1. **Start session**: `chainlink session start` to see prior context
2. **Find work**: `chainlink next` or `chainlink ready`
3. **Focus**: `chainlink session work <id>`
4. **Work on it**: Implement, test, document
5. **Discover new work?** Create linked issue:
   - `chainlink create "Found bug" -p high`
   - `chainlink block <new_id> <parent_id>` (if blocked)
6. **Complete**: `chainlink close <id>`
7. **End session**: `chainlink session end --notes "Summary of progress"`

### Organization Features

```bash
chainlink subissue <parent_id> "Subtask title"  # Create child issue
chainlink label <id> <label>                     # Add labels
chainlink relate <id1> <id2>                     # Link related issues
chainlink tree                                   # Visualize hierarchy
```

### Important Rules

- Use chainlink for ALL task tracking
- Start/end sessions with handoff notes for AI continuity
- Check `chainlink next` before asking "what should I work on?"
- Do NOT create markdown TODO lists
- Do NOT use external issue trackers
- Do NOT duplicate tracking systems

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python dependency management.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv automatically)
uv sync

# Install Firefox browser for Playwright (required for fetching FTN content)
uv run playwright install firefox

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

(Tracked in chainlink, not implemented yet)
- Family calendar integration
- Rotating single-panel cartoons
- "Dinner Table Question" section
- Weekend edition with puzzles
- Email subscription for automated delivery
