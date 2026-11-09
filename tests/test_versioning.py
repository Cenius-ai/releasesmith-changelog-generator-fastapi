"""Semantic version bumping (feature F4)."""

import pytest

from app.services.parser import parse_commits
from app.services.versioning import is_valid_version, suggest_version

BREAKING = parse_commits("refactor(db)!: swap driver\n")
FEATURE = parse_commits("feat(api): add token refresh\n")
FIX_ONLY = parse_commits("fix(ui): stop double submit\n\nfix(api): retry once\n")


def test_breaking_change_bumps_major():
    suggestion = suggest_version("1.4.2", BREAKING)

    assert suggestion.version == "2.0.0"
    assert suggestion.level == "major"
    assert suggestion.previous == "1.4.2"


def test_feature_bumps_minor():
    suggestion = suggest_version("1.4.2", FEATURE)

    assert suggestion.version == "1.5.0"
    assert suggestion.level == "minor"


def test_fixes_only_bump_patch():
    suggestion = suggest_version("1.4.2", FIX_ONLY)

    assert suggestion.version == "1.4.3"
    assert suggestion.level == "patch"


def test_breaking_wins_over_features():
    groups = parse_commits("feat(api)!: drop v1\n\nfeat(ui): new panel\n\nfix(x): y\n")
    assert suggest_version("3.2.1", groups).version == "4.0.0"


def test_leading_v_and_whitespace_are_accepted():
    assert suggest_version(" v1.4.2 ", FIX_ONLY).version == "1.4.3"


def test_invalid_previous_version_is_rejected():
    with pytest.raises(ValueError):
        suggest_version("not-a-version", FIX_ONLY)


def test_default_previous_version_is_used_when_blank():
    assert suggest_version("", FIX_ONLY).previous == "1.0.0"


def test_version_helper_matches_major_minor_patch_only():
    assert is_valid_version("2.0.0")
    assert is_valid_version("v2.0.0")
    assert not is_valid_version("2.0")
    assert not is_valid_version("two.zero.zero")
    assert not is_valid_version("")
