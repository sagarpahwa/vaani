import { describe, expect, it } from '@jest/globals';

import { bytesToBase64 } from './base64';

function bytes(s: string): Uint8Array {
  return new Uint8Array([...s].map((c) => c.charCodeAt(0)));
}

describe('bytesToBase64', () => {
  it('encodes the empty buffer as the empty string', () => {
    expect(bytesToBase64(new Uint8Array([]))).toBe('');
  });

  it('matches the RFC 4648 test vectors for each padding case', () => {
    // 3 bytes → no padding; 1 byte → "=="; 2 bytes → "=".
    expect(bytesToBase64(bytes('Man'))).toBe('TWFu');
    expect(bytesToBase64(bytes('M'))).toBe('TQ==');
    expect(bytesToBase64(bytes('Ma'))).toBe('TWE=');
  });

  it('encodes high bytes (>127) without sign-extension errors', () => {
    expect(bytesToBase64(new Uint8Array([0xff, 0xfe, 0xfd]))).toBe('//79');
  });

  it('round-trips through atob to the original bytes', () => {
    const src = new Uint8Array([0, 1, 2, 250, 251, 252, 253, 254, 255]);
    const decoded = Uint8Array.from(atob(bytesToBase64(src)), (c) => c.charCodeAt(0));
    expect(Array.from(decoded)).toEqual(Array.from(src));
  });
});
