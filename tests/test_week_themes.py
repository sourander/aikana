"""Tests of the WeekTheme package's validation and of the weekly view's week theme, its dialogs and its admin guard,
per ./tests.sdd.
"""

from datetime import date

import pytest

from aikana.week_themes.services import (
    DuplicateWeekThemeError,
    InvalidWeekThemeError,
    UnknownRealizationError,
    UnknownWeekThemeError,
)
from conftest import week_card_html

WEEK_START = date(2026, 9, 14)
WEEK_NUMBER = WEEK_START.isocalendar()[1]


@pytest.fixture
def semester_id(admin_client):
    response = admin_client.post("/semesters", data={"year": "2026", "term": "fall"}, follow_redirects=False)
    return int(response.headers["location"].removeprefix("/?semester_id="))


@pytest.fixture
def realization_id(admin_client, course_service, services, semester_id):
    admin_client.post(
        "/courses",
        data={"name": "Machine Learning", "description": "An introduction.", "ects_credits": "5"},
        follow_redirects=True,
    )
    course_id = course_service.list_courses()[0].id
    admin_client.post(
        f"/courses/{course_id}/realizations",
        data={"group": "TTV24SP", "semester_id": str(semester_id)},
        follow_redirects=True,
    )
    return services.realizations.list_realizations_for_semester(semester_id)[0].id


def _weekly_view(client, realization_id, semester_id):
    return client.get(f"/realizations?realization_id={realization_id}&semester_id={semester_id}")


def _add_theme(client, realization_id, week_start=WEEK_START, title="Gradient descent"):
    return client.post(
        "/realizations/week-themes",
        data={"realization_id": str(realization_id), "week_start": week_start.isoformat(), "title": title},
        follow_redirects=True,
    )


def _update_theme(client, theme_id, week_start=WEEK_START, title="Gradient descent II"):
    return client.post(
        f"/realizations/week-themes/{theme_id}",
        data={"week_start": week_start.isoformat(), "title": title},
        follow_redirects=True,
    )


def _delete_theme(client, theme_id):
    return client.post(f"/realizations/week-themes/{theme_id}/delete", follow_redirects=True)


def _week_head(html: str) -> str:
    """The rendered head of the themed week's card, so a test asserts on that head's own content."""
    card = week_card_html(html, WEEK_NUMBER)
    return card[card.index('class="week-head') : card.index('class="week-lessons')]


# The service layer


def test_a_week_theme_needs_an_existing_realization(services):
    with pytest.raises(UnknownRealizationError):
        services.week_themes.add_week_theme(999, WEEK_START, "Gradient descent")


def test_a_week_must_start_on_a_monday(services, realization_id):
    with pytest.raises(InvalidWeekThemeError, match="Monday"):
        services.week_themes.add_week_theme(realization_id, date(2026, 9, 15), "Gradient descent")


def test_a_week_theme_needs_a_non_empty_title(services, realization_id):
    with pytest.raises(InvalidWeekThemeError):
        services.week_themes.add_week_theme(realization_id, WEEK_START, "   ")


def test_a_week_has_at_most_one_theme_per_realization(services, realization_id):
    services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")

    with pytest.raises(DuplicateWeekThemeError):
        services.week_themes.add_week_theme(realization_id, WEEK_START, "Another theme")


def test_editing_a_week_theme_ignores_the_theme_being_edited(services, realization_id):
    theme = services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")

    edited = services.week_themes.update_week_theme(theme.id, WEEK_START, "Gradient descent II")

    assert edited.title == "Gradient descent II"
    assert edited.week_start == WEEK_START
    assert edited.course_realization_id == realization_id


def test_deleting_a_week_theme_leaves_the_realizations_other_themes_alone(services, realization_id):
    other = services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")
    kept = services.week_themes.add_week_theme(realization_id, date(2026, 9, 21), "Convolutional networks")

    services.week_themes.delete_week_theme(other.id)

    assert services.week_themes.list_week_themes(realization_id) == [kept]


def test_an_unknown_week_theme_is_rejected(services):
    with pytest.raises(UnknownWeekThemeError):
        services.week_themes.update_week_theme(123, WEEK_START, "Gradient descent")
    with pytest.raises(UnknownWeekThemeError):
        services.week_themes.delete_week_theme(123)


# The weekly view


def test_a_week_shows_its_theme_on_the_week_numbers_line(
    admin_client, realization_id, semester_id, services
):
    services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")

    head = _week_head(_weekly_view(admin_client, realization_id, semester_id).text)

    assert f">{WEEK_NUMBER}<" in head
    assert head.index(f">{WEEK_NUMBER}<") < head.index("Gradient descent") < head.index("14.9.2026")


def test_a_week_without_a_theme_offers_an_empty_add_form(admin_client, realization_id, semester_id):
    response = _weekly_view(admin_client, realization_id, semester_id)

    assert '<input name="title" value=""' in response.text
    # The add form has no stored theme to delete, so that week carries no delete confirmation.
    assert f'id="week-theme-delete-dialog-{WEEK_START.isoformat()}"' not in response.text


