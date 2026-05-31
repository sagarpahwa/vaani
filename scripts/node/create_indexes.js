/**
 * Vaani — Index Creator
 * Creates all indexes for the public_speaking_intelligence database.
 * Safe to re-run (createIndex is idempotent).
 * Run: node scripts/node/create_indexes.js
 */

import { MongoClient } from 'mongodb';
import 'dotenv/config';

const MONGO_URI = process.env.MONGO_URI
  || 'mongodb://vaani_admin:vaani_secret@localhost:27017/public_speaking_intelligence?authSource=admin';
const DB_NAME = process.env.MONGO_DB || 'public_speaking_intelligence';

async function createIndexes() {
  const client = new MongoClient(MONGO_URI);
  await client.connect();
  const db = client.db(DB_NAME);
  console.log(`✓ Connected — creating indexes on '${DB_NAME}'\n`);

  let total = 0;

  async function idx(colName, spec, opts = {}) {
    try {
      await db.collection(colName).createIndex(spec, opts);
      console.log(`  ✓ ${colName}: ${JSON.stringify(spec)}${opts.name ? ' (' + opts.name + ')' : ''}`);
      total++;
    } catch (e) {
      console.warn(`  ⚠ ${colName}: ${e.message}`);
    }
  }

  // ── speakers ─────────────────────────────────────────────────────────────
  console.log('speakers:');
  await idx('speakers', { slug: 1 },                              { unique: true, name: 'slug_unique' });
  await idx('speakers', { canonical_name: 1 },                   { name: 'canonical_name' });
  await idx('speakers', { 'external_ids.wikidata': 1 },          { sparse: true, name: 'ext_wikidata' });
  await idx('speakers', { 'external_ids.pantheon': 1 },          { sparse: true, name: 'ext_pantheon' });
  await idx('speakers', { profession_category: 1 },              { name: 'profession_category' });
  await idx('speakers', { country_or_region: 1 },                { name: 'country_or_region' });
  await idx('speakers', { era: 1 },                              { name: 'era' });
  await idx('speakers', { primary_language: 1 },                 { name: 'primary_language' });
  await idx('speakers', { speaker_archetypes: 1 },               { name: 'speaker_archetypes' });
  await idx('speakers', { signature_capability_ids: 1 },         { name: 'signature_capabilities' });
  await idx('speakers', { overall_speaker_score: -1 },           { name: 'overall_score_desc' });
  await idx('speakers', { greatness_score: -1 },                 { name: 'greatness_score_desc' });
  await idx('speakers', { ethical_alignment_score: -1 },         { name: 'ethical_alignment_desc' });
  await idx('speakers', { living_status: 1, greatness_score: -1},{ name: 'living_status_greatness' });
  await idx('speakers', { needs_review: 1 },                     { sparse: true, name: 'needs_review' });
  await idx('speakers',
    { canonical_name: 'text', aliases: 'text', impact_summary: 'text' },
    { name: 'speakers_text', weights: { canonical_name: 10, aliases: 5, impact_summary: 1 } }
  );

  // ── candidate_speakers ───────────────────────────────────────────────────
  console.log('\ncandidate_speakers:');
  await idx('candidate_speakers', { 'external_ids.wikidata': 1 },  { unique: true, sparse: true, name: 'ext_wikidata_unique' });
  await idx('candidate_speakers', { verification_status: 1 },      { name: 'verification_status' });
  await idx('candidate_speakers', { source: 1 },                   { name: 'source' });
  await idx('candidate_speakers', { profession_category: 1 },      { name: 'profession_category' });
  await idx('candidate_speakers', { slug: 1 },                     { sparse: true, name: 'slug' });

  // ── speeches ─────────────────────────────────────────────────────────────
  console.log('\nspeeches:');
  await idx('speeches', { speaker_id: 1 },               { name: 'speaker_id' });
  await idx('speeches', { year: 1 },                     { name: 'year' });
  await idx('speeches', { speech_context: 1 },           { name: 'speech_context' });
  await idx('speeches', { language: 1 },                 { name: 'language' });
  await idx('speeches', { memorability: -1 },            { name: 'memorability_desc' });
  await idx('speeches', { analysis_status: 1 },          { name: 'analysis_status' });
  await idx('speeches', { speaker_id: 1, year: -1 },     { name: 'speaker_year' });
  await idx('speeches', { title: 'text', famous_lines: 'text' },
    { name: 'speeches_text', weights: { title: 10, famous_lines: 5 } }
  );

  // ── transcripts ──────────────────────────────────────────────────────────
  console.log('\ntranscripts:');
  await idx('transcripts', { speech_id: 1 },              { unique: true, name: 'speech_id_unique' });
  await idx('transcripts', { speaker_id: 1 },             { name: 'speaker_id' });
  await idx('transcripts', { copyright_status: 1 },       { name: 'copyright_status' });
  await idx('transcripts', { storage_policy: 1 },         { name: 'storage_policy' });
  await idx('transcripts', { transcript_text_hash: 1 },   { sparse: true, name: 'text_hash' });

  // ── sources ──────────────────────────────────────────────────────────────
  console.log('\nsources:');
  await idx('sources', { url: 1 },             { unique: true, name: 'url_unique' });
  await idx('sources', { domain: 1 },          { name: 'domain' });
  await idx('sources', { source_type: 1 },     { name: 'source_type' });
  await idx('sources', { source_tier: 1 },     { name: 'source_tier' });
  await idx('sources', { reliability_score: -1},{ name: 'reliability_desc' });
  await idx('sources', { crawl_status: 1 },    { name: 'crawl_status' });

  // ── evidence_items ───────────────────────────────────────────────────────
  console.log('\nevidence_items:');
  await idx('evidence_items', { speaker_id: 1 },                   { name: 'speaker_id' });
  await idx('evidence_items', { speech_id: 1 },                    { sparse: true, name: 'speech_id' });
  await idx('evidence_items', { source_id: 1 },                    { name: 'source_id' });
  await idx('evidence_items', { claim_type: 1 },                   { name: 'claim_type' });
  await idx('evidence_items', { human_review_status: 1 },          { name: 'review_status' });
  await idx('evidence_items', { speaker_id: 1, claim_type: 1 },    { name: 'speaker_claim_type' });
  await idx('evidence_items', { confidence: -1 },                  { name: 'confidence_desc' });

  // ── capability_taxonomy ──────────────────────────────────────────────────
  console.log('\ncapability_taxonomy:');
  await idx('capability_taxonomy', { capability_id: 1 }, { unique: true, name: 'capability_id_unique' });
  await idx('capability_taxonomy', { parent_category: 1},{ name: 'parent_category' });
  await idx('capability_taxonomy', { trainable: 1 },     { name: 'trainable' });

  // ── profession_taxonomy ──────────────────────────────────────────────────
  console.log('\nprofession_taxonomy:');
  await idx('profession_taxonomy', { profession_id: 1 }, { unique: true, name: 'profession_id_unique' });

  // ── speaker_scores ───────────────────────────────────────────────────────
  console.log('\nspeaker_scores:');
  await idx('speaker_scores', { speaker_id: 1, scoring_version: -1 }, { name: 'speaker_version' });
  await idx('speaker_scores', { speaker_id: 1, created_at: -1 },      { name: 'speaker_history' });
  await idx('speaker_scores', { greatness_score: -1 },                { name: 'greatness_desc' });

  // ── extraction_runs ──────────────────────────────────────────────────────
  console.log('\nextraction_runs:');
  await idx('extraction_runs', { run_type: 1, started_at: -1 }, { name: 'run_type_time' });
  await idx('extraction_runs', { status: 1 },                   { name: 'status' });

  // ── media_assets ─────────────────────────────────────────────────────────
  console.log('\nmedia_assets:');
  await idx('media_assets', { speech_id: 1 },  { name: 'speech_id' });
  await idx('media_assets', { speaker_id: 1 }, { name: 'speaker_id' });
  await idx('media_assets', { platform: 1 },   { name: 'platform' });

  // ── practice_drills ──────────────────────────────────────────────────────
  console.log('\npractice_drills:');
  await idx('practice_drills', { capability_id: 1 },              { name: 'capability_id' });
  await idx('practice_drills', { difficulty: 1 },                 { name: 'difficulty' });
  await idx('practice_drills', { capability_id: 1, difficulty: 1},{ name: 'capability_difficulty' });

  console.log(`\n✓ Done — ${total} indexes created/verified.`);
  await client.close();
}

createIndexes().catch(err => {
  console.error('✗ Index creation failed:', err.message);
  process.exit(1);
});
