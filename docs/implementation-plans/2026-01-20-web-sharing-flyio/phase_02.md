# Web Sharing via fly.io - Phase 2

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:executing-an-implementation-plan to implement this plan task-by-task.

## Phase 2: Second Main Story Generation

**Goal:** Generate a second main story to fill space when Duke/SF/XKCD features are disabled for the public web version.

**Done when:** When Duke/SF disabled, a second main story renders in their place with appropriate styling.

---

### Task 1: Create Second Main Story Prompt

**Files:**
- Create: `code/prompts/second_main_story.txt`

**Step 1: Create the prompt file**

Create `code/prompts/second_main_story.txt`:

```
You are rewriting a news story for "News, Fixed," a daily newspaper for bright 10-14 year olds. This is the SECOND main story on the front page, appearing below the lead story.

ORIGINAL STORY:
{original_content}

SOURCE: {source_url}

THEME: {theme}

Your task: Rewrite this as a 120-140 word secondary story. This is slightly shorter than the lead story but still prominent on the front page. BE VERY CONCISE.

Guidelines:
- Write for bright 10-14 year olds: accessible but not condescending
- Use analogies when helpful (e.g., "like leveling up in a video game")
- Explain WHY this news matters to young readers
- Emphasize youth agency and possibility
- Use active voice and vivid language
- Include specific numbers and facts
- Show how this connects to readers' lives or futures
- End with a forward-looking or inspiring note

Format: Return ONLY the story text in plain paragraphs. No title/headline (that will be generated separately).
```

**Step 2: Verify file created**

Run: `cat code/prompts/second_main_story.txt | head -5`
Expected: First 5 lines of the prompt

**Step 3: Commit**

```bash
git add code/prompts/second_main_story.txt
git commit -m "feat: add second_main_story prompt for web version

Shorter version (120-140 words) of main story for secondary placement
when personalized features are disabled."
```

---

### Task 2: Add Second Main Story Generator Method

**Files:**
- Modify: `code/src/generator.py:103-104` (after generate_main_story method)

**Step 1: Add generate_second_main_story method**

Add after the `generate_main_story` method (after line 103):

```python
    def generate_second_main_story(
        self,
        original_content: str,
        source_url: str,
        theme: str,
        original_title: str = ""
    ) -> Dict[str, str]:
        """
        Generate second main story content (120-140 words).

        Used when personalized features (Duke, SF, XKCD) are disabled
        to fill space on the front page.

        Args:
            original_content: Original news story text
            source_url: Source URL
            theme: Today's theme
            original_title: Original story title

        Returns:
            Dict with 'title' and 'content' keys
        """
        full_text = f"{original_title} {original_content}".strip() if original_title else original_content

        template = self._load_prompt("second_main_story")
        prompt = template.format(
            original_content=full_text,
            source_url=source_url,
            theme=theme
        )

        content = self._call_claude(prompt, max_tokens=500)
        title = self.generate_headline(content)

        return {
            "title": title,
            "content": content
        }
```

**Step 2: Verify method exists**

Run: `cd code && python -c "from generator import ContentGenerator; print(hasattr(ContentGenerator, 'generate_second_main_story'))"`
Expected: `True`

**Step 3: Commit**

```bash
git add code/src/generator.py
git commit -m "feat: add generate_second_main_story() method

Generates 120-140 word story for secondary front page placement."
```

---

### Task 3: Update Template for Second Main Story

**Files:**
- Modify: `code/templates/newspaper.html:59-67` (after front_page_stories section, before feature_box)

**Step 1: Add second_main_story section to template**

Add after the `{% endif %}` for `front_page_stories` (after line 59), before the feature_box section:

```html
        <!-- Second Main Story (shown when personalized features disabled) -->
        {% if second_main_story %}
        <article class="second-main-story">
            <h3 class="second-main-headline">{{ second_main_story.title }}</h3>
            <div class="second-main-layout">
                <div class="second-main-content">
                    {{ second_main_story.content }}
                </div>
                <div class="second-main-qr">
                    <img src="{{ second_main_story.qr_code }}" alt="QR Code" class="qr-code-medium">
                    <p class="qr-label">{{ second_main_story.source_name }}</p>
                </div>
            </div>
        </article>
        {% endif %}
```

