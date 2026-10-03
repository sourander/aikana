"""Pure rendering of the courses page, its create form, the per-Course edit and delete dialogs and the Realizations of
each Course with their add, edit and delete dialogs, per ./courses.sdd.
"""

from fasthtml.common import A, Button, Dialog, Div, Form, Input, Option, P, Select, Span

from .domain import Course

_INPUT_CLS = "border border-gray-300 rounded px-2 py-1"
_DELETE_BTN_CLS = "bg-red-600 text-white rounded px-3 py-1"
_CANCEL_BTN_CLS = "border border-gray-300 rounded px-3 py-1"


def create_course_form(error: str = ""):
    return Div(
        Div("Create a Course to get started.", cls="font-semibold text-lg mb-2"),
        Form(
            Input(name="name", placeholder="Name", required=True, cls=_INPUT_CLS),
            Input(name="description", placeholder="Description", cls=f"{_INPUT_CLS} flex-1"),
            Input(name="ects_credits", type="number", min="0", placeholder="ECTS credits", cls=f"{_INPUT_CLS} w-32"),
            Button("Create Course", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
            P(error, cls="text-red-600 text-sm") if error else "",
            method="post",
            action="/courses",
            cls="flex items-center gap-2",
        ),
        cls="p-4",
    )


def no_course_notice():
    return P("No Course has been created yet.", cls="p-4 text-sm text-gray-500")


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
            cls="border border-gray-200 rounded px-3 py-2",
        )

    if is_admin:
        return Div(
            Div(
                Div("Courses", cls="font-semibold text-lg"),
                A("+ New Course", href="/courses/new", cls="text-sm text-blue-700 hover:text-blue-900"),
                cls="flex items-center justify-between mb-2",
            ),
            P(error, cls="text-red-600 text-sm mb-2") if error else "",
            Div(*[course_block(course) for course in courses], cls="flex flex-col gap-2"),
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
            cls="p-4",
        )
    return Div(
        Div("Courses", cls="font-semibold text-lg mb-2"),
        Div(*[course_block(course) for course in courses], cls="flex flex-col gap-2"),
        cls="p-4",
    )


def _course_details(course: Course):
    return (
        Div(course.name, cls="font-semibold text-gray-900"),
        Div(course.description, cls="text-sm text-gray-600") if course.description else "",
        Div(f"{course.ects_credits} ECTS", cls="text-xs text-gray-500"),
    )


def _course_details_row(course: Course, is_admin: bool):
    """The Course's own values; for the admin the row opens the edit dialog, the block around it does not."""
    if not is_admin:
        return Div(*_course_details(course))
    return Div(
        *_course_details(course),
        onclick=f"document.getElementById('course-dialog-{course.id}').showModal()",
        cls="cursor-pointer hover:bg-gray-50",
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
            cls="text-sm text-blue-700 hover:text-blue-900",
        )
        if is_admin
        else ""
    )
    return Div(
        Div(
            Span("Realizations", cls="text-xs font-semibold text-gray-500"),
            add_control,
            cls="flex items-center gap-3 justify-between border-t border-gray-100 mt-2 pt-1",
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
            or Div("No realization yet.", cls="text-xs text-gray-400"),
            cls="flex flex-col gap-1 mt-1",
        ),
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
            cls="text-sm text-gray-700 hover:text-blue-900",
        ),
        Div(
            A(
                "Edit",
                href="#",
                onclick=_open_dialog(f"realization-edit-dialog-{realization_id}"),
                cls="text-xs text-blue-700 hover:text-blue-900",
            ),
            A(
                "Delete",
                href="#",
                onclick=_open_dialog(f"realization-delete-dialog-{realization_id}"),
                cls="text-xs text-red-700 hover:text-red-900",
            ),
            cls="flex items-center gap-3",
        )
        if is_admin
        else "",
        cls="flex items-center gap-3 justify-between",
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
            Input(name="name", value=course.name, required=True, cls=_INPUT_CLS),
            Input(name="description", value=course.description, cls=_INPUT_CLS),
            Input(name="ects_credits", type="number", min="0", value=str(course.ects_credits), cls=_INPUT_CLS),
            Div(
                Button("Save", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
                Button(
                    "Delete Course",
                    type="button",
                    onclick=_open_dialog(f"course-delete-dialog-{course.id}"),
                    cls=_DELETE_BTN_CLS,
                ),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2",
            ),
            method="post",
            action=f"/courses/{course.id}",
            cls="flex flex-col gap-2",
        ),
        id=f"course-dialog-{course.id}",
        cls="rounded p-4 w-96",
    )


