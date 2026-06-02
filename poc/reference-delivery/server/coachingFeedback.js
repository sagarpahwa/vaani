/**
 * Human-language coaching feedback generator.
 *
 * Rules:
 * - No percentages in top fixes.
 * - No raw dB or ms numbers in top fixes.
 * - Every fix: what happened → why it hurts → what to do → the effect.
 * - When coverage < 50%, first fix is always "complete the script".
 * - Advanced delivery coaching only when script is mostly complete.
 */
import OpenAI from 'openai';
import dotenv from 'dotenv';
dotenv.config();

const TEXT_MODEL = process.env.OPENAI_TEXT_MODEL || 'gpt-4.1-mini';

function getClient() {
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
}

// ── Overview messages ─────────────────────────────────────────────────

export function buildOverviewMessage(validity, overallScore) {
  if (validity === 'catastrophic_script_mismatch' || overallScore < 10) {
    return 'This attempt is not yet a valid delivery performance because too much of the script was skipped or changed. First complete the speech accurately. Then Vaani can coach your pace, pauses, emphasis, and emotion.';
  }
  if (validity === 'major_script_mismatch' || overallScore < 25) {
    return 'You attempted the script, but the structure is broken. Focus first on completing the full speech and keeping the ideas in order.';
  }
  if (overallScore < 40) {
    return 'You attempted the speech but missed key sections. Practice until you can get through the full script without stopping, then work on delivery.';
  }
  if (overallScore < 70) {
    return 'The script is mostly present. Now improve pacing, pauses, and emphasis — especially on the product name and the key contrast moments.';
  }
  return 'You are ready for advanced delivery work: emotional arc, word pressure, and presence.';
}

// ── Fixed top-fixes for catastrophic/major ────────────────────────────

function getScriptCompletionFixes(validityInfo, alignStats) {
  const { validity } = validityInfo;
  const fixes = [];

  if (validity === 'catastrophic_script_mismatch' || validity === 'major_script_mismatch') {
    fixes.push('Complete the script first. You skipped or changed too much of the speech, so Vaani cannot judge advanced delivery yet. Practice reading the full script from start to finish without stopping.');
    fixes.push('Say the product name clearly every time. The product name is the hero of the speech. If the listener misses it, the whole pitch loses power.');
    fixes.push('Keep the main ideas in order. The speech should move from product introduction, to child benefit, to screen-time contrast, to launch reveal. Each section must be present.');
    fixes.push('Do not rush through the benefit list. Give each benefit its own space — creativity, focus, motor skills, confidence — so the listener can picture the value of each one.');
    fixes.push('Land the ending cleanly. The final lines should sound intentional and memorable, not rushed or thrown away.');
  }

  return fixes;
}

// ── AI-generated fixes for partial/valid attempts ─────────────────────

const TOP5_SYSTEM = `You are a world-class public speaking coach giving feedback.

Rules:
- Never use percentages (e.g., "increase by 15%").
- Never use technical numbers like dB, milliseconds, Hz, or wpm in primary feedback.
- Numbers only belong in Advanced Diagnostics — never in top fixes.
- Every fix must follow this structure:
  1. What you did
  2. Why it hurts the listener
  3. What to do instead
  4. What effect it creates
- Keep each fix to 1–3 sentences.
- Be concrete: reference specific words or moments from the script.
- Use "you" to address the speaker.
- Never say "great job" or be encouraging when the score is below 60.
- Fixes must be about delivery coaching, not script memorization.`;

