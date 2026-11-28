import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium, expect } from '@playwright/test';

const port = Number(process.env.PORT || 3018);
const origin = `http://127.0.0.1:${port}`;
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ acceptDownloads: true });
  await page.goto(`${origin}/studios/video/create`, { waitUntil: 'domcontentloaded', timeout: 90_000 });
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
  await page.getByRole('spinbutton', { name: 'Duração desejada (segundos)' }).fill('24');
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
  assert.ok(!('decoupageNotes' in basic));
  assert.ok(!('format' in basic.scriptDirection));
  assert.equal(basic.scriptDirection.scenePlan.length, 3);
  assert.equal(basic.scriptDirection.references.length, 2);

  const format = page.getByLabel('Objetivo do roteiro no briefing', { exact: true });
  const techniques = page.getByRole('group', { name: 'Inclua os temas pertinentes ao corte' });
  await page.getByText('Técnicas práticas de decupagem', { exact: true }).click();
  await expect(techniques.getByRole('checkbox')).toHaveCount(4);
  await format.selectOption('explainer');
  await techniques.getByRole('checkbox', { name: 'Tempo, comparação e interface', exact: true }).check();
  await group.getByRole('checkbox', { name: 'Decupagem', exact: true }).check();
  await group.getByRole('checkbox', { name: 'Narração', exact: true }).check();
  const packet = await downloadBriefing();
  assert.deepEqual(packet.briefing, basic.briefing);
  assert.deepEqual(packet.materials, basic.materials);
  assert.deepEqual(packet.assembly, basic.assembly);
  assert.equal(packet.scriptDirection.format.id, 'explainer');
  assert.match(packet.scriptDirection.format.question, /que dado mudou/);
  assert.deepEqual(packet.decoupageNotes.map(topic => topic.id), ['reading']);
  assert.equal(packet.decoupageNotes[0].techniques.length, 5);
  assert.ok(packet.decoupageNotes[0].techniques.every(technique => technique.practice && technique.check));
  assert.deepEqual(packet.directionNotes.map(note => note.id), ['decupagem', 'narracao']);
  for (const note of packet.directionNotes) {
    assert.ok(note.technique && note.example && note.check);
    assert.match(note.source, /^https:/);
  }
  assert.ok(!JSON.stringify(packet).includes('file://'));

  await format.selectOption('ad');
  for (const checkbox of await techniques.getByRole('checkbox').all()) await checkbox.check();
  const ad = await downloadBriefing();
  assert.equal(ad.scriptDirection.format.id, 'ad');
  assert.equal(ad.commercialCopy.status, 'pending');
  assert.match(ad.scriptDirection.format.variation, /CTA/);
  assert.equal(ad.decoupageNotes.flatMap(topic => topic.techniques).length, 20);
  assert.equal(new Set(ad.decoupageNotes.flatMap(topic => topic.techniques.map(technique => technique.name))).size, 20);
  assert.deepEqual(ad.assembly, basic.assembly);

  const copy = page.locator('details.ad-copy-process');
  await copy.getByText('Copy para anúncios em vídeo', { exact: true }).click();
  await expect(copy.getByRole('button', { name: 'Gerar copy na Clicko' })).toBeDisabled();
  const badRequest = await page.request.post(`${origin}/api/ai/generate-video-ad-copy`, { data: { data: {} } });
  assert.equal(badRequest.status(), 422);
  await copy.getByLabel('Tipo de oferta', { exact: true }).selectOption('product');
  await copy.getByLabel('Momento do público', { exact: true }).selectOption('consideration');
  await expect(copy.getByText(/Mostre o produto em uso/)).toBeVisible();
  await expect(copy.getByText(/Nomeie a dúvida/)).toBeVisible();
  const context = {
    'O que é anunciado': 'Etiquetas laváveis',
    'Benefício para o público': 'Identificar o conteúdo do pote',
    'Oferta': 'Kit de etiquetas para potes',
    'Ação desejada': 'Abra a página do kit',
    'Destino da ação': 'Página de produto',
    'Condições e limites': 'Para recipientes lisos',
  };
  for (const [name, value] of Object.entries(context)) await copy.getByRole('textbox', { name, exact: true }).fill(value);
  const evidence = copy.getByRole('textbox', { name: 'Afirmações confirmadas', exact: true });
  await evidence.fill('As etiquetas aderem a recipientes lisos | Ficha do kit | 2000-01-01');
  await expect(copy.getByRole('button', { name: 'Gerar copy na Clicko' })).toBeDisabled();
  await evidence.fill('As etiquetas aderem a recipientes lisos | Ficha do kit');
  await expect(copy.getByRole('button', { name: 'Gerar copy na Clicko' })).toBeEnabled();
  await page.route('**/api/ai/generate-video-ad-copy', async route => {
    const request = route.request().postDataJSON();
    assert.equal(request.data.videoMoment, 'consideration');
    assert.equal(request.data.videoKind, 'product');
    assert.equal(request.durationSeconds, 24);
    await route.fulfill({ json: {
      angle: 'Resolva a busca vendo o rótulo',
      hook: 'Qual dos potes tem arroz?',
      alternateHook: 'Ache o pote sem tirar a tampa.',
      body: 'As etiquetas aderem a recipientes lisos. Escreva o conteúdo e identifique o pote.',
      hypothesis: 'Comparar começar pela dúvida ou pelo benefício.',
    } });
  });
  await copy.getByRole('button', { name: 'Gerar copy na Clicko' }).click();
  const selectedHook = copy.getByRole('textbox', { name: 'Gancho escolhido', exact: true });
  await expect(selectedHook).toHaveValue('Qual dos potes tem arroz?');
  await copy.getByRole('button', { name: 'Usar a outra abertura' }).click();
  await copy.getByRole('button', { name: 'Salvar contexto e copy' }).click();
  await expect(copy.getByRole('status')).toHaveText('Versão 1 incluída no briefing do anúncio.');
  const withCopy = await downloadBriefing();
  assert.equal(withCopy.commercialCopy.revision, 1);
  assert.equal(withCopy.commercialCopy.durationSeconds, 24);
  assert.equal(withCopy.commercialCopy.copy.hook, 'Ache o pote sem tirar a tampa.');
  assert.equal(withCopy.commercialCopy.copy.cta, context['Ação desejada']);
  assert.equal(withCopy.commercialCopy.context.evidence[0].source, 'Ficha do kit');
  assert.equal(withCopy.commercialCopy.context.restrictions, 'Para recipientes lisos');
  assert.equal(withCopy.commercialCopy.experiment.alternateHook, 'Qual dos potes tem arroz?');
  assert.deepEqual(withCopy.assembly, basic.assembly);
  await selectedHook.fill('Alteração não salva');
  assert.equal((await downloadBriefing()).commercialCopy.copy.hook, withCopy.commercialCopy.copy.hook);

  await format.selectOption('brand');
  const brand = await downloadBriefing();
  assert.ok(!('commercialCopy' in brand));
  assert.equal(brand.scriptDirection.format.id, 'brand');
  assert.match(brand.scriptDirection.format.example, /despertador/);
  await page.getByLabel('Importar o plano do Claude', { exact: true }).setInputFiles({
    name: 'montagem.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({ assembly: brand.assembly })),
  });
  const assemblyInput = page.getByRole('textbox', { name: 'Plano de montagem do Claude (JSON)', exact: true });
  await expect(assemblyInput).toHaveValue(JSON.stringify({ assembly: brand.assembly }, null, 2));

  const projectId = await project.inputValue();
  await project.selectOption('');
  await project.selectOption(projectId);
  await expect(group.getByRole('checkbox', { name: 'Decupagem', exact: true })).not.toBeChecked();
  await expect(group.getByRole('checkbox', { name: 'Narração', exact: true })).not.toBeChecked();
  await expect(format).toHaveValue('');
  assert.deepEqual((await downloadBriefing()).commercialCopy, withCopy.commercialCopy);
  await page.getByText('Técnicas práticas de decupagem', { exact: true }).click();
  for (const checkbox of await techniques.getByRole('checkbox').all()) await expect(checkbox).not.toBeChecked();
  process.stdout.write(JSON.stringify(packet, null, 2) + '\n');
} finally {
  await browser.close();
}
