# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Fetch Fix The News content using a dedicated Firefox profile."""

import sys
import re
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def get_profile_dir() -> Path:
    """Get the dedicated Firefox profile directory for FTN fetching."""
    # Navigate from code/src/ to project root
    profile_dir = Path(__file__).parent.parent.parent / ".firefox-profile-ftn"
    profile_dir.mkdir(exist_ok=True)
    return profile_dir


def _setup_browser_session(profile_dir: Path, headless: bool, force_login: bool) -> tuple[Path, bool]:
    """Setup browser session and determine if first run."""
    print(f"🦊 Using dedicated Firefox profile at: {profile_dir}")

    cookies_file = profile_dir / "cookies.json"
    first_run = not cookies_file.exists() or force_login

    if first_run:
        print("📝 First run or forced login - browser will open for you to log in")
        print("   After logging in, the script will save your session for future use")
        headless = False  # Force visible on first run

    print(f"   Headless mode: {headless}")
    return cookies_file, first_run


def _handle_first_run_login(page, browser, cookies_file: Path):
    """Handle interactive login on first run."""
    print("\n" + "=" * 60)
    print("Please log in to Fix The News in the browser window.")
    print("Once you're logged in and see the main page, press Enter here...")
    print("=" * 60)
    try:
        input()
    except EOFError:
        print("⚠️  Running in non-interactive environment")
        print("   Waiting 30 seconds for manual login...")
        page.wait_for_timeout(30000)

    # Save cookies for future runs
    print("💾 Saving cookies for future use...")
    cookies = browser.cookies()
    with open(cookies_file, 'w') as f:
        json.dump(cookies, f)
    print("✅ Cookies saved!")


def _strip_preview_suffix_from_url(page, current_url: str, url_was_provided: bool) -> str:
    """Strip public preview suffix from URL if needed."""
    if url_was_provided:
        return current_url

    # IMPORTANT: /latest redirects to a public preview URL (e.g., ending in -d49)
    # We need to strip the suffix to get the full paid version
    preview_match = re.search(r'-d\d+$', current_url)
    if preview_match:
        paid_url = current_url[:preview_match.start()]
        print(f"🔓 Detected public preview URL (suffix: {preview_match.group()})")
        print(f"   Navigating to paid version: {paid_url}")
        page.goto(paid_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        return paid_url

    return current_url


def _check_authentication(page, first_run: bool):
    """Check if user is properly authenticated."""
    initial_content = page.content()
    paywall_indicators = [
        "You're reading the free version",
        "For paid subscribers this week"
    ]

    if any(indicator in initial_content for indicator in paywall_indicators):
        print("\n" + "⚠️ " * 20)
        print("WARNING: You appear to be viewing the FREE version of Fix The News!")
        print("The fetched content contains subscriber paywall text.")
        print("\nTo fix this:")
        print("1. Run: python login_to_ftn.py")
        print("2. Log in to your PAID FTN account in the browser window")
        print("3. After logging in, press Ctrl+C to save the session")
        print("4. Then re-run this fetch script")
        print("⚠️ " * 20 + "\n")

        if not first_run:
            print("Your saved session may have expired. Please log in again.")
            sys.exit(1)
    else:
        print("✅ Authenticated - fetching full subscriber content")


def _extract_issue_number(current_url: str, page_title: str, html_content: str) -> str:
    """Extract issue number from URL, title, or content."""
    # Try from URL first
    url_match = re.search(r'/p/(\d+)-', current_url)
    if url_match:
        return url_match.group(1)

    # Try from page title
    issue_match = re.search(r'#(\d+)', page_title)
    if issue_match:
        return issue_match.group(1)

    # Try in content
    issue_match = re.search(r'#(\d+)', html_content[:5000])
    if issue_match:
        return issue_match.group(1)

    # Fallback to current date
    return datetime.now().strftime("%Y%m%d")


def _save_html_output(html_content: str, issue_number: str, output_dir: str) -> Path:
    """Save HTML content to file."""
    output_path = Path(output_dir) / f"FTN-{issue_number}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ Saved to: {output_path}")
    print(f"   Size: {len(html_content):,} bytes")
    print(f"   Issue: #{issue_number}")

    return output_path


def fetch_ftn_latest(output_dir: str = ".", headless: bool = True, force_login: bool = False, url: str = None):
    """
    Fetch Fix The News content using a dedicated Firefox profile.

    On first run (or with --force-login), opens browser for you to log in.
    Subsequent runs use saved cookies.

    Args:
        output_dir: Directory to save HTML file
        headless: Run in headless mode (default: True)
        force_login: Force interactive login even if cookies exist
        url: Specific FTN article URL to fetch (default: /latest)

    Returns:
        Path to saved HTML file
    """
    profile_dir = get_profile_dir()
    cookies_file, first_run = _setup_browser_session(profile_dir, headless, force_login)

    with sync_playwright() as p:
        # Launch Firefox with persistent context using dedicated profile
        browser = p.firefox.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless if not first_run else False,
            timeout=60000
        )

        try:
            page = browser.new_page()

            # Navigate to Fix The News (use provided URL or default to /latest)
            target_url = url if url else "https://fixthenews.com/latest"
            print(f"🌐 Navigating to: {target_url}")
            page.goto(target_url, wait_until="networkidle", timeout=30000)

            # On first run, wait for user to log in
            if first_run:
                _handle_first_run_login(page, browser, cookies_file)

            # Wait for content to load
            page.wait_for_timeout(3000)

            current_url = page.url
            print(f"📰 Loaded: {current_url}")

            # Strip preview suffix if needed
            current_url = _strip_preview_suffix_from_url(page, current_url, url is not None)

            # Check authentication
            _check_authentication(page, first_run)

            # Now activate reader mode to get clean content
            print("📖 Activating reader mode...")
            reader_url = f"about:reader?url={current_url}"
            page.goto(reader_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            # Get the reader mode HTML
            html_content = page.content()
            print("   ✓ Reader mode HTML captured")

            # Extract issue number
            page_title = page.title()
            issue_number = _extract_issue_number(current_url, page_title, html_content)

            # Save output
            return _save_html_output(html_content, issue_number, output_dir)

        except PlaywrightTimeout as e:
            print(f"❌ Timeout error: {e}")
            print("   Try running with --no-headless to see what's happening")
            sys.exit(1)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        finally:
            browser.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fetch Fix The News content using dedicated Firefox profile',
        epilog='On first run, browser opens for login. Subsequent runs are automatic.'
    )
    parser.add_argument(
        '--output',
        default='.',
        help='Output directory for HTML file (default: current directory)'
    )
    parser.add_argument(
        '--url',
        help='Specific FTN article URL to fetch (default: /latest)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser window (useful for debugging)'
    )
    parser.add_argument(
        '--force-login',
        action='store_true',
        help='Force login even if cookies exist (to refresh session)'
    )

    args = parser.parse_args()

    fetch_ftn_latest(
        output_dir=args.output,
        headless=not args.no_headless,
        force_login=args.force_login,
        url=args.url
    )


if __name__ == '__main__':
    main()
