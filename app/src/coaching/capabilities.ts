/** Canonical coaching capabilities — must match the backend scorer keys
 *  (services/api/domain/goal_signature.py CANONICAL_CAPABILITIES). */

export const CANONICAL_CAPABILITIES = [
  'clarity',
  'pace',
  'fluency',
  'confidence',
  'engagement',
  'conciseness',
] as const;

export type Capability = (typeof CANONICAL_CAPABILITIES)[number];

const LABELS: Record<string, string> = {
  clarity: 'Clarity',
  pace: 'Pace',
  fluency: 'Fluency',
  confidence: 'Confidence',
  engagement: 'Engagement',
  conciseness: 'Conciseness',
};

const DESCRIPTIONS: Record<string, string> = {
  clarity: 'How understandable and well-articulated your words are.',
  pace: 'Speaking speed — not rushed, not dragging.',
  fluency: 'Smooth delivery with few fillers and false starts.',
  confidence: 'Assured tone without hedging.',
  engagement: 'How compelling and lively your delivery feels.',
  conciseness: 'Saying it without padding or rambling.',
};

function titleCase(key: string): string {
  return key
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

/** Human label for a capability key, with a sensible fallback for unknown keys. */
export function capabilityLabel(key: string): string {
  return LABELS[key] ?? titleCase(key);
}

/** One-line description for a capability key, or empty string if unknown. */
export function capabilityDescription(key: string): string {
  return DESCRIPTIONS[key] ?? '';
}

/** Order a score map: canonical capabilities first (in canonical order), then
 *  any extra keys the backend may add later, alphabetically. */
export function orderedCapabilityScores(
  scores: Record<string, number>,
): [string, number][] {
  const seen = new Set<string>();
  const ordered: [string, number][] = [];
  for (const cap of CANONICAL_CAPABILITIES) {
    if (cap in scores) {
      ordered.push([cap, scores[cap]]);
      seen.add(cap);
    }
  }
  for (const key of Object.keys(scores).sort()) {
    if (!seen.has(key)) ordered.push([key, scores[key]]);
  }
  return ordered;
}
