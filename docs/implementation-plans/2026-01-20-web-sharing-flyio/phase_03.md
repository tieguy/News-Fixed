# Web Sharing via fly.io - Phase 3

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

## Phase 3: Combined Multi-Day PDF

**Goal:** Generate single PDF containing all 4 daily editions (8 pages total).

**Done when:** `./news-fixed --combined` produces single 8-page PDF with all 4 days.

---

### Task 1: Add Page Break CSS for Combined PDF

**Files:**
- Modify: `code/templates/styles.css` (add page break utilities)

**Step 1: Add page break CSS at end of styles.css**

Add at the end of `code/templates/styles.css`:

```css
/* Combined PDF Page Breaks */
.day-separator {
    page-break-before: always;
}

@media print {
    .day-separator {
        page-break-before: always;
    }
}
```

**Step 2: Verify CSS addition**

Run: `grep -c "day-separator" code/templates/styles.css`
Expected: `2` (two occurrences)

**Step 3: Commit**

```bash
git add code/templates/styles.css
git commit -m "feat: add day-separator CSS for combined PDF page breaks"
```

---

### Task 2: Create Combined PDF Template

**Files:**
- Create: `code/templates/newspaper_combined.html`

**Step 1: Create the combined template**

Create `code/templates/newspaper_combined.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News, Fixed - Weekly Edition</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
{% for day in days %}
    {% if not loop.first %}
    <div class="day-separator"></div>
    {% endif %}

    <!-- PAGE 1: FRONT - Day {{ day.day_number }} -->
    <div class="page page-1">
        <!-- Header -->
        <header class="masthead">
            <h1 class="title">News, Fixed</h1>
            <p class="tagline">Global Good News, One Day At A Time</p>
        </header>

        <!-- Date bar -->
        <div class="date-bar">
            <span class="day-info">{{ day.day_of_week }}</span>
            <span class="date">{{ day.date }}</span>
            <span class="theme">{{ day.theme }}</span>
        </div>

        <!-- World News Section -->
        <div class="section-header">WORLD</div>
        <article class="lead-story">
            <h2 class="lead-headline">{{ day.main_story.title }}</h2>
            <div class="lead-layout">
                <div class="lead-content">
                    {{ day.main_story.content }}
                </div>
                <div class="lead-qr">
                    <img src="{{ day.main_story.qr_code }}" alt="QR Code" class="qr-code-medium">
                    <p class="qr-label">{{ day.main_story.source_name }}</p>
                </div>
            </div>
        </article>

        <!-- Local News Section -->
        {% if day.front_page_stories %}
        <div class="section-header">SAN FRANCISCO</div>
        <div class="local-stories">
            {% for article in day.front_page_stories %}
            <article class="local-story">
                <h3 class="local-headline">{{ article.title }}</h3>
                <div class="local-layout">
                    <div class="local-content">
                        {{ article.content }}
                    </div>
                    <div class="local-qr">
                        <img src="{{ article.qr_code }}" alt="QR Code" class="qr-code-medium">
                        <p class="qr-label">{{ article.source_name }}</p>
                    </div>
                </div>
            </article>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Second Main Story (shown when personalized features disabled) -->
        {% if day.second_main_story %}
        <article class="second-main-story">
            <h3 class="second-main-headline">{{ day.second_main_story.title }}</h3>
            <div class="second-main-layout">
                <div class="second-main-content">
                    {{ day.second_main_story.content }}
                </div>
                <div class="second-main-qr">
                    <img src="{{ day.second_main_story.qr_code }}" alt="QR Code" class="qr-code-medium">
                    <p class="qr-label">{{ day.second_main_story.source_name }}</p>
                </div>
            </div>
        </article>
        {% endif %}

        <!-- Feature Box (only shown when content provided, e.g., sports games) -->
        {% if day.feature_box %}
        <aside class="feature-box">
            <h3>{{ day.feature_box.title }}</h3>
            <p>{{ day.feature_box.content | safe }}</p>
        </aside>
        {% endif %}

        <!-- Tomorrow Teaser -->
        {% if day.tomorrow_teaser %}
        <div class="tomorrow-teaser">
            <h4>Tomorrow</h4>
            <p>{{ day.tomorrow_teaser }}</p>
        </div>
        {% endif %}

        <!-- Footer Page 1 -->
        <footer class="page-footer">
            <p class="footer-note">News, Fixed • Day {{ day.day_number }} • Page 1 of 2</p>
        </footer>
    </div>

    <!-- PAGE 2: BACK - Day {{ day.day_number }} -->
    <div class="page page-2">
        <!-- Header (smaller) -->
        <header class="page-header">
            <h2 class="page-title">News, Fixed</h2>
            <p class="page-date">{{ day.day_of_week }}, {{ day.date }}</p>
        </header>

        <!-- Mini Articles Grid -->
        <section class="mini-articles">
            {% for article in day.mini_articles %}
            <article class="mini-article">
                <h3 class="mini-headline">{{ article.title }}</h3>
                <div class="mini-layout">
                    <div class="mini-content">
                        <p>{{ article.content }}</p>
                    </div>
                    <div class="mini-qr">
                        <img src="{{ article.qr_code }}" alt="QR Code" class="qr-code-small">
                        <p class="qr-label-small">{{ article.source_name }}</p>
                    </div>
                </div>
            </article>
            {% endfor %}
        </section>

        <!-- By The Numbers -->
        <section class="by-the-numbers">
            <h3 class="section-title">By The Numbers</h3>
            <div class="stats-grid">
                {% for stat in day.statistics %}
                <div class="stat-item">
                    <p class="stat-number">{{ stat.number }}</p>
                    <p class="stat-description">{{ stat.description }}</p>
                </div>
                {% endfor %}
            </div>
        </section>

        <!-- xkcd Comic -->
        {% if day.xkcd_comic %}
        <section class="xkcd-section">
            <div class="xkcd-layout">
                <img src="{{ day.xkcd_comic.image_path }}" alt="xkcd: {{ day.xkcd_comic.title }}" class="xkcd-image">
                <div class="xkcd-info">
                    <p class="xkcd-title">xkcd: {{ day.xkcd_comic.title }}</p>
                    <p class="xkcd-alt">{{ day.xkcd_comic.alt }}</p>
                    <p class="xkcd-link">xkcd.com/{{ day.xkcd_comic.num }}</p>
                </div>
            </div>
        </section>
        {% endif %}

        <!-- Footer Page 2 -->
        <footer class="page-footer">
            <p class="footer-message">{{ day.footer_message }}</p>
            <p class="footer-note">News, Fixed • Day {{ day.day_number }} • Page 2 of 2</p>
        </footer>
    </div>
{% endfor %}
</body>
</html>
```

