import express from 'express';
import { createHash } from 'node:crypto';
import { readFileSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { authenticate } from './governance';

type EvolutionEntry = { id: string; document: string; date: string; category: string; status: string };
export function readEvolutionCatalog(root = process.cwd()) {
  const directory = path.resolve(root, 'docs/evolution');
  const catalog = JSON.parse(readFileSync(path.join(directory, 'catalog.json'), 'utf8'));
  if (catalog.schemaVersion !== 'clicko.product-evolution.v1' || !Array.isArray(catalog.entries)) throw new Error('Invalid evolution catalog');
  const ids = new Set<string>();
  for (const entry of catalog.entries as EvolutionEntry[]) {
    const file = realpathSync(path.resolve(directory, entry.document));
    if (ids.has(entry.id) || path.dirname(file) !== directory || path.extname(file) !== '.md'
      || !['feature', 'update', 'fix', 'removal', 'analysis', 'pending'].includes(entry.category)
      || !['integrated', 'implemented', 'in_progress', 'planned'].includes(entry.status)) throw new Error('Invalid evolution record');
    readFileSync(file, 'utf8');
    ids.add(entry.id);
  }
  return { directory, catalog };
}

/** Evolution uses the current Clicko session; it does not require a media module. */
export function createEvolutionRouter(root = process.cwd()) {
  const router = express.Router();
  router.use(authenticate);
  router.get('/', (_req, res) => {
    try { res.json(readEvolutionCatalog(root).catalog); }
    catch { res.status(503).json({ detail: 'O histórico está temporariamente indisponível.' }); }
  });
  const detail = (download: boolean): express.RequestHandler => (req, res) => {
    try {
      const { directory, catalog } = readEvolutionCatalog(root);
      const entry = (catalog.entries as EvolutionEntry[]).find(item => item.id === req.params.id);
      if (!entry) return res.sendStatus(404);
      const markdown = readFileSync(path.join(directory, entry.document), 'utf8');
      res.set('Cache-Control', 'private, no-store');
      if (download) return res.type('text/markdown').attachment(entry.document).send(markdown);
      res.json({ ...entry, markdown, checksumSha256: createHash('sha256').update(markdown).digest('hex') });
    } catch { res.status(503).json({ detail: 'O documento está temporariamente indisponível.' }); }
  };
  router.get('/:id', detail(false));
  router.get('/:id/document', detail(true));
  return router;
}
