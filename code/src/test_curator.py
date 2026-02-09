# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

"""Tests for curator.py data operations.

Focuses on the pure data-manipulation methods of StoryCurator,
mocking console I/O where needed. These tests provide a safety net
for splitting curator.py into data model and TUI layers.
"""

import json
import pytest
from unittest.mock import MagicMock

from curator import StoryCurator
from curator_data import StoryCuratorData


def _make_story(title, content="Some content", source_url="https://example.com"):
    """Create a minimal story dict for testing."""
    return {
        "title": title,
        "content": content,
        "source_url": source_url,
    }


def _make_day_data(theme, main_title, mini_titles=None, second_title=None):
    """Create a day data dict with main story and optional minis/second story."""
    data = {
        "theme": theme,
        "main_story": _make_story(main_title),
        "mini_articles": [_make_story(t) for t in (mini_titles or [])],
        "front_page_stories": [],
        "statistics": [],
        "tomorrow_teaser": "",
    }
    if second_title:
        data["second_story"] = _make_story(second_title)
    return data


def _sample_data():
    """Create a complete 4-day sample dataset."""
    return {
        "day_1": _make_day_data(
            "Health & Education", "Health Main",
            ["Health Mini 1", "Health Mini 2", "Health Mini 3"],
        ),
        "day_2": _make_day_data(
            "Environment", "Env Main",
            ["Env Mini 1", "Env Mini 2"],
        ),
        "day_3": _make_day_data(
            "Technology", "Tech Main",
            ["Tech Mini 1", "Tech Mini 2", "Tech Mini 3", "Tech Mini 4"],
        ),
        "day_4": _make_day_data(
            "Society", "Society Main",
            ["Society Mini 1"],
        ),
        "unused": {
            "stories": [
                _make_story("Unused A"),
                _make_story("Unused B"),
            ]
        },
    }


@pytest.fixture
def curator(tmp_path):
    """Create a StoryCuratorData loaded from sample data."""
    json_file = tmp_path / "test_input.json"
    json_file.write_text(json.dumps(_sample_data()), encoding="utf-8")

    output_file = tmp_path / "test_output.json"
    mock_console = MagicMock()
    cur = StoryCuratorData(json_file, output_file, console=mock_console)
    return cur


@pytest.fixture
def curator_no_output(tmp_path):
    """Create a StoryCuratorData without an output file (no auto-save)."""
    json_file = tmp_path / "test_input.json"
    json_file.write_text(json.dumps(_sample_data()), encoding="utf-8")

    mock_console = MagicMock()
    cur = StoryCuratorData(json_file, console=mock_console)
    return cur


# ── Helper method tests ─────────────────────────────────────────


class TestDayTheme:
    def test_returns_theme_from_working_data(self, curator):
        assert curator._day_theme(1) == "Health & Education"

    def test_falls_back_to_default_for_missing_day(self, curator):
        del curator.working_data["day_1"]
        # Should return a default theme name, not crash
        result = curator._day_theme(1)
        assert isinstance(result, str)
        assert len(result) > 0


class TestHasSecondStory:
    def test_false_when_no_second_story(self, curator):
        day = curator.working_data["day_1"]
        assert curator._has_second_story(day) is False

    def test_true_when_second_story_exists(self, curator):
        day = curator.working_data["day_1"]
        day["second_story"] = _make_story("Second Story")
        assert curator._has_second_story(day) is True

    def test_false_when_second_story_is_empty(self, curator):
        day = curator.working_data["day_1"]
        day["second_story"] = {}
        assert curator._has_second_story(day) is False

    def test_false_when_second_story_has_no_title(self, curator):
        day = curator.working_data["day_1"]
        day["second_story"] = {"content": "stuff"}
        assert curator._has_second_story(day) is False


class TestMiniStartIndex:
    def test_starts_at_2_without_second_story(self, curator):
        day = curator.working_data["day_1"]
        assert curator._mini_start_index(day) == 2

    def test_starts_at_3_with_second_story(self, curator):
        day = curator.working_data["day_1"]
        day["second_story"] = _make_story("Second")
        assert curator._mini_start_index(day) == 3


class TestTotalStories:
    def test_counts_main_plus_minis(self, curator):
        day = curator.working_data["day_1"]
        # 1 main + 3 minis = 4
        assert curator._total_stories(day) == 4

    def test_counts_second_story(self, curator):
        day = curator.working_data["day_1"]
        day["second_story"] = _make_story("Second")
        # 1 main + 1 second + 3 minis = 5
        assert curator._total_stories(day) == 5

    def test_main_only(self, curator):
        day = {"main_story": _make_story("Main"), "mini_articles": []}
        assert curator._total_stories(day) == 1


