"""Tests for work commands helpers."""

from engram.services.workflow_helpers import slugify


def test_slugify_empty_string():
    """Empty string should return 'misc'."""
    assert slugify("") == "misc"


def test_slugify_normal_text():
    """Normal text should be lowercased."""
    assert slugify("Feature") == "feature"
    assert slugify("bugfix") == "bugfix"


def test_slugify_with_spaces():
    """Spaces should be replaced with hyphens."""
    assert slugify("Add new feature") == "add-new-feature"
    assert slugify("  Extra   spaces  ") == "extra-spaces"


def test_slugify_with_special_characters():
    """Special characters should be replaced with hyphens."""
    assert slugify("feat: add feature!") == "feat-add-feature"
    assert slugify("bugfix/123-issue") == "bugfix-123-issue"
    assert slugify("user@domain.com") == "user-domain-com"


def test_slugify_strips_leading_trailing_hyphens():
    """Leading and trailing hyphens should be removed."""
    assert slugify("---test---") == "test"
    assert slugify("!@#test!@#") == "test"


def test_slugify_mixed_case():
    """Mixed case should be lowercased and hyphenated correctly."""
    assert slugify("Some-Mixed_Case-String") == "some-mixed-case-string"
