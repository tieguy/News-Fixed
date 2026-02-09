# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Utility functions for News, Fixed."""

import qrcode
import io
import base64
from datetime import datetime, timedelta
from urllib.parse import urlparse


def generate_qr_code(url: str, size: int = 10) -> str:
    """
    Generate a QR code for a URL and return as base64 data URI.

    Args:
        url: The URL to encode in the QR code
        size: Size of the QR code (default: 10)

    Returns:
        Base64 data URI string for embedding in HTML
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create an image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 for embedding
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode()

    return f"data:image/png;base64,{img_base64}"


def format_date(date_str: str = None) -> str:
    """
    Format date for newspaper display.

    Args:
        date_str: ISO format date string, or None for today

    Returns:
        Formatted date string (e.g., "Monday, October 21, 2025")
    """
    if date_str:
        date_obj = datetime.fromisoformat(date_str)
    else:
        date_obj = datetime.now()

    return date_obj.strftime("%A, %B %d, %Y")


def get_theme_name(day_number: int) -> str:
    """
    Get the theme name for a given day number.

    Args:
        day_number: Day number (1-4)

    Returns:
        Theme name string
    """
    from ftn_to_json import DEFAULT_THEMES
    theme = DEFAULT_THEMES.get(day_number)
    return theme["name"] if theme else "Unknown Theme"


def get_target_week_monday(base_date: datetime = None) -> datetime:
    """
    Get the Monday of the target newspaper week.

    On Friday-Sunday, targets next week's Monday.
    On Monday-Thursday, targets this week's Monday.

    Args:
        base_date: Base date (defaults to now)

    Returns:
        datetime for the Monday of the target week
    """
    if base_date is None:
        base_date = datetime.now()

    current_weekday = base_date.weekday()  # Monday=0, Sunday=6

    if current_weekday >= 4:  # Friday-Sunday → next week
        days_until_monday = (7 - current_weekday) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        monday = base_date + timedelta(days=days_until_monday)
    else:  # Monday-Thursday → this week
        monday = base_date - timedelta(days=current_weekday)

    return monday


def extract_source_name(url: str) -> str:
    """
    Extract a readable source name from a URL.

    Args:
        url: Source URL

    Returns:
        Readable source name (e.g., "nature.com")
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    # Remove www. prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain


if __name__ == "__main__":
    # Test QR code generation
    print("Testing QR code generation...")
    test_url = "https://www.nature.com/articles/example"
    qr_data = generate_qr_code(test_url)
    print(f"Generated QR code data URI (length: {len(qr_data)})")

    # Test date formatting
    print(f"\nFormatted date: {format_date()}")

    # Test theme names
    print("\nThemes:")
    for i in range(1, 5):
        print(f"  Day {i}: {get_theme_name(i)}")

    # Test source name extraction
    print(f"\nSource name: {extract_source_name(test_url)}")

    print("\n✓ All utilities working!")
