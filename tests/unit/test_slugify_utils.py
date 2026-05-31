"""
Unit tests for make_slug() in utils/slugify_utils.py.
Pure function — no DB, no network.
"""
from utils.slugify_utils import make_slug


class TestMakeSlug:
    def test_simple_name(self):
        assert make_slug("Martin Luther King Jr") == "martin-luther-king-jr"

    def test_accented_characters_are_ascii(self):
        result = make_slug("Andrés Manuel López Obrador")
        assert result.isascii()
        assert len(result) > 0

    def test_result_is_lowercase(self):
        result = make_slug("WINSTON CHURCHILL")
        assert result == result.lower()

    def test_spaces_become_hyphens(self):
        result = make_slug("Barack Obama")
        assert " " not in result
        assert "-" in result

    def test_no_trailing_hyphen(self):
        result = make_slug("  Leading and trailing spaces  ")
        assert not result.endswith("-")
        assert not result.startswith("-")

    def test_max_length_truncation(self):
        long_name = "A" * 200
        result = make_slug(long_name)
        assert len(result) <= 80

    def test_empty_string_does_not_raise(self):
        result = make_slug("")
        assert isinstance(result, str)

    def test_numeric_name(self):
        result = make_slug("42")
        assert result == "42"

    def test_special_characters_stripped(self):
        result = make_slug("O'Brien & Associates")
        assert "'" not in result
        assert "&" not in result

    def test_result_uses_hyphen_separator(self):
        result = make_slug("John F Kennedy")
        assert "_" not in result
