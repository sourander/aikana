"""Tests of the Conference package's validation, of the day dialog's Conference tab with its admin guard, and of
the wall planner's and the weekly view's purple Conference titles, per ./tests.sdd.
"""

from datetime import date, time

import pytest

from aikana.conferences.services import (
    DuplicateConferenceError,
    InvalidConferenceError,
    UnknownConferenceError,
)
from conftest import has_checked_calendar_day

# The dialog is only reachable through an HTMX request, per ./src/aikana/day_dialog/day_dialog.sdd.
HTMX = {"HX-Request": "true"}

# 2026-10-20 is a Tuesday of the fall 2026 Semester, outside its default NoTeachWeeks in weeks 42 and 51.
FREE_DAY = "2026-10-20"
# The day after it, for a second entry or a re-dating.
OTHER_DAY = "2026-10-21"
# A Monday of the same Semester, so its row can never be tinted by the weekend rule.
MONDAY = "2026-09-07"
# The date the realization's Lesson falls on, one of the free days above.
LESSON_DAY = date(2026, 10, 20)

CONFERENCE_STATE = (
    "This conference or event might affect teaching schedule or availability of the teacher"
)


@pytest.fixture
def semester(services):
    """A fall 2026 Semester, seeded on the same temporary database the app was built on."""
    return services.semesters.create_semester(2026, "fall")


def _range(day: str):
    parsed = date.fromisoformat(day)
    return parsed, parsed


def _open_dialog(client, semester, kind="conference", day=FREE_DAY, follow_redirects=True):
    return client.get(
        "/day/dialog",
        params={"semester_id": semester.id, "day": day, "kind": kind},
        headers=HTMX,
        follow_redirects=follow_redirects,
    )


def _assert_bare_grid(response):
    """A successful write responds with the bare grid, never a second dialog container."""
    assert response.text.count('id="semester-grid"') == 1
    assert 'id="day-dialog"' not in response.text


def _day_row(html: str, day: str) -> str:
    """One admin day row, from its own dialog trigger up to the next row's, so a test asserts on that day's markers
    and on no other. Every day row carries the date in its trigger, unlike a visitor's."""
    row_cls = 'class="flex items-center gap-1 border-b border-gray-100'
    start = html.index(f"day={day}")
    # The row's own class follows its trigger, so the next one marks the following row.
    end = html.index(row_cls, html.index(row_cls, start) + len(row_cls))
    return html[start:end]


def _add_realization_with_lesson(services, semester, lesson_day: date = LESSON_DAY):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    services.lessons.add_lesson(realization.id, lesson_day, time(8, 0), time(10, 0), "Intro", "")
    return realization


# The service layer


def test_a_conference_needs_a_non_empty_title(services):
    with pytest.raises(InvalidConferenceError):
        services.conferences.add_conference(date(2026, 11, 12), "   ")


def test_a_date_carries_at_most_one_conference(services):
    services.conferences.add_conference(date(2026, 11, 12), "Nordic Conference")

    with pytest.raises(DuplicateConferenceError):
        services.conferences.add_conference(date(2026, 11, 12), "Second Conference")

    stored = services.conferences.list_conferences_for_range(*_range("2026-11-12"))
    assert [conference.title for conference in stored] == ["Nordic Conference"]


def test_a_conference_spans_exactly_one_day(services):
    services.conferences.add_conference(date(2026, 11, 12), "Nordic Conference")
    services.conferences.add_conference(date(2026, 11, 13), "Nordic Conference")

    stored = services.conferences.list_conferences_for_range(date(2026, 11, 1), date(2026, 11, 30))
    assert [conference.date for conference in stored] == [date(2026, 11, 12), date(2026, 11, 13)]


def test_a_conference_leaves_a_lessons_day_alone(services, semester):
    realization = _add_realization_with_lesson(services, semester)
    services.conferences.add_conference(date(2026, 10, 20), "Nordic Conference")

    assert [lesson.date for lesson in services.lessons.list_lessons_for_realization(realization.id)] == [
        date(2026, 10, 20)
    ]


