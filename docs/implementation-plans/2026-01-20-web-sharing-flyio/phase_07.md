# Web Sharing via fly.io - Phase 7

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

## Phase 7: Scheduled Generation

**Goal:** Automatic weekly PDF generation without manual intervention.

**Done when:** PDF for new week appears in cache each Monday morning without manual action.

---

### Task 1: Create Scheduled Generation Script

**Files:**
- Create: `code/src/scheduled_generate.py`

**Step 1: Create the generation script**

Create `code/src/scheduled_generate.py`:

```python
#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""
Scheduled generation script for News, Fixed web deployment.

Runs weekly to generate the combined 4-day PDF and cache it.
Designed to run as a fly.io scheduled machine.
"""

import os
import sys
import json
import tempfile
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add code/src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cache import PDFCache, get_current_week
from generator import ContentGenerator
from pdf_generator import NewspaperGenerator
from utils import get_theme_name

# Load environment variables
load_dotenv()


def send_notification(message: str, priority: str = "default") -> None:
    """
    Send notification via ntfy.sh (optional).

    Args:
        message: Notification message
        priority: Priority level (min, low, default, high, urgent)
    """
    ntfy_topic = os.getenv("NTFY_TOPIC")
    if not ntfy_topic:
        print(f"[INFO] {message}")
        return

    try:
        requests.post(
            f"https://ntfy.sh/{ntfy_topic}",
            data=message.encode('utf-8'),
            headers={
                "Title": "News, Fixed Generation",
                "Priority": priority,
                "Tags": "newspaper"
            },
            timeout=10
        )
    except Exception as e:
        print(f"[WARN] Notification failed: {e}")


def load_ftn_content() -> dict | None:
    """
    Load curated Fix The News content from JSON file.

    The FTN content should be pre-curated using the curator workflow and
    uploaded to the cache directory before running scheduled generation.

    Looks for JSON files in order:
    1. /app/cache/current_week.json (explicit current week file)
    2. /app/cache/ftn-curated.json (general curated file)
    3. /app/data/processed/*.json (latest processed file)

    Returns:
        Dict with day_1 through day_4 structure, or None if not found
    """
    print("[INFO] Loading curated FTN content...")

    cache_dir = Path(os.getenv('CACHE_DIR', 'cache'))
    data_dir = Path('/app/data/processed') if Path('/app/data').exists() else Path('data/processed')

    # Check for curated JSON files in order of priority
    candidates = [
        cache_dir / "current_week.json",
        cache_dir / "ftn-curated.json",
    ]

    # Also check data/processed for any curated JSON files
    if data_dir.exists():
        processed_files = sorted(data_dir.glob("*-curated.json"), reverse=True)
        candidates.extend(processed_files[:1])  # Most recent only

    for json_path in candidates:
        if json_path.exists():
            print(f"[INFO] Found FTN content: {json_path}")
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    ftn_data = json.load(f)

                # Validate structure
                for day_num in range(1, 5):
                    day_key = f"day_{day_num}"
                    if day_key not in ftn_data:
                        print(f"[WARN] Missing {day_key} in FTN data")

                return ftn_data
            except Exception as e:
                print(f"[ERROR] Failed to load {json_path}: {e}")
                continue

    print("[ERROR] No curated FTN content found")
    print("[INFO] To provide content, upload a curated JSON to:")
    print(f"       {cache_dir}/current_week.json")
    print(f"       or {cache_dir}/ftn-curated.json")
    return None


def generate_week_content(ftn_data: dict, content_gen: ContentGenerator) -> list[dict]:
    """
    Generate content for all 4 days.

    Args:
        ftn_data: Dict with day_1 through day_4 structure
        content_gen: ContentGenerator instance

    Returns:
        List of day data dicts ready for PDF generation
    """
    from main import calculate_week_dates, generate_content_with_ai

    week_dates = calculate_week_dates()
    days_data = []

    for day_num in range(1, 5):
        day_key = f"day_{day_num}"
        if day_key not in ftn_data:
            print(f"[WARN] Skipping {day_key} - no data")
            continue

        date_info = week_dates[day_num]
        day_data = ftn_data[day_key]

        print(f"[INFO] Generating Day {day_num}: {date_info['day_name']}...")

        # Generate content with AI
        main_story, front_page_stories, mini_articles, statistics, tomorrow_teaser = \
            generate_content_with_ai(content_gen, day_data, day_num)

        days_data.append({
            'day_number': day_num,
            'day_of_week': date_info['day_name'],
            'date': date_info['formatted_date'],
            'theme': get_theme_name(day_num),  # Required for template
            'main_story': main_story,
            'front_page_stories': front_page_stories or [],
            'mini_articles': mini_articles,
            'statistics': statistics,
            'feature_box': None,  # Disabled for web version
            'tomorrow_teaser': tomorrow_teaser if day_num < 4 else '',
            'xkcd_comic': None,  # Disabled for web version
            'second_main_story': day_data.get('second_main_story'),  # From curated data
            'footer_message': "Good news exists, but it travels slowly."  # Required for template
        })

    return days_data


def main() -> int:
    """
    Main entry point for scheduled generation.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 60)
    print("News, Fixed - Scheduled Generation")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    week = get_current_week()
    print(f"[INFO] Generating for week: {week}")

    # Check if already cached
    cache = PDFCache()
    if cache.is_cached(week):
        print(f"[INFO] Week {week} already cached, skipping generation")
        send_notification(f"Week {week} already cached", priority="low")
        return 0

    # Initialize generators
    try:
        content_gen = ContentGenerator()
    except ValueError as e:
        print(f"[ERROR] Content generator init failed: {e}")
        send_notification(f"Generation failed: {e}", priority="high")
        return 1

    pdf_gen = NewspaperGenerator()

    # Load curated FTN content
    ftn_data = load_ftn_content()
    if not ftn_data:
        send_notification("No curated FTN content found - upload JSON first", priority="high")
        return 1

    # Generate content for all days
    try:
        days_data = generate_week_content(ftn_data, content_gen)
    except Exception as e:
        print(f"[ERROR] Content generation failed: {e}")
        send_notification(f"Content generation failed: {e}", priority="high")
        return 1

    if len(days_data) < 4:
        print(f"[WARN] Only {len(days_data)} days generated (expected 4)")

    # Generate combined PDF
    print("[INFO] Generating combined PDF...")
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        pdf_gen.generate_combined_pdf(days_data, str(tmp_path))
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {e}")
        send_notification(f"PDF generation failed: {e}", priority="high")
        tmp_path.unlink(missing_ok=True)
        return 1

    # Cache the PDF
    print("[INFO] Caching PDF...")
    cached_path = cache.cache_pdf(tmp_path, week)
    tmp_path.unlink(missing_ok=True)

    # Verify cache
    if not cache.is_cached(week):
        print("[ERROR] Cache verification failed")
        send_notification("Cache verification failed", priority="high")
        return 1

    print(f"[SUCCESS] PDF cached at: {cached_path}")
    print(f"[SUCCESS] Size: {cached_path.stat().st_size / 1024:.1f} KB")

    send_notification(f"Week {week} generated successfully!", priority="default")

    print("=" * 60)
    print(f"Completed: {datetime.now().isoformat()}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Make script executable**

Run: `chmod +x code/src/scheduled_generate.py`

**Step 3: Verify script syntax**

Run: `cd code && python -c "import scheduled_generate; print('Module loaded')"`
Expected: `Module loaded`

**Step 4: Commit**

```bash
git add code/src/scheduled_generate.py
git commit -m "feat: add scheduled generation script for fly.io

