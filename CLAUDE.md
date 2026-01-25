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

**Entry Points:**
- `code/src/main.py` - Interactive CLI for local generation (family mode default)
- `code/src/scheduled_generate.py` - Unattended web generation for fly.io (friends mode default)
- `code/src/web.py` - Flask web server for PDF downloads

**Content Pipeline:**
- `code/src/parser.py` - Parse Fix The News HTML into structured data
- `code/src/ftn_to_json.py` - Categorize articles into 4-day format using Claude
- `code/src/content_generation.py` - Shared content generation logic (mode detection, AI rewriting)
- `code/src/generator.py` - Claude API integration for content rewriting
- `code/src/pdf_generator.py` - Generate print-ready PDFs from HTML templates

**Supporting:**
- `code/src/cache.py` - PDF caching for web downloads
- `code/src/utils.py` - QR code generation and theme utilities
- `code/src/xkcd.py` - XKCD comic selection (family mode only)
- `code/src/sports_schedule.py` - Duke basketball schedule (family mode only)
- `code/src/readwise_fetcher.py` - Local SF news from Readwise (family mode only)

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

### Local CLI (Family Mode)

```bash
# Generate a single day edition from FTN JSON
./news-fixed --input ftn-content.json --day 1

# Generate all 4 days
./news-fixed --input ftn-content.json --all

# Generate combined 4-day PDF
./news-fixed --input ftn-content.json --combined

# Skip AI rewriting (use content as-is)
./news-fixed --input ftn-content.json --day 1 --no-rewrite
```

### Web/Scheduled (Friends Mode)

The scheduled generator runs automatically on fly.io, but can be triggered manually:

```bash
# On fly.io
fly ssh console -C "uv run python /app/code/src/scheduled_generate.py"

# Locally (for testing)
NEWS_MODE=friends uv run python code/src/scheduled_generate.py
```

## Testing

```bash
# Run all tests
PYTHONPATH=code/src uv run pytest code/src/

# Test PDF generation with sample data
./news-fixed --test

# Test specific module
PYTHONPATH=code/src uv run pytest code/src/test_ftn_to_json.py -v
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

**Environment Variables (.env):**
- `ANTHROPIC_API_KEY` - Required for Claude API content generation
- `NEWS_MODE` - Content mode: `family` (personalized) or `friends` (generic)
  - `family`: Includes Duke sports, SF local news, XKCD comics
  - `friends`: Generic content only, second main story instead of personalized features
  - CLI defaults to `family`, web deployment defaults to `friends`

**Config Files:**
- `fly.toml` - Fly.io deployment configuration
- `code/.env.example` - Template for local environment variables

## Web Deployment (fly.io)

The app runs on fly.io with scheduled PDF generation:

- **URL**: https://news-fixed.fly.dev/
- **Cron**: Mondays at 6 AM UTC generates the week's PDF
- **Mode**: `NEWS_MODE=friends` (no personalized content)

```bash
fly deploy          # Deploy changes
fly status          # Check app status
fly ssh console     # SSH into container
fly logs            # View logs
```

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
