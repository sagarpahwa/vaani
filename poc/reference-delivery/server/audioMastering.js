import { execFile } from 'child_process';
import { promisify } from 'util';
import ffmpegPath from 'ffmpeg-static';

const execFileAsync = promisify(execFile);

async function runFfmpeg(args) {
  await execFileAsync(ffmpegPath, ['-y', ...args]).catch(err => {
    throw new Error(`ffmpeg mastering error: ${err.stderr || err.message}`);
  });
}

export async function masterAudio(inputWav, outputMp3) {
  // loudnorm: EBU R128 integrated loudness -16 LUFS, true peak -1.5 dBTP
  await runFfmpeg([
    '-i', inputWav,
    '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
    '-b:a', '192k',
    '-ar', '44100',
    outputMp3,
  ]);
  return outputMp3;
}