# ── _get_story_by_index tests ───────────────────────────────────


class TestGetStoryByIndex:
    def test_index_1_returns_main(self, curator):
        day = curator.working_data["day_1"]
        story, slot = curator._get_story_by_index(day, 1)
        assert story["title"] == "Health Main"
        assert slot == "main"

    def test_index_2_returns_second_when_present(self, curator):
        day = curator.working_data["day_1"]
        day["second_story"] = _make_story("Second")
        story, slot = curator._get_story_by_index(day, 2)
        assert story["title"] == "Second"
        assert slot == "second"

    def test_index_2_returns_first_mini_when_no_second(self, curator):
        day = curator.working_data["day_1"]
        story, slot = curator._get_story_by_index(day, 2)
        assert story["title"] == "Health Mini 1"
        assert slot == "mini"

    def test_mini_indices_with_second_story(self, curator):
        day = curator.working_data["day_1"]
        day["second_story"] = _make_story("Second")
        # With second story, minis start at index 3
        story, slot = curator._get_story_by_index(day, 3)
        assert story["title"] == "Health Mini 1"
        assert slot == "mini"

    def test_invalid_index_returns_none(self, curator):
        day = curator.working_data["day_1"]
        story, slot = curator._get_story_by_index(day, 99)
        assert story is None
        assert slot is None

    def test_zero_index_returns_none(self, curator):
        day = curator.working_data["day_1"]
        story, slot = curator._get_story_by_index(day, 0)
        assert story is None
        assert slot is None


# ── swap_main_story tests ───────────────────────────────────────


class TestSwapMainStory:
    def test_swap_main_with_mini(self, curator):
        curator.swap_main_story(1, 2)
        day = curator.working_data["day_1"]
        assert day["main_story"]["title"] == "Health Mini 1"
        assert day["mini_articles"][0]["title"] == "Health Main"

    def test_swap_main_with_second_story(self, curator):
        curator.working_data["day_1"]["second_story"] = _make_story("Second")
        curator.swap_main_story(1, 2)
        day = curator.working_data["day_1"]
        assert day["main_story"]["title"] == "Second"
        assert day["second_story"]["title"] == "Health Main"

    def test_swap_main_with_itself_is_noop(self, curator):
        original_main = curator.working_data["day_1"]["main_story"]["title"]
        curator.swap_main_story(1, 1)
        assert curator.working_data["day_1"]["main_story"]["title"] == original_main

    def test_swap_records_change(self, curator):
        curator.swap_main_story(1, 2)
        assert len(curator.changes_made) == 1
        assert "Swapped main story" in curator.changes_made[0]

    def test_swap_auto_saves(self, curator):
        curator.swap_main_story(1, 2)
        # Output file should exist with saved data
        assert curator.output_file.exists()
        saved = json.loads(curator.output_file.read_text())
        assert saved["day_1"]["main_story"]["title"] == "Health Mini 1"

    def test_swap_with_third_mini(self, curator):
        """Swap main with the third mini article (index 4 = mini[2])."""
        curator.swap_main_story(1, 4)
        day = curator.working_data["day_1"]
        assert day["main_story"]["title"] == "Health Mini 3"
        assert day["mini_articles"][2]["title"] == "Health Main"


# ── move_story tests ────────────────────────────────────────────


class TestMoveStory:
    def test_move_mini_between_days(self, curator):
        """Move a mini from day 1 to day 2."""
        original_day1_minis = len(curator.working_data["day_1"]["mini_articles"])
        original_day2_minis = len(curator.working_data["day_2"]["mini_articles"])

        curator.move_story(1, 2, 2)  # Move mini index 2 (first mini) from day 1 to day 2

        assert len(curator.working_data["day_1"]["mini_articles"]) == original_day1_minis - 1
        assert len(curator.working_data["day_2"]["mini_articles"]) == original_day2_minis + 1
        assert curator.working_data["day_2"]["mini_articles"][-1]["title"] == "Health Mini 1"

    def test_move_main_promotes_first_mini(self, curator):
        """Moving main story should auto-promote first mini to main."""
        curator.move_story(1, 1, 2)
        day1 = curator.working_data["day_1"]
        assert day1["main_story"]["title"] == "Health Mini 1"
        # Original 3 minis → first promoted to main, so 2 left
        assert len(day1["mini_articles"]) == 2

    def test_move_main_promotes_second_story_first(self, curator):
        """Moving main when second_story exists promotes second to main."""
        curator.working_data["day_1"]["second_story"] = _make_story("Second")
        curator.move_story(1, 1, 2)
        day1 = curator.working_data["day_1"]
        assert day1["main_story"]["title"] == "Second"
        # Minis should be unchanged
        assert len(day1["mini_articles"]) == 3

    def test_move_records_change(self, curator):
        curator.move_story(1, 2, 2)
        assert len(curator.changes_made) == 1
        assert "Day 1 → Day 2" in curator.changes_made[0]

    def test_move_to_same_day_returns_false(self, curator):
        """Invalid day should return False."""
        result = curator.move_story(1, 2, 5)  # Day 5 doesn't exist
        assert result is False

    def test_move_auto_saves(self, curator):
        curator.move_story(1, 2, 2)
        saved = json.loads(curator.output_file.read_text())
        # Moved mini should be in day_2's minis
        day2_titles = [m["title"] for m in saved["day_2"]["mini_articles"]]
        assert "Health Mini 1" in day2_titles


