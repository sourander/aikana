"""In-process client tests of the admin day dialog, per ./tests.sdd."""

from datetime import date, time

import pytest

from conftest import AIKANA_PASSWD, has_checked_calendar_day

# The dialog is only reachable through an HTMX request, per ./src/aikana/day_dialog/day_dialog.sdd.
HTMX = {"HX-Request": "true"}

# A free week of the fall 2026 Semester, outside its default NoTeachWeeks in weeks 42 and 51.
FREE_DAY = "2026-10-20"
FREE_WEEK = "43"


@pytest.fixture
def semester(services):
    """A fall 2026 Semester, seeded on the same temporary database the app was built on."""
    return services.semesters.create_semester(2026, "fall")


def _open_dialog(client, semester, kind="holiday", day=FREE_DAY):
    return client.get(
        "/day/dialog",
        params={"semester_id": semester.id, "day": day, "kind": kind},
        headers=HTMX,
    )


def _add_realization(services, semester, group="TTV24SP"):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    return services.realizations.add_realization(course.id, semester.id, group)


def _assert_bare_grid(response):
    """A successful write responds with the bare grid, never a second dialog container."""
    assert response.text.count('id="semester-grid"') == 1
    assert 'id="day-dialog"' not in response.text
    # ../semester/semester.sdd's legend bar is a sibling of the grid, so the swap leaves the bar in the page.
    assert 'id="semester-legend"' not in response.text


def test_admin_sees_a_day_dialog_trigger_on_every_day_row(admin_client, semester):
    response = admin_client.get(f"/?semester_id={semester.id}")

    assert response.status_code == 200
    assert 'id="semester-grid"' in response.text
    assert 'id="day-dialog"' in response.text
    assert f'hx-get="/day/dialog?semester_id={semester.id}&amp;day={FREE_DAY}&amp;kind=lesson"' in response.text


def test_visitor_sees_no_day_dialog_trigger(client, semester):
    client.post("/login", data={"password": AIKANA_PASSWD}, follow_redirects=True)
    client.post("/logout", follow_redirects=True)

    response = client.get(f"/?semester_id={semester.id}")

    assert "/day/dialog" not in response.text
    assert 'id="day-dialog"' not in response.text


def test_lesson_square_stays_a_link_to_the_weekly_view(admin_client, semester, services):
    realization = _add_realization(services, semester)
    services.lessons.add_lesson(
        realization.id, date(2026, 10, 20), time(8, 30), time(10, 0), "Intro", ""
    )

    response = admin_client.get(f"/?semester_id={semester.id}")

    assert f'href="/realizations?realization_id={realization.id}"' in response.text
    # The square is a link, so it must not also open the dialog of the row it sits in.
    assert "event.stopPropagation()" in response.text


def test_admin_opens_the_dialog_for_a_day(admin_client, semester):
    response = _open_dialog(admin_client, semester)

    assert response.status_code == 200
    assert '<dialog id="day-dialog-modal"' in response.text
    # The response is the bare <dialog>, so swapping it into the container cannot nest a second #day-dialog.
    assert 'id="day-dialog"' not in response.text
    assert "Tuesday, 20.10.2026" in response.text
    assert 'name="day" type="hidden" value="2026-10-20"' in response.text
    assert 'hx-post="/day/dialog/holiday"' in response.text
    assert 'hx-target="#semester-grid"' in response.text


def test_dialog_offers_a_tab_per_kind(admin_client, semester, services):
    _add_realization(services, semester)

    for kind, expected in (
        ("holiday", "/day/dialog/holiday"),
        ("no_teach_week", "/day/dialog/no-teach-week"),
        ("lesson", "/day/dialog/lesson"),
    ):
        response = _open_dialog(admin_client, semester, kind=kind)
        assert response.status_code == 200
        assert f'hx-post="{expected}"' in response.text


def test_no_teach_week_form_prefills_the_clicked_day_s_iso_week(admin_client, semester):
    response = _open_dialog(admin_client, semester, kind="no_teach_week")

    assert 'name="week_number"' in response.text
    assert f'value="{FREE_WEEK}"' in response.text
    assert 'value="No teaching week"' in response.text