**Step 2: Verify template syntax**

Run: `cd code && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); t = env.get_template('newspaper.html'); print('Template valid')"`
Expected: `Template valid`

**Step 3: Commit**

```bash
git add code/templates/newspaper.html
git commit -m "feat: add second_main_story section to newspaper template

Displays when personalized features are disabled in web version."
```

---

### Task 4: Add CSS Styling for Second Main Story

**Files:**
- Modify: `code/templates/styles.css` (add after local-stories styling)

**Step 1: Find local-stories CSS section**

Run: `grep -n "local-story" code/templates/styles.css | head -5`

Note the line number range for local story styles.

**Step 2: Add second-main-story styles**

Add after the local-stories CSS section (find appropriate location):

```css
/* Second Main Story (when personalized features disabled) */
.second-main-story {
    margin: 0.8rem 0;
    padding: 0.6rem;
    border: 1px solid #333;
    background: #f9f9f9;
}

.second-main-headline {
    font-family: 'Times New Roman', serif;
    font-size: 1.1rem;
    font-weight: bold;
    margin: 0 0 0.4rem 0;
    line-height: 1.2;
}

.second-main-layout {
    display: flex;
    gap: 0.5rem;
}

.second-main-content {
    flex: 1;
    font-size: 0.75rem;
    line-height: 1.4;
}

.second-main-qr {
    flex-shrink: 0;
    text-align: center;
}
```

**Step 3: Verify CSS syntax**

Run: `cd code && python -c "import cssutils; cssutils.parseFile('templates/styles.css'); print('CSS valid')" 2>/dev/null || echo "CSS syntax check skipped (cssutils not installed)"`

**Step 4: Commit**

```bash
git add code/templates/styles.css
git commit -m "feat: add CSS styling for second main story

Consistent with local-stories styling, bordered box presentation."
```

---

### Task 5: Update PDF Generator to Accept Second Main Story

**Files:**
- Modify: `code/src/pdf_generator.py` (generate_pdf method signature and template rendering)

**Step 1: Read current pdf_generator to find generate_pdf method**

Run: `grep -n "def generate_pdf" code/src/pdf_generator.py`

Note the line number.

**Step 2: Add second_main_story parameter to generate_pdf**

Update the `generate_pdf` method signature to include `second_main_story=None` parameter, and add it to the template context.

The method signature should include:
```python
def generate_pdf(
    self,
    day_number: int,
    main_story: dict,
    front_page_stories: list,
    mini_articles: list,
    statistics: list,
    output_path: str,
    date_str: str,
    day_of_week: str,
    feature_box: dict = None,
    tomorrow_teaser: str = "",
    xkcd_comic: dict = None,
    second_main_story: dict = None  # Add this parameter
) -> None:
```

And in the template rendering context, add:
```python
second_main_story=self._prepare_story_with_qr(second_main_story) if second_main_story else None,
```

**Step 3: Verify changes**

Run: `cd code && python -c "from pdf_generator import NewspaperGenerator; import inspect; sig = inspect.signature(NewspaperGenerator().generate_pdf); print('second_main_story' in str(sig))"`
Expected: `True`

**Step 4: Commit**

```bash
git add code/src/pdf_generator.py
git commit -m "feat: add second_main_story parameter to generate_pdf

Allows passing optional second main story for web version rendering."
```

---

### Task 6: Integrate Second Main Story in Main Orchestrator

**Files:**
- Modify: `code/src/main.py` (generate_day_newspaper function)

**Step 1: Add second_main_story generation when features disabled**

In `generate_day_newspaper()`, after the feature flag checks and before PDF generation, add logic to generate a second main story when all personalized features are disabled.

Find the section after XKCD handling (around line 295) and before PDF generation (around line 297). Add:

