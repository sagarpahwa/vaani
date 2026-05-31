/** Wire types mirroring the FastAPI coaching backend (services/api/models.py).
 *  Kept in sync by hand — the backend Pydantic models are the source of truth. */

export type SessionMode = 'guided' | 'user_script';

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
