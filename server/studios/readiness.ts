/** Liveness is not readiness: Studios must answer with its own dependency report. */
export async function studiosReadiness(options: { origin?: string; fetch?: typeof fetch } = {}) {
  try {
    const response = await (options.fetch || fetch)(new URL('/health/ready', options.origin || process.env.CLICKO_STUDIOS_ORIGIN || 'http://127.0.0.1:8000'), {
      signal: AbortSignal.timeout(4_000), redirect: 'error',
    });
    const body = await response.json();
    const required = body?.dependencies;
    if (!response.ok || body?.service !== 'clicko-studios' || body?.status !== 'ready' || !required ||
      !['database', 'storage', 'ffmpeg'].every(key => required[key] === 'ok') || !['ok', 'local-thread-pool'].includes(required.queue)) {
      return { status: 'not_ready' as const };
    }
    return { status: 'ready' as const };
  } catch { return { status: 'not_ready' as const }; }
}
