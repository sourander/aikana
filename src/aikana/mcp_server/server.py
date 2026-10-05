"""The MCP driving adapter: builds the `mcp` SDK server exposing @McpService, per ./mcp_server.sdd.

The only module in the package allowed to import the `mcp` SDK, per ../architecture.sdd. Every tool is a thin
pass-through to ./services.py: the SDK builds each tool's input schema from the function's signature and its
description from its docstring, so every tool docstring is a single line (the SDK does not dedent them).
"""

from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from .services import (
    ConferenceDict,
    CourseDict,
    DeadlineDict,
    DeletedDict,
    HolidayDict,
    LessonDict,
    McpError,
    McpService,
    McpWriteGuard,
    NoTeachWeekDict,
    RealizationDict,
    SemesterDict,
    WeekThemeDict,
)

# The annotations let agents tell read-only and destructive tools apart, per ./mcp_server.sdd.
_READ = ToolAnnotations(read_only_hint=True)
_WRITE = ToolAnnotations(read_only_hint=False)
_DELETE = ToolAnnotations(read_only_hint=False, destructive_hint=True)

_INSTRUCTIONS = (
    "Aikana is a teacher's lesson calendar. A Semester is a teaching period (spring: January to June, fall: "
    "August to December). A Course is realized as a CourseRealization (the Course taught to one group in one "
    "Semester), which has Lessons, one WeekTheme per themed week and Deadlines (dated obligations such as an "
    "assignment due date). Holidays block single days and NoTeachWeeks block Monday-to-Friday weeks; a Lesson "
    "cannot be dated inside a NoTeachWeek, and at most one Lesson exists per day and CourseRealization, while a "
    "CourseRealization may have many Deadlines on the same date. "
    "A Conference marks one dated event that does not block teaching and coexists with that day's Lessons and "
    "Holidays; a conference spanning several days is stored as one Conference per day, and a date carries at most one. "
    "Dates are ISO yyyy-mm-dd and times HH:MM. Reads need no credentials; writes require the AIKANA_MCP_TOKEN "
    "bearer token."
)


