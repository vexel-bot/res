import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';

export async function stopLocalStudios(child?: ChildProcess) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  await new Promise<void>(resolve => {
    const fallback = setTimeout(() => { child.kill(); }, 8_000);
    const deadline = setTimeout(resolve, 10_000);
    child.once('exit', () => { clearTimeout(fallback); clearTimeout(deadline); resolve(); });
    child.stdin?.end('shutdown\n');
  });
}

/** Start only the local Studio API. Production uses its configured service. */
export async function startLocalStudios() {
  if (process.env.NODE_ENV === 'production' || process.env.CLICKO_STUDIOS_AUTOSTART === 'false') return undefined;
  const origin = new URL(process.env.CLICKO_STUDIOS_ORIGIN || 'http://127.0.0.1:8000');
  if (origin.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(origin.hostname) || origin.pathname !== '/') return undefined;
  const port = Number(origin.port || 80);
  const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  if (!existsSync(python)) throw new Error('CLICKO_PYTHON_VENV_REQUIRED');
  let occupied = false;
  try {
    const ready = await fetch(new URL('/health/ready', origin), { signal: AbortSignal.timeout(1500) });
    occupied = true;
    if (ready.ok && (await ready.json()).service === 'clicko-studios') return undefined;
  } catch { /* The local API is not running yet. */ }
  if (occupied) throw new Error('CLICKO_STUDIOS_PORT_OCCUPIED_OR_NOT_READY');
  const root = path.resolve(process.env.CLICKO_STUDIOS_DATA_DIR || '.clicko-data/studios');
  mkdirSync(root, { recursive: true });
  const child: ChildProcess = spawn(python, ['-m', 'app.local_studio_server', String(port)], {
    cwd: process.cwd(), windowsHide: true, stdio: ['pipe', 'inherit', 'inherit'],
    env: {
      ...process.env,
      ENVIRONMENT: 'development', DATABASE_URL: `sqlite:///${path.join(root, 'records.sqlite').replace(/\\/g, '/')}`,
      STORAGE_PATH: path.join(root, 'uploads'), CELERY_TASK_ALWAYS_EAGER: 'true',
      STUDIO_ISOLATED_QUEUES_ENABLED: 'false', PYTHONPATH: path.resolve('backend'),
      // Autostart is a free local editing profile, not authority to spend API credits.
      GEMINI_OUTBOUND_ENABLED: 'false', GEMINI_VIDEO_GENERATION_ENABLED: 'false', STUDIO_GEMINI_ENABLED: 'false',
      OPENAI_OUTBOUND_ENABLED: 'false', OPENAI_VIDEO_GENERATION_ENABLED: 'false', STUDIO_RUNWAY_ENABLED: 'false',
      STUDIO_EDITING_AI_PLANNING_PROVIDER: 'none', STUDIO_EDITING_AI_IMAGE_PROVIDER: 'none', STUDIO_EDITING_AI_VIDEO_PROVIDER: 'none',
    },
  });
  child.stdin?.on('error', () => undefined);
  child.once('error', () => console.error('CLICKO_STUDIOS_START_FAILED'));
  for (let attempt = 0; attempt < 120 && child.exitCode === null; attempt += 1) {
    try {
      const response = await fetch(new URL('/health/ready', origin), { signal: AbortSignal.timeout(1000) });
      if (response.ok && (await response.json()).service === 'clicko-studios') return child;
    } catch { /* Startup continues; readiness never returns a fabricated success. */ }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  await stopLocalStudios(child);
  throw new Error('CLICKO_STUDIOS_NOT_READY');
}
