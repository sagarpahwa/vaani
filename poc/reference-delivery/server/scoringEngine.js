/**
 * Hard-gated scoring engine.
 *
 * Scoring is gated: transcript validity is checked FIRST.
 * If too much script is missing, a hard cap is applied before delivery scoring.
 *
 * Validity tiers:
 *   catastrophic_script_mismatch  coverage < 0.50  → maxOverall =  5
 *   major_script_mismatch         coverage < 0.70  → maxOverall = 25
 *   partial_attempt               coverage < 0.85  → maxOverall = 55
 *   valid_attempt                 coverage ≥ 0.85  → maxOverall = 100
 *
 * Additional hard caps:
 *   missingWords > 40% of expected         → maxOverall ≤ 5
 *   (extra + sub) > 25% of expected        → maxOverall ≤ 20
 *   prosodyReady = false                   → block analysis entirely
 */

// ── Pace band reference ───────────────────────────────────────────────
const PACE_BAND = {
  slow:   { ideal: 105 },
  medium: { ideal: 135 },
  fast:   { ideal: 175 },
};

function paceContourToIdealWpm(paceContour = 'medium') {
  const last = paceContour.split('→').pop().trim().toLowerCase();
  return PACE_BAND[last]?.ideal ?? 135;
}

// ── Individual dimension scorers ──────────────────────────────────────

function scorePace(actualWpm, idealWpm) {
  if (!actualWpm || !idealWpm) return null;
  const dev = Math.abs(1 - actualWpm / idealWpm);
  if (dev <= 0.10) return 100;
  if (dev >= 0.60) return 0;
  return Math.round(100 * (1 - (dev - 0.10) / 0.50));
}

function scoreEnergy(meanVolumeDb, energyTarget) {
  if (meanVolumeDb == null || energyTarget == null) return null;
  const normalized = Math.max(0, Math.min(1, (meanVolumeDb + 30) / 30));
  const dev = Math.abs(normalized - energyTarget);
  if (dev <= 0.10) return 100;
  if (dev >= 0.60) return 0;
  return Math.round(100 * (1 - (dev - 0.10) / 0.50));
}

function scorePause(trailSilenceMs, targetPauseMs) {
  if (!targetPauseMs) return null;
  if (!trailSilenceMs) return 40;
  const dev = Math.abs(1 - trailSilenceMs / targetPauseMs);
  if (dev <= 0.30) return 100;
  if (dev >= 0.80) return 0;
  return Math.round(100 * (1 - (dev - 0.30) / 0.50));
}

function scoreExpression(prosody, energyMid) {
  if (!prosody) return null;
  const range = prosody.pitchRangeSemitones ?? 0;
  const minRange = energyMid >= 0.7 ? 4 : 2;
  if (range >= minRange + 2) return 100;
  if (range <= 0.5) return 20;
  return Math.round(20 + 80 * Math.min(1, (range - 0.5) / (minRange + 1.5)));
}

// ── Script coverage calculation ───────────────────────────────────────

/**
 * Compute script coverage and validity from alignment stats.
 *
 * @param {object} alignStats - {correct, missing, extra, substitution, total, possibleAsrConfusion}
 * @returns {{ coverage, validity, maxOverall, capReason }}
 */
export function computeValidity(alignStats) {
  const { correct = 0, missing = 0, extra = 0, substitution = 0,
          possibleAsrConfusion = 0, total = 1 } = alignStats;

  // Script coverage: correct + half-credit for ASR confusion
  const coverage = (correct + possibleAsrConfusion * 0.5) / Math.max(total, 1);
  const missingRatio = missing / Math.max(total, 1);
  const errorRatio   = (extra + substitution) / Math.max(total, 1);

  let validity, maxOverall, capReason;

  if (coverage < 0.50) {
    validity   = 'catastrophic_script_mismatch';
    maxOverall = 5;
    capReason  = `Score capped at ${maxOverall} — more than half the script was skipped or changed.`;
  } else if (coverage < 0.70) {
    validity   = 'major_script_mismatch';
    maxOverall = 25;
    capReason  = `Score capped at ${maxOverall} — significant portions of the script were missing.`;
  } else if (coverage < 0.85) {
    validity   = 'partial_attempt';
    maxOverall = 55;
    capReason  = `Score capped at ${maxOverall} — some script sections were incomplete.`;
  } else {
    validity   = 'valid_attempt';
    maxOverall = 100;
    capReason  = null;
  }

  // Additional hard caps
  if (missingRatio > 0.40) {
    maxOverall = Math.min(maxOverall, 5);
    capReason  = `Score capped at ${maxOverall} — more than 40% of expected words were not spoken.`;
  }
  if (errorRatio > 0.25) {
    maxOverall = Math.min(maxOverall, 20);
    if (!capReason || maxOverall < parseInt(capReason.match(/\d+/)?.[0] ?? '100')) {
      capReason = `Score capped at ${maxOverall} — high substitution/extra word rate.`;
    }
  }

  return { coverage, validity, maxOverall, capReason };
}

