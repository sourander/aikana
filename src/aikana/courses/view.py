"""Pure rendering of the courses page, its create form, the per-Course edit dialogs and the Realizations of each
Course with the per-Course add-realization dialogs, per ./courses.sdd.
"""

from fasthtml.common import A, Button, Dialog, Div, Form, Input, Option, P, Select, Span

from .domain import Course

_INPUT_CLS = "border border-gray-300 rounded px-2 py-1"


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
    realizations_by_course: dict[str, list[tuple[str, str]]] | None = None,
    semester_options: list[tuple[str, str]] = (),
    selected_semester_id: str = "",
):
    realizations_by_course = realizations_by_course or {}

    def course_block(course: Course):
        return Div(
            _course_details_row(course, is_admin),
            _realizations_block(
                realizations_by_course.get(course.id, []),
                course.id,
                is_admin,
                semester_options,
                selected_semester_id,
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
            *[realization_dialog(course, semester_options, selected_semester_id) for course in courses],
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
    rows: list[tuple[str, str]],
    course_id: str,
    is_admin: bool,
    semester_options: list[tuple[str, str]],
    selected_semester_id: str,
):
    """A Course's realizations across every Semester, each linking to its weekly view."""
    add_control = (
        A(
            "+ Add Realization",
            href="#",
            onclick=f"document.getElementById('realization-dialog-{course_id}').showModal()",
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
                A(
                    label,
                    href=_realization_href(realization_id, selected_semester_id),
                    cls="text-sm text-gray-700 hover:text-blue-900",
                )
                for realization_id, label in rows
            ]
            or Div("No realization yet.", cls="text-xs text-gray-400"),
            cls="flex flex-col gap-1 mt-1",
        ),
    )


def _realization_href(realization_id: str, selected_semester_id: str) -> str:
    if selected_semester_id:
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
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="border border-gray-300 rounded px-3 py-1",
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


def realization_dialog(
    course: Course,
    semester_options: list[tuple[str, str]],
    selected_semester_id: str = "",
):
    """The add-realization form for one Course; reports the missing Semester instead of an unusable select."""
    return Dialog(
        Div(f"Add a realization of {course.name}.", cls="font-semibold text-sm mb-2"),
        (
            _realization_form(course, semester_options, selected_semester_id)
            if semester_options
            else P("No Semester has been created yet.", cls="text-sm text-gray-500")
        ),
        id=f"realization-dialog-{course.id}",
        cls="rounded p-4 w-96",
    )


def _realization_form(course: Course, semester_options: list[tuple[str, str]], selected_semester_id: str):
    option_ids = [option_id for option_id, _ in semester_options]
    selected = selected_semester_id if selected_semester_id in option_ids else option_ids[0]
    return Form(
        Input(name="course_id", type="hidden", value=course.id),
        Span("Group", cls="text-xs font-semibold text-gray-500"),
        Input(name="group", placeholder="Group", required=True, cls=_INPUT_CLS),
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
            Button("Add Realization", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
            Button(
                "Cancel",
                type="button",
                onclick="this.closest('dialog').close()",
                cls="border border-gray-300 rounded px-3 py-1",
            ),
            cls="flex gap-2 mt-3",
        ),
        method="post",
        action=f"/courses/{course.id}/realizations",
        cls="flex flex-col gap-1",
    )
