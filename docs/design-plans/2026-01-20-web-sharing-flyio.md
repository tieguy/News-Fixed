# Web Sharing via fly.io Design

## Summary

This design extends the News Fixed newspaper generation pipeline with a public-facing web application deployed on fly.io. The application serves a single weekly combined PDF (8 pages covering Monday-Thursday) through a minimalist landing page. Instead of the current CLI workflow requiring manual execution, an autonomous scheduled task generates new editions every Sunday night, caching the result for instant downloads throughout the week.

The implementation reuses all existing content pipeline components (fetcher, processor, generator, pdf_generator) but introduces three key changes: (1) feature flags to disable personalized content (Duke basketball, SF local news, XKCD) for the public version, (2) a second main story to fill the space vacated by those features, and (3) a Flask web layer with caching to serve pre-generated PDFs. Deployment on fly.io provides persistent storage for cached PDFs and a scheduled machine for weekly regeneration, positioning the project for eventual handoff to the Fix The News team with minimal operational overhead.

## Definition of Done

- Flask web app running on fly.io serving a landing page
- Single "Download This Week's Edition" button returns combined 4-day PDF
- Autonomous weekly generation via scheduled task (no upload endpoint)
- Default configuration: Duke basketball OFF, SF local news OFF, XKCD OFF
- Second main story fills space vacated by disabled features
- Pre-generated PDFs cached by week for instant downloads
- Existing code reused: fetcher, processor, generator, pdf_generator
- Private alpha messaging on landing page (friend-of-Luis tone)

## Glossary

- **Flask**: Lightweight Python web framework used to create the landing page and download endpoints
- **fly.io**: Platform-as-a-service (PaaS) for deploying containerized applications with persistent volume storage and scheduled task support
- **WeasyPrint**: Python library that converts HTML/CSS to PDF, used by the existing pdf_generator module
- **Persistent Volume**: Storage on fly.io that survives VM restarts, required for caching weekly PDFs
- **Scheduled Machine**: fly.io feature that runs a VM on a cron-like schedule (used for Sunday night generation)
- **ISO Week**: International standard week numbering (YYYY-WWW format, e.g., "2026-W03" for the 3rd week of 2026)
- **Fix The News (FTN)**: Source publication providing positive news stories that feed the News Fixed pipeline
- **RSS Feed**: Syndication format providing structured access to FTN's published content
- **Feature Flags**: Environment variables controlling whether optional features (Duke basketball, SF local news, XKCD) are enabled
- **Playwright**: Browser automation library used by the existing fetcher for web scraping when RSS is insufficient
- **Combined PDF**: Single 8-page document containing all four daily editions (Monday-Thursday) of a week
- **ntfy.sh**: Simple notification service for alerting when scheduled generation completes or fails

## Architecture

Flask web application deployed on fly.io, reusing the existing News Fixed pipeline.

**Components:**

```
┌─────────────────────────────────────────────────────────┐
│                      fly.io VM                          │
├─────────────────────────────────────────────────────────┤
│  Flask App                                              │
│  ├── Landing page (/)                                   │
│  ├── Download endpoint (/download)                      │
│  └── Health check (/health)                             │
├─────────────────────────────────────────────────────────┤
│  Generation Pipeline (reused from CLI)                  │
│  ├── src/fetcher.py      → Fetch FTN content           │
│  ├── src/processor.py    → Categorize stories          │
│  ├── src/generator.py    → Claude API rewriting        │
│  └── src/pdf_generator.py → WeasyPrint output          │
├─────────────────────────────────────────────────────────┤
│  Persistent Volume                                      │
│  └── cache/                                             │
│      └── YYYY-WWW/       → Weekly cached PDFs          │
│          ├── combined.pdf                               │
│          └── content.json                               │
└─────────────────────────────────────────────────────────┘
```

**Request flow:**

1. User visits `/` → Render landing page with current week info
2. User clicks download → `/download` checks cache
3. If cached → Return PDF immediately
4. If not cached → Generate (rare, only if scheduled job failed)

**Scheduled generation:**

fly.io scheduled machine runs weekly (Sunday night) to:
1. Fetch current FTN content via RSS or existing fetcher
2. Run processor with default story selection
3. Generate content via Claude API
4. Render combined 4-day PDF
5. Cache result for the week

## Existing Patterns

Investigation found the following patterns in the current codebase:

**CLI orchestration in `code/src/main.py`:**
- Click-based CLI with `--day`, `--input`, `--output` options
- Calls generator and pdf_generator sequentially
- Feature integration (sports, local news, xkcd) controlled by conditional logic

**Configuration via environment variables:**
- `ANTHROPIC_API_KEY` for Claude API
- `READWISE_TOKEN` for SF local news
- No centralized config file; settings distributed in code

**Caching patterns:**
- XKCD cache in `data/xkcd_cache.json`
- SF articles tracking in `data/sf_articles_used.json`
- QR code cache in `code/cache/qr_codes/`

**This design follows existing patterns:**
- Reuses existing module structure (`src/*.py`)
- Extends environment variable pattern for feature flags
- Follows existing cache directory structure