**Step 2: Verify template syntax**

Run: `cd code && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); t = env.get_template('newspaper_combined.html'); print('Template valid')"`
Expected: `Template valid`

**Step 3: Commit**

```bash
git add code/templates/newspaper_combined.html
git commit -m "feat: add combined PDF template for weekly edition

Renders all 4 days in one HTML document with page breaks between days."
```

---

### Task 3: Add generate_combined_pdf Method to PDF Generator

**Files:**
- Modify: `code/src/pdf_generator.py` (add new method after generate_pdf)

**Step 1: Add generate_combined_pdf method**

Add after the `generate_pdf` method (before `if __name__ == "__main__":`):

```python
    def generate_combined_pdf(
        self,
        days_data: List[Dict],
        output_path: str
    ) -> Path:
        """
        Generate a combined multi-day newspaper PDF (8 pages for 4 days).

        Args:
            days_data: List of day context dicts, each containing:
                - day_number: int
                - day_of_week: str
                - date: str
                - theme: str
                - main_story: dict
                - front_page_stories: list
                - mini_articles: list
                - statistics: list
                - feature_box: dict (optional)
                - tomorrow_teaser: str (optional)
                - xkcd_comic: dict (optional)
                - second_main_story: dict (optional)
            output_path: Output PDF file path

        Returns:
            Path to generated PDF
        """
        # Prepare all days' contexts with QR codes
        prepared_days = []
        for day_data in days_data:
            context = self._prepare_context(
                day_number=day_data['day_number'],
                day_of_week=day_data['day_of_week'],
                date_str=day_data['date'],
                main_story=day_data['main_story'],
                front_page_stories=day_data.get('front_page_stories', []),
                mini_articles=day_data['mini_articles'],
                statistics=day_data['statistics'],
                feature_box=day_data.get('feature_box'),
                tomorrow_teaser=day_data.get('tomorrow_teaser', ''),
                xkcd_comic=day_data.get('xkcd_comic')
            )

            # Add second_main_story if present
            if day_data.get('second_main_story'):
                context['second_main_story'] = self._add_qr_codes_to_article(
                    day_data['second_main_story']
                )

            prepared_days.append(context)

        # Render combined template
        template = self.env.get_template("newspaper_combined.html")
        html_content = template.render(days=prepared_days)

        css_path = self.templates_dir / "styles.css"
        html = HTML(string=html_content, base_url=str(self.templates_dir))
        css = CSS(filename=str(css_path))

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        html.write_pdf(output_file, stylesheets=[css])

        # Verify page count (should be 8 for 4 days)
        expected_pages = len(days_data) * 2
        page_count = self.get_pdf_page_count(str(output_file))
        if page_count != -1 and page_count != expected_pages:
            print(f"   ⚠️  Combined PDF has {page_count} pages (expected {expected_pages})")

        return output_file
```

**Step 2: Add List to imports if not present**

Ensure `List` is imported from typing at the top of the file. (It should already be there based on current imports.)

**Step 3: Verify method exists**

Run: `cd code && python -c "from pdf_generator import NewspaperGenerator; print(hasattr(NewspaperGenerator, 'generate_combined_pdf'))"`
Expected: `True`

**Step 4: Commit**

```bash
git add code/src/pdf_generator.py
git commit -m "feat: add generate_combined_pdf() method

Generates 8-page PDF with all 4 days using combined template."
```

