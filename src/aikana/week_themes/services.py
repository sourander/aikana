"""@WeekThemeRepository-backed use cases, per ./week_themes.sdd."""

from datetime import date

from ..realizations.ports import CourseRealizationRepository
from .domain import WeekTheme, is_week_start
from .ports import WeekThemeRepository


class UnknownRealizationError(Exception):
    pass


class UnknownWeekThemeError(Exception):
    pass


class InvalidWeekThemeError(Exception):
    pass


class DuplicateWeekThemeError(Exception):
    pass


class WeekThemeService:
    def __init__(self, repo: WeekThemeRepository, realization_repo: CourseRealizationRepository) -> None:
        self.repo = repo
        # ../realizations/realizations.sdd's port, used only to validate a CourseRealization id, per
        # ../architecture.sdd.
        self.realization_repo = realization_repo

    def list_week_themes(self, course_realization_id: int) -> list[WeekTheme]:
        return self.repo.list_for_realization(course_realization_id)

    def get_week_theme(self, week_theme_id: int | None) -> WeekTheme | None:
        return self.repo.get(week_theme_id) if week_theme_id is not None else None

    def add_week_theme(self, course_realization_id: int | None, week_start: date, title: str) -> WeekTheme:
        realization = self._realization(course_realization_id)
        start = self._week_start(week_start)
        self._reject_duplicate(realization.id, start)
        return self.repo.add(realization.id, start, self._title(title))

    def update_week_theme(self, week_theme_id: int | None, week_start: date, title: str) -> WeekTheme:
        """Re-themes a week in place; the WeekTheme stays in the realization it already belongs to."""
        existing = self.get_week_theme(week_theme_id)
        if existing is None:
            raise UnknownWeekThemeError(f"No WeekTheme with id {week_theme_id!r}.")
        start = self._week_start(week_start)
        self._reject_duplicate(existing.course_realization_id, start, ignore_id=existing.id)
        return self.repo.update(existing.id, start, self._title(title))

    def delete_week_theme(self, week_theme_id: int | None) -> None:
        existing = self.get_week_theme(week_theme_id)
        if existing is None:
            raise UnknownWeekThemeError(f"No WeekTheme with id {week_theme_id!r}.")
        self.repo.delete(existing.id)

    def _realization(self, course_realization_id: int | None):
        realization = self.realization_repo.get(course_realization_id) if course_realization_id is not None else None
        if realization is None:
            raise UnknownRealizationError(f"No CourseRealization with id {course_realization_id!r}.")
        return realization

    @staticmethod
    def _week_start(week_start: date) -> date:
        if not is_week_start(week_start):
            raise InvalidWeekThemeError(
                f"A WeekTheme's week starts on a Monday, but {week_start.isoformat()} is not one."
            )
        return week_start

    @staticmethod
    def _title(title: str) -> str:
        stripped = title.strip()
        if not stripped:
            raise InvalidWeekThemeError("A WeekTheme needs a non-empty title.")
        return stripped

    def _reject_duplicate(
        self, course_realization_id: int, week_start: date, ignore_id: int | None = None
    ) -> None:
        if any(
            theme.week_start == week_start and theme.id != ignore_id
            for theme in self.repo.list_for_realization(course_realization_id)
        ):
            raise DuplicateWeekThemeError(
                f"The week starting {week_start.isoformat()} already has a WeekTheme for this CourseRealization."
            )