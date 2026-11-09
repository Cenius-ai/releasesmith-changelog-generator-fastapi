"""Composer, persistence, detail, edit, delete and export (features F3, F5, F6)."""

from __future__ import annotations

import itertools
import re

from tests.conftest import SAMPLE_COMMITS

_names = itertools.count(1)


def unique_name(prefix: str = "Spring cleaning") -> str:
    return f"{prefix} #{next(_names)}"


def create_release(client, name: str | None = None, **overrides):
    """POST a release and return (name, response)."""
    name = name or unique_name()
    payload = {
        "commits": SAMPLE_COMMITS,
        "previous_version": "1.4.2",
        "name": name,
        "version": "2.0.0",
        "notes": "A tidy release.",
    }
    payload.update(overrides)
    return name, client.post("/releases", data=payload, follow_redirects=False)


def release_id_for(client, name: str) -> int:
    html = client.get("/dashboard").text
    match = re.search(r'href="/releases/(\d+)"[^>]*>' + re.escape(name), html)
    assert match, f"release row {name!r} not found on the dashboard"
    return int(match.group(1))


def test_new_release_screen_is_reachable_at_releases_new(second_user_client):
    response = second_user_client.get("/releases/new")

    assert response.status_code == 200
    assert "New release" in response.text
    assert 'name="commits"' in response.text
    assert "Nothing previewed yet" in response.text
    # /composer renders the same composer, and a numeric id still resolves.
    assert second_user_client.get("/composer").status_code == 200


