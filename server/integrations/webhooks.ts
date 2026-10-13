import { createHmac, timingSafeEqual } from 'node:crypto';

export type SocialWebhookVerification = {
  rawBody: Buffer;
  secret: string;
  signature: string | undefined;
  algorithm?: 'sha256' | 'sha512';
  signaturePrefix?: string;
};

function signatureBytes(signature: string | undefined, prefix: string) {
  if (!signature) return null;
  const value = prefix && signature.startsWith(prefix) ? signature.slice(prefix.length) : signature;
  if (!/^[a-f\d]+$/i.test(value) || value.length % 2 !== 0) return null;
  return Buffer.from(value, 'hex');
}

/**
 * Verifies an official provider HMAC against the untouched HTTP request body.
 * The caller must capture `express.raw()` before JSON parsing; reconstructed
 * JSON is deliberately rejected by the API contract of this helper.
 */
export function verifySocialWebhookSignature(input: SocialWebhookVerification) {
  if (!input.secret || !Buffer.isBuffer(input.rawBody)) return false;
  const algorithm = input.algorithm || 'sha256';
  const prefix = input.signaturePrefix ?? `${algorithm}=`;
  const received = signatureBytes(input.signature, prefix);
  if (!received) return false;
  const expected = createHmac(algorithm, input.secret).update(input.rawBody).digest();
  return received.length === expected.length && timingSafeEqual(received, expected);
}

export function verifySocialWebhookChallenge(received: unknown, configuredToken: string | undefined) {
  if (typeof received !== 'string' || !configuredToken) return false;
  const left = Buffer.from(received);
  const right = Buffer.from(configuredToken);
  return left.length === right.length && timingSafeEqual(left, right);
}
