"""Unit tests for the NoTeachWeek package's pure domain rules, per ./tests.sdd."""

from datetime import date

import pytest

from aikana.no_teach_weeks.domain import (
    DEFAULT_TITLE,
    default_week_numbers,
    teaching_days,
    week_monday,
    week_sunday,
)


def test_default_week_numbers_are_the_fall_and_spring_sets():
    assert default_week_numbers("fall") == (42, 51)
    assert default_week_numbers("spring") == (1, 10, 22)


def test_default_week_numbers_are_empty_for_an_unknown_term():
    assert default_week_numbers("summer") == ()


def test_the_default_title_is_a_generic_no_teaching_week():
    assert DEFAULT_TITLE == "No teaching week"


def test_week_monday_returns_the_monday_of_that_iso_week():
    assert week_monday(2026, 42) == date(2026, 10, 12)
    # Spring 2026's week 1 starts in December 2025.
    assert week_monday(2026, 1) == date(2025, 12, 29)


def test_week_monday_rejects_a_week_the_year_does_not_have():
    # 2027 is a 52-week ISO year.
    with pytest.raises(ValueError, match="53"):
        week_monday(2027, 53)


def test_week_sunday_is_six_days_after_the_monday():
    assert week_sunday(date(2026, 10, 12)) == date(2026, 10, 18)


def test_teaching_days_are_the_weekdays_only():
    days = teaching_days(date(2026, 10, 12))
    assert days == (
        date(2026, 10, 12),
        date(2026, 10, 13),
        date(2026, 10, 14),
        date(2026, 10, 15),
        date(2026, 10, 16),
    )
    assert all(day.weekday() < 5 for day in days)