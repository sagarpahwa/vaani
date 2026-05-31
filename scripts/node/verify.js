/**
 * Vaani — DB Verification
 * Runs a suite of checks to confirm the database is healthy and seeded.
 * Run: node scripts/node/verify.js
 */

import { MongoClient } from 'mongodb';
import 'dotenv/config';

const MONGO_URI = process.env.MONGO_URI
  || 'mongodb://vaani_admin:vaani_secret@localhost:27017/public_speaking_intelligence?authSource=admin';
const DB_NAME = process.env.MONGO_DB || 'public_speaking_intelligence';

const PASS = '✓'; const FAIL = '✗'; const WARN = '⚠';

async function verify() {
  const client = new MongoClient(MONGO_URI);
  await client.connect();
  const db = client.db(DB_NAME);

  let passed = 0, failed = 0;
  const check = (label, ok, detail = '') => {
    const icon = ok ? PASS : FAIL;
    console.log(`  ${icon} ${label}${detail ? ': ' + detail : ''}`);
    ok ? passed++ : failed++;
  };

  // ── 1. Collections exist ─────────────────────────────────────────────────
  console.log('\n── Collections ─────────────────────────────────────────');
  const required = [
    'speakers','candidate_speakers','speeches','transcripts','sources',
    'evidence_items','capability_taxonomy','profession_taxonomy',
    'speaker_scores','extraction_runs','media_assets','practice_drills',
  ];
  const existing = (await db.listCollections().toArray()).map(c => c.name);
  for (const col of required) {
    check(col, existing.includes(col));
  }

  // ── 2. Indexes exist ─────────────────────────────────────────────────────
  console.log('\n── Key Indexes ─────────────────────────────────────────');
  const checkIndex = async (col, name) => {
    const indexes = await db.collection(col).indexInformation();
    check(`${col}.${name}`, name in indexes || Object.values(indexes).some(
      idx => idx.some && idx[0] && JSON.stringify(idx[0]).includes(name.replace(/_unique|_desc|_asc/,''))
    ));
  };
  // Spot-check a few key indexes
  const speakersIdx = await db.collection('speakers').indexInformation();
  check('speakers has slug_unique index', 'slug_unique' in speakersIdx);
  check('speakers has text index', Object.keys(speakersIdx).some(k => k.includes('text')));
  const sourcesIdx = await db.collection('sources').indexInformation();
  check('sources has url_unique index', 'url_unique' in sourcesIdx);
  const candidateIdx = await db.collection('candidate_speakers').indexInformation();
  check('candidate_speakers has wikidata unique index', 'ext_wikidata_unique' in candidateIdx);

  // ── 3. Seed data counts ──────────────────────────────────────────────────
  console.log('\n── Seed Counts ─────────────────────────────────────────');
  const counts = {};
  for (const col of required) {
    counts[col] = await db.collection(col).countDocuments();
  }
  for (const [col, n] of Object.entries(counts)) {
    const ok = col === 'capability_taxonomy' ? n >= 25
             : col === 'profession_taxonomy'  ? n >= 20
             : col === 'speakers'             ? n >= 10
             : col === 'sources'              ? n >= 5
             : true;
    const warn = !ok && n > 0;
    console.log(`  ${ok ? PASS : warn ? WARN : FAIL} ${col}: ${n} docs`);
    if (ok || warn) passed++; else failed++;
  }

  // ── 4. Sample speaker spot-check ─────────────────────────────────────────
  console.log('\n── Sample Speaker ──────────────────────────────────────');
  const speaker = await db.collection('speakers').findOne({}, { sort: { greatness_score: -1 } });
  if (speaker) {
    check('speaker has slug',       !!speaker.slug);
    check('speaker has source_ids', Array.isArray(speaker.source_ids) && speaker.source_ids.length > 0);
    check('speaker has capabilities', Array.isArray(speaker.speaking_capabilities) && speaker.speaking_capabilities.length > 0);
    console.log(`     Name: ${speaker.canonical_name}`);
    console.log(`     Greatness: ${speaker.greatness_score ?? 'unscored'}`);
  } else {
    console.log(`  ${WARN} No speakers in DB yet — run seed_speakers.py`);
  }

  // ── 5. Capability taxonomy spot-check ────────────────────────────────────
  console.log('\n── Capability Taxonomy ─────────────────────────────────');
  const cap = await db.collection('capability_taxonomy').findOne({ capability_id: 'strategic_pause' });
  check('strategic_pause capability exists', !!cap);
  if (cap) {
    check('has definition',         !!cap.definition);
    check('has observable_markers', Array.isArray(cap.observable_markers));
    check('has parent_category',    !!cap.parent_category);
  }

  // ── Summary ──────────────────────────────────────────────────────────────
  console.log(`\n──────────────────────────────────────────────────────`);
  console.log(`  ${PASS} Passed: ${passed}   ${FAIL} Failed: ${failed}`);
  if (failed > 0) {
    console.log(`\n  Some checks failed — run seed scripts first:`);
    console.log(`  python3 scripts/python/seed_taxonomies.py`);
    console.log(`  python3 scripts/python/seed_speakers.py`);
  } else {
    console.log(`\n  Database is healthy ✓`);
  }

  await client.close();
  process.exit(failed > 0 ? 1 : 0);
}

verify().catch(err => {
  console.error('✗ Verify failed:', err.message);
  process.exit(1);
});
