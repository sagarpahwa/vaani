"""
Unit tests for file-loading utility functions in seed scripts.
Uses tmp_path fixture — no DB or network.
"""
import json

import pytest

from seed_speakers import load_speakers
from seed_taxonomies import load_json


class TestLoadSpeakers:
    def test_loads_list_from_json_file(self, tmp_path):
        data = [{"canonical_name": "A", "slug": "a"}, {"canonical_name": "B", "slug": "b"}]
        f = tmp_path / "speakers.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = load_speakers(f)
        assert result == data

    def test_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]", encoding="utf-8")
        assert load_speakers(f) == []

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_speakers(tmp_path / "nonexistent.json")


class TestLoadJson:
    def test_loads_list_from_json_file(self, tmp_path):
        data = [{"capability_id": "cap_a"}, {"capability_id": "cap_b"}]
        f = tmp_path / "caps.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = load_json(f)
        assert result == data

    def test_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]", encoding="utf-8")
        assert load_json(f) == []

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_json(tmp_path / "missing.json")
