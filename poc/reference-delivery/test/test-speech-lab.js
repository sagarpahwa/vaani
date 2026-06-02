/**
 * Regression test: bad_user_audio.webm must score ≤ 5/100 with
 * validity = catastrophic_script_mismatch.
 *
 * Usage:
 *   npm run test:speech-lab
 *
 * Requires:
 *   - Server running: npm run dev  (in another terminal)
 *   - Fixture file:   fixtures/bad_user_audio.webm
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT      = path.join(__dirname, '..');
const PORT      = process.env.PORT || 8081;
const BASE_URL  = `http://localhost:${PORT}`;
const FIXTURE   = path.join(ROOT, 'fixtures', 'bad_user_audio.webm');

// The TinyTrail script used as the expected text
const TINYTRAIL_SCRIPT = `Today, we are excited to introduce TinyTrail, a new toy created for children who love to explore, imagine, and learn through play.

TinyTrail is not just a toy you hand to a child. It is a little adventure box. Every piece is designed to help kids build stories, solve small challenges, and create their own world using their hands and imagination.

In a time when children spend more and more time on screens, TinyTrail brings them back to real play. It helps develop creativity, focus, motor skills, and confidence—without making learning feel like learning.

Parents get a toy they can trust. Children get a world they can control.

TinyTrail is safe, colorful, durable, and made for endless play.

Today, we are not just launching a toy.

We are launching curiosity.

TinyTrail. Small pieces. Big adventures.`;

// ── SSE parser ────────────────────────────────────────────────────────

async function parseSSEResponse(response) {
  const text = await response.text();
  const events = [];
  const parts = text.split('\n\n');
  for (const part of parts) {
    if (!part.trim()) continue;
    let evtName = 'message', dataStr = '';
    for (const line of part.split('\n')) {
      if (line.startsWith('event: ')) evtName = line.slice(7).trim();
      else if (line.startsWith('data: ')) dataStr = line.slice(6);
    }
    if (dataStr) {
      try { events.push({ event: evtName, data: JSON.parse(dataStr) }); } catch { /* ignore */ }
    }
  }
  return events;
}

// ── Assertion helpers ─────────────────────────────────────────────────

let passed = 0;
let failed = 0;

function assert(condition, msg, detail = '') {
  if (condition) {
    console.log(`  ✓  ${msg}`);
    passed++;
  } else {
    console.error(`  ✗  ${msg}${detail ? `\n     → ${detail}` : ''}`);
    failed++;
  }
}

// ── Main test ─────────────────────────────────────────────────────────

async function run() {
  console.log('\nVaani Speech Lab — Regression Test');
  console.log('══════════════════════════════════\n');

  // ── Pre-flight checks ─────────────────────────────────────────────

  if (!fs.existsSync(FIXTURE)) {
    console.log('SKIP  Fixture not found: fixtures/bad_user_audio.webm');
    console.log('      Place the bad-recording WebM file at that path and re-run.\n');
    process.exit(0);
  }
  console.log(`  Fixture: ${path.relative(ROOT, FIXTURE)}`);

  let health;
  try {
    const r = await fetch(`${BASE_URL}/api/health/audio`);
    health = await r.json();
  } catch {
    console.error('FAIL  Server is not running at ' + BASE_URL);
    console.error('      Start it first: npm run dev\n');
    process.exit(1);
  }
  console.log(`  Server: OK  (prosodyReady=${health?.prosodyReady})\n`);

  // ── Submit fixture ────────────────────────────────────────────────

  console.log('Submitting bad fixture to /api/analyze-user-speech…\n');
  const fileData = fs.readFileSync(FIXTURE);
  const blob = new Blob([fileData], { type: 'audio/webm' });
  const form = new FormData();
  form.append('audio', blob, 'bad_user_audio.webm');
  form.append('script', TINYTRAIL_SCRIPT);

  let response;
  try {
    response = await fetch(`${BASE_URL}/api/analyze-user-speech`, {
      method: 'POST',
      body: form,
    });
  } catch (err) {
    console.error('FAIL  Request error:', err.message);
    process.exit(1);
  }

  // ── Parse SSE events ──────────────────────────────────────────────

  const events = await parseSSEResponse(response);
  const errorEvt    = events.find(e => e.event === 'error');
  const completeEvt = events.find(e => e.event === 'complete');

  if (errorEvt) {
    console.error('FAIL  Server returned error:', errorEvt.data?.message);
    process.exit(1);
  }

  const result = completeEvt?.data ?? null;
  console.log('Results:');

  // ── Assertions ────────────────────────────────────────────────────

  assert(
    result !== null,
    'Received a complete event',
    'No complete event in SSE stream'
  );

  const score    = result?.summary?.overallScore;
  const validity = result?.summary?.validity;
  const maxOver  = result?.validityInfo?.maxOverall ?? result?.summary?.maxOverall;
  const firstFix = result?.feedback?.top5Fixes?.[0] ?? '';

  assert(
    score != null && score <= 5,
    `Overall score ≤ 5  (got ${score})`,
    `Expected a score of 1–5 for a catastrophic mismatch`
  );

  assert(
    validity === 'catastrophic_script_mismatch',
    `validity = catastrophic_script_mismatch  (got "${validity}")`
  );

  assert(
    maxOver != null && maxOver <= 5,
    `maxOverall ≤ 5  (got ${maxOver})`
  );

  assert(
    firstFix.toLowerCase().includes('complete the script') ||
    firstFix.toLowerCase().includes('complete') ||
    firstFix.toLowerCase().includes('script'),
    `First fix mentions script completion`,
    `Got: "${firstFix.slice(0, 80)}"`
  );

  assert(
    Array.isArray(result?.feedback?.top5Fixes) && result.feedback.top5Fixes.length >= 3,
    `At least 3 top fixes generated  (got ${result?.feedback?.top5Fixes?.length ?? 0})`
  );

  const alignment = result?.alignment;
  assert(
    alignment != null && alignment.stats != null,
    'Alignment stats present'
  );

  assert(
    (alignment?.stats?.coverage ?? 1) < 0.50,
    `Coverage < 50%  (got ${(alignment?.stats?.coverage * 100)?.toFixed(1)}%)`
  );

  // ── Summary ───────────────────────────────────────────────────────

  console.log(`\n${'─'.repeat(40)}`);
  console.log(`${passed} passed,  ${failed} failed`);

  if (failed === 0) {
    console.log('\n✅  All assertions passed.\n');
  } else {
    console.log('\n❌  Some assertions failed — check the scoring engine.\n');
    process.exit(1);
  }
}

run().catch(err => {
  console.error('\nUnhandled test error:', err.message ?? err);
  process.exit(1);
});