// ── Per-unit status ───────────────────────────────────────────────────

/**
 * Determine per-unit status based on unit-level coverage.
 */
export function computeUnitStatus(unitOps, unitExpectedCount) {
  if (!unitOps?.length || !unitExpectedCount) return 'too_short_to_score';
  const correct = unitOps.filter(o => o.type === 'correct').length;
  const confusion = unitOps.filter(o => o.type === 'possible_asr_confusion').length;
  const coverage = (correct + confusion * 0.5) / unitExpectedCount;

  if (coverage < 0.30) return 'mostly_skipped';
  if (coverage < 0.60) return 'partial';
  return 'complete';
}

// ── Main scoring function ─────────────────────────────────────────────

/**
 * Score one unit with hard gating applied.
 *
 * @param {object} feature     - from audioFeatureExtractor (enriched with prosody)
 * @param {object} beatMapUnit - from the beat map
 * @param {object} unitOps     - alignment ops for this unit
 * @param {object} validityInfo - from computeValidity()
 */
export function scoreUnit(feature, beatMapUnit, unitOps, validityInfo) {
  const unitExpectedCount = unitOps.filter(o => o.type !== 'extra').length || 1;
  const unitStatus = computeUnitStatus(unitOps, unitExpectedCount);

  // Count correct for this unit
  const correct   = unitOps.filter(o => o.type === 'correct').length;
  const confusion = unitOps.filter(o => o.type === 'possible_asr_confusion').length;
  const unitCoverage = (correct + confusion * 0.5) / unitExpectedCount;

  const base = {
    unitIndex: beatMapUnit.index ?? 0,
    unitText:  (beatMapUnit.text ?? '').slice(0, 80),
    unitStatus,
    unitCoverage: Math.round(unitCoverage * 100),
  };

  // Mostly skipped: score 0-5, no delivery assessment
  if (unitStatus === 'mostly_skipped') {
    return {
      ...base,
      overall: Math.max(0, Math.round(unitCoverage * 10)),
      dimensions: { accuracy: Math.round(unitCoverage * 100), pace: null, energy: null, pauses: null, expression: null },
      skippedReason: 'This part was mostly skipped.',
    };
  }

  if (!feature || feature.tooShort || feature.noTimestamp) {
    return {
      ...base,
      overall: unitStatus === 'partial' ? Math.round(unitCoverage * 25) : null,
      dimensions: { accuracy: Math.round(unitCoverage * 100), pace: null, energy: null, pauses: null, expression: null },
      skippedReason: feature?.tooShort ? 'Segment too short to analyze.' : 'No timestamp — speech may have been reordered.',
    };
  }

  // Accuracy for this unit
  const accuracyScore = Math.round(unitCoverage * 100);

  // Delivery scores (only meaningful when unit has enough content)
  const idealWpm    = paceContourToIdealWpm(beatMapUnit.paceContour);
  const paceScore   = unitStatus === 'complete' ? scorePace(feature.wpm, idealWpm) : null;
  const energyMid   = ((beatMapUnit.energyStart ?? 0.5) + (beatMapUnit.energyEnd ?? 0.5)) / 2;
  const energyScore = scoreEnergy(feature.meanVolumeDb, energyMid);
  const trailMs     = (feature.trailSilenceSec ?? 0) * 1000;
  const pauseScore  = unitStatus === 'complete' ? scorePause(trailMs, beatMapUnit.pauseAfterMs) : null;
  const exprScore   = unitStatus === 'complete' ? scoreExpression(feature.prosody, energyMid) : null;

  // Weighted overall for this unit
  const weights = { accuracy: 3, pace: 2, energy: 2, pauses: 1, expression: 2 };
  const scores  = { accuracy: accuracyScore, pace: paceScore, energy: energyScore, pauses: pauseScore, expression: exprScore };
  let wSum = 0, wTotal = 0;
  for (const [k, w] of Object.entries(weights)) {
    if (scores[k] != null) { wSum += scores[k] * w; wTotal += w; }
  }
  let unitOverall = wTotal > 0 ? Math.round(wSum / wTotal) : null;

  // Apply partial cap
  if (unitStatus === 'partial' && unitOverall != null) {
    unitOverall = Math.min(unitOverall, 25);
  }

  return {
    ...base,
    overall: unitOverall,
    dimensions: scores,
    reference: {
      idealWpm,
      paceContour:  beatMapUnit.paceContour,
      energyStart:  beatMapUnit.energyStart,
      energyEnd:    beatMapUnit.energyEnd,
      pauseAfterMs: beatMapUnit.pauseAfterMs,
      pauseReason:  beatMapUnit.pauseReason,
    },
    user: {
      wpm:                 feature.wpm,
      meanVolumeDb:        feature.meanVolumeDb,
      trailSilenceSec:     feature.trailSilenceSec,
      pitchRangeSemitones: feature.prosody?.pitchRangeSemitones ?? null,
      durationSec:         feature.durationSec,
    },
  };
}

