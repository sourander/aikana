"""Tests of the Deadline package's validation, of the weekly view's Deadlines section with its dialogs and admin
guard, and of the wall planner's deadline circles, per ./tests.sdd.
"""

from datetime import date, time

import pytest

from aikana.deadlines.services import (
    InvalidDeadlineError,
    UnknownDeadlineError,
    UnknownRealizationError,
)
from conftest import week_card_html

DEADLINE_DATE = date(2026, 9, 21)
WEEK_START = date(2026, 9, 21)
LESSON_DATE = date(2026, 9, 1)
PALETTE_BLUE = "#2563eb"


@pytest.fixture
def semester_id(admin_client):
    response = admin_client.post("/semesters", data={"year": "2026", "term": "fall"}, follow_redirects=False)
    return int(response.headers["location"].removeprefix("/?semester_id="))


@pytest.fixture
def realization_id(admin_client, course_service, services, semester_id):
    admin_client.post(
        "/courses",
        data={"name": "Machine Learning", "description": "An introduction.", "ects_credits": "5"},
        follow_redirects=True,
    )
    course_id = course_service.list_courses()[0].id
    admin_client.post(
        f"/courses/{course_id}/realizations",
        data={"group": "TTV24SP", "semester_id": str(semester_id)},
        follow_redirects=True,
    )
    return services.realizations.list_realizations_for_semester(semester_id)[0].id


def _weekly_view(client, realization_id, semester_id):
    return client.get(f"/realizations?realization_id={realization_id}&semester_id={semester_id}")


def _add_deadline(client, realization_id, day=DEADLINE_DATE, title="Assignment 1"):
    return client.post(
        "/realizations/deadlines",
        data={"realization_id": str(realization_id), "day": day.isoformat(), "title": title},
        follow_redirects=True,
    )


def _update_deadline(client, deadline_id, day=DEADLINE_DATE, title="Assignment 1 resubmitted"):
    return client.post(
        f"/realizations/deadlines/{deadline_id}",
        data={"day": day.isoformat(), "title": title},
        follow_redirects=True,
    )


def _delete_deadline(client, deadline_id):
    return client.post(f"/realizations/deadlines/{deadline_id}/delete", follow_redirects=True)


def _circle_anchor(html: str, realization_id: int) -> str:
    """The rendered `<a>` of the realization's one deadline circle, which links to that realization's weekly view."""
    start = html.index(f'<a href="/realizations?realization_id={realization_id}"')
    return html[start : html.index(">", start)]


# The service layer


def test_a_deadline_needs_an_existing_realization(services):
    with pytest.raises(UnknownRealizationError):
        services.deadlines.add_deadline(999, DEADLINE_DATE, "Assignment 1")


def test_a_deadline_needs_a_non_empty_title(services, realization_id):
    with pytest.raises(InvalidDeadlineError):
        services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "   ")


def test_a_realization_has_many_deadlines_including_several_on_one_date(services, realization_id):
    services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")
    services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 2")

    deadlines = services.deadlines.list_deadlines_for_realization(realization_id)

    assert [deadline.title for deadline in deadlines] == ["Assignment 1", "Assignment 2"]


def test_a_realizations_deadlines_are_listed_by_date(services, realization_id):
    services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")
    services.deadlines.add_deadline(realization_id, LESSON_DATE, "Reading")

    deadlines = services.deadlines.list_deadlines_for_realization(realization_id)

    assert [deadline.date for deadline in deadlines] == [LESSON_DATE, DEADLINE_DATE]


def test_editing_a_deadline_keeps_it_in_its_realization(services, realization_id):
    deadline = services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")

    edited = services.deadlines.update_deadline(deadline.id, LESSON_DATE, "Assignment 1")

    assert edited.title == "Assignment 1"
    assert edited.date == LESSON_DATE
    assert edited.course_realization_id == realization_id


def test_deleting_a_deadline_leaves_the_realizations_other_deadlines_alone(services, realization_id):
    removed = services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")
    kept = services.deadlines.add_deadline(realization_id, LESSON_DATE, "Reading")

    services.deadlines.delete_deadline(removed.id)

    assert services.deadlines.list_deadlines_for_realization(realization_id) == [kept]


def test_deleting_a_realization_takes_its_deadlines_with_it(services, realization_id):
    services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")

    services.realizations.delete_realization(realization_id)

    assert services.deadlines.list_deadlines_for_realization(realization_id) == []


def test_an_unknown_deadline_is_rejected(services):
    with pytest.raises(UnknownDeadlineError):
        services.deadlines.update_deadline(123, DEADLINE_DATE, "Assignment 1")
    with pytest.raises(UnknownDeadlineError):
        services.deadlines.delete_deadline(123)


def test_the_deadlines_of_a_date_range_are_listed_across_realizations(services, realization_id):
    services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")
    services.deadlines.add_deadline(realization_id, LESSON_DATE, "Reading")

    deadlines = services.deadlines.list_deadlines_for_range(LESSON_DATE, DEADLINE_DATE)

    assert [deadline.title for deadline in deadlines] == ["Reading", "Assignment 1"]


