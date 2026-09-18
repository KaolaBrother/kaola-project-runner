from src.text import slugify


def test_lowercases_input():
    assert slugify("HelloWorld") == "helloworld"


def test_replaces_each_non_alphanumeric_run_with_one_hyphen():
    assert slugify("one__two...three / four") == "one-two-three-four"


def test_strips_leading_and_trailing_hyphens():
    assert slugify("---hello world---") == "hello-world"


def test_returns_empty_string_when_no_alphanumeric_characters_exist():
    assert slugify(" --_!? ") == ""


def test_docstring_names_empty_result_behavior():
    assert slugify.__doc__ is not None
    assert "empty string" in slugify.__doc__.lower()


def test_none_max_length_keeps_the_default_behavior():
    assert slugify("Alpha -- Beta", max_length=None) == "alpha-beta"


def test_max_length_truncates_without_leaving_a_trailing_hyphen():
    slug = slugify("alpha beta gamma", max_length=6)

    assert slug == "alpha"
    assert len(slug) <= 6
    assert not slug.endswith("-")
