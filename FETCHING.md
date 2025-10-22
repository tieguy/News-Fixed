# Fetching Fix The News Content

This document explains the different methods for getting FTN content into the News, Fixed pipeline.

## Recommended: Dedicated Firefox Profile (Automated)

The `fetch_ftn_clean.py` script uses a dedicated Firefox profile just for fetching FTN content.

### First Time Setup

```bash
# Run with visible browser for first-time login
python -m src.fetch_ftn_clean --no-headless
```

This will:
1. Open Firefox with a clean, dedicated profile
2. Navigate to fixthenews.com
3. Wait for you to log in with your Substack credentials
4. Save your session cookies for future use

**Press Enter after logging in** to continue the script.

### Subsequent Runs (Automated)

Once you've logged in once, future runs can be fully automated:

```bash
# Headless mode (no browser window)
python -m src.fetch_ftn_clean

# Or with visible browser for debugging
python -m src.fetch_ftn_clean --no-headless

# Save to specific directory
python -m src.fetch_ftn_clean --output ~/Downloads
```

The script will:
- Use your saved login session
- Navigate to FTN
- Find the latest post
- Download the HTML
- Save as `FTN-{issue_number}.html`

### Refresh Login

If your session expires:

```bash
python -m src.fetch_ftn_clean --force-login
```

## Alternative: Manual Save (Current Method)

For this week, we've been manually saving FTN content:

1. Open fixthenews.com in your regular Firefox
2. Navigate to the latest post
3. Right-click → "Save Page As"
4. Save as `FTN-{number}.html` in the project directory

This is simple and reliable, but manual.

## Alternative: Email Forwarding

If you receive FTN via email:

1. Forward the email to yourself
2. Save the HTML from the email
3. Use the parser on that HTML

The email HTML might be messier than the web version.

## Profile Location

The dedicated Firefox profile is stored in:
```
.firefox-profile-ftn/
```

This directory is git-ignored since it contains your cookies/session.

To start fresh (clear all saved data):
```bash
rm -rf .firefox-profile-ftn/
```

## Troubleshooting

**"Target page, context or browser has been closed"**
- Don't use your main Firefox profile (`~/.mozilla/firefox/your-profile`)
- Always use the dedicated profile (handled automatically by `fetch_ftn_clean.py`)

**"Timeout error"**
- Run with `--no-headless` to see what's happening
- Check your internet connection
- FTN site might be slow or down

**Cookies not working**
- Try `--force-login` to refresh your session
- Delete `.firefox-profile-ftn/` and start fresh

## Next Steps

Once FTN HTML is downloaded, use the parser to extract stories:

```bash
# Parse FTN content
python -m src.parser FTN-315.html

# Or integrate into full pipeline (future enhancement)
python main.py --fetch-and-generate --day 1
```
