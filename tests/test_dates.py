"""Unit tests for the shared Europe/Helsinki date policy, per ./tests.sdd."""

from datetime import date, datetime, timezone

from aikana.shared import dates


def test_format_date_uses_the_european_form():
    assert dates.format_date(date(2026, 10, 2)) == "2.10.2026"


def test_time_zone_is_helsinki():
    assert dates.TIME_ZONE.key == "Europe/Helsinki"


def test_today_uses_the_helsinki_calendar_date(monkeypatch):
    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 20, 23, 30, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(dates, "datetime", _FrozenDateTime)

    # 23:30 UTC on 2026-10-20 is already 2026-10-21 in Helsinki (EEST, UTC+3).
    assert dates.today() == date(2026, 10, 21)
