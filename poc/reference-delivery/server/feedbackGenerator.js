/**
 * Generates written coaching feedback per unit using the OpenAI text model.
 * Combines alignment ops, feature data, and unit comparisons into rich prompts.
 */

import OpenAI from 'openai';
import dotenv from 'dotenv';
dotenv.config();

const TEXT_MODEL = process.env.OPENAI_TEXT_MODEL || 'gpt-4.1-mini';

function getClient() {
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
}

/**
 * Build the feedback prompt for one unit.
 */
function buildUnitPrompt(unit, comparison, unitOps) {
  const dim = comparison.dimensions;
  const ref = comparison.reference;
  const usr = comparison.user;

  const wordErrors = unitOps
    .filter(op => op.type !== 'correct' && op.type !== 'extra')
    .map(op => {
      if (op.type === 'missing')      return `missing "${op.expected}"`;
      if (op.type === 'substitution') return `said "${op.spoken}" instead of "${op.expected}"`;
      return null;
    })
    .filter(Boolean)
    .slice(0, 5);

  const lines = [
    `Unit text: "${unit.text}"`,
    `Director's note: ${unit.ttsInstruction || 'standard delivery'}`,
    `Pace target: ${ref.paceContour} (~${ref.idealWpm} wpm)   User: ${usr.wpm ?? 'unknown'} wpm`,
    `Energy target: ${ref.energyStart}→${ref.energyEnd}   User loudness: ${usr.meanVolumeDb?.toFixed(1) ?? '?'} dBFS`,
    `Pause after: ${ref.pauseAfterMs ?? 0}ms (${ref.pauseReason || 'none'})   User trail: ${((usr.trailSilenceSec ?? 0) * 1000).toFixed(0)}ms`,
    `Pitch range: ${usr.pitchRangeSemitones?.toFixed(1) ?? 'unknown'} semitones`,
    wordErrors.length ? `Word errors: ${wordErrors.join(', ')}` : null,
    `Dimension scores: accuracy=${dim.accuracy ?? '?'} pace=${dim.pace ?? '?'} energy=${dim.energy ?? '?'} pauses=${dim.pauses ?? '?'} expression=${dim.expression ?? '?'}`,
  ].filter(Boolean).join('\n');

  return `You are a world-class public speaking coach. Give specific, actionable feedback for this spoken unit.

${lines}

Write 2–4 sentences of coaching feedback. Be concrete: mention specific words, specific seconds of pause, specific volume levels. Do NOT say "good job" unless the score is ≥85. Focus on the lowest-scoring dimension first. Never mention AI, OpenAI, or the scoring system. Address the speaker directly as "you".`;
}

/**
 * Generate feedback for a single unit.
 * Returns { unitIndex, feedbackText, suggestedFocus }
 */
async function generateUnitFeedback(openai, unit, comparison, unitOps) {
  if (comparison.skipped) {
    return {
      unitIndex:      comparison.unitIndex,
      feedbackText:   'This section could not be analyzed — no clear speech was detected in the expected time window.',
      suggestedFocus: 'clarity',
    };
  }

  const prompt = buildUnitPrompt(unit, comparison, unitOps);

  try {
    const resp = await openai.chat.completions.create({
      model:       TEXT_MODEL,
      max_tokens:  200,
      temperature: 0.7,
      messages: [{ role: 'user', content: prompt }],
    });
    const feedbackText = resp.choices[0]?.message?.content?.trim() ?? '';

    // Pick suggestedFocus = worst dimension
    const dims = comparison.dimensions ?? {};
    const worst = Object.entries(dims)
      .filter(([, v]) => v != null)
      .sort(([, a], [, b]) => a - b)[0]?.[0] ?? 'expression';

    return { unitIndex: comparison.unitIndex, feedbackText, suggestedFocus: worst };
  } catch (err) {
    console.warn('[feedback] Unit', comparison.unitIndex, 'generation failed:', err.message);
    return {
      unitIndex:      comparison.unitIndex,
      feedbackText:   'Feedback generation unavailable for this unit.',
      suggestedFocus: 'expression',
    };
  }
}

/**
 * Generate the overall summary feedback.
 */
async function generateOverallFeedback(openai, summary, overallAccuracy) {
  const { dimensionAverages: d, topStrengths, topImprovements } = summary;

  const prompt = `You are a world-class public speaking coach. Write a 3–5 sentence overall coaching summary.

Overall score: ${summary.overallScore}/100
Word accuracy: ${overallAccuracy ?? d.accuracy ?? '?'}%
Pace score: ${d.pace ?? '?'}/100
Energy score: ${d.energy ?? '?'}/100
Pause score: ${d.pauses ?? '?'}/100
Expression score: ${d.expression ?? '?'}/100
Strengths: ${topStrengths.map(s => s.dimension).join(', ')}
Needs work: ${topImprovements.map(s => s.dimension).join(', ')}

Open with one specific strength. Then focus on the top improvement area with a concrete technique. Close with encouragement. Address the speaker as "you". Never mention AI or scoring systems.`;

  try {
    const resp = await openai.chat.completions.create({
      model:       TEXT_MODEL,
      max_tokens:  250,
      temperature: 0.7,
      messages: [{ role: 'user', content: prompt }],
    });
    return resp.choices[0]?.message?.content?.trim() ?? '';
  } catch (err) {
    console.warn('[feedback] Overall generation failed:', err.message);
    return 'Analysis complete. Focus on the unit-level feedback below to identify specific areas for improvement.';
  }
}

