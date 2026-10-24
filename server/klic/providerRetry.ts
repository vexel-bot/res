import { setTimeout as delay } from 'node:timers/promises';
import { providerFailure, safeGoogleFailure } from './providerErrors';

export const KLIC_MAX_ATTEMPTS = 3;
type RetryContext = { requestId?: string; provider: string; model: string; stage: string };
type RetryEvent = RetryContext & Partial<ReturnType<typeof safeGoogleFailure>> & {
  attempt: number; event: 'started' | 'completed' | 'failed'; retryInMs?: number;
};
type RetryDependencies = {
  random?: () => number;
  wait?: (milliseconds: number, signal: AbortSignal) => Promise<void>;
  report?: (event: RetryEvent) => void;
};

export function isTransientGoogleFailure(error: unknown) {
  const { upstreamStatus, upstreamCode, upstreamReason } = safeGoogleFailure(error);
  const transientReason = !upstreamReason || ['RATE_LIMIT_EXCEEDED', 'QUOTA_EXCEEDED', 'CAPACITY_EXHAUSTED'].includes(upstreamReason);
  return transientReason && providerFailure(error).retryable && (
    (upstreamStatus === 503 && (!upstreamCode || upstreamCode === 'UNAVAILABLE')) ||
    (upstreamStatus === 429 && (!upstreamCode || upstreamCode === 'RESOURCE_EXHAUSTED'))
  );
}

/** One retry owner, three total attempts, same model. Never replay an already published stream. */
export async function* streamWithKlicRetry<T>(
  operation: () => AsyncIterable<T>, signal: AbortSignal, context: RetryContext,
  dependencies: RetryDependencies = {},
): AsyncGenerator<T> {
  const random = dependencies.random ?? Math.random;
  const wait = dependencies.wait ?? ((ms, abortSignal) => delay(ms, undefined, { signal: abortSignal }));
  const report = dependencies.report ?? (event => console.info('KLIC_PROVIDER_ATTEMPT', event));
  for (let attempt = 1; attempt <= KLIC_MAX_ATTEMPTS; attempt++) {
    signal.throwIfAborted();
    report({ ...context, attempt, event: 'started' });
    let published = false;
    try {
      for await (const item of operation()) {
        signal.throwIfAborted();
        published = true;
        yield item;
      }
      signal.throwIfAborted();
      report({ ...context, attempt, event: 'completed' });
      return;
    } catch (error) {
      signal.throwIfAborted();
      const retry = !published && attempt < KLIC_MAX_ATTEMPTS && isTransientGoogleFailure(error);
      const retryInMs = retry ? Math.round(1000 * 2 ** (attempt - 1) * (0.75 + random() * 0.5)) : undefined;
      report({ ...context, attempt, event: 'failed', ...safeGoogleFailure(error), retryInMs });
      if (!retry) throw error;
      try { await wait(retryInMs!, signal); } catch (waitError) {
        signal.throwIfAborted();
        throw waitError;
      }
    }
  }
}

export async function withKlicRetry<T>(operation: () => Promise<T>, signal: AbortSignal, context: RetryContext): Promise<T> {
  let result!: T;
  for await (const value of streamWithKlicRetry(async function* () { yield await operation(); }, signal, context)) result = value;
  return result;
}
