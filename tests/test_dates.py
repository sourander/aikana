"""Unit tests for the shared Europe/Helsinki date policy, per ./tests.sdd."""

from datetime import date, datetime, timezone

from aikana.shared import dates


def test_format_date_uses_the_european_form():
    assert dates.format_date(date(2026, 10, 2)) == "2.10.2026"


def test_today_uses_the_helsinki_calendar_date(monkeypatch):
    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 20, 23, 30, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(dates, "datetime", _FrozenDateTime)

    # 23:30 UTC on 2026-10-20 is already 2026-10-21 in Helsinki (EEST, UTC+3).
    assert dates.today() == date(2026, 10, 21)


def test_month_grid_starts_every_week_on_monday():
    weeks = dates.month_grid(date(2026, 10, 21))

    # 2026-10-01 is a Thursday, so October opens with three empty Monday-to-Wednesday cells.
    assert weeks[0] == [None, None, None, date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3), date(2026, 10, 4)]
    assert weeks[-1][-2] == date(2026, 10, 31)
    assert weeks[-1][-1] is None
    assert all(len(week) == 7 for week in weeks)
    assert all(day.weekday() == index for week in weeks for index, day in enumerate(week) if day)


def test_month_grid_covers_a_month_that_ends_on_a_sunday():
    weeks = dates.month_grid(date(2026, 5, 15))

    # 2026-05-01 is a Friday and 2026-05-31 is a Sunday, so the last week ends without trailing padding.
    assert weeks[0][4] == date(2026, 5, 1)
    assert weeks[-1][-1] == date(2026, 5, 31)