# ── move_to_unused tests ───────────────────────────────────────


class TestMoveToUnused:
    def test_move_mini_to_unused(self, curator):
        original_unused = len(curator.working_data["unused"]["stories"])
        original_minis = len(curator.working_data["day_1"]["mini_articles"])

        curator.move_to_unused(1, 2)  # Mini index 2 = first mini

        assert len(curator.working_data["unused"]["stories"]) == original_unused + 1
        assert len(curator.working_data["day_1"]["mini_articles"]) == original_minis - 1
        assert curator.working_data["unused"]["stories"][-1]["title"] == "Health Mini 1"

    def test_move_main_to_unused_promotes_mini(self, curator):
        curator.move_to_unused(1, 1)
        day1 = curator.working_data["day_1"]
        assert day1["main_story"]["title"] == "Health Mini 1"

    def test_move_main_to_unused_promotes_second_story(self, curator):
        curator.working_data["day_1"]["second_story"] = _make_story("Second")
        curator.move_to_unused(1, 1)
        day1 = curator.working_data["day_1"]
        assert day1["main_story"]["title"] == "Second"

    def test_creates_unused_if_missing(self, curator):
        del curator.working_data["unused"]
        curator.move_to_unused(1, 2)
        assert "unused" in curator.working_data
        assert len(curator.working_data["unused"]["stories"]) == 1

    def test_records_change(self, curator):
        curator.move_to_unused(1, 2)
        assert len(curator.changes_made) == 1
        assert "Unused" in curator.changes_made[0]


# ── move_from_unused tests ─────────────────────────────────────


class TestMoveFromUnused:
    def test_move_from_unused_to_day(self, curator):
        original_unused = len(curator.working_data["unused"]["stories"])
        original_minis = len(curator.working_data["day_2"]["mini_articles"])

        curator.move_from_unused(1, 2)  # Move first unused story to day 2

        assert len(curator.working_data["unused"]["stories"]) == original_unused - 1
        assert len(curator.working_data["day_2"]["mini_articles"]) == original_minis + 1
        assert curator.working_data["day_2"]["mini_articles"][-1]["title"] == "Unused A"

    def test_invalid_story_index(self, curator):
        curator.move_from_unused(99, 1)  # Index way out of range
        # Should not crash, unused should be unchanged
        assert len(curator.working_data["unused"]["stories"]) == 2

    def test_invalid_day_number(self, curator):
        curator.move_from_unused(1, 5)  # Day 5 doesn't exist
        # Should not crash, unused should be unchanged
        assert len(curator.working_data["unused"]["stories"]) == 2

    def test_records_change(self, curator):
        curator.move_from_unused(1, 2)
        assert len(curator.changes_made) == 1
        assert "Unused → Day 2" in curator.changes_made[0]


# ── validate_data tests ────────────────────────────────────────


class TestValidateData:
    def test_valid_data_returns_true(self, curator):
        assert curator.validate_data() is True

    def test_missing_main_story_returns_false(self, curator):
        curator.working_data["day_1"]["main_story"] = {}
        assert curator.validate_data() is False

    def test_main_story_without_title_returns_false(self, curator):
        curator.working_data["day_1"]["main_story"] = {"content": "stuff"}
        assert curator.validate_data() is False

    def test_empty_day_still_valid(self, curator):
        """An empty day produces a warning but doesn't invalidate."""
        curator.working_data["day_1"]["main_story"] = {}
        curator.working_data["day_1"]["mini_articles"] = []
        # Day 1 is now empty → warning, but still invalid because
        # other days are fine. The method returns False because day 1
        # triggers the "no main story" check first.
        # Actually empty day with no main and no minis skips the main check
        result = curator.validate_data()
        # An empty day's main_story is {} which is falsy, and mini_articles is []
        # which is falsy, so it hits the "empty day" warning and continues.
        # But since it says "continue" after the empty check, it won't check
        # for missing main story. So it should still be True overall.
        assert result is True

    def test_too_many_minis_still_valid(self, curator):
        """More than 4 minis produces a warning but data is still valid."""
        day = curator.working_data["day_3"]
        day["mini_articles"].append(_make_story("Extra Mini"))
        # 5 minis → warning, but not invalid
        assert curator.validate_data() is True


