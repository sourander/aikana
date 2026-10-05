"""Adapter implementing @ConferenceRepository using `fastlite`, per ../architecture.sdd."""

from datetime import date

from fastlite import Database

from .domain import Conference


def _to_domain(row: dict) -> Conference:
    return Conference(id=row["id"], date=date.fromisoformat(row["date"]), title=row["title"])


class SqliteConferenceRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.conferences
        self._table.create(
            columns={"id": int, "date": str, "title": str},
            pk="id",
            if_not_exists=True,
            not_null=["date", "title"],
            strict=True,
        )
        # A date carries at most one Conference, per ./conferences.sdd. An earlier database may already hold a
        # non-unique index of the same name, which `if_not_exists` would silently keep, so it is dropped first.
        db.execute("DROP INDEX IF EXISTS [idx_conferences_date]")
        self._table.create_index(["date"], unique=True, if_not_exists=True)

    def get(self, conference_id: int) -> Conference | None:
        row = self._table.get(conference_id, default=None)
        return _to_domain(row) if row else None

    def list_for_range(self, start: date, end: date) -> list[Conference]:
        rows = self._table(
            where="date >= ? and date <= ?",
            where_args=[start.isoformat(), end.isoformat()],
            order_by="date",
        )
        return [_to_domain(row) for row in rows]

    def add(self, conference_date: date, title: str) -> Conference:
        row = self._table.insert({"date": conference_date.isoformat(), "title": title})
        return _to_domain(row)

    def update(self, conference_id: int, conference_date: date, title: str) -> Conference:
        row = self._table.update({"id": conference_id, "date": conference_date.isoformat(), "title": title})
        return _to_domain(row)

    def delete(self, conference_id: int) -> None:
        self._table.delete(conference_id)