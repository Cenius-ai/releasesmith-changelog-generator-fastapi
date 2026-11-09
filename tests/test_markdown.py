"""Markdown rendering (feature F6)."""

from app.services.markdown import render_markdown
from app.services.parser import parse_commits

ALL_THREE = parse_commits(
    "refactor(db)!: swap driver\n\n"
    "feat(api): add token refresh\n\n"
    "fix(ui): stop double submit\n"
)


def test_sections_render_in_order_with_scope_bullets():
    markdown = render_markdown(version="2.0.0", previous_version="1.4.2", groups=ALL_THREE)

    assert markdown.startswith("## v2.0.0")
    breaking_at = markdown.index("### Breaking Changes")
    features_at = markdown.index("### Features")
    fixes_at = markdown.index("### Fixes")
    assert breaking_at < features_at < fixes_at
    assert "- swap driver (db)" in markdown
    assert "- add token refresh (api)" in markdown
    assert "- stop double submit (ui)" in markdown


def test_notes_appear_between_the_version_heading_and_the_sections():
    markdown = render_markdown(
        version="1.5.0",
        groups=parse_commits("feat(cli): add --dry-run\n"),
        notes="Thanks to everyone who tried the beta.",
    )

    heading_at = markdown.index("## v1.5.0")
    notes_at = markdown.index("Thanks to everyone who tried the beta.")
    section_at = markdown.index("### Features")
    assert heading_at < notes_at < section_at


def test_unscoped_commit_renders_without_parentheses():
    markdown = render_markdown(version="1.0.1", groups=parse_commits("fix: guard empty paste\n"))
    assert "- guard empty paste\n" in markdown


def test_empty_sections_are_omitted():
    markdown = render_markdown(version="1.0.1", groups=parse_commits("fix(cli): guard empty paste\n"))

    assert "### Fixes" in markdown
    assert "### Breaking Changes" not in markdown
    assert "### Features" not in markdown


def test_release_without_commits_renders_a_placeholder():
    markdown = render_markdown(version="1.0.0", groups=parse_commits(""))
    assert "_No conventional-commit changes in this release._" in markdown


def test_name_is_rendered_as_a_bold_line():
    markdown = render_markdown(
        version="1.0.0", groups=ALL_THREE, name="Spring cleaning"
    )
    assert "**Spring cleaning**" in markdown
