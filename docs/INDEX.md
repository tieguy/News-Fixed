# News, Fixed - Documentation

## Overview Documents

- **[design-spec.md](design-spec.md)** - Original project design and requirements
- **[FETCHING.md](FETCHING.md)** - Guide to fetching Fix The News content

## Project Structure

```
DailyNews/
├── news-fixed             # Unified wrapper script
├── README.md              # Quick start guide
├── CLAUDE.md              # AI assistant guidance
├── docs/                  # Design and technical documentation
├── code/
│   ├── src/               # Python source code
│   ├── templates/         # HTML/CSS newspaper templates
│   └── main.py            # PDF generator
├── prompts/               # Claude API prompt templates
├── data/
│   ├── raw/               # FTN HTML downloads
│   └── processed/         # Parsed JSON files
└── output/                # Generated PDFs
```

## Development Workflow

### Complete Pipeline (Recommended)

```bash
./news-fixed run https://fixthenews.com/latest
```

This will:
1. Fetch FTN content to `data/raw/`
2. Parse HTML to JSON in `data/processed/`
3. Generate all 4 PDFs in `output/`

### Individual Steps

```bash
# 1. Fetch FTN content
./news-fixed fetch https://fixthenews.com/latest

# 2. Parse HTML to JSON
./news-fixed parse data/raw/FTN-317.html

# 3. Generate PDFs
./news-fixed generate data/processed/ftn-317.json --all

# Or generate single day without AI rewriting (faster)
./news-fixed generate data/processed/ftn-317.json --day 1 --no-rewrite
```

### Test Mode

```bash
# Generate test newspaper with sample data (no API calls)
./news-fixed test
```

## Features

- ✅ Automated FTN content fetching with browser automation
- ✅ Intelligent story parsing and categorization by theme
- ✅ AI-powered content rewriting for 10-14 year olds
- ✅ Duke basketball game schedules in feature boxes
- ✅ 2-page print-optimized PDFs
- ✅ QR codes linking to original sources
- ✅ High-contrast black & white for photocopying
