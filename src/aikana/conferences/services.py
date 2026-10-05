"""@ConferenceRepository-backed use cases, per ./conferences.sdd."""

from datetime import date

from .domain import Conference
from .ports import ConferenceRepository


class InvalidConferenceError(Exception):
    pass


class DuplicateConferenceError(Exception):
    pass


class UnknownConferenceError(Exception):
    pass


class ConferenceService:
    def __init__(self, repo: ConferenceRepository) -> None:
        self.repo = repo

    def get_conference(self, conference_id: int | None) -> Conference | None:
        return self.repo.get(conference_id) if conference_id is not None else None

    def list_conferences_for_range(self, start: date, end: date) -> list[Conference]:
        return self.repo.list_for_range(start, end)

    def add_conference(self, conference_date: date, title: str) -> Conference:
        self._reject_duplicate(conference_date)
        return self.repo.add(conference_date, self._validated_title(title))

    def update_conference(self, conference_id: int | None, conference_date: date, title: str) -> Conference:
        existing = self.get_conference(conference_id)
        if existing is None:
            raise UnknownConferenceError(f"No Conference with id {conference_id!r}.")
        self._reject_duplicate(conference_date, ignore_id=existing.id)
        return self.repo.update(existing.id, conference_date, self._validated_title(title))

    def delete_conference(self, conference_id: int | None) -> None:
        existing = self.get_conference(conference_id)
        if existing is None:
            raise UnknownConferenceError(f"No Conference with id {conference_id!r}.")
        self.repo.delete(existing.id)

    @staticmethod
    def _validated_title(title: str) -> str:
        title = title.strip()
        if not title:
            raise InvalidConferenceError("A Conference needs a non-empty title.")
        return title

    def _reject_duplicate(self, conference_date: date, ignore_id: int | None = None) -> None:
        """A Conference spans one day and a date carries at most one, per ./conferences.sdd."""
        if any(
            conference.id != ignore_id and conference.date == conference_date
            for conference in self.repo.list_for_range(conference_date, conference_date)
        ):
            raise DuplicateConferenceError(f"{conference_date.isoformat()} already has a Conference.")