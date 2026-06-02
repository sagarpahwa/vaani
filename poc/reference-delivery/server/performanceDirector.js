import OpenAI from 'openai';

export const TAKE_CONFIGS = {
  restrained: {
    name: 'Take A — Restrained Keynote',
    direction: `TAKE STYLE: RESTRAINED KEYNOTE
Goal: whispered certainty. Intimate. The audience leans in.
- energyStart and energyEnd for most units: 2–4.
- pauseAfterMs for punchline / short lines: 1200–1800ms.
- ttsInstruction tone: conversational, understated, almost private.
- Avoid: any theatrical push, volume spikes, announcer feel.
- The reveal line should feel like a quiet truth, not a fanfare.`,
  },
  emotional: {
    name: 'Take B — Emotional Keynote',
    direction: `TAKE STYLE: EMOTIONAL KEYNOTE
Goal: genuine human warmth + building conviction.
- Energy arc: problem units at 2–3, contrast units at 4–5, reveal at 6–7, final at 7–8.
- Problem lines: quiet empathy — the speaker has lived this too.
- Reveal line "So we built Vaani.": pause before (400ms), land with quiet pride, long pause after.
- "Vaani listens to you.": intimate, direct, like a personal promise.
- Final three lines: emotional payoff — each more certain than the last.
- ttsInstruction tone: warm, human, earned conviction.`,
  },
  launch: {
    name: 'Take C — Product Launch Reveal',
    direction: `TAKE STYLE: PRODUCT LAUNCH REVEAL
Goal: cinematic tension → maximum reveal → conviction verdict.
- Build dread in the problem section. Each problem heavier than the last.
- "So we built Vaani." = the central reveal. pauseBeforeMs equivalent: 500ms. pauseAfterMs: 1800–2200ms. energy 8.
- "Not another course. / Not another video library. / Not another generic AI tool." = three separate units, rhythmic building, each with 800–1200ms pause.
- "Vaani listens to you." = sharp pivot — intimate but electrically direct.
- Final line: "That is what Vaani is built for." — verdict tone. Maximum certainty. Slowest delivery in the speech.
- ttsInstruction tone: cinematic, controlled, climactic.`,
  },
};

const SYSTEM = `You are an elite keynote performance director.
You create human performance maps for world-class product keynotes.
You do not clone, imitate, or impersonate any real person's exact voice.
You direct breath groups, word pressure, pitch contour, volume movement, and strategic silence.
Output: valid JSON only. No markdown. No code blocks. No explanation.`;

function buildV2Prompt(text, style, emphasisBoost = false) {
  const { direction } = TAKE_CONFIGS[style];
  const boostNote = emphasisBoost
    ? '\nEMPHASIS BOOST: Make word pressures more visceral. More contrast between quiet and loud. Push harder on primaryStress words. Make emotional transitions more pronounced. The previous take was too flat — fix that.'
    : '';

  return `Convert this speech into a V2 performance map.

${direction}${boostNote}

QUALITY STANDARD FOR ttsInstruction:
Write ttsInstruction like a film director's note to a human actor. Be specific, sensory, and actionable.

GOOD example:
"Rush through 'They have a' — it's just setup. Tiny mental catch before 'listening'. That word should rise in pitch and hold just a moment longer, vowel stretching slightly. Then 'problem' falls lower than everything before it, slowing on the last syllable. The listener should feel you just named something they already knew but never said out loud."

BAD example:
"Speak with emotion. Emphasize the word listening. Use medium pace."

GROUPING RULES:
- A breath group is what a skilled speaker delivers in one continuous thought.
- Group short related sentences into single units where natural: e.g., three "they do not know" lines can be one unit with internal rhythm variation.
- A major contrast, reveal, or emotional shift always starts a new unit.
- Target: 15–22 units for a 300-word speech. Do NOT create one unit per sentence.

UNIVERSAL RULES:
1. Keep every original word. Do not rewrite, cut, or reorder the speech.
2. Pause rules — strict:
   - Normal thought transition: 300–600ms (most units)
   - Meaningful beat: 700–1100ms (important lines)
   - Strategic reveal: 1200–1600ms (maximum 4 of these)
   - Major moment: 1700–2200ms (maximum 2 of these)
   - Total units with pauseAfterMs > 1000 must not exceed 8.
   - Never use the same pauseAfterMs value twice in a row.
3. No pauseBeforeMs field — handled inside ttsInstruction as a micro-pause direction.
4. microPauses are inside the line — tell TTS to add them via ttsInstruction.
5. targetDurationSec for the whole take should be 75–90 seconds.
6. Speech ratio target: 65–78% of audio should be voice.

RETURN EXACTLY THIS JSON STRUCTURE (raw JSON only):
{
  "title": "Steve Jobs-inspired product keynote performance",
  "targetDurationSec": 82,
  "overallDirection": {
    "style": "world-class product keynote",
    "emotionArc": "one-sentence arc",
    "avoid": ["robotic pacing", "equal sentence rhythm", "same pause pattern", "flat volume", "announcer voice", "celebrity impersonation"]
  },
  "performanceUnits": [
    {
      "index": 1,
      "text": "exact original words only",
      "unitType": "e.g. opening hook",
      "breathGroup": "brief description of what this breath contains",
      "emotion": "e.g. quiet intrigue",
      "energyStart": 2,
      "energyEnd": 3,
      "paceContour": "e.g. normal opening, slight slowdown on final phrase",
      "volumeContour": "e.g. soft-medium, controlled",
      "pitchContour": "e.g. slightly low, rise on 'not', lower landing on 'problem'",
      "primaryStress": "single most important word",
      "secondaryStress": "second most important word or phrase",
      "wordDirectives": [
        { "word": "not", "action": "sharper attack, small pitch lift, slight stress" },
        { "word": "problem", "action": "slow final syllable, land lower and heavier" }
      ],
      "microPauses": [
        { "position": "before 'speaking problem'", "durationMs": 130, "reason": "micro-suspense" }
      ],
      "pauseAfterMs": 850,
      "pauseReason": "let the hook settle",
      "ttsInstruction": "DIRECTOR'S NOTE HERE — specific, sensory, word-level"
    }
  ]
}

Speech:
${text}`;
}

function extractJSON(raw) {
  const m = raw.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
  return m ? m[1].trim() : raw.trim();
}

export async function generateBeatMap(text, style, emphasisBoost = false) {
  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const primaryModel = process.env.OPENAI_TEXT_MODEL || 'gpt-4.1-mini';
  const messages = [
    { role: 'system', content: SYSTEM },
    { role: 'user', content: buildV2Prompt(text, style, emphasisBoost) },
  ];

  let raw;
  try {
    const resp = await openai.chat.completions.create({
      model: primaryModel,
      messages,
      temperature: 0.75,
      response_format: { type: 'json_object' },
    });
    raw = resp.choices[0].message.content;
  } catch (err) {
    if (err.status === 404 || err.code === 'model_not_found') {
      const resp = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages,
        temperature: 0.75,
        response_format: { type: 'json_object' },
      });
      raw = resp.choices[0].message.content;
    } else {
      throw err;
    }
  }

  const beatMap = JSON.parse(extractJSON(raw));
  beatMap._takeName = TAKE_CONFIGS[style].name;
  beatMap._style = style;
  return beatMap;
}