def test_update_conference_keeps_its_own_date_and_rejects_another_conferences(services):
    conference = services.conferences.add_conference(date(2026, 11, 12), "Nordic Conference")
    other = services.conferences.add_conference(date(2026, 11, 20), "Workshop")

    with pytest.raises(DuplicateConferenceError):
        services.conferences.update_conference(conference.id, date(2026, 11, 20), "Nordic Conference")

    assert services.conferences.get_conference(other.id).title == "Workshop"


def test_update_conference_changes_the_stored_values(services):
    conference = services.conferences.add_conference(date(2026, 11, 12), "Nordic Conference")

    updated = services.conferences.update_conference(conference.id, date(2026, 11, 13), "Retitled")

    assert services.conferences.get_conference(conference.id) == updated
    assert (updated.date, updated.title) == (date(2026, 11, 13), "Retitled")


def test_update_conference_rejects_an_unknown_id(services):
    with pytest.raises(UnknownConferenceError):
        services.conferences.update_conference("no-such-conference", date(2026, 11, 12), "Nordic Conference")


def test_update_conference_rejects_an_empty_title(services):
    conference = services.conferences.add_conference(date(2026, 11, 12), "Nordic Conference")

    with pytest.raises(InvalidConferenceError):
        services.conferences.update_conference(conference.id, date(2026, 11, 12), "  ")

    assert services.conferences.get_conference(conference.id).title == "Nordic Conference"


def test_delete_conference_removes_it(services):
    conference = services.conferences.add_conference(date(2026, 11, 12), "Nordic Conference")

    services.conferences.delete_conference(conference.id)

    assert services.conferences.list_conferences_for_range(date(2026, 11, 1), date(2026, 11, 30)) == []


def test_delete_conference_rejects_an_unknown_id(services):
    with pytest.raises(UnknownConferenceError):
        services.conferences.delete_conference("no-such-conference")


# The day dialog's Conference tab


def test_the_dialog_offers_a_conference_tab(admin_client, semester):
    response = _open_dialog(admin_client, semester)

    assert ">Conference</button>" in response.text
    assert 'action="/day/dialog/conference"' in response.text


def test_admin_adds_a_conference(admin_client, semester, services):
    response = admin_client.post(
        "/day/dialog/conference",
        data={"semester_id": semester.id, "day": FREE_DAY, "title": "Nordic Conference"},
        headers=HTMX,
    )

    assert response.status_code == 200
    _assert_bare_grid(response)
    assert [conference.title for conference in services.conferences.list_conferences_for_range(*_range(FREE_DAY))] == [
        "Nordic Conference"
    ]


