"""Unit tests for the Semester package's pure domain rules, per ./tests.sdd."""

from datetime import date

from aikana.semester.domain import Semester, default_semester, semester_bounds, semester_months

FALL_2026 = Semester(id=1, year=2026, term="fall")
SPRING_2027 = Semester(id=2, year=2027, term="spring")


def test_fall_semester_spans_august_to_december():
    assert semester_bounds(FALL_2026) == (date(2026, 8, 1), date(2026, 12, 31))


def test_spring_semester_spans_january_to_june():
    assert semester_bounds(SPRING_2027) == (date(2027, 1, 1), date(2027, 6, 30))


def test_semester_months_lists_each_spanned_month_in_order():
    assert semester_months(FALL_2026) == [(2026, 8), (2026, 9), (2026, 10), (2026, 11), (2026, 12)]
    assert semester_months(SPRING_2027) == [(2027, 1), (2027, 2), (2027, 3), (2027, 4), (2027, 5), (2027, 6)]


def test_default_semester_prefers_the_most_recently_started():
    assert default_semester([SPRING_2027, FALL_2026], date(2026, 10, 1)) == FALL_2026


def test_default_semester_keeps_the_previous_semester_after_it_ends():
    # Per semester.sdd: a visit on 2027-07-15 still defaults to spring 2027, the previous one.
    assert default_semester([FALL_2026, SPRING_2027], date(2027, 7, 15)) == SPRING_2027


def test_default_semester_falls_back_to_the_earliest_when_none_has_started():
    assert default_semester([FALL_2026], date(2020, 1, 1)) == FALL_2026


def test_default_semester_returns_none_without_semesters():
    assert default_semester([], date(2026, 10, 1)) is None
