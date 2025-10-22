"""Fetch Fix The News content using a dedicated Firefox profile."""

import sys
import re
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def get_profile_dir() -> Path:
    """Get the dedicated Firefox profile directory for FTN fetching."""
    profile_dir = Path(__file__).parent.parent / ".firefox-profile-ftn"
    profile_dir.mkdir(exist_ok=True)
    return profile_dir


def fetch_ftn_latest(output_dir: str = ".", headless: bool = True, force_login: bool = False):
    """
    Fetch the latest Fix The News post using a dedicated Firefox profile.

    On first run (or with --force-login), opens browser for you to log in.
    Subsequent runs use saved cookies.

    Args:
        output_dir: Directory to save HTML file
        headless: Run in headless mode (default: True)
        force_login: Force interactive login even if cookies exist

    Returns:
        Path to saved HTML file
    """
    profile_dir = get_profile_dir()

    print(f"🦊 Using dedicated Firefox profile at: {profile_dir}")

    # Check if this is first run
    cookies_file = profile_dir / "cookies.json"
    first_run = not cookies_file.exists() or force_login

    if first_run:
        print("📝 First run or forced login - browser will open for you to log in")
        print("   After logging in, the script will save your session for future use")
        headless = False  # Force visible on first run

    print(f"   Headless mode: {headless}")

    with sync_playwright() as p:
        # Launch Firefox with persistent context using dedicated profile
        browser = p.firefox.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            timeout=60000
        )

        try:
            page = browser.new_page()

            # Navigate to Fix The News latest post
            print("🌐 Navigating to Fix The News latest post...")
            page.goto("https://fixthenews.com/latest", wait_until="networkidle", timeout=30000)

            # On first run, wait for user to log in
            if first_run:
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

            # /latest redirects to the actual latest post, so we're already there
            # Wait for content to load after redirect
            page.wait_for_timeout(3000)

            current_url = page.url
            print(f"📰 Loaded latest post: {current_url}")

            # Try to trigger reader mode by navigating to about:reader?url=...
            print("📖 Activating reader mode...")
            reader_url = f"about:reader?url={current_url}"
            page.goto(reader_url, wait_until="networkidle", timeout=30000)

            # Wait for reader mode to render
            page.wait_for_timeout(2000)

            # Get the full HTML (now in reader mode)
            html_content = page.content()
            print("   ✓ Reader mode HTML captured")

            # Try to extract issue number from URL (e.g., /p/315-shell-shocked)
            url_match = re.search(r'/p/(\d+)-', current_url)
            if url_match:
                issue_number = url_match.group(1)
            else:
                # Try from page title
                page_title = page.title()
                issue_match = re.search(r'#(\d+)', page_title)
                if not issue_match:
                    # Try in content
                    issue_match = re.search(r'#(\d+)', html_content[:5000])

                if issue_match:
                    issue_number = issue_match.group(1)
                else:
                    # Fallback to current date
                    issue_number = datetime.now().strftime("%Y%m%d")

            # Save HTML to file
            output_path = Path(output_dir) / f"FTN-{issue_number}.html"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ Saved to: {output_path}")
            print(f"   Size: {len(html_content):,} bytes")
            print(f"   Issue: #{issue_number}")

            return output_path

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
        force_login=args.force_login
    )


if __name__ == '__main__':
    main()
