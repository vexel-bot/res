/** Safe, persistent, isolated local profile. Never inherits authority to spend. */
import { fork } from 'node:child_process';
import { createHash, randomBytes } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync, createWriteStream, existsSync, realpathSync } from 'node:fs';
import { createServer, connect } from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
process.chdir(project);
if (process.env.NODE_ENV === 'production') throw new Error('LOCAL_PROFILE_FORBIDDEN_IN_PRODUCTION');
const developer = process.env.CLICKO_DEV_MODE !== 'false' && process.env.CLICKO_LOCAL_REQUIRE_LOGIN !== 'true';
const root = path.resolve(process.env.CLICKO_LOCAL_DATA_DIR || (developer ? '.codex-runtime/clicko-dev' : '.codex-runtime/stage1-local'));
const command = process.argv[2];
if (developer && command !== 'status' && command !== 'stop') {
  const parent = path.resolve('.codex-runtime');
  if (path.dirname(root) !== parent || !/^clicko-dev(?:-[a-zA-Z0-9_-]+)?$/.test(path.basename(root))) throw new Error('DEV_PRIVATE_DATA_DIRECTORY_REQUIRED');
  for (const candidate of [parent, root]) if (existsSync(candidate) && realpathSync(candidate) !== candidate) throw new Error('DEV_DATA_SYMLINK_FORBIDDEN');
}
for (const directory of ['public', 'dist']) {
  const relative = path.relative(path.join(project, directory), root);
  if (!relative || (!relative.startsWith('..' + path.sep) && relative !== '..' && !path.isAbsolute(relative))) throw new Error('CLICKO_PRIVATE_LOCAL_DATA_REQUIRED');
}
mkdirSync(root, { recursive: true });
const control = process.platform === 'win32' ? '\\\\.\\pipe\\clicko-local-' + createHash('sha256').update(root).digest('hex').slice(0, 32) : path.join(root, 'control.sock');
if (command === 'status' || command === 'stop') {
  const socket = connect(control);
  // The server's health probe may take 4 s. Do not silently close the control
  // socket first and report exit 0 with no status under CPU/memory pressure.
  socket.setTimeout(7000, () => socket.destroy(new Error('CLICKO_LOCAL_CONTROL_TIMEOUT')));
  socket.on('connect', () => socket.write(command + '\n'));
  socket.on('data', data => process.stdout.write(data));
  socket.on('error', error => { console.error(error.message === 'CLICKO_LOCAL_CONTROL_TIMEOUT'
    ? 'CLICKO_LOCAL_CONTROL_TIMEOUT' : 'CLICKO_LOCAL_NOT_RUNNING'); process.exitCode = 1; });
  socket.on('end', () => socket.destroy());
} else {
  if (developer) {
    const marker = path.join(root, 'dev-profile.json');
    if (!existsSync(marker)) writeFileSync(marker, JSON.stringify({ schemaVersion: 'clicko.local-dev.v1', root }), { flag: 'wx', mode: 0o600 });
    const saved = JSON.parse(readFileSync(marker, 'utf8'));
    if (saved.schemaVersion !== 'clicko.local-dev.v1' || path.resolve(saved.root) !== root) throw new Error('DEV_PROFILE_MARKER_INVALID');
  }
  const port = Number(process.env.PORT || 3018);
  const studioPort = Number(process.env.CLICKO_LOCAL_STUDIO_PORT || 8018);
  if (![port, studioPort].every(value => Number.isInteger(value) && value >= 1 && value <= 65535) || port === studioPort) throw new Error('CLICKO_LOCAL_PORT_INVALID');
  async function free(number) {
    await new Promise((resolve, reject) => {
      const probe = createServer().once('error', reject).listen(number, '127.0.0.1', () => probe.close(resolve));
    });
  }
  await free(port);
  await free(studioPort);
  function secret(filename) {
    const target = path.join(root, filename);
    try { writeFileSync(target, randomBytes(48).toString('hex'), { flag: 'wx', mode: 0o600 }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
    return readFileSync(target, 'utf8').trim();
  }
  let child;
  const server = createServer(socket => {
    socket.once('data', async data => {
      if (String(data).trim() === 'stop') { socket.end('CLICKO_LOCAL_STOPPING\n'); stop(); return; }
      try {
        const response = await fetch(`http://127.0.0.1:${port}/api/ready`, { signal: AbortSignal.timeout(4000) });
        socket.end(JSON.stringify({ pid: child?.pid, ready: response.ok, health: await response.json(), dataDirectory: root }) + '\n');
      } catch { socket.end('CLICKO_LOCAL_STARTING_OR_UNAVAILABLE\n'); }
    });
  });
  await new Promise((resolve, reject) => server.once('error', reject).listen(control, resolve));
  const env = {
    ...process.env, NODE_ENV: 'development', PORT: String(port), CLICKO_PREVIEW_HOST: '127.0.0.1',
    PUBLIC_APP_URL: `http://127.0.0.1:${port}`, CLICKO_DEV_MODE: String(developer), CLICKO_LOCAL_DATA_DIR: root,
    CLICKO_STUDIOS_ORIGIN: `http://127.0.0.1:${studioPort}`, CLICKO_STUDIOS_AUTOSTART: 'true',
    CLICKO_STUDIOS_DATA_DIR: path.join(root, 'studios'), CLICKO_STUDIOS_BRIDGE_SECRET: secret('bridge-key'),
    STUDIO_LLM_CREDENTIAL_KEY: process.env.STUDIO_LLM_CREDENTIAL_KEY || secret('llm-credential-key'),
    CLICKO_GOVERNANCE_DATA_FILE: path.join(root, 'governance.json'), CLICKO_SOCIAL_DATA_FILE: path.join(root, 'social.json'),
    CLICKO_KLIC_DATA_FILE: path.join(root, 'klic.json'), CLICKO_CONVERSATIONS_DIR: path.join(root, 'conversations'),
    CLICKO_RADAR_DATA_FILE: path.join(root, 'radar.json'),
    SOCIAL_STORAGE_DRIVER: 'json', SOCIAL_TOKEN_ENCRYPTION_KEY: createHash('sha256').update(secret('social-key')).digest('hex'),
    CLICKO_NODE_OUTBOUND_ENABLED: 'false', KLIC_GOOGLE_TTS_ENABLED: 'false',
    CLICKO_DEV_AUTH_BYPASS: 'false', STUDIO_NODE_OUTBOUND_ENABLED: 'false', STUDIO_PRODUCTION_TEST_BUDGET_USD: '0',
  };
  const log = createWriteStream(path.join(root, 'service.log'), { flags: 'a', mode: 0o600 });
  child = fork(path.join(project, 'server.ts'), [], { execArgv: ['--import', 'tsx'], env, windowsHide: true, stdio: ['inherit', 'pipe', 'pipe', 'ipc'] });
  child.stdout.on('data', data => { process.stdout.write(data); log.write(data); });
  child.stderr.on('data', data => { process.stderr.write(data); log.write(data); });
  let terminating = false;
  function stop() {
    if (terminating) return;
    terminating = true;
    if (child.connected) child.send('shutdown');
    setTimeout(() => { if (child.exitCode === null) child.kill(); }, 20_000).unref();
  }
  const startupDeadline = setTimeout(() => { console.error('CLICKO_LOCAL_STARTUP_TIMEOUT'); stop(); }, 120_000).unref();
  const startupProbe = setInterval(async () => {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/ready`, { signal: AbortSignal.timeout(1000) });
      if (response.ok) { clearTimeout(startupDeadline); clearInterval(startupProbe); }
    } catch { /* Readiness, not an allocated process, completes startup. */ }
  }, 2000).unref();
  child.once('exit', (code, signal) => { clearTimeout(startupDeadline); clearInterval(startupProbe);
    console.info('CLICKO_LOCAL_SERVER_EXIT', { code, signal }); log.end(); server.close(); process.exitCode = code ?? 1; });
  for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, stop);
  console.info(`Clicko local: http://127.0.0.1:${port} | ${developer ? 'DEV session (isolated)' : 'commercial login required'} | paid providers disabled | data: ${root}`);
}
