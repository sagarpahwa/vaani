"""
Validates that all JSON Schema files and seed data files are well-formed,
structurally correct, and internally consistent — no DB required.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
SCHEMAS_DIR = ROOT / "schemas"
SEED_DIR = ROOT / "seed"

SCHEMA_FILES = list(SCHEMAS_DIR.glob("*.json"))
EXPECTED_SCHEMAS = {
    "speakers", "candidate_speakers", "speeches", "transcripts", "sources",
    "evidence_items", "capability_taxonomy", "profession_taxonomy",
    "speaker_scores", "extraction_runs", "media_assets", "practice_drills",
}


class TestSchemaFiles:
    def test_all_schema_files_parse_as_valid_json(self):
        errors = []
        for path in SCHEMA_FILES:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                errors.append(f"{path.name}: {e}")
        assert errors == [], "\n".join(errors)

    def test_all_expected_schemas_are_present(self):
        names = {p.stem for p in SCHEMA_FILES}
        missing = EXPECTED_SCHEMAS - names
        assert not missing, f"Missing schema files: {missing}"

    def test_all_schemas_have_json_schema_key(self):
        missing = []
        for path in SCHEMA_FILES:
            data = json.loads(path.read_text(encoding="utf-8"))
            if "$jsonSchema" not in data:
                missing.append(path.name)
        assert not missing, f"Missing $jsonSchema key: {missing}"

    def test_speakers_schema_required_fields(self):
        data = json.loads((SCHEMAS_DIR / "speakers.json").read_text(encoding="utf-8"))
        required = data["$jsonSchema"]["required"]
        for field in ["canonical_name", "slug", "created_at", "schema_version"]:
            assert field in required, f"speakers schema missing required field: {field}"

    def test_speeches_schema_has_speech_context_enum(self):
        data = json.loads((SCHEMAS_DIR / "speeches.json").read_text(encoding="utf-8"))
        props = data["$jsonSchema"]["properties"]
        assert "speech_context" in props
        enum = props["speech_context"].get("enum", [])
        for expected in ["ted_talk", "debate", "political_address"]:
            assert expected in enum, f"speeches.speech_context missing value: {expected}"

    def test_extraction_runs_schema_has_status_enum(self):
        data = json.loads((SCHEMAS_DIR / "extraction_runs.json").read_text(encoding="utf-8"))
        props = data["$jsonSchema"]["properties"]
        assert "status" in props
        enum = props["status"].get("enum", [])
        for expected in ["running", "completed", "failed"]:
            assert expected in enum, f"extraction_runs.status missing value: {expected}"


class TestSeedSpeakers:
    def setup_method(self):
        self.speakers = json.loads((SEED_DIR / "speakers_100.json").read_text(encoding="utf-8"))

    def test_seed_speakers_parses_as_valid_json(self):
        assert isinstance(self.speakers, list)

    def test_seed_speakers_has_minimum_count(self):
        assert len(self.speakers) >= 100, f"Expected >=100 speakers, got {len(self.speakers)}"

    def test_no_duplicate_slugs(self):
        slugs = [s["slug"] for s in self.speakers]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found in speakers_100.json"

    def test_every_speaker_has_slug(self):
        missing = [s.get("canonical_name", f"[idx {i}]") for i, s in enumerate(self.speakers) if not s.get("slug")]
        assert not missing, f"Speakers missing slug: {missing[:5]}"

    def test_every_speaker_has_canonical_name(self):
        missing = [i for i, s in enumerate(self.speakers) if not s.get("canonical_name")]
        assert not missing, f"Speakers at indices {missing[:5]} have no canonical_name"

    def test_all_speaker_scores_in_range(self):
        score_fields = ["overall_speaker_score", "greatness_score", "ethical_alignment_score"]
        violations = []
        for s in self.speakers:
            for field in score_fields:
                val = s.get(field)
                if val is not None and not (0.0 <= val <= 1.0):
                    violations.append(f"{s['slug']}.{field}={val}")
        assert not violations, f"Score out of [0,1]: {violations[:5]}"


class TestSeedCapabilityTaxonomy:
    def setup_method(self):
        self.caps = json.loads((SEED_DIR / "capability_taxonomy.json").read_text(encoding="utf-8"))

    def test_parses_as_valid_json(self):
        assert isinstance(self.caps, list)

    def test_minimum_count(self):
        assert len(self.caps) >= 25, f"Expected >=25 capabilities, got {len(self.caps)}"

    def test_no_duplicate_capability_ids(self):
        ids = [c["capability_id"] for c in self.caps]
        assert len(ids) == len(set(ids)), "Duplicate capability_ids found"

    def test_every_capability_has_capability_id(self):
        missing = [i for i, c in enumerate(self.caps) if not c.get("capability_id")]
        assert not missing, f"Capabilities at indices {missing} have no capability_id"


class TestSeedProfessionTaxonomy:
    def setup_method(self):
        self.profs = json.loads((SEED_DIR / "profession_taxonomy.json").read_text(encoding="utf-8"))

    def test_parses_as_valid_json(self):
        assert isinstance(self.profs, list)

    def test_minimum_count(self):
        assert len(self.profs) >= 20, f"Expected >=20 professions, got {len(self.profs)}"

    def test_no_duplicate_profession_ids(self):
        ids = [p["profession_id"] for p in self.profs]
        assert len(ids) == len(set(ids)), "Duplicate profession_ids found"

    def test_every_profession_has_profession_id(self):
        missing = [i for i, p in enumerate(self.profs) if not p.get("profession_id")]
        assert not missing, f"Professions at indices {missing} have no profession_id"
