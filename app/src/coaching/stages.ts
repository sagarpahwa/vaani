/** Processing stages, mirroring the backend WS timeline
 *  (services/api/routes/events.py STAGES). The processing screen animates
 *  through these while the utterances submission is in flight. */
export const STAGES = [
  'received',
  'transcribing',
  'analyzing',
  'scoring',
  'generating_feedback',
] as const;

export type Stage = (typeof STAGES)[number];

const LABELS: Record<Stage, string> = {
  received: 'Received your recording',
  transcribing: 'Transcribing your speech',
  analyzing: 'Analyzing your delivery',
  scoring: 'Scoring each capability',
  generating_feedback: 'Writing your coaching',
};

/** Friendly label for a stage name, falling back to the raw key if unknown. */
export function stageLabel(stage: string): string {
  return LABELS[stage as Stage] ?? stage;
}

/** Per-stage dwell for the client-side progress animation (ms). */
export const STAGE_INTERVAL_MS = 450;
