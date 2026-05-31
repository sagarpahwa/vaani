"""Tests for pure text utilities, including Mode B script splitting."""

from services.api.domain.text import normalize, split_script_text, stable_seed, tokenize


def test_tokenize_strips_punctuation_and_lowercases():
    assert tokenize("Hello, World! It's ME.") == ["hello", "world", "it's", "me"]


def test_tokenize_empty():
    assert tokenize("") == []
    assert tokenize(None) == []


def test_normalize_lowercases_and_strips_edge_apostrophes():
    assert normalize("'quoted'") == "quoted"
    assert normalize("It's") == "it's"  # internal apostrophe preserved
    assert normalize("HELLO") == "hello"


def test_stable_seed_is_deterministic_and_order_sensitive():
    assert stable_seed("a", 1) == stable_seed("a", 1)
    assert stable_seed("a", 1) != stable_seed("1", "a")
    assert 0 <= stable_seed("x") <= 0xFFFFFFFF


def test_split_script_uses_explicit_newlines():
    text = "First line here\nSecond line here\n\nThird line"
    assert split_script_text(text) == ["First line here", "Second line here", "Third line"]


def test_split_script_falls_back_to_sentences():
    text = "We stand together. We will not yield! Will we win?"
    assert split_script_text(text) == [
        "We stand together.",
        "We will not yield!",
        "Will we win?",
    ]


def test_split_script_empty_is_empty_list():
    assert split_script_text("") == []
    assert split_script_text("   \n  ") == []
