/**
 * Compares user unit features against the reference beat map targets.
 * Returns per-unit dimension scores and a top-level summary.
 *
 * Dimensions scored per unit:
 *   - accuracy   (word accuracy from alignment — correct / total expected)
 *   - pace       (words/min vs beat map paceContour target)
 *   - energy     (loudness vs beat map energyStart/End targets)
 *   - pauses     (pause placement vs beat map pauseAfterMs)
 *   - expression (pitch range / monotone score — how expressive vs flat)
 *
 * Each dimension: 0–100 (100 = matches reference perfectly)
 */

// ── Beat map pace bands (slow / medium / fast) → approximate words/min ranges
const PACE_BAND = {
  slow:   { min: 80,  ideal: 105, max: 130 },
  medium: { min: 110, ideal: 135, max: 160 },
  fast:   { min: 150, ideal: 175, max: 210 },
};

/**
 * Map a paceContour string like "slow→fast" or "medium" to an ideal WPM.
 */
function paceContourToIdealWpm(paceContour = 'medium') {
  const last = paceContour.split('→').pop().trim().toLowerCase();
  return PACE_BAND[last]?.ideal ?? PACE_BAND.medium.ideal;
}

/**
 * Score pace: 100 if within ±10% of ideal, degrades to 0 at ±60%.
 */
function scorePace(actualWpm, idealWpm) {
  if (!actualWpm || !idealWpm) return null;
  const ratio = actualWpm / idealWpm;
  const dev = Math.abs(1 - ratio);
  if (dev <= 0.10) return 100;
  if (dev >= 0.60) return 0;
  return Math.round(100 * (1 - (dev - 0.10) / 0.50));
}

/**
 * Score energy match.
 * We compare the user's meanVolumeDb relative difference vs the beat map energy level (0–1).
 * energy in beat map is 0–1 scalar (0=quiet, 1=full power).
 * User loudness is -60..0 dBFS range.
 * We use a simple normalization: map -30..0 dBFS → 0..1 and compare.
 */
function scoreEnergy(meanVolumeDb, energyTarget) {
  if (meanVolumeDb == null || energyTarget == null) return null;
  // Normalize user loudness: clamp to -30..0, then 0..1
  const normalized = Math.max(0, Math.min(1, (meanVolumeDb + 30) / 30));
  const dev = Math.abs(normalized - energyTarget);
  if (dev <= 0.10) return 100;
  if (dev >= 0.60) return 0;
  return Math.round(100 * (1 - (dev - 0.10) / 0.50));
}

/**
 * Score pause after unit.
 * Compare actualPauseMs (silence at end of user clip) vs beatMap pauseAfterMs.
 * Within 30% → 100. Beyond 80% off → 0.
 */
function scorePause(actualTrailSilenceMs, targetPauseMs) {
  if (!targetPauseMs) return null; // no pause target → skip
  if (!actualTrailSilenceMs) return 40; // user gave no pause when one was expected
  const ratio = actualTrailSilenceMs / targetPauseMs;
  const dev = Math.abs(1 - ratio);
  if (dev <= 0.30) return 100;
  if (dev >= 0.80) return 0;
  return Math.round(100 * (1 - (dev - 0.30) / 0.50));
}

/**
 * Score expression (pitch variety).
 * Beat map gives energyStart/End + pitchContour hints.
 * We use prosody.pitchRangeSemitones: 0 = totally flat, 8+ = very expressive.
 * Target range: ≥4 semitones for expressive units, ≥2 for quieter ones.
 */
function scoreExpression(prosody, energyTarget) {
  if (!prosody) return null;
  const range = prosody.pitchRangeSemitones ?? 0;
  // Higher energy target → expect more expression
  const minRange = energyTarget >= 0.7 ? 4 : 2;
  if (range >= minRange + 2) return 100;
  if (range <= 0.5) return 20;
  const frac = (range - 0.5) / (minRange + 1.5);
  return Math.round(20 + 80 * Math.min(1, frac));
}

/**
 * Compare a single user unit against its beat map unit.
 *
 * @param {object} unitFeature   - from audioFeatureExtractor (enriched with prosody)
 * @param {object} beatMapUnit   - from the stored beat map (performanceUnits[i])
 * @param {object} alignStats    - {correct, total} for this unit's expected words
 * @returns {object} dimensionScores + overall + metadata
 */
