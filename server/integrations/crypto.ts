import { createCipheriv, createDecipheriv, createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { SocialIntegrationError } from './errors';

const PREFIX = 'aes-256-gcm:v1';
const ROTATABLE_PREFIX = 'aes-256-gcm:v2';

function decodeKey(value: string) {
  const trimmed = value.trim();
  if (/^[a-f0-9]{64}$/i.test(trimmed)) return Buffer.from(trimmed, 'hex');
  try {
    const decoded = Buffer.from(trimmed, 'base64url');
    if (decoded.length === 32) return decoded;
  } catch { /* Report a stable configuration error below. */ }
  throw new SocialIntegrationError('SOCIAL_ENCRYPTION_KEY_INVALID', 503, 'A criptografia das integrações sociais precisa ser configurada pelo administrador.');
}

export type TokenCipher = ReturnType<typeof createTokenCipher>;

export function createTokenCipher(value: string | undefined, previousValues: string[] = []) {
  if (!value) return null;
  const keys = [value, ...previousValues].filter(Boolean).map(decodeKey);
  const key = keys[0];
  const keyId = (candidate: Buffer) => createHash('sha256').update(candidate).digest('base64url').slice(0, 12);
  return {
    encrypt(plainText: string) {
      const iv = randomBytes(12);
      const cipher = createCipheriv('aes-256-gcm', key, iv);
      const encrypted = Buffer.concat([cipher.update(plainText, 'utf8'), cipher.final()]);
      return [ROTATABLE_PREFIX, keyId(key), iv.toString('base64url'), cipher.getAuthTag().toString('base64url'), encrypted.toString('base64url')].join(':');
    },
    decrypt(payload: string) {
      const parts = payload.split(':');
      const prefix = `${parts[0]}:${parts[1]}`;
      const isLegacy = prefix === PREFIX;
      const isRotatable = prefix === ROTATABLE_PREFIX;
      const encodedKeyId = isRotatable ? parts[2] : undefined;
      const [ivEncoded, tagEncoded, encryptedEncoded] = isRotatable ? parts.slice(3) : parts.slice(2);
      if ((!isLegacy && !isRotatable) || !ivEncoded || !tagEncoded || !encryptedEncoded) {
        throw new SocialIntegrationError('SOCIAL_TOKEN_INVALID', 503, 'A conexão armazenada não pôde ser lida com segurança.');
      }
      const candidates = isRotatable ? keys.filter(candidate => keyId(candidate) === encodedKeyId) : keys;
      for (const candidate of candidates) {
        try {
          const iv = Buffer.from(ivEncoded, 'base64url');
          const tag = Buffer.from(tagEncoded, 'base64url');
          const encrypted = Buffer.from(encryptedEncoded, 'base64url');
          const decipher = createDecipheriv('aes-256-gcm', candidate, iv);
          decipher.setAuthTag(tag);
          return Buffer.concat([decipher.update(encrypted), decipher.final()]).toString('utf8');
        } catch { /* Try a configured previous key for legacy payloads. */ }
      }
      throw new SocialIntegrationError('SOCIAL_TOKEN_INVALID', 503, 'A conexão armazenada não pôde ser lida com segurança.');
    },
    matches(candidate: string, encrypted: string) {
      const actual = Buffer.from(this.decrypt(encrypted));
      const expected = Buffer.from(candidate);
      return actual.length === expected.length && timingSafeEqual(actual, expected);
    },
  };
}

export function createTokenCipherFromEnvironment() {
  const previous = String(process.env.SOCIAL_TOKEN_ENCRYPTION_PREVIOUS_KEYS || '').split(',').map(value => value.trim()).filter(Boolean);
  return createTokenCipher(process.env.SOCIAL_TOKEN_ENCRYPTION_KEY, previous);
}
