#!/usr/bin/env python3
"""Open Firefox with dedicated FTN profile for manual login."""

from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    profile_dir = Path(__file__).parent / ".firefox-profile-ftn"
    profile_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("Opening Firefox for Fix The News login...")
    print("=" * 70)
    print(f"Profile directory: {profile_dir}")
    print()
    print("Instructions:")
    print("1. Log in to Fix The News with your PAID SUBSCRIBER account")
    print("2. After login, open a recent post to verify you can see full content")
    print("   (Look for absence of 'You're reading the free version' text)")
    print("3. Once verified, press Ctrl+C here to save the session")
    print()
    print("IMPORTANT: Make sure you're logged in to a PAID account!")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.firefox.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False
        )

        page = browser.new_page()
        page.goto("https://fixthenews.com")

        try:
            # Wait indefinitely
            print("\nBrowser is open. Press Ctrl+C when you're done...")
            while True:
                page.wait_for_timeout(1000)
        except KeyboardInterrupt:
            print("\n\n✅ Closing browser. Your session has been saved!")
            print(f"   Profile saved to: {profile_dir}")
            print("\nYou can now run automated fetching with:")
            print("   python -m src.fetch_ftn_clean")
        finally:
            browser.close()


if __name__ == '__main__':
    main()