def test_a_rejected_conference_is_not_stored_and_the_dialog_reports_it(admin_client, semester, services):
    response = admin_client.post(
        "/day/dialog/conference",
        data={"semester_id": semester.id, "day": FREE_DAY, "title": "   "},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#day-dialog"
    assert "non-empty title" in response.text
    assert services.conferences.list_conferences_for_range(*_range(FREE_DAY)) == []


def test_a_second_conference_on_the_same_date_is_rejected(admin_client, semester, services):
    data = {"semester_id": semester.id, "day": FREE_DAY, "title": "Nordic Conference"}
    admin_client.post("/day/dialog/conference", data=data, headers=HTMX)

    response = admin_client.post("/day/dialog/conference", data=data, headers=HTMX)

    assert response.status_code == 422
    assert "already has a Conference" in response.text
    assert len(services.conferences.list_conferences_for_range(*_range(FREE_DAY))) == 1


def test_a_malformed_day_is_reported_before_the_conference_is_stored(admin_client, semester, services):
    response = admin_client.post(
        "/day/dialog/conference",
        data={"semester_id": semester.id, "day": "not-a-day", "title": "Nordic Conference"},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "not a valid date" in response.text
    assert services.conferences.list_conferences_for_range(*_range(FREE_DAY)) == []


def test_the_conference_tab_edits_the_conference_already_on_that_day(admin_client, semester, services):
    conference = services.conferences.add_conference(date(2026, 10, 20), "Nordic Conference")

    response = _open_dialog(admin_client, semester)

    assert f'action="/day/dialog/conferences/{conference.id}"' in response.text
    assert 'value="Nordic Conference"' in response.text
    assert has_checked_calendar_day(response.text, FREE_DAY)
    assert 'action="/day/dialog/conference"' not in response.text
    # One day calendar, one Save and one Delete, so the edit form replaces the add form instead of doubling it.
    assert response.text.count(">Mon</span>") == 1
    assert response.text.count(">Save</button>") == 1
    assert response.text.count(">Delete</button>") == 1


def test_the_admin_edits_a_conference_through_the_dialog(admin_client, semester, services):
    conference = services.conferences.add_conference(date(2026, 10, 20), "Nordic Conference")

    response = admin_client.post(
        f"/day/dialog/conferences/{conference.id}",
        data={"semester_id": semester.id, "day": OTHER_DAY, "title": "Retitled"},
        headers=HTMX,
    )

    assert response.status_code == 200
    _assert_bare_grid(response)
    assert "Retitled" in response.text
    assert "Nordic Conference" not in response.text
    stored = services.conferences.get_conference(conference.id)
    assert (stored.date, stored.title) == (date(2026, 10, 21), "Retitled")
    assert services.conferences.list_conferences_for_range(*_range(FREE_DAY)) == []


def test_a_rejected_conference_edit_keeps_the_stored_conference_and_what_the_admin_typed(
    admin_client, semester, services
):
    conference = services.conferences.add_conference(date(2026, 10, 20), "Nordic Conference")

    response = admin_client.post(
        f"/day/dialog/conferences/{conference.id}",
        data={"semester_id": semester.id, "day": FREE_DAY, "title": "  "},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#day-dialog"
    assert 'value="  "' in response.text
    stored = services.conferences.get_conference(conference.id)
    assert (stored.date, stored.title) == (date(2026, 10, 20), "Nordic Conference")


def test_a_conference_edit_onto_a_day_that_already_has_one_is_rejected(admin_client, semester, services):
    conference = services.conferences.add_conference(date(2026, 10, 20), "Nordic Conference")
    services.conferences.add_conference(date(2026, 10, 21), "Workshop")

    response = admin_client.post(
        f"/day/dialog/conferences/{conference.id}",
        data={"semester_id": semester.id, "day": OTHER_DAY, "title": "Nordic Conference"},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "already has a Conference" in response.text
    assert services.conferences.get_conference(conference.id).date == date(2026, 10, 20)


def test_the_admin_deletes_a_conference_through_the_dialog(admin_client, semester, services):
    conference = services.conferences.add_conference(date(2026, 10, 20), "Nordic Conference")

    dialog = _open_dialog(admin_client, semester)
    assert f'hx-post="/day/dialog/conferences/{conference.id}/delete"' in dialog.text
    assert 'hx-confirm="Delete the Conference Nordic Conference on 20.10.2026?"' in dialog.text

    response = admin_client.post(
        f"/day/dialog/conferences/{conference.id}/delete",
        data={"semester_id": semester.id, "day": FREE_DAY},
        headers=HTMX,
    )

    assert response.status_code == 200
    _assert_bare_grid(response)
    assert "Nordic Conference" not in response.text
    assert services.conferences.list_conferences_for_range(*_range(FREE_DAY)) == []


def test_deleting_an_unknown_conference_is_reported_in_the_dialog(admin_client, semester):
    response = admin_client.post(
        "/day/dialog/conferences/9999/delete",
        data={"semester_id": semester.id, "day": FREE_DAY},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "No Conference with id" in response.text


def test_a_visitor_can_neither_add_nor_delete_a_conference(client, semester, services):
    conference = services.conferences.add_conference(date(2026, 10, 20), "Nordic Conference")

    assert _open_dialog(client, semester, follow_redirects=False).status_code == 303
    assert _open_dialog(client, semester, follow_redirects=False).headers["location"] == "/login"
    add = client.post(
        "/day/dialog/conference",
        data={"semester_id": semester.id, "day": FREE_DAY, "title": "Smuggled"},
        headers=HTMX,
        follow_redirects=False,
    )
    delete = client.post(
        f"/day/dialog/conferences/{conference.id}/delete",
        data={"semester_id": semester.id, "day": FREE_DAY},
        headers=HTMX,
        follow_redirects=False,
    )

    assert add.status_code == 303
    assert add.headers["location"] == "/login"
    assert delete.status_code == 303
    assert delete.headers["location"] == "/login"
    assert [c.title for c in services.conferences.list_conferences_for_range(*_range(FREE_DAY))] == [
        "Nordic Conference"
    ]


def test_a_conference_is_added_from_a_week_row_through_the_weekly_table_swap(admin_client, semester, services):
    """The weekly view's dialog re-renders the weekly table, not the grid, as the other tabs do."""
    realization = _add_realization_with_lesson(services, semester)

    response = admin_client.post(
        "/day/dialog/conference",
        data={
            "semester_id": semester.id,
            "day": FREE_DAY,
            "title": "Nordic Conference",
            "realization_id": realization.id,
        },
        headers=HTMX,
    )

    assert response.status_code == 200
    assert 'id="realization-week-table"' in response.text
    assert 'id="semester-grid"' not in response.text
    assert len(services.conferences.list_conferences_for_range(*_range(FREE_DAY))) == 1


# The wall planner's purple title


def test_a_conference_shows_in_purple_with_a_tooltip_carrying_its_title_and_state(admin_client, services):
    semester = services.semesters.create_semester(2026, "fall")
    services.conferences.add_conference(LESSON_DAY, "Nordic Conference")

    row = _day_row(admin_client.get(f"/?semester_id={semester.id}").text, FREE_DAY)
    assert "text-purple-600" in row
    assert "Nordic Conference" in row
    # The title is the tooltip's anchor and the tooltip body carries the title over the state a Conference states.
    assert 'data-tip=""' in row
    assert 'data-tip-body=""' in row
    assert CONFERENCE_STATE in row


def test_a_conference_day_is_not_tinted(admin_client, services):
    semester = services.semesters.create_semester(2026, "fall")
    services.conferences.add_conference(date(2026, 9, 7), "Nordic Conference")

    row = _day_row(admin_client.get(f"/?semester_id={semester.id}").text, MONDAY)

    # A Monday's row is never tinted by the weekend rule, so a Conference adds no tint of its own.
    assert "bg-red-50" not in row


def test_a_conference_coexists_with_a_holiday_and_that_holidays_tint(admin_client, services):
    semester = services.semesters.create_semester(2026, "fall")
    services.holidays.add_holiday(date(2026, 9, 7), "Autumn break")
    services.conferences.add_conference(date(2026, 9, 7), "Nordic Conference")

    row = _day_row(admin_client.get(f"/?semester_id={semester.id}").text, MONDAY)

    assert "text-red-600" in row
    assert "text-purple-600" in row
    assert "bg-red-50" in row


def test_a_conference_day_keeps_its_lesson_squares(admin_client, services):
    semester = services.semesters.create_semester(2026, "fall")
    _add_realization_with_lesson(services, semester)
    services.conferences.add_conference(LESSON_DAY, "Nordic Conference")

    row = _day_row(admin_client.get(f"/?semester_id={semester.id}").text, FREE_DAY)

    # A Conference does not block teaching, so the day's realization square is still drawn on the row.
    assert 'href="/realizations?realization_id=' in row
    assert "text-purple-600" in row


def test_an_admin_row_holding_a_conference_opens_the_dialog_on_the_conference_tab(admin_client, services):
    semester = services.semesters.create_semester(2026, "fall")
    services.conferences.add_conference(date(2026, 10, 20), "Nordic Conference")

    html = admin_client.get(f"/?semester_id={semester.id}").text

    assert "day=2026-10-20&amp;kind=conference" in html


# The weekly view's purple sub-row


def test_a_conference_is_a_purple_sub_row_in_the_weekly_view(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    realization = _add_realization_with_lesson(services, semester)
    services.conferences.add_conference(LESSON_DAY, "Nordic Conference")

    html = client.get(f"/realizations?realization_id={realization.id}").text

    assert "text-purple-600 italic" in html
    assert "text-purple-400 italic" in html
    assert "Nordic Conference" in html
    # The sub-row shows the Conference's own day under its title, like a Lesson's, and carries no time range.
    assert "Tue 20.10." in html