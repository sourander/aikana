"""Service-layer validation tests against a temporary database, per ./tests.sdd."""

from datetime import date, time

import pytest

from aikana.courses.domain import Course
from aikana.courses.services import (
    DuplicateCourseError,
    InvalidCourseError,
    UnknownCourseError as UnknownCourseIdError,
)
from aikana.holidays.services import DuplicateHolidayError, InvalidHolidayError, UnknownHolidayError
from aikana.lessons.services import InvalidLessonError, UnknownLessonError, UnknownRealizationError
from aikana.no_teach_weeks.services import (
    DuplicateNoTeachWeekError,
    InvalidNoTeachWeekError,
    UnknownNoTeachWeekError,
)
from aikana.no_teach_weeks.services import UnknownSemesterError as UnknownNoTeachWeekSemesterIdError
from aikana.realizations.services import (
    InvalidRealizationError,
    UnknownCourseError,
    UnknownSemesterError,
)
from aikana.semester.services import DuplicateSemesterError, InvalidTermError
from aikana.semester.services import UnknownSemesterError as UnknownSemesterIdError


@pytest.fixture
def realization(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    semester = services.semesters.create_semester(2026, "fall")
    return services.realizations.add_realization(course.id, semester.id, "TTV24SP")


# Courses


def test_add_course_rejects_an_empty_name(services):
    with pytest.raises(InvalidCourseError):
        services.courses.add_course("   ", "An introduction.", 5)


def test_add_course_rejects_a_duplicate_name_ignoring_case_and_whitespace(services):
    services.courses.add_course("Machine Learning", "An introduction.", 5)
    with pytest.raises(DuplicateCourseError):
        services.courses.add_course("  machine learning ", "Another one.", 5)


def test_update_course_rejects_an_unknown_id(services):
    with pytest.raises(UnknownCourseIdError):
        services.courses.update_course("no-such-course", "Machine Learning", "An introduction.", 5)


def test_update_course_rejects_an_empty_name(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    with pytest.raises(InvalidCourseError):
        services.courses.update_course(course.id, "   ", "An introduction.", 5)


def test_update_course_rejects_a_duplicate_name_ignoring_case_and_whitespace(services):
    services.courses.add_course("Machine Learning", "An introduction.", 5)
    course = services.courses.add_course("Databases", "Another one.", 5)
    with pytest.raises(DuplicateCourseError):
        services.courses.update_course(course.id, "  machine learning ", "Another one.", 5)


def test_update_course_ignores_itself_when_looking_for_a_duplicate(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    updated = services.courses.update_course(course.id, "  machine LEARNING ", "An introduction.", 5)
    assert updated.name == "machine LEARNING"
    assert [listed.id for listed in services.courses.list_courses()] == [course.id]


def test_update_course_changes_the_stored_values(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    updated = services.courses.update_course(course.id, "Deep Learning", "Advanced.", 8)
    assert updated == Course(id=course.id, name="Deep Learning", description="Advanced.", ects_credits=8)
    assert services.courses.get_course(course.id) == updated


# Semesters


def test_create_semester_rejects_a_duplicate_year_term_combination(services):
    services.semesters.create_semester(2026, "fall")
    with pytest.raises(DuplicateSemesterError):
        services.semesters.create_semester(2026, "fall")


def test_create_semester_rejects_an_invalid_term(services):
    with pytest.raises(InvalidTermError):
        services.semesters.create_semester(2026, "summer")


def test_delete_semester_removes_it(services):
    semester = services.semesters.create_semester(2026, "fall")
    services.semesters.delete_semester(semester.id)
    assert services.semesters.list_semesters() == []


def test_delete_semester_rejects_an_unknown_id(services):
    with pytest.raises(UnknownSemesterIdError):
        services.semesters.delete_semester("no-such-semester")


def test_creating_a_fall_semester_creates_its_default_no_teach_weeks(services):
    semester = services.semesters.create_semester(2026, "fall")
    weeks = services.no_teach_weeks.list_no_teach_weeks(semester.id)
    assert [(week.week_number, week.title) for week in weeks] == [(42, "Syysvapaat"), (51, "Jouluvapaat")]


def test_creating_a_spring_semester_creates_its_default_no_teach_weeks(services):
    semester = services.semesters.create_semester(2026, "spring")
    weeks = services.no_teach_weeks.list_no_teach_weeks(semester.id)
    assert [(week.week_number, week.title) for week in weeks] == [
        (1, "Tammivapaat"),
        (10, "Talvivapaat"),
        (22, "Kesävapaat"),
    ]


# CourseRealizations


def test_add_realization_rejects_an_unknown_course(services):
    semester = services.semesters.create_semester(2026, "fall")
    with pytest.raises(UnknownCourseError):
        services.realizations.add_realization("no-such-course", semester.id, "TTV24SP")


def test_add_realization_rejects_an_unknown_semester(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    with pytest.raises(UnknownSemesterError):
        services.realizations.add_realization(course.id, "no-such-semester", "TTV24SP")


def test_add_realization_rejects_an_empty_group(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    semester = services.semesters.create_semester(2026, "fall")
    with pytest.raises(InvalidRealizationError):
        services.realizations.add_realization(course.id, semester.id, " ")


# Lessons


def test_add_lesson_rejects_an_unknown_realization(services):
    with pytest.raises(UnknownRealizationError):
        services.lessons.add_lesson("no-such-realization", date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")


def test_add_lesson_rejects_an_empty_topic(services, realization):
    with pytest.raises(InvalidLessonError):
        services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "", "")


def test_add_lesson_rejects_an_end_time_not_after_the_start_time(services, realization):
    with pytest.raises(InvalidLessonError):
        services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(10, 0), time(10, 0), "Intro", "")


def test_add_lesson_stores_a_valid_lesson(services, realization):
    lesson = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "Room B")
    assert services.lessons.list_lessons_for_realization(realization.id) == [lesson]


def test_lessons_are_ordered_by_date_then_start_time(services, realization):
    second_day = services.lessons.add_lesson(realization.id, date(2026, 9, 2), time(8, 0), time(10, 0), "Later day", "")
    # A Lesson is unique per date and CourseRealization, so a same-day pair comes from two realizations; the
    # listing still has to read them in chronological order.
    other_course = services.courses.add_course("Databases", "Storage and queries.", 5)
    other = services.realizations.add_realization(other_course.id, realization.semester_id, "TTV24SP")
    late = services.lessons.add_lesson(other.id, date(2026, 9, 1), time(13, 0), time(15, 0), "Late", "")
    early = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Early", "")
    assert services.lessons.list_lessons_for_range(date(2026, 9, 1), date(2026, 9, 2)) == [early, late, second_day]


def test_add_lesson_rejects_a_second_lesson_on_the_same_day(services, realization):
    services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    with pytest.raises(InvalidLessonError):
        services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(13, 0), time(15, 0), "Second", "")


def test_a_second_lesson_on_another_day_of_the_same_realization_is_accepted(services, realization):
    first = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    second = services.lessons.add_lesson(realization.id, date(2026, 9, 2), time(8, 0), time(10, 0), "Later day", "")
    assert services.lessons.list_lessons_for_realization(realization.id) == [first, second]


def test_the_same_day_of_another_realization_is_free(services, realization):
    services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    other_course = services.courses.add_course("Databases", "Storage and queries.", 5)
    other = services.realizations.add_realization(
        other_course.id, services.semesters.get_default_semester().id, "TTV24SP"
    )
    lesson = services.lessons.add_lesson(other.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    assert services.lessons.list_lessons_for_realization(other.id) == [lesson]


def test_update_lesson_changes_the_stored_values(services, realization):
    lesson = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "Room B")

    updated = services.lessons.update_lesson(
        lesson.id, date(2026, 9, 3), time(12, 0), time(14, 0), "Regression", "Room A"
    )

    assert updated.date == date(2026, 9, 3)
    assert updated.start_time == time(12, 0)
    assert updated.end_time == time(14, 0)
    assert updated.topic == "Regression"
    assert updated.notes == "Room A"
    # The CourseRealization is never changed by an edit, per ./lessons.sdd.
    assert updated.course_realization_id == realization.id


def test_update_lesson_rejects_an_unknown_id(services):
    with pytest.raises(UnknownLessonError):
        services.lessons.update_lesson(
            "no-such-lesson", date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", ""
        )


def test_update_lesson_rejects_an_empty_topic(services, realization):
    lesson = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    with pytest.raises(InvalidLessonError):
        services.lessons.update_lesson(lesson.id, date(2026, 9, 1), time(8, 0), time(10, 0), " ", "")
    assert services.lessons.get_lesson(lesson.id).topic == "Intro"


def test_update_lesson_rejects_an_end_time_not_after_the_start_time(services, realization):
    lesson = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    with pytest.raises(InvalidLessonError):
        services.lessons.update_lesson(lesson.id, date(2026, 9, 1), time(10, 0), time(10, 0), "Intro", "")


def test_update_lesson_rejects_a_date_inside_a_no_teach_week(services, realization):
    lesson = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    with pytest.raises(InvalidLessonError):
        services.lessons.update_lesson(lesson.id, date(2026, 10, 13), time(8, 0), time(10, 0), "Intro", "")


def test_update_lesson_rejects_a_day_another_lesson_already_has(services, realization):
    kept = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Kept", "")
    moved = services.lessons.add_lesson(realization.id, date(2026, 9, 2), time(8, 0), time(10, 0), "Moved", "")
    with pytest.raises(InvalidLessonError):
        services.lessons.update_lesson(moved.id, date(2026, 9, 1), time(12, 0), time(14, 0), "Moved", "")
    assert [lesson.id for lesson in services.lessons.list_lessons_for_realization(realization.id)] == [kept.id, moved.id]


def test_update_lesson_ignores_its_own_day(services, realization):
    lesson = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    updated = services.lessons.update_lesson(lesson.id, date(2026, 9, 1), time(9, 0), time(11, 0), "Intro", "")
    assert updated.start_time == time(9, 0)


def test_delete_lesson_removes_only_that_lesson(services, realization):
    removed = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Gone", "")
    kept = services.lessons.add_lesson(realization.id, date(2026, 9, 2), time(8, 0), time(10, 0), "Kept", "")

    services.lessons.delete_lesson(removed.id)

    assert services.lessons.list_lessons_for_realization(realization.id) == [kept]


def test_delete_lesson_rejects_an_unknown_id(services, realization):
    with pytest.raises(UnknownLessonError):
        services.lessons.delete_lesson("no-such-lesson")


def test_add_lesson_rejects_a_date_inside_a_no_teach_week(services, realization):
    # The `realization` fixture's fall-2026 Semester blocks weeks 42 and 51, Monday to Friday.
    with pytest.raises(InvalidLessonError):
        services.lessons.add_lesson(realization.id, date(2026, 10, 13), time(8, 0), time(10, 0), "Intro", "")


def test_add_lesson_accepts_a_saturday_inside_a_no_teach_week(services, realization):
    lesson = services.lessons.add_lesson(realization.id, date(2026, 10, 17), time(8, 0), time(10, 0), "Extra", "")
    assert services.lessons.list_lessons_for_realization(realization.id) == [lesson]


# Holidays


def test_add_holiday_rejects_an_empty_title(services):
    with pytest.raises(InvalidHolidayError):
        services.holidays.add_holiday(date(2026, 12, 6), "  ")


def test_add_holiday_rejects_a_date_that_already_has_one(services):
    services.holidays.add_holiday(date(2026, 12, 6), "Independence Day")

    with pytest.raises(DuplicateHolidayError):
        services.holidays.add_holiday(date(2026, 12, 6), "Second Holiday")

    stored = services.holidays.list_holidays_for_range(date(2026, 12, 6), date(2026, 12, 6))
    assert [(holiday.date, holiday.title) for holiday in stored] == [(date(2026, 12, 6), "Independence Day")]


def test_update_holiday_keeps_its_own_date_and_rejects_another_holidays(services):
    holiday = services.holidays.add_holiday(date(2026, 12, 6), "Independence Day")
    other = services.holidays.add_holiday(date(2026, 12, 24), "Christmas Eve")

    updated = services.holidays.update_holiday(holiday.id, date(2026, 12, 6), "Retitled")
    assert (updated.date, updated.title) == (date(2026, 12, 6), "Retitled")

    with pytest.raises(DuplicateHolidayError):
        services.holidays.update_holiday(holiday.id, date(2026, 12, 24), "Christmas Eve")
    assert services.holidays.get_holiday(other.id).title == "Christmas Eve"


def test_update_holiday_changes_the_stored_values(services):
    holiday = services.holidays.add_holiday(date(2026, 12, 6), "Independence Day")
    updated = services.holidays.update_holiday(holiday.id, date(2026, 12, 24), "Christmas Eve")
    assert (updated.date, updated.title) == (date(2026, 12, 24), "Christmas Eve")
    assert services.holidays.get_holiday(holiday.id) == updated


def test_update_holiday_rejects_an_unknown_id(services):
    with pytest.raises(UnknownHolidayError):
        services.holidays.update_holiday("no-such-holiday", date(2026, 12, 6), "Independence Day")


def test_update_holiday_rejects_an_empty_title(services):
    holiday = services.holidays.add_holiday(date(2026, 12, 6), "Independence Day")
    with pytest.raises(InvalidHolidayError):
        services.holidays.update_holiday(holiday.id, date(2026, 12, 6), "  ")
    assert services.holidays.get_holiday(holiday.id).title == "Independence Day"


def test_delete_holiday_removes_it(services):
    holiday = services.holidays.add_holiday(date(2026, 12, 6), "Independence Day")
    services.holidays.delete_holiday(holiday.id)
    assert services.holidays.list_holidays_for_range(date(2026, 12, 1), date(2026, 12, 31)) == []


def test_delete_holiday_rejects_an_unknown_id(services):
    with pytest.raises(UnknownHolidayError):
        services.holidays.delete_holiday("no-such-holiday")


def test_create_defaults_for_range_stores_the_finnish_public_holidays_of_the_range(services):
    added = services.holidays.create_defaults_for_range(date(2026, 12, 1), date(2026, 12, 31))

    assert [(holiday.date, holiday.title) for holiday in added] == [
        (date(2026, 12, 6), "Itsenäisyyspäivä"),
        (date(2026, 12, 24), "Jouluaatto"),
        (date(2026, 12, 25), "Joulupäivä"),
        (date(2026, 12, 26), "Tapaninpäivä"),
    ]


def test_create_defaults_for_range_covers_each_year_the_range_touches(services):
    services.holidays.create_defaults_for_range(date(2025, 12, 1), date(2026, 1, 31))

    titles = {
        holiday.date: holiday.title
        for holiday in services.holidays.list_holidays_for_range(date(2025, 12, 1), date(2026, 1, 31))
    }
    assert titles[date(2026, 1, 1)] == "Uudenvuodenpäivä"
    assert titles[date(2026, 1, 6)] == "Loppiainen"


def test_create_defaults_for_range_skips_a_date_that_already_has_a_holiday(services):
    services.holidays.add_holiday(date(2026, 12, 6), "School closed")

    added = services.holidays.create_defaults_for_range(date(2026, 12, 1), date(2026, 12, 31))

    assert all(holiday.date != date(2026, 12, 6) for holiday in added)
    stored = services.holidays.list_holidays_for_range(date(2026, 12, 6), date(2026, 12, 6))
    assert [(holiday.date, holiday.title) for holiday in stored] == [(date(2026, 12, 6), "School closed")]


def test_create_defaults_for_range_adds_nothing_when_the_range_already_holds_them(services):
    services.holidays.create_defaults_for_range(date(2026, 12, 1), date(2026, 12, 31))

    assert services.holidays.create_defaults_for_range(date(2026, 12, 1), date(2026, 12, 31)) == []


def test_creating_a_fall_semester_pre_populates_the_public_holidays_of_its_period(services):
    semester = services.semesters.create_semester(2026, "fall")

    titles = {
        holiday.date: holiday.title
        for holiday in services.holidays.list_holidays_for_range(date(2026, 8, 1), date(2026, 12, 31))
    }
    # A fall Semester never reaches a Semester's January or Easter holidays.
    assert titles[date(2026, 10, 31)] == "Pyhäinpäivä"
    assert titles[date(2026, 12, 24)] == "Jouluaatto"
    assert services.holidays.list_holidays_for_range(date(2026, 1, 1), date(2026, 7, 31)) == []


def test_creating_a_spring_semester_pre_populates_the_public_holidays_of_its_period(services):
    services.semesters.create_semester(2027, "spring")

    titles = {
        holiday.date: holiday.title
        for holiday in services.holidays.list_holidays_for_range(date(2027, 1, 1), date(2027, 6, 30))
    }
    assert titles[date(2027, 1, 6)] == "Loppiainen"
    # Juhannusaatto is the Friday within 19 June to 25 June, so it falls on 2027-06-25.
    assert titles[date(2027, 6, 25)] == "Juhannusaatto"
    assert titles[date(2027, 6, 26)] == "Juhannuspäivä"
    assert services.holidays.list_holidays_for_range(date(2027, 7, 1), date(2027, 12, 31)) == []


def test_two_semesters_of_one_academic_year_never_compete_for_the_same_holiday(services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")
    assert (fall.year, spring.year) == (2026, 2027)

    # Re-running the pre-population for either period changes nothing.
    assert services.holidays.create_defaults_for_range(date(2026, 8, 1), date(2026, 12, 31)) == []
    assert services.holidays.create_defaults_for_range(date(2027, 1, 1), date(2027, 6, 30)) == []


# NoTeachWeeks


def test_add_no_teach_week_rejects_an_unknown_semester(services):
    with pytest.raises(UnknownNoTeachWeekSemesterIdError):
        services.no_teach_weeks.add_no_teach_week("no-such-semester", 5, "Study week")


def test_add_no_teach_week_rejects_a_week_the_year_does_not_have(services):
    semester = services.semesters.create_semester(2027, "spring")  # 2027 is a 52-week ISO year.
    with pytest.raises(InvalidNoTeachWeekError):
        services.no_teach_weeks.add_no_teach_week(semester.id, 53, "Study week")


def test_add_no_teach_week_rejects_an_empty_title(services):
    semester = services.semesters.create_semester(2026, "fall")
    with pytest.raises(InvalidNoTeachWeekError):
        services.no_teach_weeks.add_no_teach_week(semester.id, 5, "   ")


def test_add_no_teach_week_rejects_a_week_already_blocked_in_the_same_semester(services):
    semester = services.semesters.create_semester(2026, "fall")
    with pytest.raises(DuplicateNoTeachWeekError):
        services.no_teach_weeks.add_no_teach_week(semester.id, 42, "Study week")


def test_add_no_teach_week_resolves_the_monday_of_the_week(services):
    semester = services.semesters.create_semester(2026, "fall")
    week = services.no_teach_weeks.add_no_teach_week(semester.id, 5, "Study week")
    assert week.week_start == date(2026, 1, 26)


def test_create_defaults_adds_nothing_when_the_defaults_already_exist(services):
    semester = services.semesters.create_semester(2026, "fall")
    assert services.no_teach_weeks.create_defaults_for_semester(semester.id) == []
    assert [week.week_number for week in services.no_teach_weeks.list_no_teach_weeks(semester.id)] == [42, 51]


def test_titles_by_teaching_day_covers_the_weekdays_only(services):
    semester = services.semesters.create_semester(2026, "fall")
    for week in services.no_teach_weeks.list_no_teach_weeks(semester.id):
        services.no_teach_weeks.delete_no_teach_week(week.id)
    services.no_teach_weeks.add_no_teach_week(semester.id, 42, "Study week")

    titles = services.no_teach_weeks.titles_by_teaching_day(semester.id)

    # Week 42 of 2026 runs Monday 2026-10-12 to Sunday 2026-10-18.
    assert titles == {date(2026, 10, day): "Study week" for day in range(12, 17)}
    assert date(2026, 10, 17) not in titles
    assert date(2026, 10, 18) not in titles


def test_update_no_teach_week_rejects_an_unknown_id(services):
    with pytest.raises(UnknownNoTeachWeekError):
        services.no_teach_weeks.update_no_teach_week("no-such-week", 5, "Study week")


def test_update_no_teach_week_changes_the_stored_values(services):
    semester = services.semesters.create_semester(2026, "fall")
    week = services.no_teach_weeks.add_no_teach_week(semester.id, 5, "Study week")
    updated = services.no_teach_weeks.update_no_teach_week(week.id, 6, "Autumn break")
    assert (updated.week_number, updated.title, updated.week_start) == (6, "Autumn break", date(2026, 2, 2))
    assert services.no_teach_weeks.get_no_teach_week(week.id) == updated


def test_update_no_teach_week_ignores_itself_when_looking_for_a_duplicate(services):
    semester = services.semesters.create_semester(2026, "fall")
    week = services.no_teach_weeks.add_no_teach_week(semester.id, 5, "Study week")
    assert services.no_teach_weeks.update_no_teach_week(week.id, 5, "Renamed").title == "Renamed"


def test_update_no_teach_week_rejects_another_week_number_already_blocked(services):
    semester = services.semesters.create_semester(2026, "fall")
    week = services.no_teach_weeks.add_no_teach_week(semester.id, 5, "Study week")
    with pytest.raises(DuplicateNoTeachWeekError):
        services.no_teach_weeks.update_no_teach_week(week.id, 42, "Study week")


def test_delete_no_teach_week_removes_it_from_the_semester(services):
    semester = services.semesters.create_semester(2026, "fall")
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)
    services.no_teach_weeks.delete_no_teach_week(week.id)
    assert [w.week_number for w in services.no_teach_weeks.list_no_teach_weeks(semester.id)] == [51]


def test_delete_no_teach_week_rejects_an_unknown_id(services):
    with pytest.raises(UnknownNoTeachWeekError):
        services.no_teach_weeks.delete_no_teach_week("no-such-week")


# Current day and current week


def test_semester_view_model_marks_only_today(services):
    semester = services.semesters.create_semester(2026, "fall")

    view_model = services.semesters.build_semester_view_model(semester, today=date(2026, 10, 20))

    marked = [day.day for month in view_model.months for day in month.days if day.is_today]
    assert marked == [date(2026, 10, 20)]


def test_semester_view_model_marks_no_day_when_today_is_outside_the_semester(services):
    semester = services.semesters.create_semester(2026, "fall")

    view_model = services.semesters.build_semester_view_model(semester, today=date(2027, 1, 15))

    assert not any(day.is_today for month in view_model.months for day in month.days)


def test_realization_view_model_marks_the_week_containing_today(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    semester = services.semesters.create_semester(2026, "fall")
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")

    view_model = services.realizations.build_realization_view_model(realization.id, today=date(2026, 10, 20))

    marked = [(week.start, week.end) for week in view_model.weeks if week.is_current_week]
    assert marked == [(date(2026, 10, 19), date(2026, 10, 25))]


def test_realization_view_model_marks_no_week_when_today_is_outside_the_semester(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    semester = services.semesters.create_semester(2026, "fall")
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")

    view_model = services.realizations.build_realization_view_model(realization.id, today=date(2027, 1, 15))

    assert not any(week.is_current_week for week in view_model.weeks)
