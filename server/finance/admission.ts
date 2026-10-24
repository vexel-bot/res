/** One USD authority: signed internal Studios admission. No browser cost/actor input. */
import { AsyncLocalStorage } from 'node:async_hooks';
import { createHash, createHmac } from 'node:crypto';
import type { RequestHandler } from 'express';
import type { AuthContext } from '../governance';
import { studioBridgeSecret } from '../studios/bridgeKey';

type Scope = { actor: () => AuthContext | undefined; key: string; attempt: number };
const context = new AsyncLocalStorage<Scope>();
export const financialContext: RequestHandler = (req, res, next) => {
  const key = String(req.header('idempotency-key') || res.locals.requestId);
  context.run({ actor: () => (req as typeof req & { auth?: AuthContext }).auth, key, attempt: 0 }, next);
};

export function runWithFinancialContext<T>(auth: AuthContext, key: string, callback: () => T) {
  return context.run({ actor: () => auth, key, attempt: 0 }, callback);
}

export function financeToken(auth: AuthContext) {
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const header = encode({ alg: 'HS256', typ: 'JWT' });
  const payload = encode({ iss: 'clicko-governance', aud: 'clicko-finance', type: 'external_finance',
    sub: auth.user.id, workspaceId: auth.workspaceId, iat: now, exp: now + 60 });
  return `${header}.${payload}.${createHmac('sha256', studioBridgeSecret()).update(`${header}.${payload}`).digest('base64url')}`;
}

export type PaidCall = { provider: 'google.klic' | 'google.cloud-tts'; model: string; operation: 'generate' | 'stream' | 'synthesize'; fingerprint: string; units?: number };
export type Receipt = { id: string; maxOutputTokens: number; reservedUsd: number; status: string };
type Settlement = { outcome: 'completed' | 'unknown'; input_tokens?: number; output_tokens?: number };

export class FinancialAdmission {
  constructor(private transport: typeof fetch = fetch) {}
  private async post(auth: AuthContext, route: string, body?: unknown) {
    const origin = new URL(process.env.CLICKO_STUDIOS_ORIGIN || 'http://127.0.0.1:8000');
    if (origin.protocol !== 'https:' && !(origin.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(origin.hostname))) throw new Error('FINANCE_ORIGIN_UNSAFE');
    let response: Response;
    try {
      response = await this.transport(new URL('/internal/finance/' + route, origin), {
        method: 'POST', redirect: 'error', headers: { authorization: `Bearer ${financeToken(auth)}`, 'content-type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(5000),
      });
    } catch { throw new Error('FINANCE_UNAVAILABLE'); }
    if (!response.ok) throw new Error(response.status === 409 ? 'FINANCE_DUPLICATE_OR_CONFLICT' : 'FINANCE_ADMISSION_DENIED');
    return response.json();
  }
  async reserve(call: PaidCall) {
    if (process.env.CLICKO_DEV_MODE === 'true') throw new Error('FINANCE_OUTBOUND_DISABLED');
    if (process.env.CLICKO_NODE_OUTBOUND_ENABLED !== 'true') throw new Error('FINANCE_OUTBOUND_DISABLED');
    const scope = context.getStore();
    const auth = scope?.actor();
    if (!auth || !scope || !auth.user?.id || !auth.workspaceId) throw new Error('FINANCE_AUTH_REQUIRED');
    const key = createHash('sha256').update(scope.key + ':' + ++scope.attempt).digest('hex');
    const receipt = await this.post(auth, 'reserve', { ...call, key }) as Receipt;
    if (!receipt.id || !Number.isInteger(receipt.maxOutputTokens) || receipt.maxOutputTokens <= 0) throw new Error('FINANCE_RECEIPT_INVALID');
    await this.post(auth, encodeURIComponent(receipt.id) + '/start');
    return {
      ...receipt,
      settle: (result: Settlement) => this.post(auth, encodeURIComponent(receipt.id) + '/settle', result),
    };
  }
}

export const financialAdmission = new FinancialAdmission();
export const requestFingerprint = (value: unknown) => createHash('sha256').update(JSON.stringify(value)).digest('hex');
