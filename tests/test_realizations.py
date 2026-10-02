"""In-process client tests of the courses page's add-realization dialog and of the weekly view, per ./tests.sdd."""

from datetime import date, time

import pytest

from aikana.courses.repository_sqlite import SqliteCourseRepository
from aikana.courses.services import CourseService
from aikana.realizations.repository_sqlite import SqliteCourseRealizationRepository
from aikana.realizations.services import RealizationService


@pytest.fixture
def realization_service(db):
    """Reads the same temporary database to look up CourseRealizations.

    The listing methods under test never touch the wired `semester_service`, so it stays unset here.
    """
    course_service = CourseService(SqliteCourseRepository(db))
    return RealizationService(SqliteCourseRealizationRepository(db), course_service, None, None, None)


def _create_semester(admin_client, year, term):
    response = admin_client.post(
        "/semesters", data={"year": str(year), "term": term}, follow_redirects=False
    )
    return response.headers["location"].removeprefix("/?semester_id=")


@pytest.fixture
def course_id(admin_client, course_service):
    admin_client.post(
        "/courses",
        data={"name": "Machine Learning", "description": "An introduction.", "ects_credits": "5"},
        follow_redirects=True,
    )
    return course_service.list_courses()[0].id


@pytest.fixture
def semester_id(admin_client):
    return _create_semester(admin_client, 2026, "fall")


def _add_realization(client, course_id, semester_id, group="TTV24SP"):
    return client.post(
        f"/courses/{course_id}/realizations",
        data={"group": group, "semester_id": semester_id},
        follow_redirects=True,
    )


def test_admin_courses_page_has_an_add_realization_dialog(admin_client, course_id, semester_id):
    response = admin_client.get("/courses")

    assert f'id="realization-dialog-{course_id}"' in response.text
    assert f'action="/courses/{course_id}/realizations"' in response.text
    assert "+ Add Realization" in response.text


def test_admin_adds_a_realization_to_a_course(admin_client, course_id, semester_id, realization_service):
    response = _add_realization(admin_client, course_id, semester_id)

    assert response.status_code == 200
    assert "TTV24SP" in response.text
    assert "Fall 2026" in response.text
    realization = realization_service.list_realizations_for_course(course_id)[0]
    assert realization.group == "TTV24SP"
    assert realization.semester_id == semester_id