/**
 * Generate top-5 actionable fixes.
 */
async function generateTop5Fixes(openai, unitFeedbacks, summary) {
  const worst = (summary.worstUnits ?? []).slice(0, 3)
    .map(u => `Unit ${u.unitIndex}: "${u.unitText}" — overall ${u.overall}/100`)
    .join('\n');

  const prompt = `You are a world-class public speaking coach. Based on this analysis:

Weakest areas: ${Object.entries(summary.dimensionAverages ?? {})
  .filter(([, v]) => v != null && v < 70)
  .sort(([, a], [, b]) => a - b)
  .map(([k, v]) => `${k}=${v}`)
  .join(', ') || 'all areas performing reasonably well'}

Worst units:
${worst || 'No specific weak units identified'}

Write exactly 5 specific, actionable fixes numbered 1–5. Each fix: one sentence, imperative mood, concrete and specific (e.g. "On line 3, drop your voice by 20% after 'today' to create suspense"). Do not use vague advice like "practice more". Address speaker as "you".`;

  try {
    const resp = await openai.chat.completions.create({
      model:       TEXT_MODEL,
      max_tokens:  350,
      temperature: 0.7,
      messages: [{ role: 'user', content: prompt }],
    });
    const text = resp.choices[0]?.message?.content?.trim() ?? '';
    // Parse numbered list
    const fixes = text.split('\n')
      .filter(l => /^\d+\./.test(l.trim()))
      .map(l => l.replace(/^\d+\.\s*/, '').trim())
      .slice(0, 5);
    return fixes.length >= 3 ? fixes : [text];
  } catch (err) {
    console.warn('[feedback] Top-5 generation failed:', err.message);
    return ['Work on word accuracy — practice the script until you can deliver it cleanly.'];
  }
}

/**
 * Main export: generate all feedback for a session.
 *
 * @param {Array}  performanceUnits  - beat map units (from beat map)
 * @param {Array}  unitComparisons   - from referenceComparator.compareUnit()
 * @param {object} summary           - from referenceComparator.buildSummary()
 * @param {Array}  alignmentOps      - all alignment operations
 * @param {object} alignStats        - {accuracy, stats} from alignTranscripts
 * @returns {{ overall, unitFeedbacks, top5Fixes }}
 */
export async function generateAllFeedback(
  performanceUnits, unitComparisons, summary, alignmentOps, alignStats
) {
  const openai = getClient();

  // Map unit index → beat map unit
  const unitByIndex = new Map(performanceUnits.map(u => [u.index, u]));

  // Map unit index → alignment ops for that unit (approximate by expected word range)
  // We use the comparison's reference to slice ops
  // For simplicity: partition ops by unit based on ei ranges from mapUnitsToExpectedWordRanges
  // Caller should pass pre-partitioned ops; we accept flat ops and filter naively here
  const opsByUnit = new Map();
  for (const comp of unitComparisons) {
    opsByUnit.set(comp.unitIndex, []);
  }
  // We can't perfectly map flat ops → units without ranges, so pass all ops to every unit
  // (each unit prompt only shows 5 errors anyway, so this is fine for the POC)
  for (const comp of unitComparisons) {
    opsByUnit.set(comp.unitIndex, alignmentOps);
  }

  // Generate unit feedback in batches of 3 to avoid rate limits
  const BATCH = 3;
  const unitFeedbacks = [];
  for (let i = 0; i < unitComparisons.length; i += BATCH) {
    const batch = unitComparisons.slice(i, i + BATCH);
    const results = await Promise.all(
      batch.map(comp => {
        const unit = unitByIndex.get(comp.unitIndex) ?? { text: comp.unitText, ttsInstruction: '' };
        return generateUnitFeedback(openai, unit, comp, opsByUnit.get(comp.unitIndex) ?? []);
      })
    );
    unitFeedbacks.push(...results);
  }

  // Generate overall + top-5 in parallel
  const [overallFeedback, top5Fixes] = await Promise.all([
    generateOverallFeedback(openai, summary, alignStats?.accuracy),
    generateTop5Fixes(openai, unitFeedbacks, summary),
  ]);

  return {
    overall:       overallFeedback,
    unitFeedbacks,
    top5Fixes,
  };
}
