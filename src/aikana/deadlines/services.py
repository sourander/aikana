"""@DeadlineRepository-backed use cases, per ./deadlines.sdd."""

from datetime import date

from ..realizations.ports import CourseRealizationRepository
from .domain import Deadline
from .ports import DeadlineRepository


class UnknownRealizationError(Exception):
    pass


class UnknownDeadlineError(Exception):
    pass


class InvalidDeadlineError(Exception):
    pass


class DeadlineService:
    def __init__(self, repo: DeadlineRepository, realization_repo: CourseRealizationRepository) -> None:
        self.repo = repo
        # ../realizations/realizations.sdd's port, used only to validate a CourseRealization id, per
        # ../architecture.sdd.
        self.realization_repo = realization_repo

    def list_deadlines_for_realization(self, course_realization_id: int) -> list[Deadline]:
        return self.repo.list_for_realization(course_realization_id)

    def list_deadlines_for_range(self, start: date, end: date) -> list[Deadline]:
        return self.repo.list_for_range(start, end)

    def get_deadline(self, deadline_id: int | None) -> Deadline | None:
        return self.repo.get(deadline_id) if deadline_id is not None else None

    def add_deadline(self, course_realization_id: int | None, deadline_date: date, title: str) -> Deadline:
        realization = self._realization(course_realization_id)
        return self.repo.add(realization.id, deadline_date, self._title(title))

    def update_deadline(self, deadline_id: int | None, deadline_date: date, title: str) -> Deadline:
        """Re-dates or re-titles one Deadline in place; it stays in the realization it already belongs to."""
        existing = self.get_deadline(deadline_id)
        if existing is None:
            raise UnknownDeadlineError(f"No Deadline with id {deadline_id!r}.")
        return self.repo.update(existing.id, deadline_date, self._title(title))

    def delete_deadline(self, deadline_id: int | None) -> None:
        existing = self.get_deadline(deadline_id)
        if existing is None:
            raise UnknownDeadlineError(f"No Deadline with id {deadline_id!r}.")
        self.repo.delete(existing.id)

    def _realization(self, course_realization_id: int | None):
        realization = self.realization_repo.get(course_realization_id) if course_realization_id is not None else None
        if realization is None:
            raise UnknownRealizationError(f"No CourseRealization with id {course_realization_id!r}.")
        return realization

    @staticmethod
    def _title(title: str) -> str:
        stripped = title.strip()
        if not stripped:
            raise InvalidDeadlineError("A Deadline needs a non-empty title.")
        return stripped