def test_new_release_screen_is_guarded_for_anonymous_visitors(client):
    response = client.get("/releases/new", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith("/signin")


def test_preview_renders_groups_without_saving(auth_client):
    before = auth_client.get("/dashboard").text.count('href="/releases/')

    response = auth_client.post(
        "/composer/preview",
        data={"commits": SAMPLE_COMMITS, "previous_version": "1.4.2"},
    )

    assert response.status_code == 200
    assert "Breaking Changes" in response.text
    assert "add token refresh" in response.text
    assert "swap driver" in response.text
    assert "v2.0.0" in response.text
    assert "1 subject line skipped" in response.text
    assert "Save release" in response.text
    # Previewing never persists anything.
    assert auth_client.get("/dashboard").text.count('href="/releases/') == before


def test_preview_rejects_an_empty_paste(auth_client):
    response = auth_client.post(
        "/composer/preview", data={"commits": "   ", "previous_version": "1.0.0"}
    )

    assert response.status_code == 400
    assert "Paste at least one commit." in response.text
    assert "Changelog preview" in response.text
    assert "Save release" not in response.text


def test_saved_release_appears_first_on_the_dashboard(auth_client):
    name, response = create_release(auth_client)

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    dashboard = auth_client.get("/dashboard").text
    assert name in dashboard
    assert "v2.0.0" in dashboard
    assert dashboard.index(name) < dashboard.index("Composer polish")


def test_dashboard_empty_state_for_a_brand_new_account(second_user_client):
    response = second_user_client.get("/dashboard")

    assert response.status_code == 200
    assert "Paste your first commits" in response.text
    assert 'href="/releases/new"' in response.text


def test_detail_page_renders_every_section_and_the_markdown_panel(auth_client):
    name, _ = create_release(auth_client)
    release_id = release_id_for(auth_client, name)

    response = auth_client.get(f"/releases/{release_id}")

    assert response.status_code == 200
    assert "v2.0.0" in response.text
    assert "A tidy release." in response.text
    assert "v1.4.2 → v2.0.0" in response.text
    assert "Breaking Changes" in response.text
    assert "## v2.0.0" in response.text  # the Markdown panel
    assert f'href="/releases/{release_id}/export.md"' in response.text


def test_detail_page_shows_empty_section_text(auth_client):
    name, response = create_release(
        auth_client, commits="fix(cli): guard the empty paste\n", version="1.4.3"
    )
    assert response.status_code == 303
    release_id = release_id_for(auth_client, name)

    detail = auth_client.get(f"/releases/{release_id}").text

    assert "No features in this release" in detail
    assert "No breaking changes in this release" in detail
    assert "guard the empty paste" in detail


def test_edit_page_prefills_every_field(auth_client):
    name, _ = create_release(auth_client)
    release_id = release_id_for(auth_client, name)

    response = auth_client.get(f"/releases/{release_id}/edit")

    assert response.status_code == 200
    assert f'value="{name}"' in response.text
    assert "A tidy release." in response.text
    assert 'value="1.4.2"' in response.text
    assert 'value="2.0.0"' in response.text
    assert "swap driver" in response.text


def test_update_keeps_name_and_notes_and_adds_the_new_commit(auth_client):
    name, _ = create_release(auth_client)
    release_id = release_id_for(auth_client, name)
    before = auth_client.get(f"/releases/{release_id}").text

    response = auth_client.post(
        f"/releases/{release_id}",
        data={
            "commits": SAMPLE_COMMITS + "\nfix(api): handle 429 backoff\n",
            "previous_version": "1.4.2",
            "name": name,
            "version": "2.0.0",
            "notes": "A tidy release.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/releases/{release_id}"

    after = auth_client.get(f"/releases/{release_id}").text
    assert "handle 429" in after
    assert name in after
    assert "A tidy release." in after
    assert "v2.0.0" in after
    saved_before = re.search(r"saved (\d{2} \w{3} \d{4})", before).group(1)
    saved_after = re.search(r"saved (\d{2} \w{3} \d{4})", after).group(1)
    assert saved_before == saved_after  # created_at is preserved


def test_invalid_version_is_rejected_inline_and_values_survive(auth_client):
    name, response = create_release(auth_client, version="not-a-version")

    assert response.status_code == 400
    assert "Version must look like 1.4.2." in response.text
    assert name in response.text
    assert "swap driver" in response.text


def test_delete_removes_the_release(auth_client):
    name, _ = create_release(auth_client)
    release_id = release_id_for(auth_client, name)

    response = auth_client.post(f"/releases/{release_id}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert name not in auth_client.get("/dashboard").text
    assert auth_client.get(f"/releases/{release_id}").status_code == 404


def test_export_serves_markdown_as_a_download(auth_client):
    name, _ = create_release(auth_client)
    release_id = release_id_for(auth_client, name)

    response = auth_client.get(f"/releases/{release_id}/export.md")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment" in response.headers["content-disposition"]
    assert response.text.startswith("## v2.0.0")
    assert "### Breaking Changes" in response.text
    assert "- swap driver (db)" in response.text


def test_another_users_release_is_not_reachable(auth_client, second_user_client):
    name, _ = create_release(auth_client)
    release_id = release_id_for(auth_client, name)

    for path in (
        f"/releases/{release_id}",
        f"/releases/{release_id}/edit",
        f"/releases/{release_id}/export.md",
    ):
        response = second_user_client.get(path)
        assert response.status_code == 404, path

    deleted = second_user_client.post(f"/releases/{release_id}/delete", follow_redirects=False)
    assert deleted.status_code == 404
    # The owner still sees it.
    assert auth_client.get(f"/releases/{release_id}").status_code == 200


def test_dashboard_filter_returns_matching_rows_only(auth_client):
    name, _ = create_release(auth_client, name=unique_name("Filterable release"), version="9.9.9")

    hits = auth_client.get("/dashboard", params={"q": name})
    assert hits.status_code == 200
    assert name in hits.text
    assert "Composer polish" not in hits.text

    misses = auth_client.get("/dashboard", params={"q": "zzzz-nothing"})
    assert misses.status_code == 200
    assert "No releases match" in misses.text
    assert 'href="/dashboard"' in misses.text


def test_unknown_page_renders_the_friendly_404(auth_client):
    response = auth_client.get("/nope/not/a/page")

    assert response.status_code == 404
    assert "We could not find that page" in response.text
    assert 'href="/dashboard"' in response.text