async function generateTop5WithAI(openai, summary, alignStats, worstUnits) {
  const dimLines = Object.entries(summary.dimensionAverages ?? {})
    .filter(([, v]) => v != null)
    .sort(([, a], [, b]) => a - b)
    .map(([k, v]) => `${k}: ${v}/100`)
    .join(', ');

  const worstLines = (worstUnits ?? []).slice(0, 3)
    .map(u => `"${u.unitText}" — scored ${u.overall}/100`)
    .join('\n');

  const prompt = `Speaker analysis:
Overall score: ${summary.overallScore}/100
Weakest dimensions: ${dimLines}
Worst sections:
${worstLines || '(none identified)'}

Write exactly 5 coaching fixes numbered 1–5.
Each fix is 1–3 sentences.
Follow the structure: what happened → why it hurts → what to do → the effect.
Do not use percentages, dB, ms, Hz, or wpm in any fix.
Focus on the lowest-scoring dimensions first.`;

  try {
    const resp = await openai.chat.completions.create({
      model:       TEXT_MODEL,
      max_tokens:  500,
      temperature: 0.6,
      messages: [
        { role: 'system', content: TOP5_SYSTEM },
        { role: 'user',   content: prompt },
      ],
    });
    const text = resp.choices[0]?.message?.content?.trim() ?? '';
    return text.split('\n')
      .filter(l => /^\d+[.)]\s/.test(l.trim()))
      .map(l => l.replace(/^\d+[.)]\s*/, '').trim())
      .filter(Boolean)
      .slice(0, 5);
  } catch (err) {
    console.warn('[coaching] Top-5 AI generation failed:', err.message);
    return null;
  }
}

// ── Per-unit feedback ─────────────────────────────────────────────────

const UNIT_SYSTEM = `You are a world-class public speaking coach. Write per-sentence delivery feedback.

Rules:
- 2–4 sentences maximum.
- Be concrete: reference the specific words in the text.
- No percentages, no dB/ms/Hz numbers.
- Do not give delivery advice if the unit was mostly skipped.
- Address the speaker as "you".
- If the unit was mostly correct but delivery was weak, give specific delivery guidance.`;

async function generateUnitFeedback(openai, unit, score, unitOps) {
  if (score.unitStatus === 'mostly_skipped') {
    return { unitIndex: score.unitIndex, feedbackText: 'This part was mostly skipped. Focus on completing the script before coaching delivery here.' };
  }
  if (score.unitStatus === 'too_short_to_score') {
    return { unitIndex: score.unitIndex, feedbackText: 'Not enough audio was detected for this section.' };
  }

  const missing = unitOps.filter(o => o.type === 'missing').map(o => `"${o.expected}"`).slice(0, 4).join(', ');
  const subs    = unitOps.filter(o => o.type === 'substitution').map(o => `"${o.expected}"→"${o.spoken}"`).slice(0, 3).join(', ');
  const d       = score.dimensions ?? {};
  const worstDim = Object.entries(d).filter(([,v]) => v != null).sort(([,a],[,b]) => a-b)[0]?.[0];

  const prompt = `Unit text: "${unit.text}"
Director's note: ${unit.ttsInstruction ?? 'standard delivery'}
Score: ${score.overall ?? '?'}/100  Status: ${score.unitStatus}
${missing ? `Words skipped: ${missing}` : ''}
${subs    ? `Changed words: ${subs}` : ''}
Weakest dimension: ${worstDim ?? 'unknown'}
User pace: ${score.user?.wpm ?? '?'} wpm (target ~${score.reference?.idealWpm ?? 135} wpm)

Write 2–4 sentences of specific coaching feedback. Focus on the weakest dimension first.
Do not use percentages or technical units in your response.`;

  try {
    const resp = await openai.chat.completions.create({
      model:       TEXT_MODEL,
      max_tokens:  180,
      temperature: 0.65,
      messages: [
        { role: 'system', content: UNIT_SYSTEM },
        { role: 'user',   content: prompt },
      ],
    });
    return { unitIndex: score.unitIndex, feedbackText: resp.choices[0]?.message?.content?.trim() ?? '' };
  } catch (err) {
    console.warn('[coaching] Unit', score.unitIndex, 'failed:', err.message);
    return { unitIndex: score.unitIndex, feedbackText: 'Coaching unavailable for this unit.' };
  }
}