export function compareUnit(unitFeature, beatMapUnit, alignStats) {
  if (!unitFeature || unitFeature.tooShort || unitFeature.noTimestamp) {
    return {
      unitIndex:  beatMapUnit.index ?? 0,
      skipped:    true,
      reason:     unitFeature?.tooShort ? 'too_short' : 'no_timestamp',
    };
  }

  // Accuracy
  const accuracyScore = alignStats?.total > 0
    ? Math.round((alignStats.correct / alignStats.total) * 100)
    : null;

  // Pace
  const idealWpm  = paceContourToIdealWpm(beatMapUnit.paceContour);
  const paceScore = scorePace(unitFeature.wpm, idealWpm);

  // Energy (use midpoint of energyStart+End)
  const energyMid   = ((beatMapUnit.energyStart ?? 0.5) + (beatMapUnit.energyEnd ?? 0.5)) / 2;
  const energyScore = scoreEnergy(unitFeature.meanVolumeDb, energyMid);

  // Pauses
  const trailMs   = (unitFeature.trailSilenceSec ?? 0) * 1000;
  const pauseScore = scorePause(trailMs, beatMapUnit.pauseAfterMs);

  // Expression
  const exprScore = scoreExpression(unitFeature.prosody, energyMid);

  // Overall (weighted average of non-null scores)
  const weights = { accuracy: 3, pace: 2, energy: 2, pauses: 1, expression: 2 };
  let weightedSum = 0, weightTotal = 0;
  for (const [dim, w] of Object.entries(weights)) {
    const score = { accuracy: accuracyScore, pace: paceScore, energy: energyScore,
                    pauses: pauseScore, expression: exprScore }[dim];
    if (score != null) { weightedSum += score * w; weightTotal += w; }
  }
  const overall = weightTotal > 0 ? Math.round(weightedSum / weightTotal) : null;

  return {
    unitIndex:      beatMapUnit.index ?? 0,
    unitText:       beatMapUnit.text?.slice(0, 80),
    overall,
    dimensions: {
      accuracy:   accuracyScore,
      pace:       paceScore,
      energy:     energyScore,
      pauses:     pauseScore,
      expression: exprScore,
    },
    reference: {
      idealWpm,
      paceContour:   beatMapUnit.paceContour,
      energyStart:   beatMapUnit.energyStart,
      energyEnd:     beatMapUnit.energyEnd,
      pauseAfterMs:  beatMapUnit.pauseAfterMs,
      pauseReason:   beatMapUnit.pauseReason,
    },
    user: {
      wpm:            unitFeature.wpm,
      meanVolumeDb:   unitFeature.meanVolumeDb,
      trailSilenceSec: unitFeature.trailSilenceSec,
      pitchRangeSemitones: unitFeature.prosody?.pitchRangeSemitones ?? null,
      durationSec:    unitFeature.durationSec,
    },
  };
}

/**
 * Produce top-level summary from all unit comparisons.
 *
 * @param {Array}  unitComparisons  - array from compareUnit()
 * @param {object} alignStats       - overall {accuracy, stats} from alignTranscripts
 * @returns {object} summary
 */
export function buildSummary(unitComparisons, alignStats) {
  const scored = unitComparisons.filter(u => !u.skipped && u.overall != null);
  if (scored.length === 0) {
    return { overallScore: 0, dimensionAverages: {}, topStrengths: [], topImprovements: [] };
  }

  const avg = (key) => {
    const vals = scored.map(u => u.dimensions[key]).filter(v => v != null);
    return vals.length ? Math.round(vals.reduce((a, b) => a + b) / vals.length) : null;
  };

  const dimensionAverages = {
    accuracy:   alignStats?.accuracy ?? avg('accuracy'),
    pace:       avg('pace'),
    energy:     avg('energy'),
    pauses:     avg('pauses'),
    expression: avg('expression'),
  };

  const overallScore = (() => {
    const vals = Object.values(dimensionAverages).filter(v => v != null);
    return vals.length ? Math.round(vals.reduce((a, b) => a + b) / vals.length) : 0;
  })();

  // Rank dimensions for strengths vs improvements
  const ranked = Object.entries(dimensionAverages)
    .filter(([, v]) => v != null)
    .sort(([, a], [, b]) => b - a);

  const topStrengths    = ranked.slice(0, 2).map(([k, v]) => ({ dimension: k, score: v }));
  const topImprovements = [...ranked].reverse().slice(0, 2).map(([k, v]) => ({ dimension: k, score: v }));

  // Worst 5 units
  const worstUnits = [...scored]
    .sort((a, b) => (a.overall ?? 100) - (b.overall ?? 100))
    .slice(0, 5)
    .map(u => ({ unitIndex: u.unitIndex, unitText: u.unitText, overall: u.overall, dimensions: u.dimensions }));

  return {
    overallScore,
    dimensionAverages,
    topStrengths,
    topImprovements,
    worstUnits,
    totalUnits: unitComparisons.length,
    scoredUnits: scored.length,
    skippedUnits: unitComparisons.length - scored.length,
    alignStats: alignStats?.stats,
  };
}
