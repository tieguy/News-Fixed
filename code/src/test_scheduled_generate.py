# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Tests for scheduled_generate module."""

import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest


def test_fetch_latest_ftn_via_rss_success():
    """fetch_latest_ftn_via_rss returns parsed FTN data on success."""
    from scheduled_generate import fetch_latest_ftn_via_rss

    # Mock RSS response
    rss_content = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Fix The News #317: Progress in Healthcare</title>
                <link>https://fixthe.news/issue/317</link>
                <content:encoded><![CDATA[<html><body>Test content</body></html>]]></content:encoded>
            </item>
        </channel>
    </rss>
    """

    with patch('scheduled_generate.httpx.get') as mock_get:
        mock_response = Mock()
        mock_response.text = rss_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_latest_ftn_via_rss()

        assert result is not None
        assert result['title'] == 'Fix The News #317: Progress in Healthcare'
        assert result['issue_number'] == '317'
        assert result['url'] == 'https://fixthe.news/issue/317'
        assert 'Test content' in result['content']


def test_fetch_latest_ftn_via_rss_http_error():
    """fetch_latest_ftn_via_rss returns None on HTTP error."""
    from scheduled_generate import fetch_latest_ftn_via_rss

    with patch('scheduled_generate.httpx.get') as mock_get:
        mock_get.side_effect = Exception("Network error")

        result = fetch_latest_ftn_via_rss()

        assert result is None


def test_fetch_latest_ftn_via_rss_xml_parse_error():
    """fetch_latest_ftn_via_rss returns None on XML parse error."""
    from scheduled_generate import fetch_latest_ftn_via_rss

    with patch('scheduled_generate.httpx.get') as mock_get:
        mock_response = Mock()
        mock_response.text = "Invalid XML"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_latest_ftn_via_rss()

        assert result is None


def test_fetch_latest_ftn_via_rss_no_channel():
    """fetch_latest_ftn_via_rss returns None when no channel element."""
    from scheduled_generate import fetch_latest_ftn_via_rss

    rss_content = """<?xml version="1.0"?>
    <rss version="2.0">
    </rss>
    """

    with patch('scheduled_generate.httpx.get') as mock_get:
        mock_response = Mock()
        mock_response.text = rss_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_latest_ftn_via_rss()

        assert result is None


def test_fetch_latest_ftn_via_rss_no_items():
    """fetch_latest_ftn_via_rss returns None when no items in channel."""
    from scheduled_generate import fetch_latest_ftn_via_rss

    rss_content = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
        </channel>
    </rss>
    """

    with patch('scheduled_generate.httpx.get') as mock_get:
        mock_response = Mock()
        mock_response.text = rss_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_latest_ftn_via_rss()

        assert result is None


def test_fetch_latest_ftn_via_rss_no_content():
    """fetch_latest_ftn_via_rss returns None when no content in item."""
    from scheduled_generate import fetch_latest_ftn_via_rss

    rss_content = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Fix The News #317</title>
                <link>https://fixthe.news/issue/317</link>
            </item>
        </channel>
    </rss>
    """

    with patch('scheduled_generate.httpx.get') as mock_get:
        mock_response = Mock()
        mock_response.text = rss_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_latest_ftn_via_rss()

        assert result is None


def test_fetch_latest_ftn_via_rss_fallback_to_description():
    """fetch_latest_ftn_via_rss falls back to description if content:encoded missing."""
    from scheduled_generate import fetch_latest_ftn_via_rss

    rss_content = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Fix The News #315</title>
                <link>https://fixthe.news/issue/315</link>
                <description>Fallback content</description>
            </item>
        </channel>
    </rss>
    """

    with patch('scheduled_generate.httpx.get') as mock_get:
        mock_response = Mock()
        mock_response.text = rss_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_latest_ftn_via_rss()

        assert result is not None
        assert result['issue_number'] == '315'
        assert result['content'] == 'Fallback content'


