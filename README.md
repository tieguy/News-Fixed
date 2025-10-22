# News, Fixed

A daily 2-page newspaper for bright children (ages 10-14) that transforms positive news content from [Fix The News](https://fixthe.news) into engaging, print-ready reading material.

**Mission**: Counter ambient negative news with evidence of human progress, formatted as a traditional black-and-white newspaper optimized for home printing.

## Features

- 📰 2-page daily newspaper (front and back)
- 🖨️ High-contrast black & white design for easy home printing
- 📱 QR codes linking to original sources for verification
- 🎯 Age-appropriate content for 10-14 year olds
- 🤖 Powered by Claude AI for content adaptation

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd DailyNews

# Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install firefox

# Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY from https://console.anthropic.com/

# One-time: Log in to Fix The News
python login_to_ftn.py
# (Browser opens - log in, then Ctrl+C when done)

# Weekly workflow (run on Sunday night):
python -m code.src.fetch_ftn_clean                # Fetch latest FTN
python -m code.src.ftn_to_json data/ftn/FTN-XXX.html  # Convert to JSON
./news-fixed --input data/ftn/ftn-XXX.json --all --no-rewrite  # Generate 4 PDFs
```

## Usage

```bash
# Fetch latest Fix The News issue
python -m code.src.fetch_ftn_clean

# Convert FTN HTML to 4-day JSON
python -m code.src.ftn_to_json data/ftn/FTN-315.html

# Generate all 4 days (Mon-Thu) with correct dates
./news-fixed --input data/ftn/ftn-315.json --all --no-rewrite

# Output files: news_fixed_2025-10-20.pdf, news_fixed_2025-10-21.pdf, etc.
# (Filenames include publication date for easy sorting)
```

## Project Structure

```
DailyNews/
├── code/                     # Source code
│   ├── src/                  # Python modules
│   │   ├── fetch_ftn_clean.py   # Fetch FTN using Firefox reader mode
│   │   ├── ftn_to_json.py       # Convert FTN HTML to 4-day JSON
│   │   ├── parser.py            # Parse and categorize FTN stories
│   │   ├── generator.py         # Claude API integration
│   │   ├── pdf_generator.py     # PDF creation
│   │   ├── sports_schedule.py   # Duke basketball schedules
│   │   └── utils.py             # QR codes, date helpers
│   ├── templates/            # HTML/CSS newspaper templates
│   └── main.py              # Main newspaper generator
├── data/                     # Data files
│   ├── ftn/                  # Fix The News downloads & JSON
│   ├── sports/               # Duke basketball ICS schedules
│   └── calendar/             # Family calendar events
├── output/                   # Generated PDFs
├── prompts/                  # Claude API prompts
├── news-fixed                # Wrapper script (use this!)
└── login_to_ftn.py           # One-time FTN login helper
```

## Issue Tracking

This project uses [beads](https://github.com/steveyegge/beads) for distributed issue tracking.

```bash
bd list              # View all issues
bd ready             # See actionable tasks
bd create "title"    # Create new issue
```

## Content Format

Each daily edition contains:

**Page 1 (Front)**
- Lead story (200-300 words)
- 2-3 secondary stories (100-150 words each)
- Feature box (Duke basketball games or quick wins)
- Tomorrow teaser (Mon-Wed only)

**Page 2 (Back)**
- 4-6 mini articles (100-150 words each)
- "By The Numbers" statistics section
- Footer with positive messaging

### Daily Themes
- **Day 1**: Health & Education
- **Day 2**: Environment & Conservation
- **Day 3**: Technology & Energy
- **Day 4**: Society & Youth Movements

## Documentation

- **Quick Start:** This README
- **AI Assistance:** [CLAUDE.md](CLAUDE.md)
- **Detailed Docs:** [docs/](docs/) - Design specs, fetching guides, etc.

## License

MIT
