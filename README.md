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

# Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY from https://console.anthropic.com/

# Generate a newspaper
python main.py --input ftn_content.txt --day 1
```

## Usage

```bash
# Generate Day 1 from Fix The News content
python main.py --input ftn_content.txt --day 1

# Generate all 4 days from one FTN issue
python main.py --input ftn_content.txt --all

# Specify output directory
python main.py --input ftn_content.txt --day 1 --output ~/Desktop/
```

## Project Structure

```
DailyNews/
├── src/                    # Python modules
│   ├── fetcher.py         # Fetch FTN content
│   ├── processor.py       # Categorize articles
│   ├── generator.py       # Claude API integration
│   ├── pdf_generator.py   # PDF creation
│   └── utils.py           # QR codes, helpers
├── templates/             # HTML/CSS newspaper templates
├── prompts/               # Claude API prompts
├── output/                # Generated PDFs
└── cache/                 # Cached content
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
- Main story (400-500 words)
- Feature box or "quick wins"
- Tomorrow teaser

**Page 2 (Back)**
- 4-6 mini articles (100-150 words each)
- "By The Numbers" statistics section
- Footer with positive messaging

### Daily Themes
- **Day 1**: Health & Education
- **Day 2**: Environment & Conservation
- **Day 3**: Technology & Energy
- **Day 4**: Society & Youth Movements

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development guidance.

## License

MIT
