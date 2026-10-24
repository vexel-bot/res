import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { isFileLoadingAllowed, normalizePath, resolveConfig } from 'vite';

const root = fileURLToPath(new URL('..', import.meta.url));
const configuration = () => resolveConfig({ root, configFile: path.join(root, 'vite.config.ts'), envFile: false, logLevel: 'silent' }, 'serve', 'test');

test('Vite rejects private files using its real filesystem policy while keeping application assets accessible', async () => {
  const config = await configuration();
  // Only evaluate paths: do not read credentials, local records, or production data.
  const denied = ['.env', '.env.local', 'nested/.env.production', '.git/config', '.secrets/provider.json',
    'nested/.secrets/provider.json', '.clicko-data/governance.json', '.codex-runtime/session.json',
    '.venv/secret.txt', 'backend/app/config.py', 'nested/local.sqlite-wal', 'nested/data.db',
    'nested/private.pem', 'nested/private.key', 'nested/oauth-credentials.json', 'nested/oauth_credentials.json',
    'nested/my-service-account.json', 'nested/my-service_account.json', 'nested/google-credentials-dev.json'];
  for (const file of denied) {
    assert.equal(isFileLoadingAllowed(config, normalizePath(path.join(root, file))), false, file);
  }
  for (const file of ['src/main.tsx', 'src/components/KlicPlasma.tsx', 'src/index.css', 'public/theme-bootstrap.js']) {
    assert.equal(isFileLoadingAllowed(config, normalizePath(path.join(root, file))), true, file);
  }
});

test('custom governance storage and its pending writes remain private', async () => {
  const previous = process.env.CLICKO_GOVERNANCE_DATA_FILE;
  const storage = path.join(root, 'test-private-records', 'governance.json');
  try {
    process.env.CLICKO_GOVERNANCE_DATA_FILE = storage;
    const config = await configuration();
    for (const suffix of ['', '.tmp', '.backup']) {
      assert.equal(isFileLoadingAllowed(config, normalizePath(storage + suffix)), false);
    }
  } finally {
    if (previous === undefined) delete process.env.CLICKO_GOVERNANCE_DATA_FILE;
    else process.env.CLICKO_GOVERNANCE_DATA_FILE = previous;
  }
});
