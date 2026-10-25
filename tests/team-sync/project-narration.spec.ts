import { test, expect, type Page } from '@playwright/test';
import type { DepartmentProject, NarrationState, StudioFormat } from '../../src/studios/department/departmentApi';

// The real application/session/bridge runs locally. Narration, project and cast
// responses below are fixtures. No ML model or person's voice is qualified.
async function fixture(page: Page, options: { format?: StudioFormat; available?: boolean; loseResponse?: boolean; complete?: boolean } = {}) {
  const project: DepartmentProject = {
    id: 'narration-project-fixture', workspaceId: 'pending', revision: 2, brandName: 'Marca de teste',
    title: 'Uma ideia clara sobre café', objective: 'Explicar a origem do café.', audience: 'Pessoas que preparam café em casa',
    tone: 'Claro', evidence: 'Origem informada pelo produtor.', format: options.format || 'image', front: 'content', intent: 'education',
    voiceVersionId: 'voice-v1', casting: { voice: { id: 'voice-v1', version: 1, consentGrantId: null } },
    directionId: 'guide', documentId: null, jobId: null, status: 'direction', planningBasis: 'Fixture editorial.', updatedAt: new Date().toISOString(),
    directions: [{ id: 'guide', title: 'Uma direção específica', rationale: 'Partir da origem informada.', opening: 'De onde vem o café?',
      beats: ['Observe a origem.', 'Compare com seu gosto.'], cta: 'Guarde para consultar.', basis: 'fixture', knowledgeRefs: ['F01'] }],
  };
  const state: NarrationState = { project, text: 'Uma fala inicial sobre a origem.', requestKey: null, generatedText: null,
    canGenerate: options.available !== false, blocker: options.available === false ? 'selected_voice_runtime_unavailable' : null,
    assetId: null, job: null };
  const submissions: unknown[] = [];
  let cancellations = 0;
  await page.route('**/api/v1/studios/v1/identity-library?**', route => {
    project.workspaceId = new URL(route.request().url()).searchParams.get('workspace_id')!;
    return route.fulfill({ json: { workspaceId: project.workspaceId, identities: [], consents: [], voices: [{
      profile: { id: 'voice-fixture', displayName: 'Narradora de teste', voiceType: 'stock', status: 'active' },
      versions: [{ id: 'voice-v1', version: 1, status: 'active' }], selectedVersionId: 'voice-v1', previewAssetId: null, unavailableReason: null,
    }] } });
  });
  await page.route('**/api/v1/studios/v1/projects?**', route => {
    project.workspaceId = new URL(route.request().url()).searchParams.get('workspace_id')!;
    return route.fulfill({ json: [project] });
  });
  await page.route(`**/api/v1/studios/v1/projects/${project.id}`, route => route.fulfill({ json: project }));
  await page.route(`**/api/v1/studios/v1/projects/${project.id}/narration`, route => {
    const request = route.request();
    if (request.method() === 'PATCH') {
      state.text = request.postDataJSON().text;
      project.revision++;
      return route.fulfill({ json: state });
    }
    if (request.method() === 'POST') {
      const body = request.postDataJSON(); submissions.push(body);
      state.text = body.text; state.requestKey = body.requestKey;
      state.job = { id: 'narration-job-fixture', status: 'queued', progress: 0, errorCode: null };
      project.revision++;
      if (options.loseResponse) return route.abort('failed');
      return route.fulfill({ status: 202, json: state });
    }
    if (options.complete && state.job?.status === 'queued') {
      state.job.status = 'succeeded'; state.job.progress = 100;
      state.assetId = 'private-narration-fixture'; state.generatedText = state.text;
    }
    return route.fulfill({ json: state });
  });
  await page.route(`**/api/v1/studios/v1/projects/${project.id}/narration/cancel`, route => {
    cancellations++;
    if (state.job) state.job.status = 'cancelled';
    return route.fulfill({ json: state });
  });
  const wav = Buffer.alloc(44 + 4800);
  wav.write('RIFF', 0); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(24000, 24); wav.writeUInt32LE(48000, 28); wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34);
  wav.write('data', 36); wav.writeUInt32LE(4800, 40);
  await page.route('**/api/v1/assets/private-narration-fixture/content', route => {
    expect(route.request().headers()['x-clicko-studio-module']).toBe(options.format === 'video' ? 'create-video' : 'create-image');
    return route.fulfill({ contentType: 'audio/wav', body: wav });
  });
  const url = `${options.format === 'video' ? '/studios/video/create' : '/studios/tools/editorial'}?format=${project.format}&voiceVersion=voice-v1&project=${project.id}`;
  await page.goto(url);
  const panel = page.locator('.ds-narration');
  await expect(panel.getByLabel('Texto da narração')).toHaveValue(state.text);
  return { panel, url, state, submissions, cancellations: () => cancellations };
}

test('narration text is saved and reopened even while the selected voice runtime is unavailable', async ({ page }, testInfo) => {
  const scene = await fixture(page, { available: false });
  await scene.panel.getByLabel('Texto da narração').fill('Um texto revisado, específico para a marca.');
  await scene.panel.getByRole('button', { name: 'Salvar texto', exact: true }).click();
  await expect(scene.panel.getByText('Texto salvo no projeto. Nenhum áudio foi gerado.')).toBeVisible();
  await expect(scene.panel.getByRole('button', { name: 'Gerar narração', exact: true })).toBeDisabled();
  await page.reload();
  await expect(scene.panel.getByLabel('Texto da narração')).toHaveValue('Um texto revisado, específico para a marca.');
  await scene.panel.screenshot({ path: testInfo.outputPath('narration-panel.png') });
  expect(scene.submissions).toHaveLength(0);
});

test('a lost response is reconciled without another narration job and the user can cancel', async ({ page }) => {
  const scene = await fixture(page, { format: 'video', loseResponse: true });
  await scene.panel.getByLabel('Texto da narração').fill('Uma fala preservada para o vídeo.');
  await scene.panel.getByRole('button', { name: 'Gerar narração', exact: true }).click();
  await expect(scene.panel.getByText('Pedido recuperado. Acompanhe a narração abaixo.')).toBeVisible();
  await expect(scene.panel.getByRole('alert')).toHaveCount(0);
  expect(scene.submissions).toHaveLength(1);
  await expect(scene.panel.getByLabel('Texto da narração')).toBeDisabled();
  await scene.panel.getByRole('button', { name: 'Cancelar narração', exact: true }).click();
  await expect(scene.panel.getByRole('status').filter({ hasText: 'Narração cancelada' })).toBeVisible();
  expect(scene.cancellations()).toBe(1);
  expect(scene.submissions).toHaveLength(1);
});

test('completed narration exposes private playback controls and a scoped download', async ({ page }, testInfo) => {
  const scene = await fixture(page, { complete: true });
  await scene.panel.getByRole('button', { name: 'Gerar narração', exact: true }).click();
  await expect(scene.panel.getByRole('status').filter({ hasText: 'Narração disponível' })).toBeVisible();
  await scene.panel.getByRole('button', { name: 'Ouvir narração', exact: true }).click();
  await expect(scene.panel.getByLabel('Narração produzida com a voz escolhida')).toHaveAttribute('src', /^blob:/);
  const download = page.waitForEvent('download');
  await scene.panel.getByRole('link', { name: 'Baixar narração', exact: true }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe('narracao.wav');
  await file.saveAs(testInfo.outputPath('narracao-fixture.wav'));
  expect(scene.submissions).toHaveLength(1);
});
