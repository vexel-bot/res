import sharp from 'sharp';
import { createHash } from 'node:crypto';

export type StoredProfileAvatar = { userId: string; workspaceId: string; data: string; version: string };
export const MAX_AVATAR_BYTES = 5 * 1024 * 1024;
export const AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/** Decode untrusted pixels, discard metadata and persist only a bounded WebP. */
export async function normalizeProfileAvatar(input: Buffer) {
  if (!input.length || input.length > MAX_AVATAR_BYTES) throw new Error('INVALID_AVATAR');
  const image = sharp(input, { limitInputPixels: 40_000_000, failOn: 'warning' });
  const metadata = await image.metadata();
  if (!['jpeg', 'png', 'webp'].includes(metadata.format || '') || (metadata.pages || 1) > 1) throw new Error('INVALID_AVATAR');
  const output = await image.rotate().resize(512, 512, { fit: 'inside', withoutEnlargement: true }).webp({ quality: 85 }).toBuffer();
  return { data: output.toString('base64'), version: createHash('sha256').update(output).digest('hex') };
}

export const profileAvatarUrl = (userId: string, version: string) => `/api/governance/users/${encodeURIComponent(userId)}/avatar?v=${version}`;
