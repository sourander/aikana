"""Data-integrity tests of the SQLite schema: foreign keys with cascade, unique constraints, NOT NULL, STRICT
column types and integer primary keys, per ./tests.sdd.
"""

from datetime import date, time
from types import SimpleNamespace

import apsw
import pytest

from aikana.courses.repository_sqlite import SqliteCourseRepository
from aikana.holidays.repository_sqlite import SqliteHolidayRepository
from aikana.lessons.repository_sqlite import SqliteLessonRepository
from aikana.no_teach_weeks.repository_sqlite import SqliteNoTeachWeekRepository
from aikana.realizations.repository_sqlite import SqliteCourseRealizationRepository
from aikana.semester.repository_sqlite import SqliteSemesterRepository


def _build(db) -> SimpleNamespace:
    """Every repository, constructed in foreign-key dependency order the way main.py does it."""
    return SimpleNamespace(
        courses=SqliteCourseRepository(db),
        holidays=SqliteHolidayRepository(db),
        semesters=SqliteSemesterRepository(db),
        no_teach_weeks=SqliteNoTeachWeekRepository(db),
        realizations=SqliteCourseRealizationRepository(db),
        lessons=SqliteLessonRepository(db),
    )


def test_foreign_keys_are_enforced_on_the_connection(db):
    assert db.conn.execute("PRAGMA foreign_keys").fetchone() == (1,)


def test_every_table_is_strict(db):
    _build(db)

    for table in ("courses", "semesters", "course_realizations", "lessons", "holidays", "no_teach_weeks"):
        sql = db.conn.execute("select sql from sqlite_master where name = ?", (table,)).fetchone()[0]
        assert sql.rstrip().endswith("STRICT")


def test_ids_are_integer_primary_keys(db):
    _build(db)
    course = db.t.courses.insert({"name": "Machine Learning", "description": "", "ects_credits": 5})

    assert isinstance(course["id"], int)


def test_a_lesson_needs_an_existing_realization(db):
    repos = _build(db)

    with pytest.raises(apsw.ConstraintError):
        repos.lessons.add(999, date(2026, 9, 1), time(8, 0), time(10, 0), "Orphan", "")


def test_deleting_a_course_cascades_to_its_realizations_and_lessons(db):
    repos = _build(db)
    course = repos.courses.add("Machine Learning", "An introduction.", 5)
    semester = repos.semesters.add(2026, "fall")
    realization = repos.realizations.add(course.id, semester.id, "TTV24SP")
    lesson = repos.lessons.add(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")

    repos.courses.delete(course.id)

    assert repos.realizations.list_for_course(course.id) == []
    assert repos.lessons.get(lesson.id) is None


def test_deleting_a_realization_cascades_to_its_lessons(db):
    repos = _build(db)
    course = repos.courses.add("Machine Learning", "An introduction.", 5)
    semester = repos.semesters.add(2026, "fall")
    realization = repos.realizations.add(course.id, semester.id, "TTV24SP")
    lesson = repos.lessons.add(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")

    repos.realizations.delete(realization.id)

    assert repos.lessons.get(lesson.id) is None
    assert repos.courses.get(course.id) is not None


def test_deleting_a_semester_cascades_to_its_realizations_and_no_teach_weeks(db):
    repos = _build(db)
    course = repos.courses.add("Machine Learning", "An introduction.", 5)
    semester = repos.semesters.add(2026, "fall")
    realization = repos.realizations.add(course.id, semester.id, "TTV24SP")
    lesson = repos.lessons.add(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")
    week = repos.no_teach_weeks.add(semester.id, 42, date(2026, 10, 12), "No teaching week")

    # The semesters port has no delete operation yet, so the constraint is exercised through the table.
    db.t.semesters.delete(semester.id)

    assert repos.realizations.list_for_semester(semester.id) == []
    assert repos.lessons.get(lesson.id) is None
    assert repos.no_teach_weeks.get(week.id) is None


def test_a_semester_year_and_term_are_unique(db):
    semesters = SqliteSemesterRepository(db)
    semesters.add(2026, "fall")

    with pytest.raises(apsw.ConstraintError):
        semesters.add(2026, "fall")


def test_a_no_teach_week_is_unique_per_semester_and_week(db):
    _build(db)
    semesters = SqliteSemesterRepository(db)
    semester = semesters.add(2026, "fall")
    weeks = SqliteNoTeachWeekRepository(db)
    weeks.add(semester.id, 42, date(2026, 10, 12), "No teaching week")

    with pytest.raises(apsw.ConstraintError):
        weeks.add(semester.id, 42, date(2026, 10, 12), "Again")


def test_a_date_has_at_most_one_holiday(db):
    holidays = SqliteHolidayRepository(db)
    holidays.add(date(2026, 12, 6), "Independence Day")

    with pytest.raises(apsw.ConstraintError):
        holidays.add(date(2026, 12, 6), "Second Holiday")


def test_a_non_unique_holiday_date_index_is_replaced_on_startup(db):
    # An earlier database already holds a non-unique index of the same name, which the unique index must replace.
    db.t.holidays.create(
        columns={"id": int, "date": str, "title": str},
        pk="id",
        if_not_exists=True,
        not_null=["date", "title"],
        strict=True,
    )
    db.t.holidays.create_index(["date"], if_not_exists=True)

    SqliteHolidayRepository(db)

    assert db.conn.execute(
        "select sql from sqlite_master where name = 'idx_holidays_date'"
    ).fetchone()[0].upper().startswith("CREATE UNIQUE INDEX")


def test_a_realization_has_at_most_one_lesson_per_date(db):
    repos = _build(db)
    course = repos.courses.add("Machine Learning", "An introduction.", 5)
    semester = repos.semesters.add(2026, "fall")
    realization = repos.realizations.add(course.id, semester.id, "TTV24SP")
    repos.lessons.add(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")

    with pytest.raises(apsw.ConstraintError):
        repos.lessons.add(realization.id, date(2026, 9, 1), time(13, 0), time(15, 0), "Second", "")


def test_course_names_are_unique_ignoring_case(db):
    courses = SqliteCourseRepository(db)
    courses.add("Machine Learning", "An introduction.", 5)

    with pytest.raises(apsw.ConstraintError):
        courses.add("machine learning", "Another one.", 5)


def test_required_columns_reject_null(db):
    SqliteCourseRepository(db)

    with pytest.raises(apsw.ConstraintError):
        db.t.courses.insert({"name": None, "description": "", "ects_credits": 5})


def test_strict_tables_reject_a_wrong_column_type(db):
    SqliteCourseRepository(db)

    with pytest.raises(apsw.ConstraintError):
        db.t.courses.insert({"name": "Machine Learning", "description": "", "ects_credits": "five"})


def test_the_group_column_is_not_a_reserved_word(db):
    repos = _build(db)
    columns = [row[1] for row in db.conn.execute("PRAGMA table_info(course_realizations)")]

    assert "group_label" in columns
    assert "group" not in columns


def test_semesters_are_listed_in_calendar_order(db):
    semesters = SqliteSemesterRepository(db)
    fall = semesters.add(2026, "fall")
    spring = semesters.add(2026, "spring")

    # `spring` starts the year and `fall` ends it, so alphabetical `term` ordering would be wrong.
    assert [semester.id for semester in semesters.list()] == [spring.id, fall.id]
