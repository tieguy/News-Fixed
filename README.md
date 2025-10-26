# News, Fixed

A daily 2-page newspaper for bright children (ages 10-14) that transforms positive news content from [Fix The News](https://fixthe.news) into engaging, print-ready reading material.

**Mission**: Counter ambient negative news with evidence of human progress, formatted as a traditional black-and-white newspaper optimized for home printing.

## Features

- 📰 2-page daily newspaper (front and back)
- 🖨️ High-contrast black & white design for easy home printing
- 📱 QR codes linking to original sources for verification
- 🎯 Age-appropriate content for 10-14 year olds
- 🤖 Powered by Claude AI for content adaptation
- 📐 Professional typesetting with Typst for reliable print layouts

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
cd code
python login_to_ftn.py
# (Browser opens - log in, then press Enter when done)

# Weekly workflow (run Thursday night after FTN publishes):
cd code
python src/fetch_ftn_clean.py --url "https://fixthenews.com/p/ISSUE-URL" --output .
python src/ftn_to_json.py FTN-XXX.html
python main.py --input ftn-XXX.json --all  # Uses Claude AI to adapt content

# Or from project root using wrapper:
cd ..
./news-fixed --input code/ftn-XXX.json --all
```

## Usage

### From the `code/` directory:

```bash
cd code

# 1. Fetch latest Fix The News issue (provide the exact article URL)
python src/fetch_ftn_clean.py --url "https://fixthenews.com/p/316-hope-painting-with-fire-global" --output .

# 2. Convert FTN HTML to 4-day JSON
python src/ftn_to_json.py FTN-316.html

# 3. Generate all 4 days with Claude AI rewriting (default)
python main.py --input ftn-316.json --all

# Output files: output/news_fixed_2025-10-28.pdf, news_fixed_2025-10-29.pdf, etc.
# (Filenames include publication date for easy sorting)
```

### From the project root:

```bash
# Use the wrapper script
./news-fixed --input code/ftn-316.json --all
```

### Additional Options:

```bash
# Fetch with visible browser (for debugging)
python src/fetch_ftn_clean.py --url "URL" --no-headless --output .

# Generate single day
python main.py --input ftn-316.json --day 1 --date 2025-10-28

# Skip AI rewriting (faster, uses raw FTN content)
python main.py --input ftn-316.json --all --no-rewrite

# Generate test newspaper with sample data
python main.py --test
```

## Project Structure

```
DailyNews/
├── code/                     # Source code
│   ├── src/                  # Python modules
│   │   ├── fetch_ftn_clean.py      # Fetch FTN using Firefox reader mode
│   │   ├── ftn_to_json.py          # Convert FTN HTML to 4-day JSON
│   │   ├── parser.py               # Parse and categorize FTN stories
│   │   ├── generator.py            # Claude API integration
│   │   ├── pdf_generator_typst.py  # PDF generation with Typst
│   │   ├── pdf_generator.py        # Legacy HTML/CSS generator
│   │   ├── sports_schedule.py      # Duke basketball schedules
│   │   └── utils.py                # QR codes, date helpers
│   ├── templates/            # Newspaper templates
│   │   ├── newspaper.typ     # Typst template (current)
│   │   ├── newspaper.html    # HTML template (legacy)
│   │   └── styles.css        # CSS styles (legacy)
│   ├── output/               # Generated PDFs
│   ├── cache/                # QR code cache
│   ├── main.py               # Main newspaper generator
│   └── login_to_ftn.py       # One-time FTN login helper
├── prompts/                  # Claude API prompts
├── venv/                     # Python virtual environment
└── news-fixed                # Wrapper script (use from root)
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
