"""
Unit tests for upsert_capabilities() and upsert_professions() in seed_taxonomies.py.
Uses mongomock — no real MongoDB needed.
"""
from seed_taxonomies import upsert_capabilities, upsert_professions


class TestUpsertCapabilities:
    def test_fresh_insert_returns_upserted_count_1(self, db, valid_capability):
        ins, _ = upsert_capabilities(db, [valid_capability])
        assert ins == 1

    def test_fresh_insert_doc_in_collection(self, db, valid_capability):
        upsert_capabilities(db, [valid_capability])
        assert db.capability_taxonomy.count_documents({"capability_id": valid_capability["capability_id"]}) == 1

    def test_second_call_does_not_insert_again(self, db, valid_capability):
        upsert_capabilities(db, [valid_capability])
        ins2, _ = upsert_capabilities(db, [valid_capability])
        assert ins2 == 0

    def test_upserted_doc_has_schema_version(self, db, valid_capability):
        upsert_capabilities(db, [valid_capability])
        doc = db.capability_taxonomy.find_one({"capability_id": valid_capability["capability_id"]})
        assert doc["schema_version"] == "1.0"

    def test_upserted_doc_has_updated_at(self, db, valid_capability):
        upsert_capabilities(db, [valid_capability])
        doc = db.capability_taxonomy.find_one({"capability_id": valid_capability["capability_id"]})
        assert "updated_at" in doc

    def test_created_at_set_on_insert(self, db, valid_capability):
        upsert_capabilities(db, [valid_capability])
        doc = db.capability_taxonomy.find_one({"capability_id": valid_capability["capability_id"]})
        assert "created_at" in doc

    def test_empty_list_returns_zeros(self, db):
        ins, upd = upsert_capabilities(db, [])
        assert ins == 0 and upd == 0

    def test_different_capability_ids_are_distinct_documents(self, db, valid_capability):
        caps = [
            {**valid_capability, "capability_id": "cap_a"},
            {**valid_capability, "capability_id": "cap_b"},
        ]
        ins, _ = upsert_capabilities(db, caps)
        assert ins == 2
        assert db.capability_taxonomy.count_documents({}) == 2

    def test_upsert_key_is_capability_id(self, db, valid_capability):
        upsert_capabilities(db, [valid_capability])
        updated = {**valid_capability, "label": "Updated Label"}
        ins, _ = upsert_capabilities(db, [updated])
        assert ins == 0
        assert db.capability_taxonomy.count_documents({}) == 1


class TestUpsertProfessions:
    def test_fresh_insert_returns_upserted_count_1(self, db, valid_profession):
        ins, _ = upsert_professions(db, [valid_profession])
        assert ins == 1

    def test_fresh_insert_doc_in_collection(self, db, valid_profession):
        upsert_professions(db, [valid_profession])
        assert db.profession_taxonomy.count_documents({"profession_id": valid_profession["profession_id"]}) == 1

    def test_second_call_does_not_insert_again(self, db, valid_profession):
        upsert_professions(db, [valid_profession])
        ins2, _ = upsert_professions(db, [valid_profession])
        assert ins2 == 0

    def test_upserted_doc_has_schema_version(self, db, valid_profession):
        upsert_professions(db, [valid_profession])
        doc = db.profession_taxonomy.find_one({"profession_id": valid_profession["profession_id"]})
        assert doc["schema_version"] == "1.0"

    def test_empty_list_returns_zeros(self, db):
        ins, upd = upsert_professions(db, [])
        assert ins == 0 and upd == 0

    def test_upsert_key_is_profession_id(self, db, valid_profession):
        upsert_professions(db, [valid_profession])
        updated = {**valid_profession, "label": "Updated"}
        ins, _ = upsert_professions(db, [updated])
        assert ins == 0
        assert db.profession_taxonomy.count_documents({}) == 1

    def test_different_profession_ids_are_distinct(self, db, valid_profession):
        profs = [
            {**valid_profession, "profession_id": "p_a"},
            {**valid_profession, "profession_id": "p_b"},
        ]
        ins, _ = upsert_professions(db, profs)
        assert ins == 2
