"""In-process client tests of the app entry point, the semester routes and the wall planner, per ./tests.sdd."""

import re
from datetime import date, time, timedelta

from aikana.lessons.repository_sqlite import SqliteLessonRepository
from aikana.semester.services import PALETTE
from aikana.shared import dates
from conftest import AIKANA_PASSWD

# A date whose `today()` is fixed, so the time-dependent highlighting is testable.
FIXED_TODAY = date(2026, 10, 20)


def test_index_shows_no_semester_notice_to_a_visitor(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Aikana" in response.text
    assert "No Semester has been created yet." in response.text
    assert "Create Semester" not in response.text


def test_every_response_carries_baseline_security_headers(client):
    for path in ("/", "/courses", "/realizations", "/login"):
        response = client.get(path)
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "same-origin"


def test_pages_do_not_load_the_mutable_cdn_scripts(client):
    # The app never used surreal.js or css-scope-inline, and their mutable `@main` CDN refs would let
    # upstream commits run arbitrary JavaScript on every page.
    for path in ("/", "/courses", "/realizations", "/login"):
        response = client.get(path)
        assert "surreal" not in response.text
        assert "css-scope-inline" not in response.text
        assert "htmx" in response.text


def test_index_shows_the_create_semester_form_to_the_admin(admin_client):
    response = admin_client.get("/")

    assert response.status_code == 200
    assert "Create a Semester to get started." in response.text


def test_admin_creates_a_semester_through_the_form(admin_client, services):
    response = admin_client.post("/semesters", data={"year": "2026", "term": "fall"}, follow_redirects=False)

    assert response.status_code == 303
    semester_id = int(response.headers["location"].removeprefix("/?semester_id="))

    page = admin_client.get(f"/?semester_id={semester_id}")
    assert "Fall 2026" in page.text
    # A new Semester starts with its term's default NoTeachWeeks, per semester.sdd.
    assert [week.week_number for week in services.no_teach_weeks.list_no_teach_weeks(semester_id)] == [42, 51]


def test_create_semester_rejects_a_duplicate_with_a_validation_message(admin_client):
    admin_client.post("/semesters", data={"year": "2026", "term": "fall"}, follow_redirects=True)

    response = admin_client.post("/semesters", data={"year": "2026", "term": "fall"}, follow_redirects=True)

    assert "already exists" in response.text


def test_create_semester_rejects_a_crafted_term_with_a_validation_message(admin_client, services):
    # The form only offers spring/fall, so an invalid term arrives only through a crafted request.
    response = admin_client.post("/semesters", data={"year": "2026", "term": "summer"}, follow_redirects=True)

    assert response.status_code == 200
    assert "Term must be" in response.text
    assert services.semesters.list_semesters() == []


def test_visitor_cannot_create_a_semester(client, services):
    response = client.post("/semesters", data={"year": "2026", "term": "fall"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert services.semesters.list_semesters() == []


def test_visitor_cannot_open_the_semester_form(client):
    response = client.get("/semesters/new", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_new_semester_control_is_admin_only(client, services):
    services.semesters.create_semester(2026, "fall")

    visitor_page = client.get("/")
    assert "+ New Semester" not in visitor_page.text

    client.post("/login", data={"password": AIKANA_PASSWD}, follow_redirects=True)
    admin_page = client.get("/")
    assert "+ New Semester" in admin_page.text
    assert 'href="/semesters/new"' in admin_page.text


def test_index_falls_back_to_the_default_semester_for_an_unknown_id(client, services, monkeypatch):
    fall = services.semesters.create_semester(2026, "fall")
    services.semesters.create_semester(2027, "spring")
    monkeypatch.setattr(dates, "today", lambda: FIXED_TODAY)

    response = client.get("/?semester_id=no-such-semester")

    assert response.status_code == 200
    assert f'<option value="{fall.id}" selected>' in response.text


def test_realizations_view_renders_without_semesters(client):
    response = client.get("/realizations")

    assert response.status_code == 200
    assert "No Semester has been created yet." in response.text


def test_semester_selector_is_present_on_every_tab(client, services):
    services.semesters.create_semester(2026, "fall")
    services.semesters.create_semester(2027, "spring")

    for path in ("/", "/courses", "/realizations"):
        response = client.get(path)
        assert response.status_code == 200
        assert 'name="semester_id"' in response.text
        assert "Fall 2026" in response.text
        assert "Spring 2027" in response.text


def test_nav_links_carry_the_selected_semester(client, services):
    spring = services.semesters.create_semester(2027, "spring")

    response = client.get(f"/courses?semester_id={spring.id}")

    assert f'href="/?semester_id={spring.id}"' in response.text
    assert f'href="/courses?semester_id={spring.id}"' in response.text
    assert f'href="/realizations?semester_id={spring.id}"' in response.text
    assert f'<option value="{spring.id}" selected>' in response.text


def test_realizations_view_filters_by_the_selected_semester(client, services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    services.realizations.add_realization(course.id, fall.id, "TTV24SP")
    spring_realization = services.realizations.add_realization(course.id, spring.id, "TTV25SP")

    response = client.get(f"/realizations?semester_id={spring.id}")

    assert "TTV25SP" in response.text
    assert "TTV24SP" not in response.text
    assert f'<option value="{spring_realization.id}" selected>' in response.text


def test_realizations_view_infers_the_semester_from_a_realization(client, services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    services.realizations.add_realization(course.id, fall.id, "TTV24SP")
    spring_realization = services.realizations.add_realization(course.id, spring.id, "TTV25SP")

    response = client.get(f"/realizations?realization_id={spring_realization.id}")

    assert "TTV25SP" in response.text
    assert "TTV24SP" not in response.text
    assert f'<option value="{spring.id}" selected>' in response.text


def test_courses_page_ignores_the_selected_semester(client, services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")
    services.courses.add_course("Machine Learning", "An introduction.", 5)

    fall_page = client.get(f"/courses?semester_id={fall.id}")
    spring_page = client.get(f"/courses?semester_id={spring.id}")

    assert "Machine Learning" in fall_page.text
    assert "Machine Learning" in spring_page.text
    assert f'<option value="{fall.id}" selected>' in fall_page.text
    assert f'<option value="{spring.id}" selected>' in spring_page.text


# Wall planner rendering


def test_wall_planner_renders_one_column_per_month(client, services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")

    assert "repeat(5, 1fr)" in client.get(f"/?semester_id={fall.id}").text
    assert "repeat(6, 1fr)" in client.get(f"/?semester_id={spring.id}").text


def test_wall_planner_grid_scrolls_instead_of_clipping(client, services):
    fall = services.semesters.create_semester(2026, "fall")

    text = client.get(f"/?semester_id={fall.id}").text

    grid = text[text.index('id="semester-grid"') : text.index('id="semester-grid"') + 200]

    assert "overflow:auto;" in grid
    assert "overflow:hidden;" not in grid


def test_wall_planner_day_rows_and_month_columns_have_a_minimum_width(client, services):
    fall = services.semesters.create_semester(2026, "fall")

    text = client.get(f"/?semester_id={fall.id}").text

    # A month column never gets narrower than a day row, so a column's rows cannot overlap the next column.
    assert "display:flex; flex-direction:column; min-width:8rem;" in text

    vm = services.semesters.build_semester_view_model(fall)
    assert text.count("flex:1; min-width:8rem;") == sum(len(month.days) for month in vm.months)


def test_wall_planner_shows_each_spanned_month_as_a_column(client, services):
    fall = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/?semester_id={fall.id}")

    for label in ("August 2026", "September 2026", "October 2026", "November 2026", "December 2026"):
        assert label in response.text


def _weekend_days(start: date, end: date) -> int:
    return sum(
        1 for offset in range((end - start).days + 1) if (start + timedelta(days=offset)).weekday() >= 5
    )


def _clear_holidays(services, semester, start, end):
    """Removes the Semester's pre-populated public holidays, so a test can assert the wall planner without them."""
    for holiday in services.holidays.list_holidays_for_range(start, end):
        services.holidays.delete_holiday(holiday.id)


def test_weekend_rows_are_tinted_even_without_holidays(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    for week in services.no_teach_weeks.list_no_teach_weeks(semester.id):
        services.no_teach_weeks.delete_no_teach_week(week.id)
    _clear_holidays(services, semester, date(2026, 8, 1), date(2026, 12, 31))

    response = client.get(f"/?semester_id={semester.id}")

    assert response.text.count("bg-red-50") == _weekend_days(date(2026, 8, 1), date(2026, 12, 31))


def test_a_holiday_row_is_tinted_and_titled(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    for week in services.no_teach_weeks.list_no_teach_weeks(semester.id):
        services.no_teach_weeks.delete_no_teach_week(week.id)
    _clear_holidays(services, semester, date(2026, 8, 1), date(2026, 12, 31))
    # 2026-09-07 is a Monday, so the row's tint cannot come from the weekend rule.
    services.holidays.add_holiday(date(2026, 9, 7), "Autumn break")

    response = client.get(f"/?semester_id={semester.id}")

    assert response.text.count("bg-red-50") == _weekend_days(date(2026, 8, 1), date(2026, 12, 31)) + 1
    assert "Autumn break" in response.text


def test_a_lesson_square_is_a_tooltip_anchor_and_the_grid_its_area(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    services.lessons.add_lesson(realization.id, date(2026, 10, 20), time(8, 0), time(10, 0), "Intro", "")

    response = client.get(f"/?semester_id={semester.id}")

    assert 'data-tip-area=""' in response.text
    assert 'data-tip=""' in response.text


# Week numbers


def _week_gutter_numbers(html: str) -> list[str]:
    """The content of every day row's week-number gutter, in render order: a number on a Monday, empty elsewhere."""
    return re.findall(r'<span class="w-6 text-xs text-gray-300 text-center shrink-0">(\d*)</span>', html)


def test_wall_planner_numbers_each_monday_of_the_semester(client, services):
    semester = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/?semester_id={semester.id}")

    numbers = _week_gutter_numbers(response.text)
    # The fall Semester starts on a Saturday, so its own first Monday is 2026-08-03 and its last one 2026-12-28.
    mondays = [date(2026, 8, 3) + timedelta(days=7 * offset) for offset in range(22)]
    assert [int(number) for number in numbers if number] == [
        monday.isocalendar().week for monday in mondays
    ]


def test_wall_planner_reserves_the_week_number_gutter_on_every_row(client, services):
    semester = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/?semester_id={semester.id}")

    # Every one of the Semester's 153 days carries the gutter, so the weekday labels stay aligned down a column.
    assert len(_week_gutter_numbers(response.text)) == 153


# Legend bar


def _legend_html(html: str) -> str:
    """The legend bar's markup, from its own opening element to the end of the page."""
    return html[html.index('id="semester-legend"') :]


def test_wall_planner_legend_sits_below_the_grid(client, services):
    semester = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/?semester_id={semester.id}")

    assert response.text.index('id="semester-grid"') < response.text.index('id="semester-legend"')


def test_wall_planner_legend_names_every_realization_in_its_own_color(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    machine_learning = services.courses.add_course("Machine Learning", "An introduction.", 5)
    databases = services.courses.add_course("Databases", "Relational modelling.", 5)
    services.realizations.add_realization(machine_learning.id, semester.id, "TTV24SP")
    services.realizations.add_realization(databases.id, semester.id, "TTV24SP2")

    response = client.get(f"/?semester_id={semester.id}")

    legend = _legend_html(response.text)
    assert "Machine Learning (TTV24SP)" in legend
    assert "Databases (TTV24SP2)" in legend
    # The first realization of the Semester takes the palette's first color, the second one its second color.
    assert _legend_chip(PALETTE[0]) in legend
    assert _legend_chip(PALETTE[1]) in legend


def _legend_chip(color: str) -> str:
    return f'<div class="w-3 h-3 rounded-sm shrink-0" style="background-color:{color};"></div>'


def test_wall_planner_legend_marks_a_square_a_lesson_and_a_circle_a_deadline(client, services):
    semester = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/?semester_id={semester.id}")

    legend = _legend_html(response.text)
    assert '<div class="w-3 h-3 rounded-sm bg-gray-400 shrink-0"></div>' in legend
    assert '<div class="w-3 h-3 rounded-full bg-gray-400 opacity-50 shrink-0"></div>' in legend
    assert ">Lesson</span>" in legend
    assert ">Deadline</span>" in legend


def test_wall_planner_shows_the_two_markers_when_the_semester_has_no_realization(client, services):
    semester = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/?semester_id={semester.id}")

    legend = _legend_html(response.text)
    assert ">Lesson</span>" in legend
    assert ">Deadline</span>" in legend


def test_wall_planner_shows_the_legend_to_a_visitor(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    services.realizations.add_realization(course.id, semester.id, "TTV24SP")

    response = client.get(f"/?semester_id={semester.id}")

    assert "Machine Learning (TTV24SP)" in _legend_html(response.text)


# NoTeachWeeks


def test_wall_planner_tints_and_titles_each_weekday_of_a_no_teach_week(client, services):
    semester = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/?semester_id={semester.id}")

    assert response.status_code == 200
    # Week 42 (2026-10-12 to 10-16) and week 51 (2026-12-14 to 12-18) each contribute five titled rows, each row
    # carrying its own break's title.
    assert response.text.count("Syysvapaat") == 5
    assert response.text.count("Jouluvapaat") == 5


def test_wall_planner_hides_lesson_squares_on_a_no_teach_week(client, db, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    # Inserted straight through the repository: @LessonService.add_lesson rejects a date inside a NoTeachWeek,
    # but rows already holding a stale Lesson must still render blocked.
    SqliteLessonRepository(db).add(realization.id, date(2026, 10, 13), time(8, 0), time(10, 0), "Inside", "")

    response = client.get(f"/?semester_id={semester.id}")

    assert "Inside" not in response.text
    assert "Syysvapaat" in response.text


def test_realizations_view_shows_a_no_teach_week_as_a_single_line(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    services.lessons.add_lesson(
        realization.id, date(2026, 9, 16), time(8, 0), time(10, 0), "Before the week", ""
    )

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    assert "Syysvapaat" in response.text
    # The week's row reads its own title, so no generic label is added in front of it.
    assert "No teaching week" not in response.text
    assert "Before the week" in response.text


def test_realizations_view_shows_a_custom_no_teach_week_title_alone(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)
    services.no_teach_weeks.update_no_teach_week(week.id, week.week_number, "Staff training")

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.text.count("Staff training") == 1
    assert "No teaching week" not in response.text


# Current day and current week highlighting


def test_wall_planner_renders_a_green_bar_on_today(client, services, monkeypatch):
    semester = services.semesters.create_semester(2026, "fall")
    monkeypatch.setattr(dates, "today", lambda: FIXED_TODAY)

    response = client.get(f"/?semester_id={semester.id}")

    assert response.status_code == 200
    assert response.text.count("border-l-green-500") == 1


def test_wall_planner_renders_no_green_bar_when_today_is_outside_the_semester(client, services, monkeypatch):
    semester = services.semesters.create_semester(2027, "spring")
    monkeypatch.setattr(dates, "today", lambda: FIXED_TODAY)

    response = client.get(f"/?semester_id={semester.id}")

    assert response.status_code == 200
    assert "border-l-green-500" not in response.text


def test_realizations_view_renders_a_green_bar_on_the_current_week(client, services, monkeypatch):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    monkeypatch.setattr(dates, "today", lambda: FIXED_TODAY)

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    assert response.text.count("border-l-green-500") == 1


def test_realizations_view_renders_week_date_ranges_in_the_european_form(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    # Fall 2026 starts Saturday 2026-08-01, so its first table week runs Monday 2026-07-27 to Sunday 2026-08-02.
    assert "27.7.2026 \u2013 2.8.2026" in response.text
