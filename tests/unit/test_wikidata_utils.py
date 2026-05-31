"""
Unit tests for parse_row() and OCCUPATION_MAP in utils/wikidata.py.
Pure functions — no network calls.
"""
import pytest

from utils.wikidata import parse_row, OCCUPATION_MAP

VALID_ROW = {
    "item": {"value": "http://www.wikidata.org/entity/Q937"},
    "itemLabel": {"value": "Albert Einstein"},
    "wikiTitle": {"value": "Albert_Einstein"},
    "birthYear": {"value": "1879"},
    "deathYear": {"value": "1955"},
    "countryLabel": {"value": "Germany"},
}


class TestParseRow:
    def test_valid_row_returns_dict(self):
        result = parse_row(VALID_ROW, "Q901")
        assert result is not None
        assert isinstance(result, dict)

    def test_valid_row_extracts_qid(self):
        result = parse_row(VALID_ROW, "Q901")
        assert result["wikidata_id"] == "Q937"

    def test_valid_row_extracts_canonical_name(self):
        result = parse_row(VALID_ROW, "Q901")
        assert result["canonical_name"] == "Albert Einstein"

    def test_valid_row_birth_year_is_integer(self):
        result = parse_row(VALID_ROW, "Q901")
        assert result["birth_year"] == 1879
        assert isinstance(result["birth_year"], int)

    def test_valid_row_death_year_is_integer(self):
        result = parse_row(VALID_ROW, "Q901")
        assert result["death_year"] == 1955
        assert isinstance(result["death_year"], int)

    def test_valid_row_country_extracted(self):
        result = parse_row(VALID_ROW, "Q901")
        assert result["country_or_region"] == "Germany"

    def test_missing_birth_year_returns_none(self):
        row = {**VALID_ROW}
        del row["birthYear"]
        result = parse_row(row, "Q901")
        assert result is not None
        assert result["birth_year"] is None

    def test_missing_death_year_returns_none(self):
        row = {**VALID_ROW}
        del row["deathYear"]
        result = parse_row(row, "Q901")
        assert result is not None
        assert result["death_year"] is None

    def test_missing_country_returns_none(self):
        row = {**VALID_ROW}
        del row["countryLabel"]
        result = parse_row(row, "Q901")
        assert result is not None
        assert result["country_or_region"] is None

    def test_missing_item_uri_returns_none(self):
        row = {**VALID_ROW, "item": {}}
        assert parse_row(row, "Q901") is None

    def test_non_q_qid_returns_none(self):
        row = {**VALID_ROW, "item": {"value": "http://www.wikidata.org/entity/P106"}}
        assert parse_row(row, "Q901") is None

    def test_label_equals_qid_returns_none(self):
        row = {**VALID_ROW, "itemLabel": {"value": "Q937"}}
        assert parse_row(row, "Q901") is None

    def test_empty_label_returns_none(self):
        row = {**VALID_ROW, "itemLabel": {"value": ""}}
        assert parse_row(row, "Q901") is None

    def test_occupation_mapped_correctly(self):
        result = parse_row(VALID_ROW, "Q901")
        assert result["profession_category"] == "scientist"

    def test_unknown_occupation_maps_to_other(self):
        result = parse_row(VALID_ROW, "Q99999999")
        assert result is not None
        assert result["profession_category"] == "other"

    def test_occupation_qid_preserved(self):
        result = parse_row(VALID_ROW, "Q82955")
        assert result["occupation_qid"] == "Q82955"


class TestOccupationMap:
    def test_politician_qid_present(self):
        assert "Q82955" in OCCUPATION_MAP
        assert OCCUPATION_MAP["Q82955"] == "politician"

    def test_scientist_qid_present(self):
        assert "Q901" in OCCUPATION_MAP
        assert OCCUPATION_MAP["Q901"] == "scientist"

    def test_journalist_qid_present(self):
        assert "Q1930187" in OCCUPATION_MAP
        assert OCCUPATION_MAP["Q1930187"] == "journalist"

    def test_all_values_are_strings(self):
        assert all(isinstance(v, str) for v in OCCUPATION_MAP.values())

    def test_minimum_occupation_count(self):
        assert len(OCCUPATION_MAP) >= 10, "OCCUPATION_MAP should cover at least 10 occupation types"
