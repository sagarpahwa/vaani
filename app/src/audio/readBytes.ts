import { File } from 'expo-file-system';

/** Native/default: read a recorded file URI (file://…) into bytes via the
 *  expo-file-system File API. Metro swaps in readBytes.web.ts on web. */
export async function readBytes(uri: string): Promise<Uint8Array> {
  const buffer = await new File(uri).arrayBuffer();
  return new Uint8Array(buffer);
}
