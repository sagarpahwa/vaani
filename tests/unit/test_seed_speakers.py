"""
Unit tests for upsert_speakers() in seed_speakers.py.
Uses mongomock — no real MongoDB needed.
"""
from seed_speakers import upsert_speakers


class TestUpsertSpeakers:
    def test_fresh_insert_returns_upserted_count_1(self, db, valid_speaker):
        ins, upd = upsert_speakers(db, [valid_speaker])
        assert ins == 1

    def test_fresh_insert_doc_in_collection(self, db, valid_speaker):
        upsert_speakers(db, [valid_speaker])
        assert db.speakers.count_documents({"slug": valid_speaker["slug"]}) == 1

    def test_second_call_does_not_insert_again(self, db, valid_speaker):
        upsert_speakers(db, [valid_speaker])
        ins2, _ = upsert_speakers(db, [valid_speaker])
        assert ins2 == 0
        assert db.speakers.count_documents({"slug": valid_speaker["slug"]}) == 1

    def test_upserted_doc_has_schema_version(self, db, valid_speaker):
        upsert_speakers(db, [valid_speaker])
        doc = db.speakers.find_one({"slug": valid_speaker["slug"]})
        assert doc["schema_version"] == "1.0"

    def test_upserted_doc_has_updated_at(self, db, valid_speaker):
        upsert_speakers(db, [valid_speaker])
        doc = db.speakers.find_one({"slug": valid_speaker["slug"]})
        assert "updated_at" in doc

    def test_created_at_set_on_insert(self, db, valid_speaker):
        upsert_speakers(db, [valid_speaker])
        doc = db.speakers.find_one({"slug": valid_speaker["slug"]})
        assert "created_at" in doc

    def test_empty_list_returns_zeros(self, db):
        ins, upd = upsert_speakers(db, [])
        assert ins == 0
        assert upd == 0

    def test_empty_list_does_not_write_anything(self, db):
        upsert_speakers(db, [])
        assert db.speakers.count_documents({}) == 0

    def test_multiple_speakers_all_inserted(self, db, valid_speaker):
        speakers = [
            {**valid_speaker, "slug": "speaker-a", "canonical_name": "Speaker A"},
            {**valid_speaker, "slug": "speaker-b", "canonical_name": "Speaker B"},
            {**valid_speaker, "slug": "speaker-c", "canonical_name": "Speaker C"},
        ]
        ins, _ = upsert_speakers(db, speakers)
        assert ins == 3
        assert db.speakers.count_documents({}) == 3

    def test_different_slugs_are_distinct_documents(self, db, valid_speaker):
        speaker_a = {**valid_speaker, "slug": "alice", "canonical_name": "Alice"}
        speaker_b = {**valid_speaker, "slug": "bob", "canonical_name": "Bob"}
        upsert_speakers(db, [speaker_a, speaker_b])
        assert db.speakers.count_documents({}) == 2

    def test_upsert_key_is_slug(self, db, valid_speaker):
        upsert_speakers(db, [valid_speaker])
        # Same slug, different canonical_name → update, not new insert
        updated = {**valid_speaker, "canonical_name": "Updated Name"}
        ins, _ = upsert_speakers(db, [updated])
        assert ins == 0
        assert db.speakers.count_documents({}) == 1
