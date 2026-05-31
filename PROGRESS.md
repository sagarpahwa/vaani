# Vaani — Build Progress Tracker

Use this file to resume safely after interruption.
Each milestone is git-committed. To resume: read this file, check which tasks are ✅, continue from the first ⬜.

## Milestone Status

| # | Milestone | Status | Git Tag |
|---|-----------|--------|---------|
| 1 | Project scaffold (dirs, docker-compose, configs, package.json, pyproject.toml) | ✅ Done | `scaffold` |
| 2 | JSON Schema validation files (11 collections) | ⬜ Pending | — |
| 3 | Node.js DB init + indexes + verify scripts | ⬜ Pending | — |
| 4 | Taxonomy seed data + Python inserter | ⬜ Pending | — |
| 5 | 100 verified speakers seed + Python inserter | ⬜ Pending | — |
| 6 | Wikidata SPARQL candidate discovery script | ⬜ Pending | — |
| 7 | Dedup + scoring + export scripts | ⬜ Pending | — |
| 8 | Tests (schema + dedup) | ⬜ Pending | — |
| 9 | Docker up → seed → verify → show counts | ⬜ Pending | — |
| 10 | README | ⬜ Pending | — |

## Key File Locations

| File | Purpose |
|------|---------|
| `docker-compose.yml` | MongoDB 7.0 + mongo-express UI |
| `.env` | Local secrets (copy of .env.example) |
| `package.json` | Node.js runner: `npm run db:setup` |
| `pyproject.toml` | Python deps: `pip install -e .` |
| `schemas/` | JSON Schema validation for each collection |
| `scripts/node/db_init.js` | Creates DB + collections with validators |
| `scripts/node/create_indexes.js` | All indexes |
| `scripts/node/verify.js` | Verification queries |
| `scripts/python/seed_taxonomies.py` | Seeds capability + profession taxonomy |
| `scripts/python/seed_speakers.py` | Seeds 100 verified speakers |
| `scripts/python/ingest_wikidata.py` | Wikidata SPARQL candidate discovery |
| `scripts/python/deduplicate.py` | Deduplication |
| `scripts/python/scoring.py` | Greatness scoring model |
| `scripts/python/export.py` | JSONL export + mongodump |
| `seed/capability_taxonomy.json` | 25+ speaking capabilities with full metadata |
| `seed/profession_taxonomy.json` | 22 profession categories |
| `seed/speakers_100.json` | 100 high-confidence verified speakers |
| `tests/` | pytest tests |

## MongoDB Collections

| Collection | Purpose |
|-----------|---------|
| `speakers` | Canonical verified speaker profiles |
| `candidate_speakers` | Unverified candidates from Wikidata/Pantheon |
| `speeches` | Individual speech records |
| `transcripts` | Transcript text and metadata |
| `sources` | Source provenance records |
| `evidence_items` | Evidence backing every claim |
| `capability_taxonomy` | Master taxonomy of speaking capabilities |
| `profession_taxonomy` | Normalized profession categories |
| `speaker_scores` | Score history per speaker |
| `extraction_runs` | Ingestion run audit log |
| `media_assets` | Audio/video metadata |
| `practice_drills` | Capability → trainable exercise mappings |

## Quick Commands (after setup)

```bash
# Start database
docker-compose up -d

# One-time DB setup (Node.js)
npm install
npm run db:setup

# Install Python deps
pip install -e ".[dev]"

# Seed data
python scripts/python/seed_taxonomies.py
python scripts/python/seed_speakers.py

# Discover candidates from Wikidata
python scripts/python/ingest_wikidata.py

# Score speakers
python scripts/python/scoring.py

# Dedup
python scripts/python/deduplicate.py

# Export
python scripts/python/export.py

# Run tests
pytest tests/
```

## Notes / Known Issues

(populated as they arise)
