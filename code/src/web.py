# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Flask web application for News, Fixed."""

import os
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent.parent / "templates"),
    static_folder=str(Path(__file__).parent.parent / "static")
)

# Configuration
app.config['CACHE_DIR'] = Path(os.getenv('CACHE_DIR', 'cache'))


def get_current_week() -> str:
    """Get current ISO week in YYYY-WWW format."""
    from datetime import datetime
    now = datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


def get_cached_pdf_path() -> Path | None:
    """Get path to current week's cached PDF if it exists."""
    week = get_current_week()
    cache_dir = app.config['CACHE_DIR']
    pdf_path = cache_dir / week / "combined.pdf"

    if pdf_path.exists():
        return pdf_path
    return None


@app.route('/')
def index():
    """Landing page."""
    week = get_current_week()
    has_pdf = get_cached_pdf_path() is not None

    return render_template(
        'landing.html',
        week=week,
        has_pdf=has_pdf
    )


@app.route('/download')
def download():
    """Download the current week's PDF."""
    pdf_path = get_cached_pdf_path()

    if pdf_path is None:
        return jsonify({
            'error': 'No PDF available for this week yet',
            'week': get_current_week()
        }), 404

    week = get_current_week()
    download_name = f"news_fixed_{week}.pdf"

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )


@app.route('/health')
def health():
    """Health check endpoint for fly.io."""
    return jsonify({
        'status': 'healthy',
        'service': 'news-fixed',
        'week': get_current_week()
    }), 200


if __name__ == '__main__':
    # Development server only - use gunicorn in production
    app.run(debug=True, port=8080)