def test_lesson_form_lists_the_semester_course_realizations(admin_client, semester, services):
    realization = _add_realization(services, semester)

    response = _open_dialog(admin_client, semester, kind="lesson")

    assert 'name="course_realization_id"' in response.text
    assert f'<option value="{realization.id}" selected>' in response.text
    assert "Machine Learning (TTV24SP)" in response.text


def test_lesson_form_says_so_when_the_semester_has_no_realization(admin_client, semester):
    response = _open_dialog(admin_client, semester, kind="lesson")

    assert "No CourseRealizations in this Semester yet." in response.text
    assert 'hx-post="/day/dialog/lesson"' not in response.text


def test_lesson_form_selects_times_from_15_minute_dropdowns(admin_client, semester, services):
    _add_realization(services, semester)

    response = _open_dialog(admin_client, semester, kind="lesson")

    assert 'type="time"' not in response.text
    assert "pattern=" not in response.text
    assert 'name="start_time"' in response.text
    assert 'name="end_time"' in response.text
    assert '<option value="08:00" selected>08:00</option>' in response.text
    assert '<option value="10:00" selected>10:00</option>' in response.text
    assert '<option value="08:15">08:15</option>' in response.text
    assert '<option value="14:30">14:30</option>' in response.text
    # Both times run on the 15-minute grid up to 20:45; only the end time reaches 21:00.
    assert response.text.count('<option value="20:45">20:45</option>') == 2
    assert response.text.count('<option value="21:00">21:00</option>') == 1


def test_lesson_form_places_the_two_time_dropdowns_on_one_row(admin_client, semester, services):
    _add_realization(services, semester)

    response = _open_dialog(admin_client, semester, kind="lesson")

    row = response.text.split('<div class="flex gap-2">', 1)[1]
    assert row.index('name="start_time"') < row.index('name="end_time"')


def test_admin_adds_a_holiday(admin_client, semester, services):
    response = admin_client.post(
        "/day/dialog/holiday",
        data={"semester_id": semester.id, "day": FREE_DAY, "title": "Autumn break"},
        headers=HTMX,
    )

    assert response.status_code == 200
    _assert_bare_grid(response)
    assert "Autumn break" in response.text
    assert [holiday.title for holiday in services.holidays.list_holidays_for_range(*_range(FREE_DAY))] == [
        "Autumn break"
    ]


def test_admin_adds_a_no_teach_week(admin_client, semester, services):
    response = admin_client.post(
        "/day/dialog/no-teach-week",
        data={"semester_id": semester.id, "day": FREE_DAY, "week_number": FREE_WEEK, "title": "Staff training"},
        headers=HTMX,
    )

    assert response.status_code == 200
    # One NoTeachWeek tints all five of its Monday-to-Friday rows, so the whole grid comes back.
    _assert_bare_grid(response)
    assert response.text.count("Staff training") == 5
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 43)
    assert week.title == "Staff training"
    assert week.week_start == date(2026, 10, 19)


def test_admin_adds_a_lesson(admin_client, semester, services):
    realization = _add_realization(services, semester)

    response = admin_client.post(
        "/day/dialog/lesson",
        data={
            "semester_id": semester.id,
            "day": FREE_DAY,
            "course_realization_id": realization.id,
            "start_time": "08:30",
            "end_time": "10:00",
            "topic": "Intro",
            "notes": "Bring the dataset",
        },
        headers=HTMX,
    )

    assert response.status_code == 200
    _assert_bare_grid(response)
    assert "Intro" in response.text
    lesson = services.lessons.list_lessons_for_realization(realization.id)[0]
    assert (lesson.date, lesson.start_time, lesson.end_time, lesson.topic) == (
        date(2026, 10, 20),
        time(8, 30),
        time(10, 0),
        "Intro",
    )
    assert lesson.notes == "Bring the dataset"