def create_mcp_server(service: McpService, guard: McpWriteGuard) -> MCPServer:
    """Build the MCP server: anonymous read tools and bearer-token-gated write tools."""
    server = MCPServer("aikana", instructions=_INSTRUCTIONS)

    def presented_token(ctx: Context) -> str | None:
        """The token the request's `Authorization: Bearer <token>` header carries, or None."""
        request = ctx.request_context.request
        if request is None:
            return None
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        return token if scheme.lower() == "bearer" and token else None

    def require_write(ctx: Context) -> None:
        """Reject the call unless it carries the configured bearer token, per ./mcp_server.sdd."""
        if not guard.allows(presented_token(ctx)):
            raise ToolError("This tool requires write access: send the AIKANA_MCP_TOKEN as a Bearer token.")

    def call(fn: Callable[..., Any], *args: Any) -> Any:
        """Invoke an @McpService method, mapping its @McpError to the SDK's tool error, per ./mcp_server.sdd."""
        try:
            return fn(*args)
        except McpError as exc:
            raise ToolError(str(exc)) from exc

    # Semesters

    @server.tool(annotations=_READ)
    def list_semesters() -> list[SemesterDict]:
        """List all Semesters in calendar order, each with its computed ISO `start` and `end` date bounds."""
        return call(service.list_semesters)

    @server.tool(annotations=_WRITE)
    def create_semester(year: int, term: str, ctx: Context) -> SemesterDict:
        """Create a Semester for `year` and `term` (`spring` or `fall`); the term's default NoTeachWeeks are created with it, and a duplicate year+term is rejected."""
        require_write(ctx)
        return call(service.create_semester, year, term)

    @server.tool(annotations=_DELETE)
    def delete_semester(semester_id: int, ctx: Context) -> DeletedDict:
        """Delete a Semester; its CourseRealizations, their Lessons and its NoTeachWeeks are deleted with it."""
        require_write(ctx)
        return call(service.delete_semester, semester_id)

    # Courses

    @server.tool(annotations=_READ)
    def list_courses() -> list[CourseDict]:
        """List all Courses, ordered by name."""
        return call(service.list_courses)

    @server.tool(annotations=_READ)
    def get_course(course_id: int) -> CourseDict:
        """Get one Course by its id."""
        return call(service.get_course, course_id)

    @server.tool(annotations=_WRITE)
    def create_course(name: str, description: str, ects_credits: int, ctx: Context) -> CourseDict:
        """Create a Course; the name must be non-empty and unique ignoring case, `ects_credits` is its ECTS credit count."""
        require_write(ctx)
        return call(service.create_course, name, description, ects_credits)

    @server.tool(annotations=_WRITE)
    def update_course(course_id: int, name: str, description: str, ects_credits: int, ctx: Context) -> CourseDict:
        """Replace a Course's name, description and ECTS credits; its CourseRealizations are kept."""
        require_write(ctx)
        return call(service.update_course, course_id, name, description, ects_credits)

    @server.tool(annotations=_DELETE)
    def delete_course(course_id: int, ctx: Context) -> DeletedDict:
        """Delete a Course; its CourseRealizations and their Lessons are deleted with it."""
        require_write(ctx)
        return call(service.delete_course, course_id)

    # CourseRealizations

    @server.tool(annotations=_READ)
    def get_realization(realization_id: int) -> RealizationDict:
        """Get one CourseRealization by its id."""
        return call(service.get_realization, realization_id)

    @server.tool(annotations=_READ)
    def list_realizations(course_id: int | None = None, semester_id: int | None = None) -> list[RealizationDict]:
        """List CourseRealizations, optionally filtered by `course_id` or `semester_id` (`course_id` wins when both are given); unfiltered when neither is given."""
        return call(service.list_realizations, course_id, semester_id)

    @server.tool(annotations=_WRITE)
    def create_realization(course_id: int, semester_id: int, group: str, ctx: Context) -> RealizationDict:
        """Create a CourseRealization: Course `course_id` taught in Semester `semester_id` to the group `group` (for example `TTV24SP`); the group label must be non-empty."""
        require_write(ctx)
        return call(service.create_realization, course_id, semester_id, group)

    @server.tool(annotations=_WRITE)
    def update_realization(realization_id: int, semester_id: int, group: str, ctx: Context) -> RealizationDict:
        """Re-label a CourseRealization or move it to another Semester; its Course never changes."""
        require_write(ctx)
        return call(service.update_realization, realization_id, semester_id, group)

    @server.tool(annotations=_DELETE)
    def delete_realization(realization_id: int, ctx: Context) -> DeletedDict:
        """Delete a CourseRealization; its Lessons are deleted with it."""
        require_write(ctx)
        return call(service.delete_realization, realization_id)

    # Lessons

    @server.tool(annotations=_READ)
    def get_lesson(lesson_id: int) -> LessonDict:
        """Get one Lesson by its id."""
        return call(service.get_lesson, lesson_id)

    @server.tool(annotations=_READ)
    def list_lessons(course_realization_id: int) -> list[LessonDict]:
        """List one CourseRealization's Lessons, ordered by date and start time."""
        return call(service.list_lessons, course_realization_id)

    @server.tool(annotations=_READ)
    def list_lessons_for_range(start: str, end: str) -> list[LessonDict]:
        """List every Lesson dated between `start` and `end` (ISO yyyy-mm-dd, inclusive) across all CourseRealizations, ordered by date and start time."""
        return call(service.list_lessons_for_range, start, end)

    @server.tool(annotations=_WRITE)
    def create_lesson(
        course_realization_id: int,
        lesson_date: str,
        start_time: str,
        end_time: str,
        topic: str,
        ctx: Context,
        notes: str = "",
    ) -> LessonDict:
        """Create a Lesson on `lesson_date` (yyyy-mm-dd) from `start_time` to `end_time` (HH:MM); the topic must be non-empty, the end after the start, and the date free of the realization's Lessons and its Semester's NoTeachWeeks."""
        require_write(ctx)
        return call(service.create_lesson, course_realization_id, lesson_date, start_time, end_time, topic, notes)

    @server.tool(annotations=_WRITE)
    def update_lesson(
        lesson_id: int,
        lesson_date: str,
        start_time: str,
        end_time: str,
        topic: str,
        ctx: Context,
        notes: str = "",
    ) -> LessonDict:
        """Edit one Lesson's date, times, topic and notes; it stays in its CourseRealization, and create_lesson's checks apply, ignoring the Lesson being edited for the one-Lesson-per-day rule."""
        require_write(ctx)
        return call(service.update_lesson, lesson_id, lesson_date, start_time, end_time, topic, notes)

    @server.tool(annotations=_DELETE)
    def delete_lesson(lesson_id: int, ctx: Context) -> DeletedDict:
        """Delete one Lesson, leaving its CourseRealization and its other Lessons untouched."""
        require_write(ctx)
        return call(service.delete_lesson, lesson_id)

    # Holidays

    @server.tool(annotations=_READ)
    def list_holidays(start: str, end: str) -> list[HolidayDict]:
        """List every Holiday dated between `start` and `end` (ISO yyyy-mm-dd, inclusive), ordered by date."""
        return call(service.list_holidays, start, end)

    @server.tool(annotations=_WRITE)
    def create_holiday(holiday_date: str, title: str, ctx: Context) -> HolidayDict:
        """Create a Holiday on `holiday_date` (yyyy-mm-dd) with a non-empty title; Holidays are global to the calendar, not owned by a Semester."""
        require_write(ctx)
        return call(service.create_holiday, holiday_date, title)

    @server.tool(annotations=_WRITE)
    def update_holiday(holiday_id: int, holiday_date: str, title: str, ctx: Context) -> HolidayDict:
        """Edit one Holiday's date and title."""
        require_write(ctx)
        return call(service.update_holiday, holiday_id, holiday_date, title)

    @server.tool(annotations=_DELETE)
    def delete_holiday(holiday_id: int, ctx: Context) -> DeletedDict:
        """Delete one Holiday."""
        require_write(ctx)
        return call(service.delete_holiday, holiday_id)

    # NoTeachWeeks

    @server.tool(annotations=_READ)
    def list_no_teach_weeks(semester_id: int) -> list[NoTeachWeekDict]:
        """List one Semester's NoTeachWeeks (Monday-to-Friday weeks in which nothing is taught), each with its ISO `week_number` and the Monday `week_start` date."""
        return call(service.list_no_teach_weeks, semester_id)

    @server.tool(annotations=_WRITE)
    def create_no_teach_week(semester_id: int, week_number: int, ctx: Context, title: str = "") -> NoTeachWeekDict:
        """Block ISO week `week_number` of a Semester's year as a NoTeachWeek; the week must exist in that year and not already be blocked in the Semester, and an empty `title` becomes the shared default title."""
        require_write(ctx)
        return call(service.create_no_teach_week, semester_id, week_number, title)

    @server.tool(annotations=_WRITE)
    def update_no_teach_week(no_teach_week_id: int, week_number: int, title: str, ctx: Context) -> NoTeachWeekDict:
        """Edit one NoTeachWeek's week number and title; it stays in its Semester."""
        require_write(ctx)
        return call(service.update_no_teach_week, no_teach_week_id, week_number, title)

    @server.tool(annotations=_DELETE)
    def delete_no_teach_week(no_teach_week_id: int, ctx: Context) -> DeletedDict:
        """Delete one NoTeachWeek, unblocking its week."""
        require_write(ctx)
        return call(service.delete_no_teach_week, no_teach_week_id)

    # WeekThemes

    @server.tool(annotations=_READ)
    def get_week_theme(week_theme_id: int) -> WeekThemeDict:
        """Get one WeekTheme by its id."""
        return call(service.get_week_theme, week_theme_id)

    @server.tool(annotations=_READ)
    def list_week_themes(course_realization_id: int) -> list[WeekThemeDict]:
        """List one CourseRealization's WeekThemes, ordered by week; a week without one carries no theme."""
        return call(service.list_week_themes, course_realization_id)

    @server.tool(annotations=_WRITE)
    def create_week_theme(course_realization_id: int, week_start: str, title: str, ctx: Context) -> WeekThemeDict:
        """Theme one week of a CourseRealization; `week_start` (yyyy-mm-dd) must be that week's Monday, the title non-empty, and the week must not already be themed for this CourseRealization."""
        require_write(ctx)
        return call(service.create_week_theme, course_realization_id, week_start, title)

    @server.tool(annotations=_WRITE)
    def update_week_theme(week_theme_id: int, week_start: str, title: str, ctx: Context) -> WeekThemeDict:
        """Edit one WeekTheme's week and title; it stays in its CourseRealization, and create_week_theme's checks apply, ignoring the WeekTheme being edited."""
        require_write(ctx)
        return call(service.update_week_theme, week_theme_id, week_start, title)

    @server.tool(annotations=_DELETE)
    def delete_week_theme(week_theme_id: int, ctx: Context) -> DeletedDict:
        """Delete one WeekTheme, leaving its CourseRealization and its other WeekThemes untouched."""
        require_write(ctx)
        return call(service.delete_week_theme, week_theme_id)

    # Deadlines

    @server.tool(annotations=_READ)
    def get_deadline(deadline_id: int) -> DeadlineDict:
        """Get one Deadline by its id."""
        return call(service.get_deadline, deadline_id)

    @server.tool(annotations=_READ)
    def list_deadlines(course_realization_id: int) -> list[DeadlineDict]:
        """List one CourseRealization's Deadlines, ordered by date; a realization may have many, and several may share a date."""
        return call(service.list_deadlines, course_realization_id)

    @server.tool(annotations=_READ)
    def list_deadlines_for_range(start: str, end: str) -> list[DeadlineDict]:
        """List every Deadline dated between `start` and `end` (ISO yyyy-mm-dd, inclusive) across all CourseRealizations, ordered by date."""
        return call(service.list_deadlines_for_range, start, end)

    @server.tool(annotations=_WRITE)
    def create_deadline(course_realization_id: int, deadline_date: str, title: str, ctx: Context) -> DeadlineDict:
        """Create a Deadline for one CourseRealization on `deadline_date` (yyyy-mm-dd) with a non-empty title; its date is not checked against the Semester or its NoTeachWeeks, and several Deadlines may share a date."""
        require_write(ctx)
        return call(service.create_deadline, course_realization_id, deadline_date, title)

    @server.tool(annotations=_WRITE)
    def update_deadline(deadline_id: int, deadline_date: str, title: str, ctx: Context) -> DeadlineDict:
        """Edit one Deadline's date and title; it stays in its CourseRealization, and create_deadline's checks apply."""
        require_write(ctx)
        return call(service.update_deadline, deadline_id, deadline_date, title)

    @server.tool(annotations=_DELETE)
    def delete_deadline(deadline_id: int, ctx: Context) -> DeletedDict:
        """Delete one Deadline, leaving its CourseRealization and its other Deadlines untouched."""
        require_write(ctx)
        return call(service.delete_deadline, deadline_id)

    # Conferences

    @server.tool(annotations=_READ)
    def list_conferences(start: str, end: str) -> list[ConferenceDict]:
        """List every Conference dated between `start` and `end` (ISO yyyy-mm-dd, inclusive), ordered by date; a Conference does not block teaching and a date carries at most one."""
        return call(service.list_conferences, start, end)

    @server.tool(annotations=_WRITE)
    def create_conference(conference_date: str, title: str, ctx: Context) -> ConferenceDict:
        """Create a Conference on `conference_date` (yyyy-mm-dd) with a non-empty title; the date must carry no Conference yet, and a multi-day conference is one entry per day. Conferences are global to the calendar, not owned by a Semester."""
        require_write(ctx)
        return call(service.create_conference, conference_date, title)

    @server.tool(annotations=_WRITE)
    def update_conference(conference_id: int, conference_date: str, title: str, ctx: Context) -> ConferenceDict:
        """Edit one Conference's date and title; create_conference's checks apply, ignoring the Conference being edited."""
        require_write(ctx)
        return call(service.update_conference, conference_id, conference_date, title)

    @server.tool(annotations=_DELETE)
    def delete_conference(conference_id: int, ctx: Context) -> DeletedDict:
        """Delete one Conference; that day's Lessons and Holidays are untouched."""
        require_write(ctx)
        return call(service.delete_conference, conference_id)

    return server
