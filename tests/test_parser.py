"""Block-aware conventional-commit parsing (feature F2)."""

from app.services.parser import parse_commits, split_blocks


def test_split_blocks_ignores_blank_runs():
    raw = "feat: one\n\n\n\nfix: two\n\n   \nchore: three\n"
    blocks = split_blocks(raw)
    assert [block[0] for block in blocks] == ["feat: one", "fix: two", "chore: three"]


def test_three_blocks_are_grouped_and_chore_is_skipped():
    raw = "feat(api): add token refresh\n\nfix(ui): stop double submit\n\nchore: bump deps\n"
    result = parse_commits(raw)

    assert [(c.type, c.scope, c.description) for c in result.features] == [
        ("feat", "api", "add token refresh")
    ]
    assert [(c.type, c.scope, c.description) for c in result.fixes] == [
        ("fix", "ui", "stop double submit")
    ]
    assert result.breaking == []
    assert result.skipped == 1
    assert result.commit_count == 2


def test_breaking_change_footer_marks_the_block_without_being_skipped():
    raw = (
        "refactor(db): swap driver\n"
        "BREAKING CHANGE: old DSNs no longer parse\n"
    )
    result = parse_commits(raw)

    assert len(result.breaking) == 1
    assert result.breaking[0].description == "swap driver"
    assert result.breaking[0].scope == "db"
    assert result.skipped == 0


def test_bang_marks_a_commit_breaking_and_keeps_skipped_at_zero():
    result = parse_commits("perf!: drop cache layer\n")

    assert len(result.breaking) == 1
    assert result.breaking[0].type == "perf"
    assert result.breaking[0].scope is None
    assert result.skipped == 0


def test_body_and_footer_lines_never_count_as_skipped_subjects():
    raw = (
        "feat(parser): split into blocks\n"
        "\n"
        "A longer body line that explains why.\n"
        "Another body line.\n"
        "\n"
        "BREAKING CHANGE: grouped sections only\n"
        "\n"
        "fix(composer): keep text\n"
    )
    result = parse_commits(raw)

    assert result.skipped == 0
    assert len(result.features) == 1
    assert len(result.fixes) == 1
    assert result.breaking[0].description == "split into blocks"


def test_whitespace_scope_and_bang_are_tolerated():
    raw = "  feat( api )!  :   add   token refresh   \n"
    result = parse_commits(raw)

    assert result.breaking[0].scope == "api"
    assert result.breaking[0].description == "add   token refresh"
    assert result.features[0].type == "feat"


def test_unrelated_subject_lines_are_skipped_but_only_subjects():
    raw = "Not even a conventional commit\n\nchore: bump deps\n"
    result = parse_commits(raw)

    assert result.skipped == 2
    assert result.has_changes is False


def test_empty_paste_parses_to_nothing():
    result = parse_commits("   \n\n \n")

    assert result.has_changes is False
    assert result.skipped == 0
    assert result.to_dict() == {
        "breaking": [],
        "features": [],
        "fixes": [],
        "skipped_count": 0,
        "commit_count": 0,
    }


def test_groups_round_trip_through_json_dicts():
    result = parse_commits("feat(api)!: drop v1\n\nfix(ui): guard double submit\n")

    restored = type(result).from_dict(result.to_dict())

    assert [c.to_dict() for c in restored.breaking] == [c.to_dict() for c in result.breaking]
    assert [c.to_dict() for c in restored.fixes] == [c.to_dict() for c in result.fixes]
    assert restored.skipped == result.skipped
