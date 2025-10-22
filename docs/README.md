# News, Fixed - Documentation

## Overview Documents

- **[design-spec.md](design-spec.md)** - Original project design and requirements
- **[FETCHING.md](FETCHING.md)** - Guide to fetching Fix The News content

## Project Structure

```
DailyNews/
├── README.md              # Quick start guide
├── CLAUDE.md              # AI assistant guidance
├── docs/                  # Design and technical documentation
├── src/                   # Python source code
├── templates/             # HTML/CSS newspaper templates
├── prompts/               # Claude API prompt templates
└── output/                # Generated PDFs
```

## Development Workflow

1. **Fetch FTN content** (see [FETCHING.md](FETCHING.md))
2. **Manual curation** - Create JSON files for each day
3. **Generate PDFs** - `python main.py --input day1.json --no-rewrite`

## Future Automation

See design-spec.md for planned features:
- Automated story parsing
- Theme-based categorization
- Full pipeline integration
- Family calendar integration
- Cartoon rotation
