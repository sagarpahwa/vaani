/** Goal Signature form model + options.
 *
 *  Option `value` strings intentionally embed the keywords the backend matches
 *  (services/api/domain/goal_signature.py _BOOST_RULES) so the chosen goal
 *  visibly re-weights the rubric. Labels are what the user sees.
 */
import type { GoalSignature } from '@/api/types';

export interface Option {
  value: string;
  label: string;
}

export const OCCASIONS: Option[] = [
  { value: 'investor pitch', label: 'Investor pitch' },
  { value: 'wedding toast', label: 'Wedding toast' },
  { value: 'job interview', label: 'Job interview' },
  { value: 'lecture / training', label: 'Lecture / training' },
  { value: 'keynote address', label: 'Keynote address' },
  { value: 'team standup', label: 'Team standup' },
];

export const OBJECTIVES: Option[] = [
  { value: 'persuade and win buy-in', label: 'Persuade' },
  { value: 'teach and explain clearly', label: 'Teach / explain' },
  { value: 'inspire and move the room', label: 'Inspire' },
  { value: 'inform with a crisp update', label: 'Inform / update' },
];

export const AUDIENCES: Option[] = [
  { value: 'investors and executives', label: 'Investors / execs' },
  { value: 'students and learners', label: 'Students' },
  { value: 'colleagues and teammates', label: 'Colleagues' },
  { value: 'friends and family', label: 'Friends & family' },
  { value: 'a general audience', label: 'General public' },
];

export const STYLES: Option[] = [
  { value: 'concise and confident', label: 'Concise & confident' },
  { value: 'warm and engaging', label: 'Warm & engaging' },
  { value: 'authoritative and clear', label: 'Authoritative' },
  { value: 'conversational and relaxed', label: 'Conversational' },
];

export interface DurationOption {
  value: number | null;
  label: string;
}

export const DURATIONS: DurationOption[] = [
  { value: null, label: 'No target' },
  { value: 60, label: '1 min' },
  { value: 120, label: '2 min' },
  { value: 300, label: '5 min' },
];

export interface GoalForm {
  objective: string;
  occasion: string;
  audience: string;
  style: string;
  language: string;
  durationSeconds: number | null;
}

export const DEFAULT_GOAL_FORM: GoalForm = {
  objective: OBJECTIVES[0].value,
  occasion: OCCASIONS[0].value,
  audience: AUDIENCES[0].value,
  style: STYLES[0].value,
  language: 'en',
  durationSeconds: null,
};

/** Convert the form into the wire GoalSignature, dropping empty fields. */
export function buildGoalSignature(form: GoalForm): GoalSignature {
  const gs: GoalSignature = { language: form.language || 'en' };
  if (form.objective.trim()) gs.objective = form.objective.trim();
  if (form.occasion.trim()) gs.occasion = form.occasion.trim();
  if (form.audience.trim()) gs.audience = form.audience.trim();
  if (form.style.trim()) gs.style = form.style.trim();
  gs.duration_seconds = form.durationSeconds;
  return gs;
}

/** Best-effort pre-fill of the occasion from a script's goal_profile (Mode A). */
export function occasionFromProfile(profile: Record<string, unknown> | null | undefined): string {
  const raw = profile?.occasion ?? profile?.objective;
  if (typeof raw !== 'string') return DEFAULT_GOAL_FORM.occasion;
  const lower = raw.toLowerCase();
  const match = OCCASIONS.find((o) => lower.includes(o.label.toLowerCase().split(' ')[0]));
  return match ? match.value : DEFAULT_GOAL_FORM.occasion;
}
