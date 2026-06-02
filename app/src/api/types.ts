/** Wire types mirroring the FastAPI coaching backend (services/api/models.py).
 *  Kept in sync by hand — the backend Pydantic models are the source of truth. */

export type SessionMode = 'guided' | 'user_script' | 'persona';

export interface GoalSignature {
  objective?: string;
  occasion?: string;
  audience?: string;
  style?: string;
  language?: string;
  duration_seconds?: number | null;
}

export interface CreateSessionRequest {
  user_id: string;
  mode: SessionMode;
  script_id?: string | null;
  script_text?: string | null;
  persona_id?: string | null;
  goal_signature?: GoalSignature | null;
}

export interface UtteranceInput {
  line_index: number;
  audio_base64?: string | null;
}

export interface Improvement {
  capability: string;
  message: string;
  severity: string;
  line_index?: number | null;
}

export interface Correction {
  line_index: number;
  focus_capability: string;
  original_text: string;
  corrected_text: string;
  explanation: string;
  user_audio_key?: string | null;
  ideal_audio_key?: string | null;
}

export interface Feedback {
  summary: string;
  strengths: string[];
  improvements: Improvement[];
  read_aloud_text: string;
}

export interface Versions {
  rubric_version: string;
  scoring_model_version: string;
  feature_extractor_version: string;
  prompt_version: string;
}

/** Session-level acoustic aggregate (persona path only).
 *  Mirrors AcousticProfile.to_dict() in services/api/domain/types.py. */
export interface AcousticProfile {
  speech_rate_sps: number;
  articulation_rate_sps: number;
  coverage_ratio: number;
  pause_count: number;
  pause_total_s: number;
  longest_pause_s: number;
  pitch_range_semitones: number;
  pitch_variation: number;
  energy_variation: number;
  voiced_ratio: number;
  duration_s: number;
  lines_recorded: number;
  lines_expected: number;
}

export interface SessionDetail {
  session_id: string;
  user_id: string;
  mode: string;
  status: string;
  script_id?: string | null;
  expected_units: string[];
  goal_signature: GoalSignature;
  attempt: number;
  parent_session_id?: string | null;
  overall_score?: number | null;
  capability_scores: Record<string, number>;
  versions?: Versions | null;
  feedback?: Feedback | null;
  corrections: Correction[];
  delta?: Record<string, number> | null;
  created_at?: string | null;
  // Persona path only (mode="persona"); null/absent for Mode A/B.
  persona_id?: string | null;
  persona_name?: string | null;
  style_match?: number | null;
  acoustic?: AcousticProfile | null;
}

export interface ScriptLine {
  line_index: number;
  text: string;
  coaching_focus: string[];
}

export interface ScriptSummary {
  script_id: string;
  title: string;
  language?: string | null;
  difficulty?: string | null;
  line_count: number;
}

export interface ScriptDetail {
  script_id: string;
  title: string;
  description?: string | null;
  language?: string | null;
  difficulty?: string | null;
  estimated_duration_seconds?: number | null;
  goal_profile?: Record<string, unknown> | null;
  target_capabilities: string[];
  lines: ScriptLine[];
}

// ---- personas (20 Legends) ------------------------------------------------

export interface PersonaReference {
  title?: string | null;
  video_url?: string | null;
}

export interface PersonaSummary {
  persona_id: string;
  name: string;
  role?: string | null;
  archetype?: string | null;
  line_count: number;
}

/** Demo-relevant slice of a persona rubric (scoring weights stay server-side). */
export interface PersonaRubricView {
  target_pace_sps: number[];
  expressiveness?: string | null;
  pause_style?: string | null;
}

export interface PersonaDetail {
  persona_id: string;
  name: string;
  role?: string | null;
  archetype?: string | null;
  reference?: PersonaReference | null;
  goal_line?: string | null;
  signature_qualities: string[];
  estimated_duration_seconds?: number | null;
  lines: ScriptLine[];
  rubric?: PersonaRubricView | null;
}
