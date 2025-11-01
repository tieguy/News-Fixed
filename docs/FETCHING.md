# Fetching Fix The News Content

This document explains how to fetch FTN content for the News, Fixed pipeline.

## Using the Unified Wrapper (Recommended)

The `news-fixed` script provides a simple interface for fetching FTN content.

### First Time Setup

On your first run, you'll need to log in to Fix The News:

```bash
# Run with visible browser for first-time login
./news-fixed fetch https://fixthenews.com/latest --no-headless
```

This will:
1. Open Firefox with a clean, dedicated profile (`.firefox-profile-ftn/`)
2. Navigate to the FTN URL
3. Wait for you to log in with your Substack credentials
4. Save your session cookies for future use

**Press Enter in the terminal after logging in** to continue the script.

### Subsequent Runs (Automated)

Once you've logged in once, future runs are fully automated:

```bash
# Fetch latest issue (headless mode)
./news-fixed fetch https://fixthenews.com/latest

# Or use the complete pipeline
./news-fixed run https://fixthenews.com/latest
```

The script will:
- Use your saved login session
- Navigate to FTN and strip preview URL suffix
- Extract issue number from URL
- Download the HTML to `data/raw/FTN-{issue}.html`

### Refresh Login

If your session expires:

```bash
./news-fixed fetch https://fixthenews.com/latest --force-login
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

Once FTN HTML is downloaded, parse and generate:

```bash
# Parse FTN content
./news-fixed parse data/raw/FTN-317.html

# Generate PDFs
./news-fixed generate data/processed/ftn-317.json --all

# Or use complete pipeline
./news-fixed run https://fixthenews.com/latest
```
