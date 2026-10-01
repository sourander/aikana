import os

import uvicorn
from fasthtml.common import FastHTML

from aikana.auth import routes as auth_routes
from aikana.auth.services import AuthService
from aikana.courses.repository_sqlite import SqliteCourseRepository
from aikana.courses.services import CourseService
from aikana.holidays.repository_sqlite import SqliteHolidayRepository
from aikana.holidays.services import HolidayService
from aikana.lessons.repository_sqlite import SqliteLessonRepository
from aikana.lessons.services import LessonService
from aikana.realizations import routes as realizations_routes
from aikana.realizations.repository_sqlite import SqliteCourseRealizationRepository
from aikana.realizations.services import RealizationService
from aikana.semester import routes as semester_routes
from aikana.semester.repository_sqlite import SqliteSemesterRepository
from aikana.semester.services import SemesterService
from aikana.shared import layout

course_service = CourseService(SqliteCourseRepository())
holiday_service = HolidayService(SqliteHolidayRepository())
lesson_service = LessonService(SqliteLessonRepository())
auth_service = AuthService(os.environ.get("ADMIN_PASSWORD", ""))

# RealizationService and SemesterService are a genuine mutual pair; realization_service is constructed first
# without a semester_service, then wired onto it once semester_service exists, per ../architecture.sdd.
realization_service = RealizationService(SqliteCourseRealizationRepository(), course_service, lesson_service, holiday_service)
semester_service = SemesterService(
    SqliteSemesterRepository(), course_service, holiday_service, lesson_service, realization_service
)
realization_service.semester_service = semester_service

app = FastHTML(title="Aikana", hdrs=layout.extra_headers())
auth_routes.register_routes(app, auth_service)
semester_routes.register_routes(app, semester_service, auth_service)
realizations_routes.register_routes(app, realization_service, auth_service)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()

