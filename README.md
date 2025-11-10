# News, Fixed

A daily 2-page newspaper for bright children (ages 10-14) that transforms positive news content from [Fix The News](https://fixthe.news) into engaging, print-ready reading material.

**Mission**: Counter ambient negative news with evidence of human progress, formatted as a traditional black-and-white newspaper optimized for home printing.

## Features

- 📰 2-page daily newspaper (front and back)
- 🖨️ High-contrast black & white design for easy home printing
- 📱 QR codes linking to original sources for verification
- 🎯 Age-appropriate content for 10-14 year olds
- 🤖 Powered by Claude AI for content adaptation
- 🏀 Duke basketball game schedules automatically included
- 📅 Mon-Thu editions with themed content each day

## Quick Start

```bash
# Clone and setup
git clone https://github.com/tieguy/News-Fixed.git
cd News-Fixed

# Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install firefox

# Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY from https://console.anthropic.com/

# Complete workflow (fetch, parse, and generate all 4 days):
./news-fixed run https://fixthenews.com/latest

# PDFs will be in output/ directory
```

## Usage

The `news-fixed` wrapper automatically activates the venv and provides a clean interface:

### Complete Pipeline (Recommended)

```bash
# Fetch, parse, and generate all 4 days in one command:
./news-fixed run https://fixthenews.com/latest
```

### Individual Steps

```bash
# 1. Fetch latest Fix The News issue
./news-fixed fetch https://fixthenews.com/latest

# 2. Parse HTML to JSON
./news-fixed parse data/raw/FTN-317.html

# 3. Curate stories (NEW - interactive review and categorization)
python code/curate.py data/processed/ftn-317.json
# Creates data/processed/ftn-317-curated.json
# Interactive CLI to fix auto-categorization, move stories, swap main/mini

# 4. Generate PDFs (all 4 days)
./news-fixed generate data/processed/ftn-317-curated.json --all

# Or generate single day
./news-fixed generate data/processed/ftn-317-curated.json --day 1

# Skip AI rewriting (faster, uses content as-is)
./news-fixed generate data/processed/ftn-317-curated.json --all --no-rewrite
```

See [docs/CURATION.md](docs/CURATION.md) for detailed curation guide.

### Test Mode

```bash
# Generate test newspaper with sample data (no API calls)
./news-fixed test
```

### First-Time Login to Fix The News

On your first fetch, you'll need to log in:

```bash
./news-fixed fetch https://fixthenews.com/latest --no-headless
# Browser opens - log in with your Substack credentials
# Press Enter in terminal when done
```

Subsequent fetches will use your saved session automatically.

## Project Structure

```
News-Fixed/
├── news-fixed                # Unified wrapper script (start here!)
├── README.md                 # This file
├── CLAUDE.md                 # AI assistant guidance
├── code/                     # Python source code
│   ├── src/                  # Core modules
│   │   ├── fetch_ftn_clean.py   # Fetch FTN content
│   │   ├── ftn_to_json.py       # Parse HTML to JSON
│   │   ├── parser.py            # Story categorization
│   │   ├── curator.py           # Interactive story curation
│   │   ├── generator.py         # Claude API integration
│   │   ├── pdf_generator.py     # PDF generation (WeasyPrint)
│   │   ├── sports_schedule.py   # Duke basketball schedules
│   │   └── utils.py             # QR codes, date helpers
│   ├── templates/            # HTML/CSS newspaper templates
│   ├── curate.py             # Interactive curation CLI
│   └── main.py               # PDF generator
├── data/
│   ├── raw/                  # FTN HTML downloads
│   ├── processed/            # Parsed JSON files
│   ├── sports/               # Basketball schedules (ICS files)
│   └── calendar/             # Family calendar events
├── output/                   # Generated PDFs
├── prompts/                  # Claude API prompts
├── docs/                     # Detailed documentation
└── venv/                     # Python virtual environment
```

## Issue Tracking

This project uses [beads](https://github.com/steveyegge/beads) for distributed issue tracking.

```bash
bd ready             # See actionable tasks
bd list              # View all issues
bd create "title"    # Create new issue
```

## Content Format

Each daily edition contains:

**Page 1 (Front)**
- Lead story (400-500 words)
- Feature box (Duke basketball games or quick wins)
- Tomorrow teaser (Mon-Wed only)

**Page 2 (Back)**
- 4-6 mini articles (100-150 words each)
- "By The Numbers" statistics section
- Footer with positive messaging

### Daily Themes
- **Monday (Day 1)**: Health & Education
- **Tuesday (Day 2)**: Environment & Conservation
- **Wednesday (Day 3)**: Technology & Energy
- **Thursday (Day 4)**: Society & Youth Movements

## Documentation

- **Quick Start:** This README
- **AI Assistance:** [CLAUDE.md](CLAUDE.md)
- **Documentation Index:** [docs/INDEX.md](docs/INDEX.md)
- **Fetching Guide:** [docs/FETCHING.md](docs/FETCHING.md)
- **Curation Guide:** [docs/CURATION.md](docs/CURATION.md)
- **Design Spec:** [docs/design-spec.md](docs/design-spec.md)

## Requirements

- Python 3.8+
- Anthropic API key (for Claude AI content rewriting)
- Fix The News subscription (for content)
- Firefox (installed via Playwright)

## License

[Blue Oak Model License 1.0.0](https://blueoakcouncil.org/license/1.0.0) - A modern, permissive open source license written in plain English.

This project is [REUSE 3.3 compliant](https://reuse.software/). All files contain clear copyright and licensing information.