**New patterns introduced:**
- Flask web layer (no existing web code)
- Scheduled generation (CLI is currently manual)
- Combined multi-day PDF output (currently generates individual days)

## Implementation Phases

### Phase 1: Feature Flag Configuration

**Goal:** Make Duke/SF/XKCD features configurable via environment variables

**Components:**
- Feature flags in `code/src/main.py` reading from environment:
  - `FEATURE_DUKE_SPORTS` (default: "false" for web, "true" for local)
  - `FEATURE_SF_LOCAL` (default: "false" for web, "true" for local)
  - `FEATURE_XKCD` (default: "false" for web, "true" for local)
- Conditional logic wrapping existing feature integrations

**Dependencies:** None (first phase)

**Done when:** Running with `FEATURE_DUKE_SPORTS=false` skips Duke basketball integration; same for other features

### Phase 2: Second Main Story Generation

**Goal:** Generate a second main story to fill space when features are disabled

**Components:**
- New prompt in `code/prompts/second_main_story.txt` — similar to main story but for secondary placement
- Generator method in `code/src/generator.py` — `generate_second_main_story()`
- Template updates in `code/templates/newspaper.html` — conditional second story block in feature box area
- Processor logic in `code/src/processor.py` — select second-best story for main treatment

**Dependencies:** Phase 1 (feature flags determine when second story is needed)

**Done when:** When Duke/SF disabled, a second main story renders in their place with appropriate styling

### Phase 3: Combined Multi-Day PDF

**Goal:** Generate single PDF containing all 4 daily editions

**Components:**
- New function in `code/src/pdf_generator.py` — `generate_combined_pdf()` that renders 4 days sequentially
- Template modifications in `code/templates/newspaper.html` — page break handling between days
- CLI option in `code/src/main.py` — `--combined` flag for local testing

**Dependencies:** Phase 2 (second main story may appear in combined output)

**Done when:** `./news-fixed --combined` produces single 8-page PDF with all 4 days

### Phase 4: Flask Web Application

**Goal:** Web interface with landing page and download endpoint

**Components:**
- New file `code/src/web.py` — Flask application
  - `/` route renders landing page
  - `/download` route serves cached PDF or triggers generation
  - `/health` route for fly.io health checks
- New template `code/templates/landing.html` — private alpha landing page
- Static assets in `code/static/` if needed (minimal CSS)

**Dependencies:** Phase 3 (download serves combined PDF)

**Done when:** `flask run` serves landing page, download button returns PDF

### Phase 5: Caching Layer

**Goal:** Cache generated PDFs by ISO week for instant downloads

**Components:**
- Cache manager in `code/src/cache.py`:
  - `get_cached_pdf(week: str) -> Path | None`
  - `cache_pdf(week: str, pdf_path: Path)`
  - `get_current_week() -> str` (ISO week format)
- Cache directory structure: `cache/YYYY-WWW/combined.pdf`
- Integration in `code/src/web.py` — check cache before generation

**Dependencies:** Phase 4 (web app uses cache)

**Done when:** Second request for same week returns cached PDF instantly

### Phase 6: fly.io Deployment

**Goal:** Deploy Flask app to fly.io with persistent storage

**Components:**
- `Dockerfile` in project root — Python image with WeasyPrint dependencies
- `fly.toml` in project root — fly.io configuration (VM size, volume mount, env vars)
- Persistent volume mounted at `/app/cache`
- Environment variables configured in fly.io secrets

**Dependencies:** Phase 5 (caching requires persistent volume)

**Done when:** `fly deploy` succeeds, app accessible at `news-fixed.fly.dev` (or similar)

### Phase 7: Scheduled Generation

**Goal:** Automatic weekly PDF generation without manual intervention

**Components:**
- Scheduled machine configuration in `fly.toml` — runs Sunday nights
- Generation script `code/src/scheduled_generate.py`:
  - Fetches current FTN content
  - Runs full pipeline with default options
  - Caches result
  - Optional: sends notification via ntfy.sh
- Error handling and logging for unattended operation

**Dependencies:** Phase 6 (runs on fly.io infrastructure)

**Done when:** PDF for new week appears in cache each Monday morning without manual action

## Additional Considerations

**RSS feed validation:** Before Phase 7 implementation, validate that FTN RSS feed (`https://fixthenews.com/feed`) provides sufficient content in `content:encoded` field. If RSS is insufficient, fall back to existing Playwright-based fetcher (requires storing browser credentials securely).

**Rate limiting:** For MVP with 5-20 users, rate limiting is not critical. If custom generation options are added later (Duke/SF/XKCD toggles), implement simple IP-based rate limiting (5 generations/day/IP).

**Handoff to FTN team:** Design prioritizes simplicity for eventual handoff:
- Self-contained repository with clear README
- Standard Python packaging (pyproject.toml)
- Dockerfile for reproducible deployment
- No external dependencies beyond fly.io and Anthropic API

**Notification (optional):** Phase 7 can include ntfy.sh notification (~5 lines of code) to alert when generation completes or fails. Not blocking for MVP.
