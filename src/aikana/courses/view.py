"""Pure rendering of the courses page, its create form, the per-Course edit and delete dialogs and the Realizations of
each Course with their add, edit and delete dialogs, per ./courses.sdd.
"""

from fasthtml.common import A, Button, Dialog, Div, Form, Input, Option, P, Select, Span

from .domain import Course


def create_course_form(error: str = ""):
    return Div(
        Div("Create a Course to get started.", cls="create-title"),
        Form(
            Input(name="name", placeholder="Name", required=True, cls="input"),
            Input(name="description", placeholder="Description", cls="input input--grow"),
            Input(
                name="ects_credits", type="number", min="0", placeholder="ECTS credits", cls="input input--ects"
            ),
            Button("Create Course", type="submit", cls="btn"),
            P(error, cls="error") if error else "",
            method="post",
            action="/courses",
            cls="create-row",
        ),
        cls="create-form",
    )


def no_course_notice():
    return P("No Course has been created yet.", cls="notice")


def courses_page(
    courses: list[Course],
    is_admin: bool,
    error: str = "",
    realizations_by_course: dict[int, list[tuple[int, str, str, int]]] | None = None,
    semester_options: list[tuple[int, str]] = (),
    selected_semester_id: int | None = None,
    course_delete_counts: dict[int, tuple[int, int]] | None = None,
    realization_lesson_counts: dict[int, int] | None = None,
):
    """`realizations_by_course` holds `(id, label, group, semester_id)` rows; the count mappings carry how many
    realizations and Lessons each Course's delete would remove with it."""
    realizations_by_course = realizations_by_course or {}
    course_delete_counts = course_delete_counts or {}
    realization_lesson_counts = realization_lesson_counts or {}

    def course_block(course: Course):
        return Div(
            _course_details_row(course, is_admin),
            _realizations_block(
                realizations_by_course.get(course.id, []),
                course,
                is_admin,
                semester_options,
                selected_semester_id,
                realization_lesson_counts,
            ),
            cls="course-card",
        )

    if is_admin:
        return Div(
            Div(
                Div("Courses", cls="page-title"),
                A("+ New Course", href="/courses/new", cls="link"),
                cls="courses-head",
            ),
            P(error, cls="error") if error else "",
            *[course_block(course) for course in courses],
            *[_course_edit_dialog(course) for course in courses],
            *[
                _course_delete_dialog(course, *course_delete_counts.get(course.id, (0, 0)))
                for course in courses
            ],
            *[realization_dialog(course, semester_options, selected_semester_id) for course in courses],
            *[
                _realization_edit_dialog(course, row, semester_options)
                for course in courses
                for row in realizations_by_course.get(course.id, [])
            ],
            *[
                _realization_delete_dialog(course, row, realization_lesson_counts.get(row[0], 0))
                for course in courses
                for row in realizations_by_course.get(course.id, [])
            ],
            cls="courses",
        )
    return Div(
        Div("Courses", cls="page-title"),
        *[course_block(course) for course in courses],
        cls="courses",
    )


def _course_details(course: Course):
    return (
        Div(course.name, cls="course-name"),
        Div(course.description, cls="course-desc") if course.description else "",
        Div(f"{course.ects_credits} ECTS", cls="course-ects"),
    )


def _course_details_row(course: Course, is_admin: bool):
    """The Course's own values; for the admin the row opens the edit dialog, the block around it does not."""
    if not is_admin:
        return Div(*_course_details(course), cls="course-head")
    return Div(
        *_course_details(course),
        onclick=f"document.getElementById('course-dialog-{course.id}').showModal()",
        cls="course-head course-head--clickable",
    )


def _realizations_block(
    rows: list[tuple[int, str, str, int]],
    course: Course,
    is_admin: bool,
    semester_options: list[tuple[int, str]],
    selected_semester_id: int | None,
    realization_lesson_counts: dict[int, int],
):
    """A Course's realizations across every Semester, each linking to its weekly view."""
    add_control = (
        A(
            "+ Add Realization",
            href="#",
            onclick=_open_dialog(f"realization-dialog-{course.id}"),
            cls="link",
        )
        if is_admin
        else ""
    )
    return Div(
        Div(
            Span("Realizations", cls="label"),
            add_control,
            cls="realizations-head",
        ),
        Div(
            *[
                _realization_row(
                    row,
                    course,
                    is_admin,
                    selected_semester_id,
                    realization_lesson_counts.get(row[0], 0),
                )
                for row in rows
            ]
            or Div("No realization yet.", cls="empty-note"),
            cls="realization-list",
        ),
        cls="realizations",
    )


def _realization_row(
    row: tuple[int, str, str, int],
    course: Course,
    is_admin: bool,
    selected_semester_id: int | None,
    lesson_count: int,
):
    """One realization's label linking to its weekly view, plus the admin's edit and delete controls."""
    realization_id, label = row[0], row[1]
    return Div(
        A(
            label,
            href=_realization_href(realization_id, selected_semester_id),
            cls="realization-link",
        ),
        Div(
            A(
                "Edit",
                href="#",
                onclick=_open_dialog(f"realization-edit-dialog-{realization_id}"),
                cls="link link--small",
            ),
            A(
                "Delete",
                href="#",
                onclick=_open_dialog(f"realization-delete-dialog-{realization_id}"),
                cls="link link--small link--danger",
            ),
            cls="row-actions",
        )
        if is_admin
        else "",
        cls="realization-row",
    )