def test_fetch_latest_ftn_via_rss_issue_number_fallback():
    """fetch_latest_ftn_via_rss uses date if no issue number in title."""
    from scheduled_generate import fetch_latest_ftn_via_rss

    rss_content = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Latest News Update</title>
                <link>https://fixthe.news</link>
                <description>Content here</description>
            </item>
        </channel>
    </rss>
    """

    with patch('scheduled_generate.httpx.get') as mock_get:
        mock_response = Mock()
        mock_response.text = rss_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_latest_ftn_via_rss()

        assert result is not None
        # Should have a date-based issue number like YYYYMMDD
        assert len(result['issue_number']) == 8
        assert result['issue_number'].isdigit()


def test_main_dry_run():
    """main with --dry-run exits without generating PDF."""
    from scheduled_generate import main

    with patch('sys.argv', ['scheduled_generate.py', '--dry-run']):
        with patch('scheduled_generate.PDFCache') as mock_cache_class:
            mock_cache = Mock()
            mock_cache.is_cached.return_value = False
            mock_cache_class.return_value = mock_cache

            exit_code = main()

            assert exit_code == 0
            # Should not have called cache_pdf
            mock_cache.cache_pdf.assert_not_called()


def test_main_already_cached():
    """main exits if PDF already cached for current week."""
    from scheduled_generate import main

    with patch('sys.argv', ['scheduled_generate.py']):
        with patch('scheduled_generate.PDFCache') as mock_cache_class:
            mock_cache = Mock()
            mock_cache.is_cached.return_value = True
            mock_cache_class.return_value = mock_cache

            with patch('scheduled_generate.get_current_week', return_value='2026-W03'):
                with patch('scheduled_generate.send_notification'):
                    exit_code = main()

                    assert exit_code == 0
                    mock_cache.cache_pdf.assert_not_called()


def test_main_fetch_ftn_fails():
    """main exits with error if FTN fetch fails."""
    from scheduled_generate import main

    with patch('sys.argv', ['scheduled_generate.py']):
        with patch('scheduled_generate.PDFCache') as mock_cache_class:
            mock_cache = Mock()
            mock_cache.is_cached.return_value = False
            mock_cache_class.return_value = mock_cache

            with patch('scheduled_generate.get_current_week', return_value='2026-W03'):
                with patch('scheduled_generate.fetch_latest_ftn_via_rss', return_value=None):
                    with patch('scheduled_generate.send_notification'):
                        exit_code = main()

                        assert exit_code == 1
                        mock_cache.cache_pdf.assert_not_called()


def test_main_parse_ftn_fails():
    """main exits with error if FTN parsing fails."""
    from scheduled_generate import main

    with patch('sys.argv', ['scheduled_generate.py']):
        with patch('scheduled_generate.PDFCache') as mock_cache_class:
            mock_cache = Mock()
            mock_cache.is_cached.return_value = False
            mock_cache_class.return_value = mock_cache

            ftn_data = {
                'title': 'Test',
                'content': '<html>Test</html>',
                'url': 'https://test.com',
                'issue_number': '300'
            }

            with patch('scheduled_generate.get_current_week', return_value='2026-W03'):
                with patch('scheduled_generate.fetch_latest_ftn_via_rss', return_value=ftn_data):
                    with patch('scheduled_generate.parse_ftn_content', return_value=None):
                        with patch('scheduled_generate.send_notification'):
                            exit_code = main()

                            assert exit_code == 1
                            mock_cache.cache_pdf.assert_not_called()


def test_main_pdf_generation_fails():
    """main exits with error if PDF generation fails."""
    from scheduled_generate import main

    with patch('sys.argv', ['scheduled_generate.py']):
        with patch('scheduled_generate.PDFCache') as mock_cache_class:
            mock_cache = Mock()
            mock_cache.is_cached.return_value = False
            mock_cache_class.return_value = mock_cache

            ftn_data = {
                'title': 'Test',
                'content': '<html>Test</html>',
                'url': 'https://test.com',
                'issue_number': '300'
            }
            ftn_json = {'day_1': {}, 'day_2': {}, 'day_3': {}, 'day_4': {}}

            with patch('scheduled_generate.get_current_week', return_value='2026-W03'):
                with patch('scheduled_generate.fetch_latest_ftn_via_rss', return_value=ftn_data):
                    with patch('scheduled_generate.parse_ftn_content', return_value=ftn_json):
                        with patch('scheduled_generate.generate_combined_pdf', return_value=False):
                            with patch('scheduled_generate.send_notification'):
                                exit_code = main()

                                assert exit_code == 1
                                mock_cache.cache_pdf.assert_not_called()


def test_main_successful_generation():
    """main successfully generates and caches PDF."""
    from scheduled_generate import main

    with patch('sys.argv', ['scheduled_generate.py']):
        with patch('scheduled_generate.PDFCache') as mock_cache_class:
            mock_cache = Mock()
            mock_cache.is_cached.return_value = False
            mock_cache_class.return_value = mock_cache

            ftn_data = {
                'title': 'Test',
                'content': '<html>Test</html>',
                'url': 'https://test.com',
                'issue_number': '300'
            }
            ftn_json = {'day_1': {}, 'day_2': {}, 'day_3': {}, 'day_4': {}}

            with patch('scheduled_generate.get_current_week', return_value='2026-W03'):
                with patch('scheduled_generate.fetch_latest_ftn_via_rss', return_value=ftn_data):
                    with patch('scheduled_generate.parse_ftn_content', return_value=ftn_json):
                        with patch('scheduled_generate.generate_combined_pdf', return_value=True):
                            with patch('scheduled_generate.send_notification'):
                                with patch('tempfile.NamedTemporaryFile') as mock_temp:
                                    # Create a real temp file for the test
                                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                                        temp_path = f.name

                                    try:
                                        mock_file = MagicMock()
                                        mock_file.name = temp_path
                                        mock_file.__enter__.return_value = mock_file
                                        mock_temp.return_value = mock_file

                                        exit_code = main()

                                        assert exit_code == 0
                                        mock_cache.cache_pdf.assert_called_once()
                                    finally:
                                        Path(temp_path).unlink(missing_ok=True)


def test_cache_pdf_called_with_correct_arguments():
    """verify cache_pdf is called with correct argument order."""
    from scheduled_generate import main
    from cache import PDFCache

    # This test ensures the argument order fix is correct
    # The signature is: cache_pdf(pdf_source: Path, week: str = None)
    # We need to verify it's called as cache_pdf(temp_pdf_path, current_week)
    # not cache_pdf(current_week, temp_pdf_path)

    with patch('sys.argv', ['scheduled_generate.py']):
        with patch('scheduled_generate.PDFCache') as mock_cache_class:
            mock_cache = Mock()
            mock_cache.is_cached.return_value = False
            mock_cache_class.return_value = mock_cache

            ftn_data = {
                'title': 'Test',
                'content': '<html>Test</html>',
                'url': 'https://test.com',
                'issue_number': '300'
            }
            ftn_json = {'day_1': {}, 'day_2': {}, 'day_3': {}, 'day_4': {}}

            with patch('scheduled_generate.get_current_week', return_value='2026-W03'):
                with patch('scheduled_generate.fetch_latest_ftn_via_rss', return_value=ftn_data):
                    with patch('scheduled_generate.parse_ftn_content', return_value=ftn_json):
                        with patch('scheduled_generate.generate_combined_pdf', return_value=True):
                            with patch('scheduled_generate.send_notification'):
                                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                                    temp_pdf_path = Path(f.name)

                                try:
                                    with patch('tempfile.NamedTemporaryFile') as mock_temp:
                                        mock_file = MagicMock()
                                        mock_file.name = str(temp_pdf_path)
                                        mock_file.__enter__.return_value = mock_file
                                        mock_temp.return_value = mock_file

                                        exit_code = main()

                                        # Verify cache_pdf was called with Path object first, week second
                                        mock_cache.cache_pdf.assert_called_once()
                                        args = mock_cache.cache_pdf.call_args
                                        # First argument should be Path, second should be string '2026-W03'
                                        assert isinstance(args[0][0], Path)
                                        assert args[0][1] == '2026-W03'
                                finally:
                                    temp_pdf_path.unlink(missing_ok=True)