/**
 * Build the session-level summary from unit scores + alignment + validity.
 *
 * @param {Array}  unitScores   - from scoreUnit() calls
 * @param {object} validityInfo - from computeValidity()
 * @param {object} alignStats   - full alignment stats
 * @param {boolean} prosodyReady
 */
export function buildSessionSummary(unitScores, validityInfo, alignStats, prosodyReady) {
  const { coverage, validity, maxOverall, capReason } = validityInfo;
  const { correct = 0, total = 1 } = alignStats;

  // For catastrophic/major: don't try to average delivery — just use the coverage-based score
  let overallScore;
  if (validity === 'catastrophic_script_mismatch') {
    overallScore = Math.max(1, Math.min(maxOverall, Math.floor(coverage * 10)));
  } else if (validity === 'major_script_mismatch') {
    overallScore = Math.max(6, Math.min(maxOverall, Math.round(6 + (coverage - 0.50) / 0.20 * 19)));
  } else {
    // Compute delivery average from scored units
    const scored = unitScores.filter(u => u.overall != null && u.unitStatus !== 'mostly_skipped');
    const avgDelivery = scored.length > 0
      ? Math.round(scored.reduce((s, u) => s + u.overall, 0) / scored.length)
      : Math.round(coverage * 100);
    overallScore = Math.min(avgDelivery, maxOverall);
  }

  // Dimension averages (only from complete/partial units with non-null scores)
  const avg = (key) => {
    const vals = unitScores
      .filter(u => u.unitStatus !== 'mostly_skipped' && u.dimensions?.[key] != null)
      .map(u => u.dimensions[key]);
    return vals.length ? Math.round(vals.reduce((a, b) => a + b) / vals.length) : null;
  };

  const dimensionAverages = {
    accuracy:   Math.round(coverage * 100),  // use overall coverage for accuracy
    pace:       avg('pace'),
    energy:     avg('energy'),
    pauses:     avg('pauses'),
    expression: prosodyReady ? avg('expression') : null,
  };

  // Worst 5 units for feedback targeting
  const worstUnits = [...unitScores]
    .filter(u => u.overall != null)
    .sort((a, b) => (a.overall ?? 100) - (b.overall ?? 100))
    .slice(0, 5)
    .map(u => ({ unitIndex: u.unitIndex, unitText: u.unitText, overall: u.overall, unitStatus: u.unitStatus, dimensions: u.dimensions }));

  return {
    overallScore,
    validity,
    maxOverall,
    capReason,
    coverage:    Math.round(coverage * 100),  // as percentage
    dimensionAverages,
    worstUnits,
    alignStats,
    prosodyReady,
    unitCount:   unitScores.length,
    scoredCount: unitScores.filter(u => u.overall != null).length,
    skippedCount: unitScores.filter(u => u.unitStatus === 'mostly_skipped').length,
  };
}
