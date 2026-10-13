import { GoogleGenAI } from '@google/genai';
import { createHash } from 'node:crypto';
import { klicProviderConfig } from './providerConfig';

let cached: { configuration: string; client: GoogleGenAI } | undefined;
export function getKlicAiClient() {
  const config = klicProviderConfig();
  if (!config.configured) throw new Error(config.configurationIssue);
  const configuration = config.mode === 'vertex'
    ? `vertex:${config.project}:${config.location}:${config.model}`
    : `developer-api:${config.model}:${createHash('sha256').update(config.apiKey!).digest('hex')}`;
  if (cached?.configuration !== configuration) {
    // Application retry owns the three-attempt budget; never multiply it with SDK retries.
    const httpOptions = { timeout: 85000, retryOptions: { attempts: 1 } };
    const client = config.mode === 'vertex'
      ? new GoogleGenAI({ vertexai: true, project: config.project, location: config.location, httpOptions })
      : new GoogleGenAI({ vertexai: false, apiKey: config.apiKey, httpOptions });
    cached = { configuration, client };
  }
  return cached.client;
}

export function assertKlicText(text: string | undefined, blocked = false): string {
  if (blocked) throw new Error('KLIC_RESPONSE_BLOCKED');
  if (!text?.trim()) throw new Error('KLIC_EMPTY_RESPONSE');
  return text;
}
