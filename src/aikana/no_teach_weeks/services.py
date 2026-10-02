"""@NoTeachWeekRepository-backed use cases, per ./no_teach_weeks.sdd."""

from datetime import date

from ..semester.ports import SemesterRepository
from .domain import DEFAULT_TITLE, NoTeachWeek, default_week_numbers, teaching_days, week_monday
from .ports import NoTeachWeekRepository


class UnknownSemesterError(Exception):
    pass


class UnknownNoTeachWeekError(Exception):
    pass


class InvalidNoTeachWeekError(Exception):
    pass


class DuplicateNoTeachWeekError(Exception):
    pass


class NoTeachWeekService:
    def __init__(self, repo: NoTeachWeekRepository, semester_repo: SemesterRepository) -> None:
        self.repo = repo
        # ../semester/semester.sdd's port, used only to validate a Semester id and read its year and term,
        # per ../architecture.sdd.
        self.semester_repo = semester_repo

    def list_no_teach_weeks(self, semester_id: str) -> list[NoTeachWeek]:
        return self.repo.list_for_semester(semester_id)

    def get_no_teach_week(self, no_teach_week_id: str) -> NoTeachWeek | None:
        return self.repo.get(no_teach_week_id) if no_teach_week_id else None

    def add_no_teach_week(
        self, semester_id: str, week_number: int, title: str = DEFAULT_TITLE
    ) -> NoTeachWeek:
        semester = self._semester(semester_id)
        self._reject_duplicate(semester_id, week_number)
        return self.repo.add(
            semester_id, week_number, self._week_start(semester.year, week_number), self._title(title)
        )

    def update_no_teach_week(self, no_teach_week_id: str, week_number: int, title: str) -> NoTeachWeek:
        existing = self.get_no_teach_week(no_teach_week_id)
        if existing is None:
            raise UnknownNoTeachWeekError(f"No NoTeachWeek with id {no_teach_week_id!r}.")
        semester = self._semester(existing.semester_id)
        self._reject_duplicate(existing.semester_id, week_number, ignore_id=existing.id)
        return self.repo.update(
            existing.id, week_number, self._week_start(semester.year, week_number), self._title(title)
        )

    def delete_no_teach_week(self, no_teach_week_id: str) -> None:
        if self.get_no_teach_week(no_teach_week_id) is None:
            raise UnknownNoTeachWeekError(f"No NoTeachWeek with id {no_teach_week_id!r}.")
        self.repo.delete(no_teach_week_id)

    def create_defaults_for_semester(self, semester_id: str) -> list[NoTeachWeek]:
        """The term's default NoTeachWeeks, skipping a week that is already blocked in that Semester."""
        semester = self._semester(semester_id)
        already_blocked = {week.week_number for week in self.repo.list_for_semester(semester_id)}
        return [
            self.repo.add(semester_id, week_number, week_monday(semester.year, week_number), DEFAULT_TITLE)
            for week_number in default_week_numbers(semester.term)
            if week_number not in already_blocked
        ]

    def titles_by_teaching_day(self, semester_id: str) -> dict[date, str]:
        """Each blocked Monday-to-Friday date of a Semester mapped to its NoTeachWeek's title."""
        titles: dict[date, str] = {}
        for week in self.repo.list_for_semester(semester_id):
            for day in teaching_days(week.week_start):
                titles[day] = week.title
        return titles

    def _semester(self, semester_id: str):
        semester = self.semester_repo.get(semester_id) if semester_id else None
        if semester is None:
            raise UnknownSemesterError(f"No Semester with id {semester_id!r}.")
        return semester

    def _week_start(self, year: int, week_number: int) -> date:
        try:
            return week_monday(year, week_number)
        except ValueError as exc:
            raise InvalidNoTeachWeekError(f"Week {week_number} does not exist in {year}.") from exc

    @staticmethod
    def _title(title: str) -> str:
        stripped = title.strip()
        if not stripped:
            raise InvalidNoTeachWeekError("A NoTeachWeek needs a non-empty title.")
        return stripped

    def _reject_duplicate(self, semester_id: str, week_number: int, ignore_id: str = "") -> None:
        if any(
            week.week_number == week_number and week.id != ignore_id
            for week in self.repo.list_for_semester(semester_id)
        ):
            raise DuplicateNoTeachWeekError(
                f"Week {week_number} is already a NoTeachWeek of this Semester."
            )