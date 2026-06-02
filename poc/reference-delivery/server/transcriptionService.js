import OpenAI from 'openai';
import fs from 'fs';

// Vocabulary hint for Whisper — reduces product-name confusion
const VOCAB_PROMPT = 'TinyTrail, adventure box, explore, imagine, learn through play, ' +
  'motor skills, confidence, real play, curiosity, small pieces, big adventures, ' +
  'creativity, focus, durable, colorful, endless play, Vaani';

/**
 * Transcribe user audio with word-level timestamps.
 * Input should be a clean 16kHz mono WAV (converted by audioConverter).
 */
export async function transcribeAudio(audioFilePath) {
  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  // Primary: whisper-1 with word timestamps + vocabulary + language hint
  try {
    const resp = await openai.audio.transcriptions.create({
      file:                    fs.createReadStream(audioFilePath),
      model:                   'whisper-1',
      language:                'en',
      prompt:                  VOCAB_PROMPT,
      response_format:         'verbose_json',
      timestamp_granularities: ['word'],
    });

    return {
      text:     resp.text,
      words:    (resp.words ?? []).map(w => ({ word: w.word.trim(), start: w.start, end: w.end })),
      duration: resp.duration ?? 0,
      quality:  'word_timestamps',
    };
  } catch (err) {
    console.warn('[transcription] whisper-1 word timestamps failed:', err.message);
  }

  // Fallback 1: gpt-4o-transcribe (text only)
  try {
    const resp = await openai.audio.transcriptions.create({
      file:            fs.createReadStream(audioFilePath),
      model:           'gpt-4o-transcribe',
      language:        'en',
      prompt:          VOCAB_PROMPT,
      response_format: 'verbose_json',
    });
    return {
      text:     resp.text,
      words:    [],
      duration: resp.duration ?? 0,
      quality:  'text_only',
      warning:  'Word-level timestamps unavailable — alignment accuracy may be reduced.',
    };
  } catch (err) {
    console.warn('[transcription] gpt-4o-transcribe failed:', err.message);
  }

  // Fallback 2: whisper-1 plain
  const resp = await openai.audio.transcriptions.create({
    file:            fs.createReadStream(audioFilePath),
    model:           'whisper-1',
    language:        'en',
    prompt:          VOCAB_PROMPT,
    response_format: 'json',
  });
  return {
    text:    resp.text,
    words:   [],
    duration: 0,
    quality: 'text_only_plain',
    warning: 'Only plain-text transcription available.',
  };
}
