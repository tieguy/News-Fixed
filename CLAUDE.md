# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**News, Fixed** is a Python application that transforms positive news content from Fix The News (https://fixthe.news) into a daily 2-page newspaper for children ages 10-14. The goal is to counter ambient negative news with evidence of human progress, formatted as a traditional black-and-white newspaper optimized for home printing.

## Issue Tracking with Beads

This project uses **beads** for distributed issue tracking. All issues are stored in `.beads/` and synced via git.

### Common Beads Commands

```bash
# Create an issue
bd create "Issue title" -d "Description" -p 1 -t bug

# List issues
bd list                  # All issues
bd list --status open    # Open issues only
bd ready                 # Issues ready to work on (no blockers)

# Show issue details
bd show <issue-id>

# Update issue status
bd update <issue-id> --status in_progress
bd close <issue-id> --reason "Completed"

# Work with dependencies
bd dep add <child-id> <parent-id> --type blocks
bd dep tree <issue-id>

# Labels
bd label add <issue-id> <label>
bd label list-all
```

**Important**: When working on tasks, use `bd ready --json` to find unblocked work. When discovering new issues during development, create them with `bd create` and link them to the parent task using `bd dep add <new-id> <parent-id> --type discovered-from`.

## Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

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
# Run with sample/test data
python main.py --input test_data/sample_ftn.txt --day 1

# Test PDF generation only
python -m src.pdf_generator

# Test QR code generation
python -m src.utils
```

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
