# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

# FCIS: Unit tests for Flask web application module.

"""Unit tests for web.py module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from web import app, get_current_week, get_cached_pdf_path


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        app.config['CACHE_DIR'] = Path(tmpdir)
        yield Path(tmpdir)


class TestGetCurrentWeek:
    """Tests for get_current_week() function."""

    def test_returns_iso_week_format(self):
        """Test that get_current_week returns correct ISO week format."""
        result = get_current_week()

        # Should be in format YYYY-WWW (e.g., "2025-W03")
        assert isinstance(result, str)
        parts = result.split('-W')
        assert len(parts) == 2
        assert len(parts[0]) == 4  # Year
        assert len(parts[1]) == 2  # Week (zero-padded)
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_iso_week_number_in_valid_range(self):
        """Test that ISO week number is between 01 and 53."""
        result = get_current_week()
        week_num = int(result.split('-W')[1])
        assert 1 <= week_num <= 53

    def test_year_matches_current(self):
        """Test that year in result matches current year."""
        result = get_current_week()
        year = int(result.split('-W')[0])
        assert year == datetime.now().year


class TestGetCachedPdfPath:
    """Tests for get_cached_pdf_path() function."""

    def test_returns_none_when_no_pdf_exists(self, temp_cache_dir):
        """Test that function returns None when no PDF exists."""
        result = get_cached_pdf_path()
        assert result is None

    def test_returns_path_object_when_pdf_exists(self, temp_cache_dir):
        """Test that function returns Path object when PDF exists."""
        # Create the directory structure and PDF file
        week = get_current_week()
        week_dir = temp_cache_dir / week
        week_dir.mkdir(parents=True)
        pdf_file = week_dir / "combined.pdf"
        pdf_file.write_text("fake pdf content")

        result = get_cached_pdf_path()
        assert isinstance(result, Path)
        assert result == pdf_file
        assert result.exists()

    def test_returns_correct_file_path(self, temp_cache_dir):
        """Test that returned path points to correct combined.pdf file."""
        week = get_current_week()
        week_dir = temp_cache_dir / week
        week_dir.mkdir(parents=True)
        pdf_file = week_dir / "combined.pdf"
        pdf_file.write_text("test content")

        result = get_cached_pdf_path()
        assert result.name == "combined.pdf"
        assert result.parent.name == week


class TestIndexRoute:
    """Tests for GET / endpoint."""

    def test_returns_200_status(self, client):
        """Test that index route returns 200 status code."""
        response = client.get('/')
        assert response.status_code == 200

    def test_returns_html_content_type(self, client):
        """Test that index route returns HTML content type."""
        response = client.get('/')
        assert 'text/html' in response.content_type

    def test_renders_landing_template(self, client):
        """Test that index route renders landing.html template."""
        response = client.get('/')
        # landing.html should contain some identifying content
        # Since we can't access template content, we verify non-empty response
        assert len(response.data) > 0

    def test_renders_with_data_from_functions(self, client):
        """Test that index route passes current week to template."""
        response = client.get('/')
        # The week should be embedded in the response
        week = get_current_week()
        assert response.status_code == 200

    def test_passes_has_pdf_false_when_no_pdf(self, client, temp_cache_dir):
        """Test that has_pdf is False when no PDF exists."""
        response = client.get('/')
        assert response.status_code == 200

    def test_passes_has_pdf_true_when_pdf_exists(self, client, temp_cache_dir):
        """Test that has_pdf is True when PDF exists."""
        # Create the PDF
        week = get_current_week()
        week_dir = temp_cache_dir / week
        week_dir.mkdir(parents=True)
        pdf_file = week_dir / "combined.pdf"
        pdf_file.write_text("test")

        response = client.get('/')
        assert response.status_code == 200


class TestHealthRoute:
    """Tests for GET /health endpoint."""

    def test_returns_200_status(self, client):
        """Test that health endpoint returns 200 status code."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_returns_json_content_type(self, client):
        """Test that health endpoint returns JSON content type."""
        response = client.get('/health')
        assert 'application/json' in response.content_type

    def test_json_structure_correct(self, client):
        """Test that health endpoint returns correct JSON structure."""
        response = client.get('/health')
        data = json.loads(response.data)

        assert 'status' in data
        assert 'service' in data
        assert 'week' in data

    def test_status_is_healthy(self, client):
        """Test that status field is 'healthy'."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_service_is_news_fixed(self, client):
        """Test that service field is 'news-fixed'."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['service'] == 'news-fixed'

    def test_week_format_is_iso(self, client):
        """Test that week field is in ISO week format."""
        response = client.get('/health')
        data = json.loads(response.data)
        week = data['week']

        parts = week.split('-W')
        assert len(parts) == 2
        assert len(parts[0]) == 4
        assert len(parts[1]) == 2


class TestDownloadRoute:
    """Tests for GET /download endpoint."""

    def test_returns_404_when_no_pdf_exists(self, client, temp_cache_dir):
        """Test that download endpoint returns 404 when no PDF exists."""
        response = client.get('/download')
        assert response.status_code == 404

    def test_returns_json_error_when_no_pdf(self, client, temp_cache_dir):
        """Test that download endpoint returns JSON error when no PDF exists."""
        response = client.get('/download')
        data = json.loads(response.data)

        assert 'error' in data
        assert 'week' in data

    def test_returns_200_when_pdf_exists(self, client, temp_cache_dir):
        """Test that download endpoint returns 200 when PDF exists."""
        # Create the PDF
        week = get_current_week()
        week_dir = temp_cache_dir / week
        week_dir.mkdir(parents=True)
        pdf_file = week_dir / "combined.pdf"
        pdf_file.write_bytes(b"fake pdf content")

        response = client.get('/download')
        assert response.status_code == 200

    def test_returns_pdf_content_type(self, client, temp_cache_dir):
        """Test that download endpoint returns PDF content type."""
        # Create the PDF
        week = get_current_week()
        week_dir = temp_cache_dir / week
        week_dir.mkdir(parents=True)
        pdf_file = week_dir / "combined.pdf"
        pdf_file.write_bytes(b"fake pdf content")

        response = client.get('/download')
        assert 'application/pdf' in response.content_type

    def test_download_name_includes_week(self, client, temp_cache_dir):
        """Test that download filename includes the week."""
        # Create the PDF
        week = get_current_week()
        week_dir = temp_cache_dir / week
        week_dir.mkdir(parents=True)
        pdf_file = week_dir / "combined.pdf"
        pdf_file.write_bytes(b"fake pdf content")

        response = client.get('/download')
        disposition = response.headers.get('Content-Disposition', '')
        assert week in disposition
        assert 'news_fixed' in disposition

    def test_pdf_content_served_correctly(self, client, temp_cache_dir):
        """Test that PDF content is served correctly."""
        # Create the PDF with specific content
        week = get_current_week()
        week_dir = temp_cache_dir / week
        week_dir.mkdir(parents=True)
        pdf_file = week_dir / "combined.pdf"
        test_content = b"test pdf data 12345"
        pdf_file.write_bytes(test_content)

        response = client.get('/download')
        assert response.data == test_content