Fetches FTN content, generates 4-day PDF, caches for web delivery.
Includes optional ntfy.sh notifications."
```

---

### Task 2: Create Cron Machine Configuration

**Files:**
- Create: `fly.cron.toml`

**Step 1: Create cron machine configuration**

Create `fly.cron.toml` in project root:

```toml
# fly.cron.toml - Scheduled generation machine configuration
# Run with: fly machine run . --config fly.cron.toml --schedule "0 6 * * 0"

app = "news-fixed"
primary_region = "sjc"

[build]
  dockerfile = "Dockerfile"

[env]
  CACHE_DIR = "/app/cache"
  FEATURE_DUKE_SPORTS = "false"
  FEATURE_SF_LOCAL = "false"
  FEATURE_XKCD = "false"

[[mounts]]
  source = "news_fixed_cache"
  destination = "/app/cache"

[processes]
  generate = "python /app/code/src/scheduled_generate.py"
```

**Step 2: Verify TOML syntax**

Run: `python -c "import tomllib; tomllib.load(open('fly.cron.toml', 'rb')); print('Valid TOML')"`
Expected: `Valid TOML`

**Step 3: Commit**

```bash
git add fly.cron.toml
git commit -m "feat: add fly.cron.toml for scheduled generation machine

Separate config for weekly generation job."
```

---

### Task 3: Create GitHub Actions Workflow for Scheduled Generation

**Files:**
- Create: `.github/workflows/generate-weekly.yml`

**Step 1: Create GitHub Actions workflow**

Create `.github/workflows/generate-weekly.yml`:

```yaml
# Weekly PDF generation via fly.io machine
# Triggers every Sunday at 6 AM UTC (Saturday 10 PM PST)
#
# This workflow spins up a one-time fly.io machine to generate
# the week's PDF and cache it for web delivery.

name: Generate Weekly PDF