def test_a_listed_realization_links_to_its_weekly_view(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    response = admin_client.get("/courses")

    assert "/realizations?" in response.text
    assert f"realization_id={realization.id}" in response.text


def test_a_course_without_realizations_says_so(admin_client, course_id):
    response = admin_client.get("/courses")

    assert "Realizations" in response.text
    assert "No realization yet." in response.text


def test_a_new_realization_shows_up_in_the_weekly_view(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    response = admin_client.get(f"/realizations?semester_id={semester_id}&realization_id={realization.id}")

    assert response.status_code == 200
    assert "Machine Learning (TTV24SP)" in response.text


def test_weekly_view_renders_the_empty_state_when_the_semester_has_no_realizations(client, services):
    semester = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/realizations?semester_id={semester.id}")

    assert response.status_code == 200
    assert "No CourseRealizations in the active Semester yet." in response.text


def test_weekly_view_falls_back_to_the_first_realization_for_an_unknown_id(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")

    response = client.get(f"/realizations?semester_id={semester.id}&realization_id=no-such-realization")

    assert response.status_code == 200
    assert f'<option value="{realization.id}" selected>' in response.text
    assert "Machine Learning (TTV24SP)" in response.text


def test_weekly_view_falls_back_when_the_realization_belongs_to_another_semester(client, services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    services.realizations.add_realization(course.id, fall.id, "TTV24SP")
    spring_realization = services.realizations.add_realization(course.id, spring.id, "TTV27SP")
    fall_realization = next(
        r for r in services.realizations.list_realizations_for_course(course.id) if r.semester_id == fall.id
    )

    response = client.get(f"/realizations?semester_id={spring.id}&realization_id={fall_realization.id}")

    assert response.status_code == 200
    assert f'<option value="{spring_realization.id}" selected>' in response.text
    assert "TTV27SP" in response.text
    assert "TTV24SP" not in response.text


def test_a_week_with_a_lesson_and_a_holiday_spans_two_sub_rows(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    # Week 43 (2026-10-19 to 10-25) is outside the Semester's default NoTeachWeeks.
    services.lessons.add_lesson(realization.id, date(2026, 10, 20), time(8, 0), time(10, 0), "Intro", "Room B")
    services.holidays.add_holiday(date(2026, 10, 21), "Autumn break")

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    # One sub-row per entry under the single Week cell, per realizations.sdd.
    assert 'rowspan="2"' in response.text
    assert "Holiday \u2013 Autumn break" in response.text
    assert "Intro" in response.text
    assert "Room B" in response.text


def test_share_button_copies_the_url_with_both_ids(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    response = admin_client.get("/realizations")
    query = f"realization_id={realization.id}&amp;semester_id={semester_id}"

    assert f'data-share-url="http://testserver/realizations?{query}"' in response.text
    assert "navigator.clipboard.writeText" in response.text


def test_share_button_completes_a_url_missing_the_semester(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    admin_response = admin_client.get(f"/realizations?realization_id={realization.id}")
    admin_client.post("/logout", follow_redirects=True)
    visitor_response = admin_client.get(f"/realizations?realization_id={realization.id}")

    assert admin_response.status_code == 200
    assert visitor_response.status_code == 200
    for response in (admin_response, visitor_response):
        assert f"realization_id={realization.id}&amp;semester_id={semester_id}" in response.text


def test_realizations_of_every_semester_are_listed(admin_client, course_id, semester_id, realization_service):
    spring_id = _create_semester(admin_client, 2027, "spring")
    _add_realization(admin_client, course_id, semester_id, group="TTV24SP")
    _add_realization(admin_client, course_id, spring_id, group="TTV27SP")

    response = admin_client.get("/courses")

    assert "TTV24SP" in response.text
    assert "TTV27SP" in response.text
    assert "Fall 2026" in response.text
    assert "Spring 2027" in response.text
    assert len(realization_service.list_realizations_for_course(course_id)) == 2


def test_add_realization_rejects_an_empty_group(admin_client, course_id, semester_id, realization_service):
    response = _add_realization(admin_client, course_id, semester_id, group="   ")

    assert "A CourseRealization needs a non-empty group label." in response.text
    assert realization_service.list_realizations_for_course(course_id) == []


def test_add_realization_rejects_an_unknown_semester(admin_client, course_id, realization_service):
    response = _add_realization(admin_client, course_id, "no-such-semester")

    assert "No Semester with id" in response.text
    assert realization_service.list_realizations_for_course(course_id) == []


def test_add_realization_rejects_an_unknown_course(admin_client, semester_id):
    response = _add_realization(admin_client, "no-such-course", semester_id)

    assert "No Course with id" in response.text


def test_add_realization_dialog_reports_a_missing_semester(admin_client, course_id):
    response = admin_client.get("/courses")

    assert "No Semester has been created yet." in response.text
    assert f'action="/courses/{course_id}/realizations"' not in response.text


def test_visitor_sees_realizations_without_add_affordances(admin_client, client, course_id, semester_id):
    _add_realization(admin_client, course_id, semester_id)
    admin_client.post("/logout", follow_redirects=True)

    response = client.get("/courses")

    assert "TTV24SP" in response.text
    assert "+ Add Realization" not in response.text
    assert "<dialog" not in response.text


def test_visitor_cannot_create_a_realization(admin_client, course_id, semester_id, realization_service):
    admin_client.post("/logout", follow_redirects=True)

    response = admin_client.post(
        f"/courses/{course_id}/realizations",
        data={"group": "TTV24SP", "semester_id": semester_id},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert realization_service.list_realizations_for_course(course_id) == []