def _course_delete_dialog(course: Course, realization_count: int, lesson_count: int):
    """The confirmation before a Course is removed; names what the cascade takes with it."""
    return Dialog(
        Div(f"Delete the Course {course.name}?", cls="font-semibold text-sm mb-2"),
        (
            P(
                f"This also deletes its {realization_count} "
                f"{'realization' if realization_count == 1 else 'realizations'} and {lesson_count} "
                f"{'lesson' if lesson_count == 1 else 'lessons'}.",
                cls="text-sm text-gray-600 mb-2",
            )
            if realization_count
            else ""
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls=_DELETE_BTN_CLS),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2 justify-end",
            ),
            method="post",
            action=f"/courses/{course.id}/delete",
        ),
        id=f"course-delete-dialog-{course.id}",
        cls="rounded p-4 w-96",
    )


def realization_dialog(
    course: Course,
    semester_options: list[tuple[int, str]],
    selected_semester_id: int | None = None,
):
    """The add-realization form for one Course; reports the missing Semester instead of an unusable select."""
    return Dialog(
        Div(f"Add a realization of {course.name}.", cls="font-semibold text-sm mb-2"),
        (
            _realization_form(
                course.id,
                f"/courses/{course.id}/realizations",
                semester_options,
                selected_semester_id,
            )
            if semester_options
            else P("No Semester has been created yet.", cls="text-sm text-gray-500")
        ),
        id=f"realization-dialog-{course.id}",
        cls="rounded p-4 w-96",
    )


def _realization_edit_dialog(course: Course, row: tuple[int, str, str, int], semester_options: list[tuple[int, str]]):
    """One realization's edit form, prefilled with its group and Semester."""
    realization_id, label, group, semester_id = row
    return Dialog(
        Div(f"Edit the realization {label}.", cls="font-semibold text-sm mb-2"),
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
            else P("No Semester has been created yet.", cls="text-sm text-gray-500")
        ),
        id=f"realization-edit-dialog-{realization_id}",
        cls="rounded p-4 w-96",
    )


def _realization_delete_dialog(course: Course, row: tuple[int, str, str, int], lesson_count: int):
    """The confirmation before one realization is removed; names the Lessons removed with it."""
    realization_id, label = row[0], row[1]
    return Dialog(
        Div(f"Delete the realization {label}?", cls="font-semibold text-sm mb-2"),
        (
            P(
                f"This also deletes its {lesson_count} {'lesson' if lesson_count == 1 else 'lessons'}.",
                cls="text-sm text-gray-600 mb-2",
            )
            if lesson_count
            else ""
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls=_DELETE_BTN_CLS),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2 justify-end",
            ),
            method="post",
            action=f"/courses/{course.id}/realizations/{realization_id}/delete",
        ),
        id=f"realization-delete-dialog-{realization_id}",
        cls="rounded p-4 w-96",
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
        Span("Group", cls="text-xs font-semibold text-gray-500"),
        Input(name="group", placeholder="Group", required=True, value=group, cls=_INPUT_CLS),
        Span("Semester", cls="text-xs font-semibold text-gray-500"),
        Select(
            *[
                Option(label, value=option_id, selected=(option_id == selected))
                for option_id, label in semester_options
            ],
            name="semester_id",
            cls=_INPUT_CLS,
        ),
        Div(
            Button(submit_label, type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
            Button(
                "Cancel",
                type="button",
                onclick="this.closest('dialog').close()",
                cls=_CANCEL_BTN_CLS,
            ),
            cls="flex gap-2 mt-3",
        ),
        method="post",
        action=action,
        cls="flex flex-col gap-1",
    )