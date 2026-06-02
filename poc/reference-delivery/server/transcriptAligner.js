/**
 * Aligns expected script words to spoken transcript words using Levenshtein DP.
 * Returns per-word operation classifications + index mappings for timestamp lookup.
 *
 * Operation types:
 *   correct               - word matches
 *   missing               - expected word not spoken
 *   extra                 - spoken word not in script
 *   substitution          - different word in place of expected
 *   possible_asr_confusion - likely ASR mishearing (product names etc.)
 */

// ── ASR confusion vocabulary ──────────────────────────────────────────
// Normalized expected tokens → set of normalized spoken alternatives
// that are likely ASR errors, not genuine mistakes.
const ASR_CONFUSION_MAP = new Map([
  ['tinytrail', new Set(['tiny', 'trail', 'train', 'trial', 'tinytrails', 'tinytrail', 'trains', 'trying', 'train\'s'])],
]);

function normalize(text) {
  return text.toLowerCase().replace(/[^a-z0-9\s']/g, ' ').replace(/\s+/g, ' ').trim();
}

function tokenize(text) {
  return normalize(text).split(' ').filter(Boolean);
}

function dpAlign(exp, spo) {
  const m = exp.length, n = spo.length;
  const dp = Array.from({ length: m + 1 }, (_, i) =>
    Array.from({ length: n + 1 }, (_, j) => ({
      cost: i === 0 ? j : j === 0 ? i : Infinity,
      op:   i === 0 ? 'ins' : j === 0 ? 'del' : null,
    }))
  );

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const isMatch = exp[i-1] === spo[j-1];
      const costs = [
        { cost: dp[i-1][j].cost + 1,                    op: 'del' },
        { cost: dp[i][j-1].cost + 1,                    op: 'ins' },
        { cost: dp[i-1][j-1].cost + (isMatch ? 0 : 1), op: isMatch ? 'match' : 'sub' },
      ];
      dp[i][j] = costs.reduce((a, b) => b.cost < a.cost ? b : a);
    }
  }

  const ops = [];
  let i = m, j = n;
  while (i > 0 || j > 0) {
    if (i === 0) {
      ops.unshift({ type: 'extra',   expected: null,      spoken: spo[j-1], ei: i,   si: j-1 }); j--;
    } else if (j === 0) {
      ops.unshift({ type: 'missing', expected: exp[i-1],  spoken: null,     ei: i-1, si: j   }); i--;
    } else {
      const { op } = dp[i][j];
      if (op === 'match') {
        ops.unshift({ type: 'correct',      expected: exp[i-1], spoken: spo[j-1], ei: i-1, si: j-1 }); i--; j--;
      } else if (op === 'sub') {
        ops.unshift({ type: 'substitution', expected: exp[i-1], spoken: spo[j-1], ei: i-1, si: j-1 }); i--; j--;
      } else if (op === 'del') {
        ops.unshift({ type: 'missing',      expected: exp[i-1], spoken: null,     ei: i-1, si: j   }); i--;
      } else {
        ops.unshift({ type: 'extra',        expected: null,      spoken: spo[j-1], ei: i,   si: j-1 }); j--;
      }
    }
  }
  return ops;
}

function detectAsrConfusions(ops) {
  return ops.map((op, idx) => {
    if (op.type !== 'substitution' && op.type !== 'missing') return op;
    const expWord = op.expected ?? '';
    const alts = ASR_CONFUSION_MAP.get(expWord);
    if (!alts) return op;

    if (op.spoken && alts.has(op.spoken)) {
      return { ...op, type: 'possible_asr_confusion',
        asrNote: `"${op.expected}" may have been misheard as "${op.spoken}"` };
    }
    if (op.type === 'missing') {
      const next = ops[idx + 1];
      if (next?.type === 'extra' && next.spoken && alts.has(next.spoken)) {
        return { ...op, type: 'possible_asr_confusion',
          asrNote: `"${op.expected}" may have been split/misheard by ASR` };
      }
    }
    return op;
  });
}

function computeAlignStats(ops, expectedWords) {
  const counts = { correct: 0, missing: 0, extra: 0, substitution: 0, possibleAsrConfusion: 0 };
  for (const op of ops) {
    if      (op.type === 'correct')                counts.correct++;
    else if (op.type === 'missing')                counts.missing++;
    else if (op.type === 'extra')                  counts.extra++;
    else if (op.type === 'substitution')           counts.substitution++;
    else if (op.type === 'possible_asr_confusion') counts.possibleAsrConfusion++;
  }
  const total    = expectedWords.length;
  const coverage = total > 0 ? (counts.correct + counts.possibleAsrConfusion * 0.5) / total : 0;
  const accuracy = total > 0 ? Math.round((counts.correct / total) * 100) : 0;
  return { ...counts, total, coverage, accuracy };
}

// ── Main export ───────────────────────────────────────────────────────

export function alignTranscripts(expectedScript, spokenText, whisperWords = []) {
  const expectedWords = tokenize(expectedScript);
  const spokenWords   = tokenize(spokenText);

  const rawOps = dpAlign(expectedWords, spokenWords);
  const ops    = detectAsrConfusions(rawOps);

  const expToSpo = new Map();
  const spoToExp = new Map();
  for (const op of ops) {
    if (['correct', 'substitution', 'possible_asr_confusion'].includes(op.type)) {
      expToSpo.set(op.ei, op.si);
      spoToExp.set(op.si, op.ei);
    } else if (op.type === 'extra') {
      spoToExp.set(op.si, null);
    } else {
      expToSpo.set(op.ei, null);
    }
  }

  const getTimestamp = (si) => {
    if (si == null || si < 0 || si >= whisperWords.length) return null;
    return { start: whisperWords[si]?.start ?? null, end: whisperWords[si]?.end ?? null };
  };

  const enriched = ops.map(op => ({
    ...op,
    timestamp: op.si != null ? getTimestamp(op.si) : null,
  }));

  const stats = computeAlignStats(ops, expectedWords);

  const transcriptReliability = stats.total === 0 ? 'low'
    : stats.coverage < 0.30 ? 'low'
    : stats.coverage < 0.55 ? 'medium'
    : 'high';

  return {
    operations: enriched,
    expectedWords,
    spokenWords,
    expToSpo,
    spoToExp,
    whisperWords,
    accuracy: stats.accuracy,
    stats,
    transcriptReliability,
  };
}

export function getUnitTimeWindow(expStart, expEnd, alignment) {
  const { expToSpo, whisperWords } = alignment;
  let minStart = null, maxEnd = null;
  for (let ei = expStart; ei <= expEnd; ei++) {
    const si = expToSpo.get(ei);
    if (si == null) continue;
    const w = whisperWords[si];
    if (!w) continue;
    if (minStart === null || w.start < minStart) minStart = w.start;
    if (maxEnd   === null || w.end   > maxEnd)   maxEnd   = w.end;
  }
  return { start: minStart, end: maxEnd };
}

export function mapUnitsToExpectedWordRanges(units) {
  const ranges = [];
  let cursor = 0;
  for (const unit of units) {
    const words = tokenize(unit.text);
    ranges.push({ index: unit.index, expStart: cursor, expEnd: cursor + words.length - 1 });
    cursor += words.length;
  }
  return ranges;
}

/** Slice ops to only those belonging to a unit's expected word range. */
export function getUnitOps(ops, expStart, expEnd) {
  return ops.filter(op => op.type !== 'extra' && op.ei >= expStart && op.ei <= expEnd);
}
