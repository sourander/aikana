"""Adapter implementing @WeekThemeRepository using `fastlite`, per ../architecture.sdd."""

from datetime import date

from fastlite import Database

from .domain import WeekTheme


def _to_domain(row: dict) -> WeekTheme:
    return WeekTheme(
        id=row["id"],
        course_realization_id=row["course_realization_id"],
        week_start=date.fromisoformat(row["week_start"]),
        title=row["title"],
    )


class SqliteWeekThemeRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.week_themes
        # `week_start` is the Monday starting the themed week; it is the week's own identity, so no week number or
        # ISO year is stored and a Semester spanning New Year cannot give two of its weeks the same number.
        self._table.create(
            columns={
                "id": int,
                "course_realization_id": int,
                "week_start": str,
                "title": str,
            },
            pk="id",
            if_not_exists=True,
            not_null=["course_realization_id", "week_start", "title"],
            strict=True,
            # Removing a CourseRealization removes its WeekThemes through this constraint, per ./week_themes.sdd.
            foreign_keys=[("course_realization_id", "course_realizations", "id")],
        )
        # @WeekThemeService allows one theme per week and CourseRealization; this index is the backstop.
        self._table.create_index(["course_realization_id", "week_start"], unique=True, if_not_exists=True)
        self._table.create_index(["week_start"], if_not_exists=True)

    def list_for_realization(self, course_realization_id: int) -> list[WeekTheme]:
        rows = self._table(
            where="course_realization_id = ?",
            where_args=[course_realization_id],
            order_by="week_start",
        )
        return [_to_domain(row) for row in rows]

    def get(self, week_theme_id: int) -> WeekTheme | None:
        row = self._table.get(week_theme_id, default=None)
        return _to_domain(row) if row else None

    def add(self, course_realization_id: int, week_start: date, title: str) -> WeekTheme:
        row = self._table.insert(
            {
                "course_realization_id": course_realization_id,
                "week_start": week_start.isoformat(),
                "title": title,
            }
        )
        return _to_domain(row)

    def update(self, week_theme_id: int, week_start: date, title: str) -> WeekTheme:
        row = self._table.update(
            {"id": week_theme_id, "week_start": week_start.isoformat(), "title": title}
        )
        return _to_domain(row)

    def delete(self, week_theme_id: int) -> None:
        self._table.delete(week_theme_id)