def _open_dialog(dialog_id: str) -> str:
    """Opens a dialog, closing the one it was opened from first so a confirm step replaces its opener."""
    return f"var d = document.getElementById('{dialog_id}'); if (d.open) d.close(); d.showModal();"


def _realization_href(realization_id: int, selected_semester_id: int | None) -> str:
    if selected_semester_id is not None:
        return f"/realizations?semester_id={selected_semester_id}&realization_id={realization_id}"
    return f"/realizations?realization_id={realization_id}"


def _course_edit_dialog(course: Course):
    return Dialog(
        Form(
            Input(name="name", value=course.name, required=True, cls="input"),
            Input(name="description", value=course.description, cls="input"),
            Input(name="ects_credits", type="number", min="0", value=str(course.ects_credits), cls="input"),
            Div(
                Button("Save", type="submit", cls="btn"),
                Button(
                    "Delete Course",
                    type="button",
                    onclick=_open_dialog(f"course-delete-dialog-{course.id}"),
                    cls="btn btn--danger",
                ),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions",
            ),
            method="post",
            action=f"/courses/{course.id}",
            cls="form",
        ),
        id=f"course-dialog-{course.id}",
    )


def _course_delete_dialog(course: Course, realization_count: int, lesson_count: int):
    """The confirmation before a Course is removed; names what the cascade takes with it."""
    return Dialog(
        Div(f"Delete the Course {course.name}?", cls="dialog-title"),
        (
            P(
                f"This also deletes its {realization_count} "
                f"{'realization' if realization_count == 1 else 'realizations'} and {lesson_count} "
                f"{'lesson' if lesson_count == 1 else 'lessons'}.",
                cls="dialog-note",
            )
            if realization_count
            else ""
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls="btn btn--danger"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions form-actions--end",
            ),
            method="post",
            action=f"/courses/{course.id}/delete",
        ),
        id=f"course-delete-dialog-{course.id}",
    )


def realization_dialog(
    course: Course,
    semester_options: list[tuple[int, str]],
    selected_semester_id: int | None = None,
):
    """The add-realization form for one Course; reports the missing Semester instead of an unusable select."""
    return Dialog(
        Div(f"Add a realization of {course.name}.", cls="dialog-title"),
        (
            _realization_form(
                course.id,
                f"/courses/{course.id}/realizations",
                semester_options,
                selected_semester_id,
            )
            if semester_options
            else P("No Semester has been created yet.", cls="muted")
        ),
        id=f"realization-dialog-{course.id}",
    )


def _realization_edit_dialog(course: Course, row: tuple[int, str, str, int], semester_options: list[tuple[int, str]]):
    """One realization's edit form, prefilled with its group and Semester."""
    realization_id, label, group, semester_id = row
    return Dialog(
        Div(f"Edit the realization {label}.", cls="dialog-title"),
        (
            _realization_form(
                course.id,
                f"/courses/{course.id}/realizations/{realization_id}",
                semester_options,
                semester_id,
                group=group,
                submit_label="Save",
            )
            if semester_options
            else P("No Semester has been created yet.", cls="muted")
        ),
        id=f"realization-edit-dialog-{realization_id}",
    )


def _realization_delete_dialog(course: Course, row: tuple[int, str, str, int], lesson_count: int):
    """The confirmation before one realization is removed; names the Lessons removed with it."""
    realization_id, label = row[0], row[1]
    return Dialog(
        Div(f"Delete the realization {label}?", cls="dialog-title"),
        (
            P(
                f"This also deletes its {lesson_count} {'lesson' if lesson_count == 1 else 'lessons'}.",
                cls="dialog-note",
            )
            if lesson_count
            else ""
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls="btn btn--danger"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions form-actions--end",
            ),
            method="post",
            action=f"/courses/{course.id}/realizations/{realization_id}/delete",
        ),
        id=f"realization-delete-dialog-{realization_id}",
    )


def _realization_form(
    course_id: int,
    action: str,
    semester_options: list[tuple[int, str]],
    selected_semester_id: int | None,
    group: str = "",
    submit_label: str = "Add Realization",
):
    option_ids = [option_id for option_id, _ in semester_options]
    selected = selected_semester_id if selected_semester_id in option_ids else option_ids[0]
    return Form(
        Input(name="course_id", type="hidden", value=course_id),
        Span("Group", cls="label"),
        Input(name="group", placeholder="Group", required=True, value=group, cls="input"),
        Span("Semester", cls="label"),
        Select(
            *[
                Option(label, value=option_id, selected=(option_id == selected))
                for option_id, label in semester_options
            ],
            name="semester_id",
            cls="input",
        ),
        Div(
            Button(submit_label, type="submit", cls="btn"),
            Button(
                "Cancel",
                type="button",
                onclick="this.closest('dialog').close()",
                cls="btn btn--plain",
            ),
            cls="form-actions",
        ),
        method="post",
        action=action,
        cls="form",
    )
