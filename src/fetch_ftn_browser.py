"""Fetch Fix The News content using Firefox with existing profile."""

import sys
import re
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def fetch_ftn_latest(firefox_profile: str, output_dir: str = ".", headless: bool = True):
    """
    Fetch the latest Fix The News post using Firefox with existing profile.

    Args:
        firefox_profile: Path to Firefox profile directory
        output_dir: Directory to save HTML file
        headless: Run in headless mode (default: True)

    Returns:
        Path to saved HTML file
    """
    print(f"🦊 Preparing Firefox profile...")

    # Copy profile to temporary directory to avoid conflicts
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_profile = Path(temp_dir) / "firefox_profile"
        print(f"   Copying profile to: {temp_profile}")
        shutil.copytree(firefox_profile, temp_profile, ignore_dangling_symlinks=True)

        print(f"   Headless mode: {headless}")

        with sync_playwright() as p:
            # Launch Firefox with persistent context (using copied profile)
            browser = p.firefox.launch_persistent_context(
                user_data_dir=str(temp_profile),
                headless=headless,
                timeout=60000  # 60 second timeout
            )

            try:
                page = browser.new_page()

                # Navigate to Fix The News
                print("🌐 Navigating to Fix The News...")
                page.goto("https://fixthenews.com", wait_until="networkidle", timeout=30000)

                # Wait a bit for any auth redirects
                page.wait_for_timeout(2000)

                # Try to find the latest post link
                print("🔍 Looking for latest post...")

                # Option 1: Click on first post link
                try:
                    # Look for the first article link in the main content
                    first_post = page.locator('article a.post-preview-title').first
                    post_url = first_post.get_attribute('href')
                    print(f"📰 Found latest post: {post_url}")

                    # Navigate to the post
                    page.goto(post_url, wait_until="networkidle", timeout=30000)

                except Exception as e:
                    print(f"⚠️  Could not auto-detect latest post: {e}")
                    print("   Using main page content instead")

                # Wait for content to load
                page.wait_for_timeout(2000)

                # Get the full HTML
                html_content = page.content()

                # Try to extract issue number from the page
                issue_match = re.search(r'#(\d+)', page.title())
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
                print("   Try running with --no-headless to see what's happening")
                sys.exit(1)

            except Exception as e:
                print(f"❌ Error: {e}")
                sys.exit(1)

            finally:
                browser.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Fetch Fix The News content using Firefox')
    parser.add_argument(
        '--profile',
        default='/home/louie/.mozilla/firefox/xc4xn4rg.default-release',
        help='Firefox profile path'
    )
    parser.add_argument(
        '--output',
        default='.',
        help='Output directory for HTML file'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser window (useful for debugging)'
    )

    args = parser.parse_args()

    # Check if profile exists
    profile_path = Path(args.profile)
    if not profile_path.exists():
        print(f"❌ Firefox profile not found: {profile_path}")
        print("\nTo find your profile path:")
        print("  1. Type 'about:profiles' in Firefox address bar")
        print("  2. Look for 'Root Directory' under your default profile")
        sys.exit(1)

    fetch_ftn_latest(
        firefox_profile=args.profile,
        output_dir=args.output,
        headless=not args.no_headless
    )


if __name__ == '__main__':
    main()
