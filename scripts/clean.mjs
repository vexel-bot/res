import { rm } from 'node:fs/promises';

for (const target of ['dist', 'server.js']) {
  await rm(new URL(`../${target}`, import.meta.url), { recursive: true, force: true });
}
