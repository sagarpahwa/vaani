import OpenAI from 'openai';
import path from 'path';
import fs from 'fs/promises';
import { analyzeSegment } from './acousticEvaluator.js';

const CANDIDATE_MODIFIERS = {
  A: 'DELIVERY VARIANT A [RESTRAINED]: Be more intimate and understated. Let every word land quietly. Slight pull-back on volume. Avoid any push or theatrical energy. The goal is whispered certainty.',
  B: '', // standard — no modification
  C: 'DELIVERY VARIANT C [EMPHATIC]: Push the word pressures harder. Sharper attack on the primary stress word. Make the contrast between quiet and loud more visceral. The key words should feel like they carry physical weight. Never overact.',
};

function buildRichInstruction(unit, variant = 'B') {
  const prefix = CANDIDATE_MODIFIERS[variant]
    ? CANDIDATE_MODIFIERS[variant] + '\n\n'
    : '';

  const wordSection = unit.wordDirectives?.length
    ? `\nKEY WORD TREATMENTS:\n${unit.wordDirectives.map(w => `- "${w.word}": ${w.action}`).join('\n')}`
    : '';

  const microSection = unit.microPauses?.length
    ? `\nMICRO-PAUSES (inside the line):\n${unit.microPauses.map(p => `- ${p.position}: ${p.durationMs}ms — ${p.reason}`).join('\n')}`
    : '';

  return (
    `${prefix}` +
    `Perform this text as part of a Steve Jobs-inspired product keynote performance. ` +
    `Do not clone or imitate any real person's exact voice. ` +
    `This is world-class keynote delivery, not narration, not a voiceover, not an announcement.\n\n` +
    `UNIT: ${unit.unitType || 'speech unit'} | EMOTION: ${unit.emotion}\n` +
    `ENERGY: ${unit.energyStart}/10 → ${unit.energyEnd}/10\n` +
    `PACE: ${unit.paceContour}\n` +
    `PITCH: ${unit.pitchContour}\n` +
    `VOLUME: ${unit.volumeContour}\n` +
    `PRIMARY STRESS: "${unit.primaryStress}"` +
    (unit.secondaryStress ? ` | SECONDARY: "${unit.secondaryStress}"` : '') +
    `${wordSection}${microSection}\n\n` +
    `DIRECTOR'S NOTE:\n${unit.ttsInstruction}\n\n` +
    `Make it human. Make it precise. Make it alive.`
  ).trim();
}

export async function generatePerformanceUnit(unit, voice, sessionDir, index) {
  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const ttsModel = process.env.OPENAI_TTS_MODEL || 'gpt-4o-mini-tts';
  const selectedVoice = voice || process.env.OPENAI_PRIMARY_VOICE || 'marin';
  const pad = String(index).padStart(3, '0');

  // Generate 3 candidates in parallel
  const variants = ['A', 'B', 'C'];
  const candidatePaths = await Promise.all(
    variants.map(async (v) => {
      const wavPath = path.join(sessionDir, `u${pad}_${v}.wav`);
      const instruction = buildRichInstruction(unit, v);
      const response = await openai.audio.speech.create({
        model: ttsModel,
        voice: selectedVoice,
        input: unit.text,
        instructions: instruction,
        response_format: 'wav',
      });
      await fs.writeFile(wavPath, Buffer.from(await response.arrayBuffer()));
      return wavPath;
    }),
  );

  // Acoustic analysis on all three
  const analyses = await Promise.all(candidatePaths.map(analyzeSegment));

  // Selection: prefer highest dynamic score, never clipping, reasonable duration
  let bestIdx = 1; // default: standard (B)
  let bestScore = analyses[1].overallScore;

  for (let i = 0; i < analyses.length; i++) {
    const a = analyses[i];
    if (!a.isClipping && !a.isFlat && a.overallScore > bestScore) {
      bestScore = a.overallScore;
      bestIdx = i;
    }
  }

  // If standard is flat but another is better, prefer that
  if (analyses[bestIdx].isFlat && !analyses[2].isFlat) bestIdx = 2; // fallback to emphatic

  const finalPath = path.join(sessionDir, `u${pad}.wav`);
  await fs.copyFile(candidatePaths[bestIdx], finalPath);

  return {
    wavPath: finalPath,
    selectedVariant: variants[bestIdx],
    candidateScores: analyses.map((a, i) => ({ variant: variants[i], score: a.overallScore, dynamic: a.dynamicRangeDb })),
  };
}