// ── Overall summary ───────────────────────────────────────────────────

async function generateOverallSummary(openai, summary, alignStats) {
  const { validity, overallScore } = summary;

  if (validity === 'catastrophic_script_mismatch' || overallScore < 10) {
    return buildOverviewMessage(validity, overallScore);
  }

  const prompt = `Speaker's performance:
Score: ${overallScore}/100
Validity: ${validity}
Word accuracy: ${Math.round((alignStats.correct / Math.max(alignStats.total, 1)) * 100)}%
Strengths: ${Object.entries(summary.dimensionAverages ?? {}).filter(([,v])=>v!=null&&v>=70).map(([k])=>k).join(', ') || 'none'}
Needs work: ${Object.entries(summary.dimensionAverages ?? {}).filter(([,v])=>v!=null&&v<60).map(([k])=>k).join(', ') || 'none'}

Write 2–4 sentences of overall coaching. Open with the single biggest strength (if any).
Then name the top improvement area with a specific technique.
Close with what will happen when they fix it — what the listener will feel.
No percentages. No technical units. Address as "you".`;

  try {
    const resp = await openai.chat.completions.create({
      model:       TEXT_MODEL,
      max_tokens:  220,
      temperature: 0.65,
      messages: [{ role: 'user', content: prompt }],
    });
    return resp.choices[0]?.message?.content?.trim() ?? buildOverviewMessage(validity, overallScore);
  } catch (err) {
    console.warn('[coaching] Overall summary failed:', err.message);
    return buildOverviewMessage(validity, overallScore);
  }
}

// ── Main export ───────────────────────────────────────────────────────

/**
 * Generate all coaching feedback for a session.
 *
 * @param {Array}  performanceUnits - beat map units
 * @param {Array}  unitScores       - from scoringEngine.scoreUnit()
 * @param {object} summary          - from scoringEngine.buildSessionSummary()
 * @param {Array}  alignmentOps     - all alignment operations
 * @param {object} alignStats       - {correct, missing, extra, substitution, total, coverage}
 * @param {object} validityInfo     - {validity, maxOverall, capReason, coverage}
 */
export async function generateAllFeedback(
  performanceUnits, unitScores, summary, alignmentOps, alignStats, validityInfo
) {
  const openai = getClient();
  const { validity } = validityInfo;
  const unitByIndex = new Map(performanceUnits.map(u => [u.index, u]));

  // ── Overall summary ─────────────────────────────────────────────────
  const overallFeedback = await generateOverallSummary(openai, summary, alignStats);

  // ── Top 5 fixes ─────────────────────────────────────────────────────
  let top5Fixes;
  if (validity === 'catastrophic_script_mismatch' || validity === 'major_script_mismatch') {
    top5Fixes = getScriptCompletionFixes(validityInfo, alignStats);
  } else {
    const aiTop5 = await generateTop5WithAI(openai, summary, alignStats, summary.worstUnits);
    top5Fixes = aiTop5 ?? getScriptCompletionFixes(validityInfo, alignStats);
  }

  // ── Per-unit feedback (batch of 3) ──────────────────────────────────
  // Skip units that are mostly_skipped or too_short — use templated messages
  const unitFeedbacks = [];
  const BATCH = 3;
  for (let i = 0; i < unitScores.length; i += BATCH) {
    const batch = unitScores.slice(i, i + BATCH);
    const results = await Promise.all(batch.map(score => {
      const unit = unitByIndex.get(score.unitIndex) ?? { text: score.unitText ?? '', ttsInstruction: '' };
      // Slice ops for this unit (approximate — no range info here, pass all ops)
      return generateUnitFeedback(openai, unit, score, alignmentOps);
    }));
    unitFeedbacks.push(...results);
  }

  return { overall: overallFeedback, unitFeedbacks, top5Fixes };
}
