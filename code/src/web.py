# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Flask web application for News, Fixed."""

import os
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify
from dotenv import load_dotenv
from cache import PDFCache, get_current_week

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent.parent / "templates"),
    static_folder=str(Path(__file__).parent.parent / "static")
)

# Configuration
cache_dir = Path(os.getenv('CACHE_DIR', 'cache'))
pdf_cache = PDFCache(cache_dir)


@app.route('/')
def index():
    """Landing page."""
    week = get_current_week()
    has_pdf = pdf_cache.is_cached(week)
    metadata = pdf_cache.get_metadata(week)

    return render_template(
        'landing.html',
        week=week,
        has_pdf=has_pdf,
        cached_at=metadata.get('cached_at') if metadata else None
    )


@app.route('/download')
def download():
    """Download the current week's PDF."""
    week = get_current_week()
    pdf_path = pdf_cache.get_cached_pdf(week)

    if pdf_path is None:
        return jsonify({
            'error': 'No PDF available for this week yet',
            'week': week
        }), 404

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
    week = get_current_week()
    return jsonify({
        'status': 'healthy',
        'service': 'news-fixed',
        'week': week,
        'has_pdf': pdf_cache.is_cached(week)
    }), 200


if __name__ == '__main__':
    # Development server only - use gunicorn in production
    app.run(debug=True, port=8080)
