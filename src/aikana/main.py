import os

import uvicorn
from fasthtml.common import FastHTML
from fastlite import Database

from aikana.auth import routes as auth_routes
from aikana.auth.services import AuthService
from aikana.courses import routes as courses_routes
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
from aikana.shared.db import create_database


def create_app(db: Database) -> FastHTML:
    """The composition root: build every repository and service from `db` and register routes.

    Importing this module has no side effects, so tests can build an app on a temporary database.
    """
    course_service = CourseService(SqliteCourseRepository(db))
    holiday_service = HolidayService(SqliteHolidayRepository(db))
    auth_service = AuthService(os.environ.get("AIKANA_PASSWD", ""))

    # LessonService validates realization ids through the realizations port, per ./architecture.sdd, so both
    # services share the one repository instance.
    realization_repo = SqliteCourseRealizationRepository(db)
    lesson_service = LessonService(SqliteLessonRepository(db), realization_repo)

    # RealizationService and SemesterService are a genuine mutual pair; realization_service is constructed first
    # without a semester_service, then wired onto it once semester_service exists, per ./architecture.sdd.
    realization_service = RealizationService(realization_repo, course_service, lesson_service, holiday_service)
    semester_service = SemesterService(
        SqliteSemesterRepository(db), course_service, holiday_service, lesson_service, realization_service
    )
    realization_service.semester_service = semester_service

    app = FastHTML(title="Aikana", hdrs=layout.extra_headers())
    app.static_route(ext=".css", prefix="/static/", static_path=str(layout.STATIC_DIR))
    auth_routes.register_routes(app, auth_service)
    courses_routes.register_routes(app, course_service, semester_service, auth_service)
    semester_routes.register_routes(app, semester_service, auth_service)
    realizations_routes.register_routes(app, realization_service, semester_service, auth_service)
    return app


def main() -> None:
    uvicorn.run(create_app(create_database()), host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