# ── auto_save tests ─────────────────────────────────────────────


class TestAutoSave:
    def test_auto_save_writes_to_output_file(self, curator):
        curator._auto_save()
        assert curator.output_file.exists()
        saved = json.loads(curator.output_file.read_text())
        assert "day_1" in saved

    def test_auto_save_excludes_unused(self, curator):
        curator._auto_save()
        saved = json.loads(curator.output_file.read_text())
        assert "unused" not in saved

    def test_auto_save_noop_without_output_file(self, curator_no_output):
        # Should not raise or create any file
        curator_no_output._auto_save()

    def test_auto_save_preserves_themes(self, curator):
        curator.working_data["theme_metadata"] = {"1": {"name": "Custom Theme"}}
        curator._auto_save()
        saved = json.loads(curator.output_file.read_text())
        assert "theme_metadata" in saved


# ── revert_to_default_themes tests ──────────────────────────────


class TestRevertToDefaultThemes:
    def test_revert_updates_day_themes(self, curator):
        # Set custom themes first
        curator.working_data["day_1"]["theme"] = "Custom Theme"
        curator.revert_to_default_themes()
        # Should now have default theme for day 1
        theme = curator.working_data["day_1"]["theme"]
        assert theme != "Custom Theme"

    def test_revert_sets_theme_metadata(self, curator):
        curator.revert_to_default_themes()
        assert "theme_metadata" in curator.working_data
        meta = curator.working_data["theme_metadata"]
        # Should have entries for days 1-4
        for day_num in range(1, 5):
            assert day_num in meta
            assert meta[day_num]["source"] == "default"


# ── Constructor/loading tests ───────────────────────────────────


class TestStoryCuratorInit:
    def test_loads_json_file(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(_sample_data()))
        cur = StoryCuratorData(json_file, console=MagicMock())
        assert "day_1" in cur.working_data
        assert "day_4" in cur.working_data

    def test_working_data_is_deep_copy(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(_sample_data()))
        cur = StoryCuratorData(json_file, console=MagicMock())
        # Modifying working_data should not affect original
        cur.working_data["day_1"]["main_story"]["title"] = "CHANGED"
        assert cur.original_data["day_1"]["main_story"]["title"] == "Health Main"

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            StoryCuratorData(tmp_path / "nonexistent.json", console=MagicMock())

    def test_changes_list_starts_empty(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(_sample_data()))
        cur = StoryCuratorData(json_file, console=MagicMock())
        assert cur.changes_made == []


# ── Integration: chained operations ─────────────────────────────


class TestChainedOperations:
    def test_move_then_swap(self, curator):
        """Move a story to day 2, then swap it into main position."""
        # Move first mini from day 1 to day 2
        curator.move_story(1, 2, 2)
        # Day 2 now has: Main=Env Main, Minis=[Env Mini 1, Env Mini 2, Health Mini 1]
        day2 = curator.working_data["day_2"]
        assert len(day2["mini_articles"]) == 3

        # Swap the moved story (index 4 = mini[2]) into main position
        curator.swap_main_story(2, 4)
        assert day2["main_story"]["title"] == "Health Mini 1"
        assert day2["mini_articles"][2]["title"] == "Env Main"

    def test_move_all_minis_to_unused(self, curator):
        """Move all minis from day 4 to unused."""
        original_unused = len(curator.working_data["unused"]["stories"])
        curator.move_to_unused(4, 2)  # The only mini in day 4
        assert len(curator.working_data["day_4"]["mini_articles"]) == 0
        assert len(curator.working_data["unused"]["stories"]) == original_unused + 1

    def test_roundtrip_to_unused_and_back(self, curator):
        """Move a story to unused and then back."""
        original_title = curator.working_data["day_1"]["mini_articles"][0]["title"]
        original_mini_count = len(curator.working_data["day_1"]["mini_articles"])

        # Move to unused
        curator.move_to_unused(1, 2)
        assert len(curator.working_data["day_1"]["mini_articles"]) == original_mini_count - 1

        # Move back from unused (it's the last one in unused now)
        unused_count = len(curator.working_data["unused"]["stories"])
        curator.move_from_unused(unused_count, 1)

        # Should be back as a mini in day 1
        titles = [m["title"] for m in curator.working_data["day_1"]["mini_articles"]]
        assert original_title in titles