```python
    # Generate second main story if personalized features are disabled
    second_main_story = None
    features_disabled = (
        not get_feature_flag('FEATURE_DUKE_SPORTS', default=True) and
        not get_feature_flag('FEATURE_SF_LOCAL', default=True) and
        not get_feature_flag('FEATURE_XKCD', default=True)
    )

    if features_disabled and content_gen and 'second_story' in day_data:
        click.echo("  ✍️  Generating second main story...")
        second_story_data = day_data['second_story']
        second_main_story = content_gen.generate_second_main_story(
            original_content=second_story_data['content'],
            source_url=second_story_data['source_url'],
            theme=get_theme_name(day_num),
            original_title=second_story_data.get('title', '')
        )
        second_main_story['source_url'] = second_story_data['source_url']
```

**Step 2: Pass second_main_story to PDF generator**

Update the `pdf_gen.generate_pdf()` call to include `second_main_story=second_main_story`.

**Step 3: Verify integration**

Run: `cd code && python -c "from main import generate_day_newspaper; print('Function exists')"`
Expected: `Function exists`

**Step 4: Commit**

```bash
git add code/src/main.py
git commit -m "feat: generate second main story when personalized features disabled

When FEATURE_DUKE_SPORTS, FEATURE_SF_LOCAL, and FEATURE_XKCD are all
false, generates a second main story to fill front page space."
```

---

### Task 7: Update use_content_from_json for Second Story

**Files:**
- Modify: `code/src/main.py` (use_content_from_json function, around line 183-192)

**Step 1: Add second_main_story to JSON content extraction**

Update `use_content_from_json()` to also extract `second_main_story` from JSON:

```python
def use_content_from_json(day_data: dict) -> tuple:
    """Use content from JSON file without AI rewriting."""
    click.echo("  📝 Using content from JSON...")
    main_story = day_data['main_story']
    front_page_stories = day_data.get('front_page_stories', [])
    mini_articles = day_data['mini_articles']
    statistics = day_data.get('statistics', [])
    tomorrow_teaser = day_data.get('tomorrow_teaser', '')
    second_main_story = day_data.get('second_main_story')

    return main_story, front_page_stories, mini_articles, statistics, tomorrow_teaser, second_main_story
```

**Step 2: Update callers to handle 6-tuple return**

Update the caller in `generate_day_newspaper()` to unpack the 6th value.

**Step 3: Commit**

```bash
git add code/src/main.py
git commit -m "feat: extract second_main_story from JSON in no-rewrite mode

Supports pre-generated second main stories in JSON input."
```

---

## Phase 2 Verification

After completing all tasks:

1. Verify prompt file exists: `ls code/prompts/second_main_story.txt`
2. Verify generator method: `cd code && python -c "from generator import ContentGenerator; print(hasattr(ContentGenerator, 'generate_second_main_story'))"`
3. Verify template has second_main_story section: `grep -c "second_main_story" code/templates/newspaper.html`
4. Test with all features disabled (requires test data with `second_story` field):
   ```bash
   FEATURE_DUKE_SPORTS=false FEATURE_SF_LOCAL=false FEATURE_XKCD=false \
     ./news-fixed --test --no-preview
   ```

Phase 2 is complete when a second main story can be generated and rendered when personalized features are disabled.

**Note:** The test data in `generate_test_newspaper()` doesn't include `second_story` data, so the second main story won't appear in test mode. This is expected - the feature activates with real FTN data that includes a second story option.

**Important:** The `second_story` field in `day_data` must be populated by the FTN curation process. The existing `ftn_to_json.py` and `curator.py` currently create `main_story` and `mini_articles`. For web deployment, the curation process should select a second-best story and store it in the `second_story` field with the same structure as `main_story` (title, content, source_url). This can be done:
1. Manually during curation by moving a strong mini_article to `second_story`
2. Automatically in a future enhancement to `ftn_to_json.py`

For MVP, if `second_story` is not present in the JSON, the second main story feature simply won't activate.
