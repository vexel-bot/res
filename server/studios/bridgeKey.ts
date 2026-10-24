import { randomBytes } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

export function studioBridgeSecret() {
  if (process.env.CLICKO_STUDIOS_BRIDGE_SECRET) {
    if (process.env.CLICKO_STUDIOS_BRIDGE_SECRET.length < 32) throw new Error('STUDIOS_BRIDGE_KEY_INVALID');
    return process.env.CLICKO_STUDIOS_BRIDGE_SECRET;
  }
  if (process.env.NODE_ENV === 'production') throw new Error('STUDIOS_BRIDGE_KEY_REQUIRED');
  const filename = path.resolve('.clicko-data/studios/bridge-key');
  mkdirSync(path.dirname(filename), { recursive: true });
  try { writeFileSync(filename, randomBytes(48).toString('hex'), { flag: 'wx', mode: 0o600 }); }
  catch (error) { if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error; }
  const key = readFileSync(filename, 'utf8').trim();
  if (key.length < 32) throw new Error('STUDIOS_BRIDGE_KEY_INVALID');
  return key;
}
