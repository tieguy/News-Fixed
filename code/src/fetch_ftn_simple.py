"""Fetch Fix The News content using browser automation (manual login)."""

import sys
import re
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def fetch_ftn_latest(output_dir: str = ".", headless: bool = False):
    """
    Fetch the latest Fix The News post using Firefox.

    Note: You'll need to log in manually the first time if prompted.

    Args:
        output_dir: Directory to save HTML file
        headless: Run in headless mode (default: False for first run)

    Returns:
        Path to saved HTML file
    """
    print(f"🦊 Launching Firefox...")
    print(f"   Headless mode: {headless}")

    with sync_playwright() as p:
        # Launch browser
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to Fix The News
            print("🌐 Navigating to Fix The News...")
            page.goto("https://fixthenews.com", wait_until="networkidle", timeout=30000)

            # Check if we need to log in
            if "sign in" in page.content().lower() or "log in" in page.content().lower():
                print("⚠️  You may need to log in. Browser window will stay open.")
                print("   Please log in, then press Enter to continue...")
                if not headless:
                    input()

            # Wait a bit for any auth
            page.wait_for_timeout(2000)

            # Try to find the latest post link
            print("🔍 Looking for latest post...")

            try:
                # Look for first article link
                first_post = page.locator('article a, .post-preview a, h2 a').first
                post_url = first_post.get_attribute('href')

                # Make sure it's a full URL
                if not post_url.startswith('http'):
                    post_url = f"https://fixthenews.com{post_url}"

                print(f"📰 Found latest post: {post_url}")

                # Navigate to the post
                page.goto(post_url, wait_until="networkidle", timeout=30000)

            except Exception as e:
                print(f"⚠️  Could not auto-detect latest post: {e}")
                print("   Using current page content instead")

            # Wait for content to load
            page.wait_for_timeout(2000)

            # Get the full HTML
            html_content = page.content()

            # Try to extract issue number from the page
            issue_match = re.search(r'#(\d+)', page.title() + html_content[:5000])
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
            print(f"   Size: {len(html_content)} bytes")

            return output_path

        except PlaywrightTimeout as e:
            print(f"❌ Timeout error: {e}")
            print("   Try running without headless mode")
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

    parser = argparse.ArgumentParser(description='Fetch Fix The News content using Firefox')
    parser.add_argument(
        '--output',
        default='.',
        help='Output directory for HTML file'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (no browser window)'
    )

    args = parser.parse_args()

    fetch_ftn_latest(
        output_dir=args.output,
        headless=args.headless
    )


if __name__ == '__main__':
    main()
