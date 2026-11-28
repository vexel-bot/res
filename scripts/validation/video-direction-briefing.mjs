import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium, expect } from '@playwright/test';

const port = Number(process.env.PORT || 3018);
const origin = `http://127.0.0.1:${port}`;
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ acceptDownloads: true });
  await page.goto(`${origin}/studios/video/create`);
  const session = await page.request.get(`${origin}/api/governance/auth/session`);
  assert.ok(session.ok(), 'Start an isolated Clicko DEV profile.');
  const status = await page.request.get(`${origin}/api/development/status`).then(response => response.json());
  assert.equal(status.mode, 'local_development', 'Run this validation on an isolated Clicko DEV profile.');
  assert.equal(status.services.bridge, true);
  const project = page.getByRole('combobox', { name: 'Projeto', exact: true });
  await expect(project).toBeVisible({ timeout: 20_000 });
  await project.selectOption('');
  await page.getByLabel('Título', { exact: true }).fill('Etiquetas da cozinha');
  await page.getByLabel('Público', { exact: true }).fill('Pessoas que dividem uma cozinha.');
  await page.getByLabel('Briefing', { exact: true }).fill('Mostre como etiquetas ajudam a achar o pote certo sem abrir três tampas.');
  await page.getByRole('button', { name: 'Salvar projeto' }).click();

  const group = page.getByRole('group', { name: 'Conhecimentos de direção para incluir no briefing' });
  await expect(group.getByRole('checkbox')).toHaveCount(6);
  const downloadButton = page.getByRole('button', { name: 'Baixar briefing e formato do plano para o Claude' });
  async function downloadBriefing() {
    const ready = page.waitForEvent('download');
    await downloadButton.click();
    const download = await ready;
    assert.equal(download.suggestedFilename(), 'direcao-claude.json');
    return JSON.parse(await readFile(await download.path(), 'utf8'));
  }

  const basic = await downloadBriefing();
  assert.ok(!('directionNotes' in basic));
  await group.getByRole('checkbox', { name: 'Decupagem', exact: true }).check();
  await group.getByRole('checkbox', { name: 'Narração', exact: true }).check();
  const packet = await downloadBriefing();
  assert.deepEqual(packet.briefing, basic.briefing);
  assert.deepEqual(packet.materials, basic.materials);
  assert.deepEqual(packet.assembly, basic.assembly);
  assert.deepEqual(packet.directionNotes.map(note => note.id), ['decupagem', 'narracao']);
  for (const note of packet.directionNotes) {
    assert.ok(note.technique && note.example && note.check);
    assert.match(note.source, /^https:/);
  }
  assert.ok(!JSON.stringify(packet).includes('file://'));

  const projectId = await project.inputValue();
  await project.selectOption('');
  await project.selectOption(projectId);
  await expect(group.getByRole('checkbox', { name: 'Decupagem', exact: true })).not.toBeChecked();
  await expect(group.getByRole('checkbox', { name: 'Narração', exact: true })).not.toBeChecked();
  process.stdout.write(JSON.stringify(packet, null, 2) + '\n');
} finally {
  await browser.close();
}
