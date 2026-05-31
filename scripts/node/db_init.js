/**
 * Vaani — DB Initializer
 * Creates the public_speaking_intelligence database, all collections with
 * JSON Schema validators, and the candidate_speakers collection.
 *
 * Safe to re-run: checks existence before creating.
 * Run: node scripts/node/db_init.js
 */

import { MongoClient } from 'mongodb';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import 'dotenv/config';

const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT  = join(__dir, '..', '..');

const MONGO_URI = process.env.MONGO_URI
  || 'mongodb://vaani_admin:vaani_secret@localhost:27017/public_speaking_intelligence?authSource=admin';
const DB_NAME = process.env.MONGO_DB || 'public_speaking_intelligence';

// ── Collection definitions ───────────────────────────────────────────────────
const COLLECTIONS = [
  { name: 'speakers',            schemaFile: 'speakers.json',            capped: false },
  { name: 'candidate_speakers',  schemaFile: 'candidate_speakers.json',  capped: false },
  { name: 'speeches',            schemaFile: 'speeches.json',            capped: false },
  { name: 'transcripts',         schemaFile: 'transcripts.json',         capped: false },
  { name: 'sources',             schemaFile: 'sources.json',             capped: false },
  { name: 'evidence_items',      schemaFile: 'evidence_items.json',      capped: false },
  { name: 'capability_taxonomy', schemaFile: 'capability_taxonomy.json', capped: false },
  { name: 'profession_taxonomy', schemaFile: 'profession_taxonomy.json', capped: false },
  { name: 'speaker_scores',      schemaFile: 'speaker_scores.json',      capped: false },
  { name: 'extraction_runs',     schemaFile: 'extraction_runs.json',     capped: false },
  { name: 'media_assets',        schemaFile: 'media_assets.json',        capped: false },
  { name: 'practice_drills',     schemaFile: 'practice_drills.json',     capped: false },
];

function loadSchema(filename) {
  const path = join(ROOT, 'schemas', filename);
  return JSON.parse(readFileSync(path, 'utf-8'));
}

async function initDB() {
  const client = new MongoClient(MONGO_URI);
  await client.connect();
  console.log(`✓ Connected to MongoDB`);

  const db = client.db(DB_NAME);
  const existing = (await db.listCollections().toArray()).map(c => c.name);
  console.log(`  Existing collections: [${existing.join(', ') || 'none'}]`);

  for (const col of COLLECTIONS) {
    if (existing.includes(col.name)) {
      // Update validator on existing collection
      try {
        const schema = loadSchema(col.schemaFile);
        await db.command({
          collMod: col.name,
          validator: schema,
          validationLevel: 'moderate',
          validationAction: 'warn',
        });
        console.log(`  ↻ Updated validator: ${col.name}`);
      } catch (e) {
        console.warn(`  ⚠ Could not update validator for ${col.name}: ${e.message}`);
      }
    } else {
      const schema = loadSchema(col.schemaFile);
      await db.createCollection(col.name, {
        validator: schema,
        validationLevel: 'moderate',   // warn on existing docs, strict on new
        validationAction: 'warn',       // log violations but don't reject (safe for iteration)
      });
      console.log(`  ✓ Created: ${col.name}`);
    }
  }

  // Create schema_version field default via application — no TTL needed
  console.log('\n✓ All collections ready.');
  await client.close();
}

initDB().catch(err => {
  console.error('✗ DB init failed:', err.message);
  process.exit(1);
});
