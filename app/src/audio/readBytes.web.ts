/** Web: a MediaRecorder produces a blob: URI; fetch it back into bytes. */
export async function readBytes(uri: string): Promise<Uint8Array> {
  const res = await fetch(uri);
  const buffer = await res.arrayBuffer();
  return new Uint8Array(buffer);
}