def test_the_admin_week_cell_has_an_add_dialog(admin_client, realization_id, semester_id):
    response = _weekly_view(admin_client, realization_id, semester_id)

    assert f'id="week-theme-dialog-{WEEK_START.isoformat()}"' in response.text
    assert 'action="/realizations/week-themes"' in response.text
    assert f'<input name="week_start" type="hidden" value="{WEEK_START.isoformat()}"' in response.text
    assert f'<input name="realization_id" type="hidden" value="{realization_id}"' in response.text


def test_the_week_cell_opens_the_theme_dialog(admin_client, realization_id, semester_id):
    response = _weekly_view(admin_client, realization_id, semester_id)

    assert (
        "var d = document.getElementById("
        f"'week-theme-dialog-{WEEK_START.isoformat()}'); if (d.open) d.close(); d.showModal();" in response.text
    )


def test_a_themed_week_has_a_prefilled_edit_dialog_and_a_delete_dialog(
    admin_client, realization_id, semester_id, services
):
    theme = services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")

    response = _weekly_view(admin_client, realization_id, semester_id)

    assert 'value="Gradient descent"' in response.text
    assert f'action="/realizations/week-themes/{theme.id}"' in response.text
    assert f'action="/realizations/week-themes/{theme.id}/delete"' in response.text
    assert f"Delete the week {WEEK_NUMBER} theme Gradient descent?" in response.text


def test_the_admin_adds_a_week_theme_from_the_weekly_view(
    admin_client, realization_id, semester_id, services
):
    response = _add_theme(admin_client, realization_id)

    assert response.status_code == 200
    assert "Gradient descent" in response.text
    assert [t.title for t in services.week_themes.list_week_themes(realization_id)] == ["Gradient descent"]


def test_the_admin_edits_a_week_theme_from_the_weekly_view(
    admin_client, realization_id, semester_id, services
):
    theme = services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")

    response = _update_theme(admin_client, theme.id)

    assert "Gradient descent II" in response.text
    assert "Gradient descent<" not in response.text
    assert services.week_themes.get_week_theme(theme.id).title == "Gradient descent II"


def test_the_admin_deletes_a_week_theme_from_the_weekly_view(
    admin_client, realization_id, semester_id, services
):
    theme = services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")

    response = _delete_theme(admin_client, theme.id)

    assert "Gradient descent" not in response.text
    assert services.week_themes.get_week_theme(theme.id) is None


def test_a_rejected_week_theme_write_returns_a_validation_message(
    admin_client, realization_id, services
):
    response = _add_theme(admin_client, realization_id, title="  ")

    assert "A WeekTheme needs a non-empty title." in response.text
    assert services.week_themes.list_week_themes(realization_id) == []


def test_a_duplicate_week_theme_is_rejected(admin_client, realization_id, services):
    services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")

    response = _add_theme(admin_client, realization_id)

    assert "already has a WeekTheme" in response.text
    assert len(services.week_themes.list_week_themes(realization_id)) == 1


def test_a_malformed_week_start_is_reported(admin_client, realization_id, services):
    response = admin_client.post(
        "/realizations/week-themes",
        data={"realization_id": str(realization_id), "week_start": "14.9.2026", "title": "Gradient descent"},
        follow_redirects=True,
    )

    assert "Enter a valid week start date." in response.text
    assert services.week_themes.list_week_themes(realization_id) == []


def test_writing_an_unknown_week_theme_is_rejected(admin_client, realization_id, semester_id, services):
    update = _update_theme(admin_client, "no-such-theme")
    delete = _delete_theme(admin_client, "no-such-theme")

    assert "No WeekTheme with id" in update.text
    assert "No WeekTheme with id" in delete.text


def test_a_visitor_sees_the_week_theme_without_any_affordance(
    admin_client, client, realization_id, semester_id, services
):
    services.week_themes.add_week_theme(realization_id, WEEK_START, "Gradient descent")
    admin_client.post("/logout", follow_redirects=True)

    response = _weekly_view(client, realization_id, semester_id)

    assert "Gradient descent" in response.text
    assert "<dialog" not in response.text
    assert "/realizations/week-themes" not in response.text


def test_a_visitor_cannot_write_a_week_theme(admin_client, client, realization_id, services):
    admin_client.post("/logout", follow_redirects=True)

    create = client.post(
        "/realizations/week-themes",
        data={"realization_id": str(realization_id), "week_start": WEEK_START.isoformat(), "title": "Nope"},
        follow_redirects=False,
    )
    delete = client.post("/realizations/week-themes/1/delete", follow_redirects=False)

    assert create.status_code == 303
    assert create.headers["location"] == "/login"
    assert delete.status_code == 303
    assert delete.headers["location"] == "/login"
    assert services.week_themes.list_week_themes(realization_id) == []