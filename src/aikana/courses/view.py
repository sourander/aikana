"""Pure rendering of the courses page, its create form and the per-Course edit dialogs."""

from fasthtml.common import A, Button, Dialog, Div, Form, Input, P

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


def courses_page(courses: list[Course], is_admin: bool, error: str = ""):
    if is_admin:
        return Div(
            Div(
                Div("Courses", cls="font-semibold text-lg"),
                A("+ New Course", href="/courses/new", cls="text-sm text-blue-700 hover:text-blue-900"),
                cls="flex items-center justify-between mb-2",
            ),
            P(error, cls="text-red-600 text-sm mb-2") if error else "",
            Div(*[_admin_course_row(course) for course in courses], cls="flex flex-col gap-2"),
            *[_course_edit_dialog(course) for course in courses],
            cls="p-4",
        )
    return Div(
        Div("Courses", cls="font-semibold text-lg mb-2"),
        Div(*[_course_row(course) for course in courses], cls="flex flex-col gap-2"),
        cls="p-4",
    )


def _course_details(course: Course):
    return (
        Div(course.name, cls="font-semibold text-gray-900"),
        Div(course.description, cls="text-sm text-gray-600") if course.description else "",
        Div(f"{course.ects_credits} ECTS", cls="text-xs text-gray-500"),
    )


def _course_row(course: Course):
    return Div(*_course_details(course), cls="border border-gray-200 rounded px-3 py-2")


def _admin_course_row(course: Course):
    return Div(
        *_course_details(course),
        onclick=f"document.getElementById('course-dialog-{course.id}').showModal()",
        cls="border border-gray-200 rounded px-3 py-2 cursor-pointer hover:bg-gray-50",
    )


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
