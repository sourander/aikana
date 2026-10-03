"""In-process client tests of the courses page's realization dialogs, of their edits and deletions, of the weekly
view and of its per-Lesson edit and delete dialogs, per ./tests.sdd.
"""

from datetime import date, time

import pytest

from aikana.courses.repository_sqlite import SqliteCourseRepository
from aikana.courses.services import CourseService
from aikana.realizations.repository_sqlite import SqliteCourseRealizationRepository
from aikana.realizations.services import RealizationService
from aikana.semester.repository_sqlite import SqliteSemesterRepository
from conftest import has_checked_calendar_day


@pytest.fixture
def realization_service(db):
    """Reads the same temporary database to look up CourseRealizations.

    The listing methods under test never touch the wired `semester_service`, so it stays unset here.
    """
    course_service = CourseService(SqliteCourseRepository(db))
    # The realizations table references the semesters table, so it is created first, per ../architecture.sdd.
    SqliteSemesterRepository(db)
    return RealizationService(SqliteCourseRealizationRepository(db), course_service, None, None, None)


def _create_semester(admin_client, year, term):
    response = admin_client.post(
        "/semesters", data={"year": str(year), "term": term}, follow_redirects=False
    )
    return int(response.headers["location"].removeprefix("/?semester_id="))


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
    # The sub-row states the weekday, day and time range; the year stays in the Week cell.
    assert "Tue 20.10. 08:00\u201310:00" in response.text
    assert "Room B" in response.text


