// Isolated browser fixture: real authentication, avatar API and disk persistence.
// Never loads .env or uses the application's user data.
import express from 'express';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createGovernanceRouter } from '../server/governance';
import { requestContext, securityHeaders } from '../server/production';

process.env.NODE_ENV = 'test';
process.env.CLICKO_DEV_AUTH_BYPASS = 'false';
process.env.AUTH_EMAIL_VERIFICATION_REQUIRED = 'false';
process.env.STRIPE_TEST_CHECKOUT = 'true';
process.env.STRIPE_WEBHOOK_SECRET = 'whsec_avatar_fixture_only';
const root = path.resolve(tmpdir());
const folder = mkdtempSync(path.join(root, 'clicko-avatar-browser-'));
const app = express();
app.use(requestContext, securityHeaders, express.json({
  verify: (req, _res, buffer) => {
    if (String(req.url).startsWith('/api/governance/billing/webhook')) {
      (req as express.Request & { rawBody?: Buffer }).rawBody = Buffer.from(buffer);
    }
  },
}));
app.use('/api/governance', createGovernanceRouter({ dataFile: path.join(folder, 'governance.json') }));
app.use('/api', (_req, res) => { res.status(404).json({ error: 'Outside avatar fixture scope' }); });
app.use(express.static(path.resolve('dist')));
app.get('*', (_req, res) => res.sendFile(path.resolve('dist/index.html')));
const server = app.listen(3109, '127.0.0.1');
function cleanup() {
  server.close();
  if (path.dirname(folder) === root && path.basename(folder).startsWith('clicko-avatar-browser-')) rmSync(folder, { recursive: true, force: true });
}
process.once('SIGTERM', () => { cleanup(); process.exit(0); });
process.once('SIGINT', () => { cleanup(); process.exit(0); });
process.once('exit', cleanup);
