"""
Unit tests for validate_record() in seed_speakers.py.
Pure function — no DB, no network, no fixtures needed beyond valid_speaker.
"""
import pytest

from seed_speakers import validate_record


class TestRequiredFields:
    def test_valid_record_passes(self, valid_speaker):
        assert validate_record(valid_speaker, 1) == []

    def test_missing_canonical_name(self, valid_speaker):
        del valid_speaker["canonical_name"]
        errors = validate_record(valid_speaker, 1)
        assert any("canonical_name" in e for e in errors)

    def test_missing_slug(self, valid_speaker):
        del valid_speaker["slug"]
        errors = validate_record(valid_speaker, 1)
        assert any("slug" in e for e in errors)

    def test_missing_era(self, valid_speaker):
        del valid_speaker["era"]
        errors = validate_record(valid_speaker, 1)
        assert any("era" in e for e in errors)

    def test_missing_all_required_fields_produces_one_error_each(self):
        required = [
            "canonical_name", "slug", "era", "living_status",
            "country_or_region", "profession", "profession_category",
            "overall_speaker_score", "greatness_score", "ethical_alignment_score",
            "speaking_capabilities", "schema_version",
        ]
        errors = validate_record({}, 1)
        assert len(errors) == len(required), f"Got {len(errors)} errors for {len(required)} required fields"


class TestSlugValidation:
    def test_slug_with_spaces_is_invalid(self, valid_speaker):
        valid_speaker["slug"] = "martin luther king"
        errors = validate_record(valid_speaker, 1)
        assert any("slug" in e for e in errors)

    def test_slug_with_at_sign_is_invalid(self, valid_speaker):
        valid_speaker["slug"] = "martin@king"
        errors = validate_record(valid_speaker, 1)
        assert any("slug" in e for e in errors)

    def test_slug_with_hyphens_is_valid(self, valid_speaker):
        valid_speaker["slug"] = "martin-luther-king-jr"
        errors = validate_record(valid_speaker, 1)
        assert not any("slug" in e for e in errors)

    def test_slug_with_numbers_is_valid(self, valid_speaker):
        valid_speaker["slug"] = "speaker-123"
        errors = validate_record(valid_speaker, 1)
        assert not any("slug" in e for e in errors)

    def test_empty_slug_skips_format_check(self, valid_speaker):
        # Slug key is present but empty: required check passes (key exists),
        # format check is skipped (falsy string). Validation produces no errors.
        valid_speaker["slug"] = ""
        errors = validate_record(valid_speaker, 1)
        assert not any("invalid slug" in e for e in errors)


class TestScoreValidation:
    def test_overall_score_above_1_fails(self, valid_speaker):
        valid_speaker["overall_speaker_score"] = 1.5
        errors = validate_record(valid_speaker, 1)
        assert any("overall_speaker_score" in e for e in errors)

    def test_greatness_score_below_0_fails(self, valid_speaker):
        valid_speaker["greatness_score"] = -0.1
        errors = validate_record(valid_speaker, 1)
        assert any("greatness_score" in e for e in errors)

    def test_score_exactly_0_is_valid(self, valid_speaker):
        valid_speaker["ethical_alignment_score"] = 0.0
        errors = validate_record(valid_speaker, 1)
        assert not any("ethical_alignment_score" in e for e in errors)

    def test_score_exactly_1_is_valid(self, valid_speaker):
        valid_speaker["overall_speaker_score"] = 1.0
        errors = validate_record(valid_speaker, 1)
        assert not any("overall_speaker_score" in e for e in errors)

    def test_optional_score_none_is_valid(self, valid_speaker):
        valid_speaker["evidence_strength_score"] = None
        errors = validate_record(valid_speaker, 1)
        assert errors == []


class TestCapabilityValidation:
    def test_capability_missing_capability_id(self, valid_speaker):
        valid_speaker["speaking_capabilities"] = [{"strength_score": 0.8}]
        errors = validate_record(valid_speaker, 1)
        assert any("capability_id" in e for e in errors)

    def test_capability_strength_score_above_1_fails(self, valid_speaker):
        valid_speaker["speaking_capabilities"] = [
            {"capability_id": "vocal_command", "strength_score": 2.0}
        ]
        errors = validate_record(valid_speaker, 1)
        assert any("strength_score" in e for e in errors)

    def test_capability_strength_score_none_is_valid(self, valid_speaker):
        valid_speaker["speaking_capabilities"] = [{"capability_id": "vocal_command"}]
        errors = validate_record(valid_speaker, 1)
        assert errors == []

    def test_empty_capabilities_list_is_valid(self, valid_speaker):
        valid_speaker["speaking_capabilities"] = []
        errors = validate_record(valid_speaker, 1)
        assert errors == []

    def test_multiple_capabilities_all_validated(self, valid_speaker):
        valid_speaker["speaking_capabilities"] = [
            {"capability_id": "cap_a", "strength_score": 0.9},
            {"strength_score": 0.5},  # missing capability_id
            {"capability_id": "cap_c", "strength_score": 1.5},  # bad score
        ]
        errors = validate_record(valid_speaker, 1)
        assert any("capability_id" in e for e in errors)
        assert any("strength_score" in e for e in errors)
