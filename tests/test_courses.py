"""In-process client tests of the courses page, its create form and its edit and delete dialogs, per ./tests.sdd.
"""

from datetime import date, time


def _create_course(client, name="Machine Learning", description="An introduction.", ects_credits=5):
    return client.post(
        "/courses",
        data={"name": name, "description": description, "ects_credits": str(ects_credits)},
        follow_redirects=True,
    )


def test_empty_courses_page_shows_the_create_form_to_the_admin(admin_client):
    response = admin_client.get("/courses")

    assert response.status_code == 200
    assert "Create a Course to get started." in response.text
    assert "Create Course" in response.text


def test_empty_courses_page_shows_a_notice_to_a_visitor(client):
    response = client.get("/courses")

    assert response.status_code == 200
    assert "No Course has been created yet." in response.text
    assert "Create Course" not in response.text


def test_courses_new_renders_the_create_form_to_the_admin(admin_client):
    response = admin_client.get("/courses/new")

    assert response.status_code == 200
    assert 'action="/courses"' in response.text
    assert "Create Course" in response.text


def test_visitor_cannot_open_the_create_course_form(client):
    response = client.get("/courses/new", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_admin_creates_a_course(admin_client):
    response = _create_course(admin_client)

    assert response.status_code == 200
    assert "Machine Learning" in response.text
    assert "An introduction." in response.text
    assert "5 ECTS" in response.text
    assert "+ New Course" in response.text


def test_create_course_rejects_an_empty_name(admin_client, course_service):
    response = _create_course(admin_client, name="   ")

    assert "A Course needs a non-empty name." in response.text
    assert course_service.list_courses() == []


def test_create_course_rejects_a_duplicate_name(admin_client, course_service):
    _create_course(admin_client)
    response = _create_course(admin_client, name="  machine learning ")

    assert "already exists" in response.text
    assert len(course_service.list_courses()) == 1


def test_courses_page_lists_courses_for_a_visitor_without_editing_affordances(admin_client):
    _create_course(admin_client)
    admin_client.post("/logout", follow_redirects=True)

    response = admin_client.get("/courses")

    assert "Machine Learning" in response.text
    assert "+ New Course" not in response.text
    assert "<dialog" not in response.text


def test_admin_courses_page_has_a_prefilled_edit_dialog(admin_client, course_service):
    _create_course(admin_client)
    course = course_service.list_courses()[0]

    response = admin_client.get("/courses")

    assert f'id="course-dialog-{course.id}"' in response.text
    assert f'action="/courses/{course.id}"' in response.text
    assert 'value="Machine Learning"' in response.text


def test_admin_updates_a_course(admin_client, course_service):
    _create_course(admin_client)
    course = course_service.list_courses()[0]

    response = admin_client.post(
        f"/courses/{course.id}",
        data={"name": "Deep Learning", "description": "Advanced.", "ects_credits": "8"},
        follow_redirects=True,
    )

    assert "Deep Learning" in response.text
    assert "Advanced." in response.text
    assert "8 ECTS" in response.text
    assert "Machine Learning" not in response.text


def test_admin_can_rename_a_course_to_its_own_name(admin_client, course_service):
    # The Course being edited is ignored when looking for a duplicate, per courses.sdd.
    _create_course(admin_client)
    course = course_service.list_courses()[0]

    response = admin_client.post(
        f"/courses/{course.id}",
        data={"name": "  machine LEARNING ", "description": "An introduction.", "ects_credits": "5"},
        follow_redirects=True,
    )

    assert "already exists" not in response.text
    assert "machine LEARNING" in response.text
    assert len(course_service.list_courses()) == 1


def test_update_course_rejects_a_duplicate_name(admin_client, course_service):
    _create_course(admin_client, name="Machine Learning")
    _create_course(admin_client, name="Databases")
    databases = next(course for course in course_service.list_courses() if course.name == "Databases")

    response = admin_client.post(
        f"/courses/{databases.id}",
        data={"name": "machine learning", "description": "", "ects_credits": "5"},
        follow_redirects=True,
    )

    assert "already exists" in response.text
    assert any(course.name == "Databases" for course in course_service.list_courses())


def test_update_an_unknown_course_is_rejected(admin_client):
    response = admin_client.post(
        "/courses/no-such-course",
        data={"name": "Machine Learning", "description": "", "ects_credits": "5"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "No Course with id" in response.text


def test_visitor_cannot_create_or_update_courses(client, course_service):
    response = client.post(
        "/courses",
        data={"name": "Machine Learning", "description": "", "ects_credits": "5"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    response = client.post(
        "/courses/whatever",
        data={"name": "Machine Learning", "description": "", "ects_credits": "5"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert course_service.list_courses() == []


def test_courses_tab_sits_between_semester_and_realizations(client):
    response = client.get("/")

    semester = response.text.index(">Semester<")
    courses = response.text.index(">Courses<")
    realizations = response.text.index(">Realizations<")
    assert semester < courses < realizations


def test_admin_courses_page_has_a_course_delete_dialog(admin_client, course_service):
    _create_course(admin_client)
    course = course_service.list_courses()[0]

    response = admin_client.get("/courses")

    assert f'id="course-delete-dialog-{course.id}"' in response.text
    assert f'action="/courses/{course.id}/delete"' in response.text
    assert "Delete Course" in response.text


def test_the_course_delete_dialog_names_what_it_removes(admin_client, course_service, services):
    _create_course(admin_client)
    course = course_service.list_courses()[0]
    semester = services.semesters.create_semester(2026, "fall")
    services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    services.realizations.add_realization(course.id, semester.id, "TTV24SP-B")

    response = admin_client.get("/courses")

    assert "This also deletes its 2 realizations and 0 lessons." in response.text


def test_the_course_delete_dialog_warns_about_nothing_when_there_are_no_realizations(
    admin_client, course_service
):
    _create_course(admin_client)

    response = admin_client.get("/courses")

    assert "Delete the Course Machine Learning?" in response.text
    assert "also deletes" not in response.text


def test_admin_deletes_a_course_with_its_realizations_and_lessons(
    admin_client, course_service, services
):
    _create_course(admin_client)
    course = course_service.list_courses()[0]
    semester = services.semesters.create_semester(2026, "fall")
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    services.lessons.add_lesson(
        realization.id, date(2026, 10, 20), time(8, 0), time(10, 0), "Intro", "Room B"
    )

    response = admin_client.post(f"/courses/{course.id}/delete", follow_redirects=True)

    assert response.status_code == 200
    assert "Machine Learning" not in response.text
    assert "Create a Course to get started." in response.text
    assert course_service.list_courses() == []
    assert services.realizations.list_realizations_for_course(course.id) == []
    assert services.lessons.list_lessons_for_realization(realization.id) == []


def test_deleting_a_course_leaves_other_courses_and_realizations_alone(
    admin_client, course_service, services
):
    _create_course(admin_client, name="Machine Learning")
    machine_learning = course_service.list_courses()[0]
    _create_course(admin_client, name="Databases")
    databases = next(course for course in course_service.list_courses() if course.name == "Databases")
    semester = services.semesters.create_semester(2026, "fall")
    kept = services.realizations.add_realization(databases.id, semester.id, "TTV24SP")

    admin_client.post(f"/courses/{machine_learning.id}/delete", follow_redirects=True)

    assert [course.name for course in course_service.list_courses()] == ["Databases"]
    assert [r.id for r in services.realizations.list_realizations_for_course(kept.course_id)] == [kept.id]


def test_deleting_an_unknown_course_is_rejected(admin_client, course_service):
    _create_course(admin_client)

    response = admin_client.post("/courses/no-such-course/delete", follow_redirects=True)

    assert "No Course with id" in response.text
    assert len(course_service.list_courses()) == 1


def test_visitor_cannot_delete_a_course(admin_client, course_service):
    _create_course(admin_client)
    course = course_service.list_courses()[0]
    admin_client.post("/logout", follow_redirects=True)

    response = admin_client.post(f"/courses/{course.id}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert [c.name for c in course_service.list_courses()] == ["Machine Learning"]