def test_a_rejected_holiday_is_not_stored_and_the_dialog_reports_it(admin_client, semester, services):
    response = admin_client.post(
        "/day/dialog/holiday",
        data={"semester_id": semester.id, "day": FREE_DAY, "title": "   "},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#day-dialog"
    assert response.headers["HX-Reswap"] == "innerHTML"
    assert "non-empty title" in response.text
    assert services.holidays.list_holidays_for_range(*_range(FREE_DAY)) == []


def test_a_duplicate_no_teach_week_is_rejected(admin_client, semester, services):
    data = {"semester_id": semester.id, "day": FREE_DAY, "week_number": FREE_WEEK, "title": "Staff training"}
    admin_client.post("/day/dialog/no-teach-week", data=data, headers=HTMX)

    response = admin_client.post("/day/dialog/no-teach-week", data=data, headers=HTMX)

    assert response.status_code == 422
    assert "already a NoTeachWeek" in response.text
    assert len(services.no_teach_weeks.list_no_teach_weeks(semester.id)) == 3


def test_a_lesson_inside_a_no_teach_week_is_rejected(admin_client, semester, services):
    realization = _add_realization(services, semester)
    admin_client.post(
        "/day/dialog/no-teach-week",
        data={"semester_id": semester.id, "day": FREE_DAY, "week_number": FREE_WEEK, "title": ""},
        headers=HTMX,
    )

    response = admin_client.post(
        "/day/dialog/lesson",
        data={
            "semester_id": semester.id,
            "day": FREE_DAY,
            "course_realization_id": realization.id,
            "start_time": "08:30",
            "end_time": "10:00",
            "topic": "Blocked",
            "notes": "",
        },
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "NoTeachWeek" in response.text
    assert services.lessons.list_lessons_for_realization(realization.id) == []


def test_a_malformed_form_field_is_reported_instead_of_reaching_the_services(admin_client, semester, services):
    realization = _add_realization(services, semester)

    response = admin_client.post(
        "/day/dialog/lesson",
        data={
            "semester_id": semester.id,
            "day": FREE_DAY,
            "course_realization_id": realization.id,
            "start_time": "half past eight",
            "end_time": "10:00",
            "topic": "Intro",
            "notes": "",
        },
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "Enter a valid start time as HH:MM." in response.text
    assert services.lessons.list_lessons_for_realization(realization.id) == []


def test_a_malformed_week_number_is_reported(admin_client, semester, services):
    response = admin_client.post(
        "/day/dialog/no-teach-week",
        data={"semester_id": semester.id, "day": FREE_DAY, "week_number": "not-a-week", "title": "Staff training"},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "A NoTeachWeek needs a whole-numbered week." in response.text
    assert [w.week_number for w in services.no_teach_weeks.list_no_teach_weeks(semester.id)] == [42, 51]


def test_a_malformed_day_is_reported(admin_client, semester, services):
    before = services.holidays.list_holidays_for_range(date(2025, 1, 1), date(2027, 12, 31))

    response = admin_client.post(
        "/day/dialog/holiday",
        data={"semester_id": semester.id, "day": "not-a-day", "title": "Autumn break"},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "not a valid date" in response.text
    # The Semester's pre-populated public holidays are untouched, and the malformed day added nothing.
    assert services.holidays.list_holidays_for_range(date(2025, 1, 1), date(2027, 12, 31)) == before
    assert all(holiday.title != "Autumn break" for holiday in before)


def test_a_rejected_form_keeps_what_the_admin_typed(admin_client, semester):
    response = admin_client.post(
        "/day/dialog/holiday",
        data={"semester_id": semester.id, "day": FREE_DAY, "title": "   "},
        headers=HTMX,
    )

    assert 'value="   "' in response.text
    assert 'name="day" type="hidden" value="2026-10-20"' in response.text


def test_a_visitor_can_neither_open_the_dialog_nor_add_through_it(client, semester, services):
    _add_realization(services, semester)

    response = client.get(
        "/day/dialog",
        params={"semester_id": semester.id, "day": FREE_DAY, "kind": "holiday"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    for path, data in (
        ("/day/dialog/holiday", {"semester_id": semester.id, "day": FREE_DAY, "title": "Nope"}),
        ("/day/dialog/no-teach-week", {"semester_id": semester.id, "day": FREE_DAY, "week_number": FREE_WEEK}),
        (
            "/day/dialog/lesson",
            {"semester_id": semester.id, "day": FREE_DAY, "start_time": "08:00", "end_time": "10:00", "topic": "Nope"},
        ),
    ):
        response = client.post(path, data=data, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"

    assert services.holidays.list_holidays_for_range(*_range(FREE_DAY)) == []
    assert len(services.no_teach_weeks.list_no_teach_weeks(semester.id)) == 2


# The Realizations weekly view's lesson add slot and its lesson-only dialog, per
# ./src/aikana/realizations/realizations.sdd.

# Monday of FREE_DAY's week, outside the fall 2026 Semester's default NoTeachWeeks.
FREE_WEEK_MONDAY = "2026-10-19"


def test_admin_sees_a_lesson_add_slot_in_the_realizations_view(admin_client, semester, services):
    realization = _add_realization(services, semester)

    response = admin_client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    assert 'id="realization-week-table"' in response.text
    assert 'id="day-dialog"' in response.text
    assert (
        f'hx-get="/day/dialog?semester_id={semester.id}&amp;day={FREE_WEEK_MONDAY}&amp;kind=lesson'
        f'&amp;realization_id={realization.id}"' in response.text
    )


def test_visitor_sees_no_lesson_add_slot(client, semester, services):
    realization = _add_realization(services, semester)

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    assert "/day/dialog" not in response.text
    assert 'id="day-dialog"' not in response.text


def test_admin_opens_the_weekly_dialog_with_the_week_s_monday_checked(admin_client, semester, services):
    realization = _add_realization(services, semester)

    response = admin_client.get(
        "/day/dialog",
        params={
            "semester_id": semester.id,
            "day": FREE_WEEK_MONDAY,
            "kind": "lesson",
            "realization_id": realization.id,
        },
        headers=HTMX,
    )

    assert response.status_code == 200
    assert has_checked_calendar_day(response.text, FREE_WEEK_MONDAY)
    assert f'name="realization_id" type="hidden" value="{realization.id}"' in response.text
    assert 'hx-target="#realization-week-table"' in response.text
    assert 'hx-target="#semester-grid"' not in response.text


def test_the_weekly_dialog_offers_only_the_lesson_form(admin_client, semester, services):
    realization = _add_realization(services, semester)

    response = admin_client.get(
        "/day/dialog",
        params={
            "semester_id": semester.id,
            "day": FREE_WEEK_MONDAY,
            "kind": "lesson",
            "realization_id": realization.id,
        },
        headers=HTMX,
    )

    assert 'hx-post="/day/dialog/lesson"' in response.text
    # No tabs and no other kind's form, per ./src/aikana/day_dialog/day_dialog.sdd.
    assert "/day/dialog/holiday" not in response.text
    assert "/day/dialog/no-teach-week" not in response.text
    assert "/day/dialog/conference" not in response.text


def test_the_weekly_lesson_form_defaults_to_the_week_s_realization(admin_client, semester, services):
    first = _add_realization(services, semester)
    other_course = services.courses.add_course("Databases", "SQL.", 5)
    second = services.realizations.add_realization(other_course.id, semester.id, "TTV24SP")

    response = admin_client.get(
        "/day/dialog",
        params={
            "semester_id": semester.id,
            "day": FREE_WEEK_MONDAY,
            "kind": "lesson",
            "realization_id": second.id,
        },
        headers=HTMX,
    )

    assert f'<option value="{second.id}" selected>' in response.text
    assert f'<option value="{first.id}">' in response.text


def test_admin_adds_a_lesson_from_the_add_slot(admin_client, semester, services):
    realization = _add_realization(services, semester)

    response = admin_client.post(
        "/day/dialog/lesson",
        data={
            "semester_id": semester.id,
            "day": "2026-10-21",
            "course_realization_id": realization.id,
            "start_time": "08:30",
            "end_time": "10:00",
            "topic": "Intro",
            "notes": "",
            "realization_id": realization.id,
        },
        headers=HTMX,
    )

    assert response.status_code == 200
    _assert_bare_week_table(response)
    assert "Intro" in response.text
    assert services.lessons.list_lessons_for_realization(realization.id)[0].date == date(2026, 10, 21)


def _assert_bare_week_table(response):
    """A successful weekly-view write responds with the bare weekly table, never a second dialog container."""
    assert response.text.count('id="realization-week-table"') == 1
    assert 'id="day-dialog"' not in response.text


def _range(day: str):
    parsed = date.fromisoformat(day)
    return parsed, parsed


# Editing and removing the entries already on the clicked date, per ./src/aikana/day_dialog/day_dialog.sdd.


def test_the_holiday_tab_edits_the_holiday_already_on_that_day(admin_client, semester, services):
    holiday = services.holidays.add_holiday(date(2026, 10, 20), "Autumn break")

    response = _open_dialog(admin_client, semester, kind="holiday")

    assert f'action="/day/dialog/holidays/{holiday.id}"' in response.text
    assert 'value="Autumn break"' in response.text
    assert has_checked_calendar_day(response.text, FREE_DAY)
    assert 'action="/day/dialog/holiday"' not in response.text
    # One day calendar, one Save and one Delete, so the edit form replaces the add form instead of doubling it.
    assert response.text.count(">Mon</span>") == 1
    assert response.text.count(">Save</button>") == 1
    assert response.text.count(">Delete</button>") == 1


def test_the_admin_edits_a_holiday_through_the_dialog(admin_client, semester, services):
    holiday = services.holidays.add_holiday(date(2026, 10, 20), "Autumn break")

    response = admin_client.post(
        f"/day/dialog/holidays/{holiday.id}",
        data={"semester_id": semester.id, "day": "2026-10-21", "title": "Staff day"},
        headers=HTMX,
    )

    assert response.status_code == 200
    _assert_bare_grid(response)
    assert "Staff day" in response.text
    assert "Autumn break" not in response.text
    stored = services.holidays.get_holiday(holiday.id)
    assert (stored.date, stored.title) == (date(2026, 10, 21), "Staff day")
    assert services.holidays.list_holidays_for_range(*_range(FREE_DAY)) == []


def test_a_rejected_holiday_edit_keeps_the_stored_holiday_and_what_the_admin_typed(
    admin_client, semester, services
):
    holiday = services.holidays.add_holiday(date(2026, 10, 20), "Autumn break")

    response = admin_client.post(
        f"/day/dialog/holidays/{holiday.id}",
        data={"semester_id": semester.id, "day": FREE_DAY, "title": "  "},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#day-dialog"
    assert 'value="  "' in response.text
    stored = services.holidays.get_holiday(holiday.id)
    assert (stored.date, stored.title) == (date(2026, 10, 20), "Autumn break")


def test_a_holiday_edit_onto_a_day_that_already_has_one_is_rejected(admin_client, semester, services):
    holiday = services.holidays.add_holiday(date(2026, 10, 20), "Autumn break")
    services.holidays.add_holiday(date(2026, 10, 21), "Staff day")

    response = admin_client.post(
        f"/day/dialog/holidays/{holiday.id}",
        data={"semester_id": semester.id, "day": "2026-10-21", "title": "Autumn break"},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "already has a Holiday" in response.text
    assert services.holidays.get_holiday(holiday.id).date == date(2026, 10, 20)


def test_the_admin_deletes_a_holiday_through_the_dialog(admin_client, semester, services):
    holiday = services.holidays.add_holiday(date(2026, 10, 20), "Autumn break")

    dialog = _open_dialog(admin_client, semester, kind="holiday")
    assert f'hx-post="/day/dialog/holidays/{holiday.id}/delete"' in dialog.text
    assert 'hx-confirm="Delete the Holiday Autumn break on 20.10.2026?"' in dialog.text

    response = admin_client.post(
        f"/day/dialog/holidays/{holiday.id}/delete",
        data={"semester_id": semester.id, "day": FREE_DAY},
        headers=HTMX,
    )

    assert response.status_code == 200
    _assert_bare_grid(response)
    assert "Autumn break" not in response.text
    assert services.holidays.list_holidays_for_range(*_range(FREE_DAY)) == []


def test_deleting_an_unknown_holiday_is_reported_in_the_dialog(admin_client, semester):
    response = admin_client.post(
        "/day/dialog/holidays/9999/delete",
        data={"semester_id": semester.id, "day": FREE_DAY},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "No Holiday with id" in response.text


def test_the_no_teach_week_tab_edits_the_week_already_blocking_that_day(admin_client, semester, services):
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)

    response = _open_dialog(admin_client, semester, kind="no_teach_week", day="2026-10-13")

    assert f'action="/day/dialog/no-teach-weeks/{week.id}"' in response.text
    assert 'name="week_number" type="number" min="1" max="53" value="42"' in response.text
    assert 'name="title" value="Syysvapaat"' in response.text
    assert 'action="/day/dialog/no-teach-week"' not in response.text
    assert response.text.count(">Save</button>") == 1
    assert response.text.count(">Delete</button>") == 1


def test_the_admin_edits_a_no_teach_week_through_the_dialog(admin_client, semester, services):
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)

    response = admin_client.post(
        f"/day/dialog/no-teach-weeks/{week.id}",
        data={"semester_id": semester.id, "day": "2026-10-13", "week_number": "44", "title": "Sick leave"},
        headers=HTMX,
    )

    assert response.status_code == 200
    # The week moved, so all five of its new Monday-to-Friday rows are tinted and titled.
    assert response.text.count("Sick leave") == 5
    stored = services.no_teach_weeks.get_no_teach_week(week.id)
    assert (stored.week_number, stored.week_start, stored.title) == (44, date(2026, 10, 26), "Sick leave")


def test_a_rejected_no_teach_week_edit_keeps_the_stored_week_and_what_the_admin_typed(
    admin_client, semester, services
):
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)
    services.no_teach_weeks.add_no_teach_week(semester.id, 44, "Sick leave")

    response = admin_client.post(
        f"/day/dialog/no-teach-weeks/{week.id}",
        data={"semester_id": semester.id, "day": "2026-10-13", "week_number": "44", "title": "Later"},
        headers=HTMX,
    )

    assert response.status_code == 422
    assert "already a NoTeachWeek" in response.text
    assert 'value="Later"' in response.text
    stored = services.no_teach_weeks.get_no_teach_week(week.id)
    assert (stored.week_number, stored.title) == (42, "Syysvapaat")


def test_the_admin_deletes_a_no_teach_week_through_the_dialog(admin_client, semester, services):
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)

    response = admin_client.post(
        f"/day/dialog/no-teach-weeks/{week.id}/delete",
        data={"semester_id": semester.id, "day": "2026-10-13"},
        headers=HTMX,
    )

    assert response.status_code == 200
    # Only the Semester's other default NoTeachWeek is left, so five rows stay tinted.
    assert response.text.count("Jouluvapaat") == 5
    assert [w.week_number for w in services.no_teach_weeks.list_no_teach_weeks(semester.id)] == [51]


def test_the_no_teach_week_tab_adds_a_week_on_a_day_no_week_blocks(admin_client, semester):
    response = _open_dialog(admin_client, semester, kind="no_teach_week")

    assert 'action="/day/dialog/no-teach-week"' in response.text
    assert "/no-teach-weeks/" not in response.text


def test_a_weekend_day_in_a_blocked_week_edits_that_week(admin_client, semester, services):
    # A NoTeachWeek blocks Monday to Friday, but Saturday and Sunday are in the same week, so a day row that is not
    # tinted still resolves to the week blocking it.
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)

    response = _open_dialog(admin_client, semester, kind="no_teach_week", day="2026-10-17")

    assert f'action="/day/dialog/no-teach-weeks/{week.id}"' in response.text
    assert 'value="42"' in response.text


def test_a_visitor_can_neither_edit_nor_delete_through_the_dialog(client, semester, services):
    holiday = services.holidays.add_holiday(date(2026, 10, 20), "Autumn break")
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)

    for path, data in (
        (f"/day/dialog/holidays/{holiday.id}", {"day": FREE_DAY, "title": "Nope"}),
        (f"/day/dialog/holidays/{holiday.id}/delete", {"day": FREE_DAY}),
        (f"/day/dialog/no-teach-weeks/{week.id}", {"day": FREE_DAY, "week_number": "44", "title": "Nope"}),
        (f"/day/dialog/no-teach-weeks/{week.id}/delete", {"day": FREE_DAY}),
    ):
        response = client.post(path, data=data, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"

    assert (services.holidays.get_holiday(holiday.id).title, week.week_number) == ("Autumn break", 42)