# The weekly view's Deadlines section


def test_the_deadlines_section_is_the_last_section_of_the_week_card(
    admin_client, realization_id, semester_id
):
    html = _weekly_view(admin_client, realization_id, semester_id).text

    card = week_card_html(html, WEEK_START.isocalendar()[1])
    assert ">Notes<" not in html
    assert card.index('class="week-head') < card.index('class="week-lessons') < card.index('class="week-deadlines')


def test_a_deadline_shows_in_the_week_card_it_falls_in(
    admin_client, realization_id, semester_id, services
):
    services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")

    card = week_card_html(_weekly_view(admin_client, realization_id, semester_id).text, WEEK_START.isocalendar()[1])

    deadlines = card[card.index('class="week-deadlines') :]
    assert "Assignment 1" in deadlines
    assert "21.9.2026" in deadlines


def test_a_week_without_a_deadline_shows_the_section_empty(admin_client, realization_id, semester_id):
    card = week_card_html(_weekly_view(admin_client, realization_id, semester_id).text, WEEK_START.isocalendar()[1])

    deadlines = card[card.index('class="week-deadlines') :]
    assert "\u2014" not in deadlines
    assert "deadline-title" not in deadlines


def test_the_admin_deadline_cell_has_an_add_dialog(admin_client, realization_id, semester_id):
    html = _weekly_view(admin_client, realization_id, semester_id).text

    assert f'id="deadline-dialog-{WEEK_START.isoformat()}"' in html
    assert 'action="/realizations/deadlines"' in html
    assert f'<input name="realization_id" type="hidden" value="{realization_id}"' in html
    # The add dialog's date field is the Monday-first month calendar with that week's Monday checked.
    assert f'type="radio" name="day" value="{WEEK_START.isoformat()}" checked' in html


def test_the_deadline_cell_opens_the_add_dialog(admin_client, realization_id, semester_id):
    html = _weekly_view(admin_client, realization_id, semester_id).text

    assert (
        "var d = document.getElementById("
        f"'deadline-dialog-{WEEK_START.isoformat()}'); if (d.open) d.close(); d.showModal();" in html
    )


def test_a_deadline_has_an_edit_dialog_and_a_delete_confirmation(
    admin_client, realization_id, semester_id, services
):
    deadline = services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")

    html = _weekly_view(admin_client, realization_id, semester_id).text

    assert f'id="deadline-edit-dialog-{deadline.id}"' in html
    assert 'value="Assignment 1"' in html
    assert f'type="radio" name="day" value="{DEADLINE_DATE.isoformat()}" checked' in html
    assert f'action="/realizations/deadlines/{deadline.id}"' in html
    assert f'action="/realizations/deadlines/{deadline.id}/delete"' in html
    assert "Delete the Deadline Assignment 1 on 21.9.2026?" in html


def test_clicking_a_deadline_opens_its_edit_dialog_without_opening_the_add_dialog(
    admin_client, realization_id, semester_id, services
):
    deadline = services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")

    html = _weekly_view(admin_client, realization_id, semester_id).text

    # The Deadline's own click stops propagation first, so the section's add dialog does not open behind the edit one.
    assert (
        "event.stopPropagation(); var d = document.getElementById("
        f"'deadline-edit-dialog-{deadline.id}')" in html
    )
    # The edit dialog's Delete closes the edit dialog before opening the confirmation, like a Lesson's does.
    assert (
        f"document.getElementById('deadline-edit-dialog-{deadline.id}').close();"
        f" var d = document.getElementById('deadline-delete-dialog-{deadline.id}')" in html
    )


def test_the_admin_adds_a_deadline_from_the_weekly_view(
    admin_client, realization_id, semester_id, services
):
    response = _add_deadline(admin_client, realization_id)

    assert response.status_code == 200
    assert "Assignment 1" in response.text
    assert [d.title for d in services.deadlines.list_deadlines_for_realization(realization_id)] == [
        "Assignment 1"
    ]


def test_the_admin_edits_a_deadline_from_the_weekly_view(
    admin_client, realization_id, semester_id, services
):
    deadline = services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")

    response = _update_deadline(admin_client, deadline.id)

    assert "Assignment 1 resubmitted" in response.text
    assert services.deadlines.get_deadline(deadline.id).title == "Assignment 1 resubmitted"


def test_the_admin_deletes_a_deadline_from_the_weekly_view(
    admin_client, realization_id, semester_id, services
):
    deadline = services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")
    kept = services.deadlines.add_deadline(realization_id, LESSON_DATE, "Reading")

    response = _delete_deadline(admin_client, deadline.id)

    assert "Assignment 1" not in response.text
    assert services.deadlines.list_deadlines_for_realization(realization_id) == [kept]


def test_a_rejected_deadline_write_returns_a_validation_message(
    admin_client, realization_id, services
):
    response = _add_deadline(admin_client, realization_id, title="  ")

    assert "A Deadline needs a non-empty title." in response.text
    assert services.deadlines.list_deadlines_for_realization(realization_id) == []


