/** Explicit, recoverable cleanup. Never deletes or touches the legacy QA/commercial stores. */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, realpathSync, renameSync } from 'node:fs';
import { connect } from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
process.chdir(project);
if (process.env.NODE_ENV === 'production') throw new Error('DEV_RESET_FORBIDDEN_IN_PRODUCTION');
const root = path.resolve(process.env.CLICKO_LOCAL_DATA_DIR || '.codex-runtime/clicko-dev');
const parent = path.join(project, '.codex-runtime');
if (path.dirname(root) !== parent || !/^clicko-dev(?:-[a-zA-Z0-9_-]+)?$/.test(path.basename(root))) throw new Error('DEV_RESET_TARGET_FORBIDDEN');
if (!process.argv.includes('--confirm=ARCHIVE_CLICKO_DEV')) {
  console.error(`Nenhum dado alterado. Pare o ambiente e confirme: npm run dev:reset -- --confirm=ARCHIVE_CLICKO_DEV\nAlvo: ${root}`);
  process.exitCode = 2;
} else if (!existsSync(root)) {
  console.info('Não há dados DEV neste diretório.');
} else {
  if (realpathSync(parent) !== parent || realpathSync(root) !== root) throw new Error('DEV_RESET_SYMLINK_FORBIDDEN');
  const marker = JSON.parse(readFileSync(path.join(root, 'dev-profile.json'), 'utf8'));
  if (marker.schemaVersion !== 'clicko.local-dev.v1' || path.resolve(marker.root) !== root) throw new Error('DEV_RESET_MARKER_REQUIRED');
  const control = process.platform === 'win32' ? '\\\\.\\pipe\\clicko-local-' + createHash('sha256').update(root).digest('hex').slice(0, 32) : path.join(root, 'control.sock');
  const running = await new Promise((resolve, reject) => {
    const socket = connect(control);
    socket.setTimeout(2000, () => { socket.destroy(); reject(new Error('DEV_RESET_CONTROL_UNAVAILABLE')); });
    socket.once('connect', () => { socket.destroy(); resolve(true); });
    socket.once('error', error => { if (['ENOENT', 'ECONNREFUSED'].includes(error.code)) resolve(false); else reject(error); });
  });
  if (running) throw new Error('DEV_RESET_STOP_SERVER_FIRST');
  const destination = root + '-backup-' + new Date().toISOString().replace(/[:.]/g, '-');
  if (existsSync(destination)) throw new Error('DEV_RESET_ARCHIVE_ALREADY_EXISTS');
  renameSync(root, destination);
  console.info(`Dados DEV arquivados de forma recuperável em: ${destination}\nO próximo dev:local criará um ambiente novo. Dados comerciais e QA anteriores não foram alterados.`);
}