---

### Task 4: Add --combined CLI Flag

**Files:**
- Modify: `code/src/main.py` (add CLI option and handling)

**Step 1: Add --combined option to CLI**

Add after the `--all` option definition (around line 332):

```python
@click.option('--combined', is_flag=True,
              help='Generate combined 8-page PDF with all 4 days')
```

**Step 2: Update main function signature**

Add `combined` parameter to the `main()` function signature:

```python
def main(input_file, day, generate_all, combined, output, date_str, test, no_rewrite, no_preview):
```

**Step 3: Add combined PDF generation logic**

Add handling for `--combined` flag in the main function, after loading FTN data and before the day loop. Add this logic:

```python
    if combined:
        click.echo("📚 Generating combined 4-day edition...")
        days_data = []

        for day_num in range(1, 5):
            day_key = f"day_{day_num}"
            if day_key not in ftn_data:
                click.echo(f"⚠️  No data found for {day_key}, skipping...")
                continue

            date_info = week_dates[day_num]
            day_data = ftn_data[day_key]

            click.echo(f"\n📅 Processing {date_info['day_name']}...")

            # Generate or load content for this day
            # Note: use_content_from_json returns 6 values after Phase 2 Task 7
            if no_rewrite:
                main_story, front_page_stories, mini_articles, statistics, tomorrow_teaser, second_main_story = \
                    use_content_from_json(day_data)
                feature_box = day_data.get('feature_box')
            else:
                main_story, front_page_stories, mini_articles, statistics, tomorrow_teaser = \
                    generate_content_with_ai(content_gen, day_data, day_num)
                feature_box = None
                second_main_story = None

            # Apply feature flags (simplified for combined - no sports/local/xkcd)
            # The combined PDF is for web, so these are typically disabled
            xkcd_comic = None

            days_data.append({
                'day_number': day_num,
                'day_of_week': date_info['day_name'],
                'date': date_info['formatted_date'],
                'theme': get_theme_name(day_num),  # Required for template
                'main_story': main_story,
                'front_page_stories': front_page_stories or [],
                'mini_articles': mini_articles,
                'statistics': statistics,
                'feature_box': feature_box,
                'tomorrow_teaser': tomorrow_teaser if day_num < 4 else '',
                'xkcd_comic': xkcd_comic,
                'second_main_story': second_main_story,
                'footer_message': "Good news exists, but it travels slowly."  # Required for template
            })

        # Generate combined PDF
        if ftn_number:
            output_filename = f"news_fixed_{ftn_number}_combined.pdf"
        else:
            week_start = week_dates[1]['date_obj'].strftime('%Y-%m-%d')
            output_filename = f"news_fixed_{week_start}_combined.pdf"

        output_path = Path(output) / output_filename

        click.echo(f"\n📄 Generating combined PDF...")
        pdf_gen.generate_combined_pdf(days_data, str(output_path))
        click.echo(f"✅ Generated: {output_path}")

        if not no_preview:
            preview_and_print(output_path)

        click.echo("\n✨ Done!")
        return
```

**Step 4: Verify CLI option added**

Run: `cd code && python src/main.py --help | grep combined`
Expected: Shows `--combined` option in help

**Step 5: Commit**

```bash
git add code/src/main.py
git commit -m "feat: add --combined CLI flag for 8-page weekly PDF

Generates single PDF with all 4 days for weekly distribution."
```

---

### Task 5: Integration Test - Combined PDF Generation

**Files:**
- None (verification only)

**Step 1: Test combined generation with test mode**

Since `--test` generates only a single day, we need to test with real data or modify the test to support combined mode. For now, verify the CLI accepts the flag:

Run: `cd /var/home/louie/Projects/family/News-Fixed && ./news-fixed --help | grep -A1 combined`
Expected: Shows `--combined` option description

**Step 2: Test with sample JSON data (if available)**

If you have a curated JSON file with all 4 days:

```bash
./news-fixed --input data/processed/ftn-XXX-curated.json --combined --no-preview
```

Expected: Generates `news_fixed_XXX_combined.pdf` with 8 pages

**Step 3: Verify page count**

Run: `pdfinfo output/news_fixed_*_combined.pdf | grep Pages` (if PDF exists)
Expected: `Pages: 8`

**Step 4: Commit final verification**

```bash
git add -A
git commit -m "docs: Phase 3 complete - combined multi-day PDF generation

- Added --combined CLI flag
- Creates 8-page PDF with all 4 days
- Uses new newspaper_combined.html template"
```

---

## Phase 3 Verification

After completing all tasks:

1. Verify combined template exists: `ls code/templates/newspaper_combined.html`
2. Verify method exists: `cd code && python -c "from pdf_generator import NewspaperGenerator; print(hasattr(NewspaperGenerator, 'generate_combined_pdf'))"`
3. Verify CLI flag: `./news-fixed --help | grep combined`
4. Test with real data if available: `./news-fixed --input <json-file> --combined --no-preview`

Phase 3 is complete when `--combined` generates an 8-page PDF with all 4 days.