def test_share_button_copies_the_url_with_both_ids(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    response = admin_client.get("/realizations")
    query = f"realization_id={realization.id}&amp;semester_id={semester_id}"

    assert f'data-share-url="https://testserver/realizations?{query}"' in response.text
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


def test_admin_courses_page_has_a_prefilled_realization_edit_dialog(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id, group="TTV24SP")
    realization = realization_service.list_realizations_for_course(course_id)[0]

    response = admin_client.get("/courses")

    assert f'id="realization-edit-dialog-{realization.id}"' in response.text
    assert f'action="/courses/{course_id}/realizations/{realization.id}"' in response.text
    assert 'value="TTV24SP"' in response.text
    assert f'<option value="{semester_id}" selected>' in response.text


def test_admin_edits_a_realization_group_and_semester(
    admin_client, course_id, semester_id, realization_service
):
    _add_realization(admin_client, course_id, semester_id, group="TTV24SP")
    realization = realization_service.list_realizations_for_course(course_id)[0]
    spring_id = _create_semester(admin_client, 2027, "spring")

    response = admin_client.post(
        f"/courses/{course_id}/realizations/{realization.id}",
        data={"group": "TTV24SP-B", "semester_id": spring_id},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "TTV24SP-B" in response.text
    assert "Spring 2027" in response.text
    edited = realization_service.list_realizations_for_course(course_id)[0]
    assert edited.group == "TTV24SP-B"
    assert edited.semester_id == spring_id
    # The Course the edit dialog belongs to is not changed by editing a realization.
    assert edited.course_id == course_id


def test_edit_realization_rejects_an_empty_group(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    response = admin_client.post(
        f"/courses/{course_id}/realizations/{realization.id}",
        data={"group": "   ", "semester_id": semester_id},
        follow_redirects=True,
    )

    assert "A CourseRealization needs a non-empty group label." in response.text
    assert realization_service.list_realizations_for_course(course_id)[0].group == "TTV24SP"


def test_edit_realization_rejects_an_unknown_semester(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    response = admin_client.post(
        f"/courses/{course_id}/realizations/{realization.id}",
        data={"group": "TTV24SP-B", "semester_id": "no-such-semester"},
        follow_redirects=True,
    )

    assert "No Semester with id" in response.text
    assert realization_service.list_realizations_for_course(course_id)[0].semester_id == semester_id


def test_edit_an_unknown_realization_is_rejected(admin_client, course_id, semester_id):
    response = admin_client.post(
        f"/courses/{course_id}/realizations/no-such-realization",
        data={"group": "TTV24SP-B", "semester_id": semester_id},
        follow_redirects=True,
    )

    assert "No CourseRealization with id" in response.text


def _delete_dialog_text(client, dialog_id: str) -> str:
    """Just the one confirmation dialog's markup, so another dialog's cascade warning cannot leak into the check."""
    page = client.get("/courses").text
    return page[page.index(f'id="{dialog_id}"') : page.index("</dialog>", page.index(f'id="{dialog_id}"'))]


def test_admin_courses_page_has_a_realization_delete_dialog(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    response = admin_client.get("/courses")

    assert f'id="realization-delete-dialog-{realization.id}"' in response.text
    assert f'action="/courses/{course_id}/realizations/{realization.id}/delete"' in response.text


def test_the_realization_delete_dialog_names_the_lessons_it_removes(
    admin_client, course_id, semester_id, services, realization_service
):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]
    services.lessons.add_lesson(
        realization.id, date(2026, 10, 20), time(8, 0), time(10, 0), "Intro", "Room B"
    )

    response = admin_client.get("/courses")

    assert "This also deletes its 1 lesson." in response.text


def test_a_realization_without_lessons_warns_about_nothing(
    admin_client, course_id, semester_id, realization_service
):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]

    dialog = _delete_dialog_text(admin_client, f"realization-delete-dialog-{realization.id}")

    assert "Delete the realization TTV24SP" in dialog
    assert "also deletes" not in dialog


def test_admin_deletes_a_realization_with_its_lessons(
    admin_client, course_id, semester_id, services, realization_service
):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]
    services.lessons.add_lesson(
        realization.id, date(2026, 10, 20), time(8, 0), time(10, 0), "Intro", "Room B"
    )

    response = admin_client.post(
        f"/courses/{course_id}/realizations/{realization.id}/delete", follow_redirects=True
    )

    assert response.status_code == 200
    assert "TTV24SP" not in response.text
    assert "No realization yet." in response.text
    assert realization_service.list_realizations_for_course(course_id) == []
    assert services.lessons.list_lessons_for_realization(realization.id) == []
    # The Course itself is untouched by deleting one of its realizations.
    assert [course.name for course in services.courses.list_courses()] == ["Machine Learning"]


def test_deleting_an_unknown_realization_is_rejected(admin_client, course_id, semester_id, realization_service):
    _add_realization(admin_client, course_id, semester_id)

    response = admin_client.post(
        f"/courses/{course_id}/realizations/no-such-realization/delete", follow_redirects=True
    )

    assert "No CourseRealization with id" in response.text
    assert len(realization_service.list_realizations_for_course(course_id)) == 1


def test_visitor_cannot_edit_or_delete_a_realization(
    admin_client, course_id, semester_id, realization_service
):
    _add_realization(admin_client, course_id, semester_id)
    realization = realization_service.list_realizations_for_course(course_id)[0]
    admin_client.post("/logout", follow_redirects=True)

    update = admin_client.post(
        f"/courses/{course_id}/realizations/{realization.id}",
        data={"group": "TTV24SP-B", "semester_id": semester_id},
        follow_redirects=False,
    )
    delete = admin_client.post(
        f"/courses/{course_id}/realizations/{realization.id}/delete", follow_redirects=False
    )

    assert update.status_code == 303
    assert update.headers["location"] == "/login"
    assert delete.status_code == 303
    assert delete.headers["location"] == "/login"
    assert realization_service.list_realizations_for_course(course_id)[0].group == "TTV24SP"


@pytest.fixture
def lesson_id(services):
    """A realization with one Lesson in week 43 (2026-10-19 to 10-25), outside the Semester's NoTeachWeeks."""
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    semester = services.semesters.create_semester(2026, "fall")
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    return (
        services.lessons.add_lesson(
            realization.id, date(2026, 10, 20), time(8, 0), time(10, 0), "Intro", "Room B"
        ).id,
        realization.id,
        semester.id,
    )


def _update_lesson(client, lesson, day="2026-10-21", start_time="12:00", end_time="14:00", topic="Regression", notes="Room A"):
    return client.post(
        f"/realizations/lessons/{lesson}",
        data={"day": day, "start_time": start_time, "end_time": end_time, "topic": topic, "notes": notes},
        follow_redirects=True,
    )


def _delete_lesson(client, lesson):
    return client.post(f"/realizations/lessons/{lesson}/delete", follow_redirects=True)


def test_admin_weekly_view_has_a_prefilled_lesson_edit_dialog(admin_client, lesson_id):
    lesson, _, semester = lesson_id

    response = admin_client.get(f"/realizations?semester_id={semester}")

    assert response.status_code == 200
    assert f'id="lesson-edit-dialog-{lesson}"' in response.text
    assert f'action="/realizations/lessons/{lesson}"' in response.text
    assert has_checked_calendar_day(response.text, "2026-10-20")
    assert '<option value="08:00" selected>08:00</option>' in response.text
    assert '<option value="10:00" selected>10:00</option>' in response.text
    assert "pattern=" not in response.text
    assert 'value="Intro"' in response.text
    assert 'value="Room B"' in response.text


def test_admin_weekly_view_has_a_lesson_delete_dialog(admin_client, lesson_id):
    lesson, _, semester = lesson_id

    response = admin_client.get(f"/realizations?semester_id={semester}")

    assert f'id="lesson-delete-dialog-{lesson}"' in response.text
    assert f'action="/realizations/lessons/{lesson}/delete"' in response.text


def test_the_lesson_delete_dialog_names_the_lesson_and_its_date(admin_client, lesson_id):
    _, _, semester = lesson_id

    response = admin_client.get(f"/realizations?semester_id={semester}")

    assert "Delete the Lesson Intro on 20.10.2026?" in response.text


def test_the_lesson_controls_stop_the_click_that_opens_the_day_dialog(admin_client, lesson_id):
    lesson, _, semester = lesson_id

    response = admin_client.get(f"/realizations?semester_id={semester}")

    assert f"event.stopPropagation(); var d = document.getElementById('lesson-edit-dialog-{lesson}')" in response.text


def test_only_a_lesson_sub_row_carries_the_lesson_controls(admin_client, lesson_id, services):
    lesson, realization, semester = lesson_id
    # A Holiday shares the week with the Lesson, so a second pair of dialogs would mean both kinds were addressed.
    services.holidays.add_holiday(date(2026, 10, 21), "Autumn break")

    response = admin_client.get(f"/realizations?semester_id={semester}")

    assert response.text.count("lesson-edit-dialog") == 2
    assert response.text.count(f'id="lesson-edit-dialog-{lesson}"') == 1
    assert "Holiday \u2013 Autumn break" in response.text


def test_admin_edits_a_lesson_from_the_weekly_view(admin_client, lesson_id, services):
    lesson, realization, semester = lesson_id

    response = _update_lesson(admin_client, lesson)

    assert response.status_code == 200
    assert "Regression" in response.text
    assert "Room A" in response.text
    assert "12:00\u201314:00" in response.text
    assert "Intro" not in response.text
    edited = services.lessons.get_lesson(lesson)
    assert edited.topic == "Regression"
    assert edited.notes == "Room A"
    assert edited.start_time == time(12, 0)
    assert edited.date == date(2026, 10, 21)
    # The edit never moves the Lesson to another CourseRealization.
    assert edited.course_realization_id == realization


def test_a_rejected_lesson_edit_returns_a_validation_message(admin_client, lesson_id, services):
    lesson, _, semester = lesson_id

    response = _update_lesson(admin_client, lesson, topic="   ")

    assert "A Lesson needs a non-empty topic." in response.text
    assert f"realization_id={services.lessons.get_lesson(lesson).course_realization_id}" in response.text
    assert services.lessons.get_lesson(lesson).topic == "Intro"


def test_a_lesson_edit_moving_onto_a_taken_day_is_rejected(admin_client, lesson_id, services):
    lesson, _, _ = lesson_id
    services.lessons.add_lesson(
        services.lessons.get_lesson(lesson).course_realization_id,
        date(2026, 10, 21),
        time(8, 0),
        time(10, 0),
        "Taken",
        "",
    )

    response = _update_lesson(admin_client, lesson, day="2026-10-21")

    assert "21.10.2026 already has a Lesson for this CourseRealization." in response.text
    assert {lesson_.topic for lesson_ in services.lessons.list_lessons_for_range(date(2026, 10, 20), date(2026, 10, 21))} == {"Intro", "Taken"}


def test_a_malformed_lesson_edit_field_is_reported(admin_client, lesson_id, services):
    lesson, _, _ = lesson_id

    response = _update_lesson(admin_client, lesson, start_time="half past eight")

    assert "Enter a valid start time as HH:MM." in response.text
    assert services.lessons.get_lesson(lesson).start_time == time(8, 0)


def test_admin_deletes_a_lesson_from_the_weekly_view(admin_client, lesson_id, services):
    lesson, realization, semester = lesson_id

    response = _delete_lesson(admin_client, lesson)

    assert response.status_code == 200
    assert "Intro" not in response.text
    assert services.lessons.list_lessons_for_realization(realization) == []
    # Only the Lesson goes; its CourseRealization and its Course stay.
    assert services.realizations.get_realization(realization).group == "TTV24SP"
    assert [course.name for course in services.courses.list_courses()] == ["Machine Learning"]


def test_deleting_one_lesson_leaves_the_realization_others_alone(admin_client, lesson_id, services):
    lesson, realization, _ = lesson_id
    kept = services.lessons.add_lesson(realization, date(2026, 10, 22), time(8, 0), time(10, 0), "Kept", "")

    _delete_lesson(admin_client, lesson)

    assert [lesson_.id for lesson_ in services.lessons.list_lessons_for_realization(realization)] == [kept.id]


def test_deleting_an_unknown_lesson_is_rejected(admin_client, lesson_id, services):
    lesson, realization, _ = lesson_id

    response = _delete_lesson(admin_client, "no-such-lesson")

    assert "No Lesson with id" in response.text
    assert [lesson_.id for lesson_ in services.lessons.list_lessons_for_realization(realization)] == [lesson]


def test_updating_an_unknown_lesson_is_rejected(admin_client, lesson_id, services):
    _, realization, _ = lesson_id

    response = _update_lesson(admin_client, "no-such-lesson")

    assert "No Lesson with id" in response.text
    assert len(services.lessons.list_lessons_for_realization(realization)) == 1


def test_visitor_sees_no_lesson_controls(admin_client, client, lesson_id):
    lesson, _, semester = lesson_id
    admin_client.post("/logout", follow_redirects=True)

    response = client.get(f"/realizations?semester_id={semester}")

    assert "Intro" in response.text
    assert "<dialog" not in response.text
    assert f"/realizations/lessons/{lesson}" not in response.text


def test_visitor_cannot_edit_or_delete_a_lesson(admin_client, lesson_id, services):
    lesson, realization, _ = lesson_id
    admin_client.post("/logout", follow_redirects=True)

    update = admin_client.post(
        f"/realizations/lessons/{lesson}",
        data={"day": "2026-10-21", "start_time": "12:00", "end_time": "14:00", "topic": "Regression", "notes": ""},
        follow_redirects=False,
    )
    delete = admin_client.post(f"/realizations/lessons/{lesson}/delete", follow_redirects=False)

    assert update.status_code == 303
    assert update.headers["location"] == "/login"
    assert delete.status_code == 303
    assert delete.headers["location"] == "/login"
    assert services.lessons.get_lesson(lesson).topic == "Intro"
