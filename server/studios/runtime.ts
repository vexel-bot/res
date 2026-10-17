import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';

/** Start only the local Studio API. Production uses its configured service. */
export async function startLocalStudios() {
  if (process.env.NODE_ENV === 'production' || process.env.CLICKO_STUDIOS_ORIGIN) return undefined;
  const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  if (!existsSync(python)) return undefined;
  try {
    const ready = await fetch('http://127.0.0.1:8000/health/ready', { signal: AbortSignal.timeout(1000) });
    if (ready.ok && (await ready.json()).service === 'clicko-studios') return undefined;
    return undefined;
  } catch { /* The local API is not running yet. */ }
  const root = path.resolve('.clicko-data/studios');
  mkdirSync(root, { recursive: true });
  const child: ChildProcess = spawn(python, ['-m', 'uvicorn', 'app.studio_app:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', '8000'], {
    cwd: process.cwd(), windowsHide: true, stdio: ['ignore', 'inherit', 'inherit'],
    env: {
      ...process.env,
      ENVIRONMENT: 'development', DATABASE_URL: `sqlite:///${path.join(root, 'records.sqlite').replace(/\\/g, '/')}`,
      STORAGE_PATH: path.join(root, 'uploads'), CELERY_TASK_ALWAYS_EAGER: 'true',
      STUDIO_ISOLATED_QUEUES_ENABLED: 'false', PYTHONPATH: path.resolve('backend'),
    },
  });
  child.once('error', () => console.error('CLICKO_STUDIOS_START_FAILED'));
  return child;
}