on:
  schedule:
    # 6 AM UTC on Sunday = 10 PM Saturday PST
    - cron: '0 6 * * 0'
  workflow_dispatch:  # Allow manual triggering

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - name: Setup flyctl
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Trigger generation machine
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        run: |
          flyctl machine run \
            --app news-fixed \
            --region sjc \
            --vm-memory 2048 \
            --vm-cpus 2 \
            --restart no \
            --rm \
            --env CACHE_DIR=/app/cache \
            --env FEATURE_DUKE_SPORTS=false \
            --env FEATURE_SF_LOCAL=false \
            --env FEATURE_XKCD=false \
            --mount source=news_fixed_cache,destination=/app/cache \
            --command "python /app/code/src/scheduled_generate.py"

      - name: Verify generation
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        run: |
          sleep 10
          curl -sf https://news-fixed.fly.dev/health | jq .
```

**Step 2: Create .github/workflows directory**

Run: `mkdir -p .github/workflows`

**Step 3: Commit**

```bash
git add .github/workflows/generate-weekly.yml
git commit -m "feat: add GitHub Actions workflow for weekly generation

Triggers fly.io machine every Sunday at 6 AM UTC.
Can also be triggered manually via workflow_dispatch."
```

---

### Task 4: Set Up GitHub Secrets

**Files:**
- None (GitHub configuration)

**Step 1: Generate fly.io API token**

Run: `fly tokens create deploy --app news-fixed`

This will output a token starting with `fo1_...`

**Step 2: Add secret to GitHub**

Go to your GitHub repository settings:
1. Settings > Secrets and variables > Actions
2. Click "New repository secret"
3. Name: `FLY_API_TOKEN`
4. Value: (paste the token from step 1)

**Step 3: Optionally add NTFY_TOPIC for notifications**

If you want notifications:
1. Create an ntfy.sh topic (visit ntfy.sh and note the topic name)
2. Add another secret: `NTFY_TOPIC` with your topic name
3. Also set it as a fly.io secret: `fly secrets set NTFY_TOPIC=your-topic --app news-fixed`

**Step 4: Document setup**

Note: GitHub secrets are configured through the GitHub web interface, not via code.

---

### Task 5: Test Scheduled Generation Locally

**Files:**
- None (verification only)

**Step 1: Test the generation script locally**

First, copy a curated JSON file to the test cache:
```bash
mkdir -p /tmp/test-cache
cp data/processed/ftn-XXX-curated.json /tmp/test-cache/ftn-curated.json
```

Then run the script:
```bash
cd /var/home/louie/Projects/family/News-Fixed
CACHE_DIR=/tmp/test-cache \
  FEATURE_DUKE_SPORTS=false \
  FEATURE_SF_LOCAL=false \
  FEATURE_XKCD=false \
  uv run python code/src/scheduled_generate.py
```

Note: This requires:
- ANTHROPIC_API_KEY set in environment
- A curated JSON file in the cache directory

If no curated JSON is found, the test will show an error but the script structure is correct.

**Step 2: Check test cache**

Run: `ls -la /tmp/test-cache/`
Expected: Shows week directory with combined.pdf (if generation succeeded)

**Step 3: Commit final verification**

```bash
git add -A
git commit -m "docs: Phase 7 complete - scheduled generation

- scheduled_generate.py script for autonomous PDF generation
- GitHub Actions workflow for weekly triggers
- fly.cron.toml for fly.io machine configuration
- Optional ntfy.sh notifications"
```

---

### Task 6: Test GitHub Actions Workflow

**Files:**
- None (GitHub Actions test)

**Step 1: Trigger manual workflow run**

Go to GitHub repository:
1. Actions tab
2. Select "Generate Weekly PDF" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

**Step 2: Monitor workflow execution**

Watch the workflow logs for:
- flyctl setup
- Machine run command
- Health check verification

**Step 3: Verify PDF was generated**

Run: `curl -s https://news-fixed.fly.dev/health | jq .`
Expected: `has_pdf: true` for current week

---

## Phase 7 Verification

After completing all tasks:

1. Script exists: `ls code/src/scheduled_generate.py`
2. Script runs: `cd code && python -c "import scheduled_generate; print('OK')"`
3. GitHub workflow exists: `ls .github/workflows/generate-weekly.yml`
4. Manual trigger works: Trigger workflow in GitHub Actions

Phase 7 is complete when:
- GitHub Actions workflow can be triggered manually
- Workflow successfully starts fly.io machine
- PDF appears in cache after generation

**Production Schedule:**

The workflow runs every Sunday at 6 AM UTC (Saturday 10 PM PST), ensuring the week's PDF is ready by Monday morning.

**Monitoring:**

- Check fly.io logs: `fly logs --app news-fixed`
- Check GitHub Actions: Repository > Actions tab
- Optional: ntfy.sh notifications for success/failure