def test_a_malformed_deadline_date_is_reported(admin_client, realization_id, services):
    response = admin_client.post(
        "/realizations/deadlines",
        data={"realization_id": str(realization_id), "day": "21.9.2026", "title": "Assignment 1"},
        follow_redirects=True,
    )

    assert "Enter a valid date." in response.text
    assert services.deadlines.list_deadlines_for_realization(realization_id) == []


def test_writing_an_unknown_deadline_is_rejected(admin_client, realization_id, semester_id, services):
    update = _update_deadline(admin_client, "no-such-deadline")
    delete = _delete_deadline(admin_client, "no-such-deadline")

    assert "No Deadline with id" in update.text
    assert "No Deadline with id" in delete.text


def test_a_visitor_sees_the_deadline_without_any_affordance(
    admin_client, client, realization_id, semester_id, services
):
    services.deadlines.add_deadline(realization_id, DEADLINE_DATE, "Assignment 1")
    admin_client.post("/logout", follow_redirects=True)

    html = _weekly_view(client, realization_id, semester_id).text

    assert "Assignment 1" in html
    assert "<dialog" not in html
    assert "/realizations/deadlines" not in html


def test_a_visitor_cannot_write_a_deadline(admin_client, client, realization_id, services):
    admin_client.post("/logout", follow_redirects=True)

    create = client.post(
        "/realizations/deadlines",
        data={"realization_id": str(realization_id), "day": DEADLINE_DATE.isoformat(), "title": "Nope"},
        follow_redirects=False,
    )
    delete = client.post("/realizations/deadlines/1/delete", follow_redirects=False)

    assert create.status_code == 303
    assert create.headers["location"] == "/login"
    assert delete.status_code == 303
    assert delete.headers["location"] == "/login"
    assert services.deadlines.list_deadlines_for_realization(realization_id) == []


# The wall planner's deadline circles


def test_a_deadline_is_a_donut_in_its_realizations_color_with_a_tooltip(
    admin_client, realization_id, semester_id, services
):
    services.deadlines.add_deadline(realization_id, LESSON_DATE, "Assignment 1")

    html = admin_client.get(f"/?semester_id={semester_id}").text

    # The donut's ring carries the realization's square color; the fill and ring styles live in the stylesheet's
    # `marker--deadline` rule, so the marker and its tooltip render at full opacity.
    assert f'class="marker marker--deadline" style="border-color:{PALETTE_BLUE};"' in html
    # The circle is a tooltip anchor like a Lesson square, and the tooltip names the Deadline and its realization.
    circle = html[html.index(f'<a href="/realizations?realization_id={realization_id}"') :][:600]
    assert 'data-tip=""' in circle
    assert 'data-tip-body=""' in circle
    assert "Assignment 1" in circle
    assert "Machine Learning (TTV24SP)" in circle


def test_a_deadline_circle_links_to_its_realizations_weekly_view(
    admin_client, client, realization_id, semester_id, services
):
    services.deadlines.add_deadline(realization_id, LESSON_DATE, "Assignment 1")

    for page in (admin_client, client):
        circle = _circle_anchor(page.get(f"/?semester_id={semester_id}").text, realization_id)

        assert f'href="/realizations?realization_id={realization_id}"' in circle
        assert 'class="marker marker--deadline"' in circle


def test_a_deadline_circle_is_drawn_after_the_squares_of_the_same_day(
    admin_client, realization_id, semester_id, services
):
    services.lessons.add_lesson(realization_id, LESSON_DATE, time(8, 0), time(10, 0), "Introduction", "")
    services.deadlines.add_deadline(realization_id, LESSON_DATE, "Assignment 1")

    html = admin_client.get(f"/?semester_id={semester_id}").text

    # The single lesson square and the single deadline circle of that day both carry the realization's color; the
    # square comes first, so a Deadline dated on a day with a Lesson overlaps that square instead of pushing it away.
    square = (
        f'<a href="/realizations?realization_id={realization_id}" data-tip="" hx-on:click="event.stopPropagation()" '
        f'class="marker marker--lesson" style="background-color:{PALETTE_BLUE};">'
    )
    circle = (
        f'<a href="/realizations?realization_id={realization_id}" data-tip="" hx-on:click="event.stopPropagation()" '
        f'class="marker marker--deadline" style="border-color:{PALETTE_BLUE};">'
    )
    assert html.count(square) == 1
    assert html.count(circle) == 1
    assert html.index(square) < html.index(circle)


def test_an_admins_deadline_circle_does_not_also_open_the_day_dialog(
    admin_client, client, realization_id, semester_id, services
):
    services.deadlines.add_deadline(realization_id, LESSON_DATE, "Assignment 1")

    admin_circle = _circle_anchor(admin_client.get(f"/?semester_id={semester_id}").text, realization_id)
    assert "event.stopPropagation()" in admin_circle

    client.post("/logout", follow_redirects=True)
    visitor_circle = _circle_anchor(client.get(f"/?semester_id={semester_id}").text, realization_id)
    assert "event.stopPropagation()" not in visitor_circle