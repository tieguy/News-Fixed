# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Utility functions for News, Fixed."""

import qrcode
import io
import base64
from datetime import datetime


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


def generate_qr_code_file(url: str, output_dir: str = None, size: int = 10) -> str:
    """
    Generate a QR code for a URL and save to file.

    Args:
        url: The URL to encode in the QR code
        output_dir: Directory to save QR code (default: cache/qr_codes)
        size: Size of the QR code (default: 10)

    Returns:
        Path to saved QR code file
    """
    from pathlib import Path
    import hashlib

    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "cache" / "qr_codes"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from URL hash
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    filename = f"qr_{url_hash}.png"
    filepath = output_dir / filename

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Save image
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(filepath))

    return str(filepath)


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
    themes = {
        1: "Health & Education",
        2: "Environment & Conservation",
        3: "Technology & Energy",
        4: "Society & Youth Movements"
    }
    return themes.get(day_number, "Unknown Theme")


def truncate_text(text: str, max_words: int) -> str:
    """
    Truncate text to a maximum number of words.

    Args:
        text: Text to truncate
        max_words: Maximum number of words

    Returns:
        Truncated text
    """
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words]) + '...'


def extract_source_name(url: str) -> str:
    """
    Extract a readable source name from a URL.

    Args:
        url: Source URL

    Returns:
        Readable source name (e.g., "nature.com")
    """
    from urllib.parse import urlparse

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
