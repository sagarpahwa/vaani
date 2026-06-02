/** Pure formatting helpers for scores and deltas (no React, fully unit-tested). */
import { colors } from '@/theme';

export type ScoreBand = 'good' | 'warn' | 'bad';

export function clamp01(n: number): number {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

/** A 0–1 score as a whole-percent string, or an em dash when absent. */
export function toPercent(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return '—';
  return `${Math.round(clamp01(score) * 100)}%`;
}

/** Bucket a 0–1 score for color coding. */
export function scoreBand(score: number | null | undefined): ScoreBand {
  if (score === null || score === undefined || Number.isNaN(score)) return 'bad';
  if (score >= 0.75) return 'good';
  if (score >= 0.5) return 'warn';
  return 'bad';
}

export function scoreColor(score: number | null | undefined): string {
  return { good: colors.good, warn: colors.warn, bad: colors.bad }[scoreBand(score)];
}

/** A score delta (parent→child, in [-1,1]) as a signed whole-percent string. */
export function signedPercent(delta: number | null | undefined): string {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return '—';
  const pts = Math.round(delta * 100);
  if (pts > 0) return `+${pts}%`;
  if (pts < 0) return `${pts}%`;
  return '±0%';
}

/** Direction of a delta for color coding (rounded so sub-percent noise reads flat). */
export function deltaBand(delta: number | null | undefined): ScoreBand {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return 'warn';
  const pts = Math.round(delta * 100);
  if (pts > 0) return 'good';
  if (pts < 0) return 'bad';
  return 'warn';
}

export function deltaColor(delta: number | null | undefined): string {
  return { good: colors.good, warn: colors.textMuted, bad: colors.bad }[deltaBand(delta)];
}

/** Milliseconds as a m:ss clock for the recording indicator. */
export function formatClock(ms: number | null | undefined): string {
  const totalSeconds = Math.max(0, Math.floor((ms ?? 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

/** Two-letter monogram from a display name ("Steve Jobs" → "SJ"). */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const SEVERITY_COLORS: Record<string, string> = {
  high: colors.bad,
  medium: colors.warn,
  low: colors.textMuted,
};

export function severityColor(severity: string): string {
  return SEVERITY_COLORS[severity.toLowerCase()] ?? colors.textMuted;
}
