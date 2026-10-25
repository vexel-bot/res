import { test, expect, type Page } from '@playwright/test';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import type { AvatarState, DepartmentProject } from '../../src/studios/department/departmentApi';

// Current application and session are real. Cast/jobs below are explicit test
// fixtures. FFmpeg creates a short silent clip, not a generated human/avatar.
async function fixture(page: Page, options: { available?: boolean; lost?: boolean; complete?: boolean } = {}) {
  const project: DepartmentProject = { id: 'avatar-project-fixture', workspaceId: 'pending', revision: 3, brandName: 'Marca de teste',
    title: 'A origem do café', objective: 'Explicar a origem e os critérios de escolha.', audience: 'Pessoas que preparam café em casa',
    tone: 'Claro', evidence: 'Origem informada pelo produtor.', format: 'video', front: 'content', intent: 'education',
    identityVersionId: 'appearance-v1', voiceVersionId: 'voice-v1', casting: { identity: { id: 'appearance-v1', version: 1, consentGrantId: null },
      voice: { id: 'voice-v1', version: 1, consentGrantId: null } }, directionId: 'guide', documentId: null, jobId: null,
    status: 'direction', planningBasis: 'Fixture editorial.', updatedAt: new Date().toISOString(),
    directions: [{ id: 'guide', title: 'Compare a origem', rationale: 'Partir da informação do produtor.', opening: 'De onde vem o café?',
      beats: ['Observe a origem.', 'Compare com seu gosto.'], cta: 'Guarde para consultar.', basis: 'fixture', knowledgeRefs: ['F01'] }] };
  const state: AvatarState = { project, requestKey: null, canGenerate: options.available !== false,
    blocker: options.available === false ? 'avatar_provider_runtime_unavailable' : null, assetId: null, job: null };
  const submissions: { key: string; body: any }[] = [];
  await page.route('**/api/v1/studios/v1/identity-library?**', route => {
    project.workspaceId = new URL(route.request().url()).searchParams.get('workspace_id')!;
    return route.fulfill({ json: { workspaceId: project.workspaceId, consents: [], identities: [{
      profile: { id: 'appearance-fixture', displayName: 'Personagem de teste', identityType: 'synthetic_character', status: 'active' },
      versions: [{ id: 'appearance-v1', version: 1, status: 'active', capabilities: ['avatar.generate'] }],
      selectedVersionId: 'appearance-v1', previewAssetId: null, unavailableReason: null,
    }], voices: [{ profile: { id: 'voice-fixture', displayName: 'Narradora de teste', voiceType: 'stock', status: 'active' },
      versions: [{ id: 'voice-v1', version: 1, status: 'active' }], selectedVersionId: 'voice-v1', previewAssetId: null, unavailableReason: null }] } });
  });
  await page.route('**/api/v1/studios/v1/projects?**', route => {
    project.workspaceId = new URL(route.request().url()).searchParams.get('workspace_id')!;
    return route.fulfill({ json: [project] });
  });
  const base = `**/api/v1/studios/v1/projects/${project.id}`;
  await page.route(base, route => route.fulfill({ json: project }));
  await page.route(base + '/narration', route => route.fulfill({ json: { project, text: 'Uma fala final de teste.', generatedText: 'Uma fala final de teste.',
    canGenerate: false, blocker: null, assetId: null, job: null, requestKey: null } }));
  await page.route(base + '/avatar/plan', route => route.fulfill({ json: { schemaVersion: 'clicko.project-avatar-plan.v1', operation: 'generate_avatar',
    documentId: 'avatar-context-fixture', expectedRevision: project.revision, durationSeconds: 2.8, planDigestSha256: 'a'.repeat(64),
    performanceDirection: route.request().postDataJSON().performanceDirection } }));
  await page.route(base + '/avatar', route => {
    if (route.request().method() === 'POST') {
      const key = route.request().headers()['idempotency-key'];
      submissions.push({ key, body: route.request().postDataJSON() });
      state.performanceDirection = route.request().postDataJSON().performanceDirection;
      state.requestKey = key; project.revision++;
      state.job = { id: 'avatar-job-fixture', status: options.complete ? 'succeeded' : 'queued', progress: options.complete ? 100 : 0, errorCode: null };
      if (options.complete) state.assetId = 'private-avatar-fixture';
      if (options.lost) return route.abort('failed');
      return route.fulfill({ status: 202, json: { id: state.job.id } });
    }
    return route.fulfill({ json: state });
  });
  await page.route(base + '/avatar/cancel', route => {
    if (state.job) state.job.status = 'cancelled';
    return route.fulfill({ json: { id: state.job?.id } });
  });
  await page.route('**/api/v1/studios/v1/jobs/avatar-job-fixture', route => route.fulfill({ json: { id: 'avatar-job-fixture', status: state.job?.status } }));
  const url = `/studios/video/create?format=video&identityVersion=appearance-v1&voiceVersion=voice-v1&project=${project.id}`;
  await page.goto(url);
  const panel = page.locator('.ds-avatar');
  await expect(panel.getByLabel('Como deve ser a apresentação?')).toBeVisible();
  return { panel, submissions, state };
}

test('avatar preserves selections and explains unavailable local production', async ({ page }, testInfo) => {
  const scene = await fixture(page, { available: false });
  await expect(scene.panel.getByText('A produção da apresentação ainda não está disponível', { exact: false })).toBeVisible();
  await expect(scene.panel.getByRole('button', { name: 'Preparar apresentação', exact: true })).toBeDisabled();
  await page.reload();
  await expect(page.locator('.ds-avatar').getByLabel('Como deve ser a apresentação?')).toBeVisible();
  expect(scene.submissions).toHaveLength(0);
  await scene.panel.screenshot({ path: testInfo.outputPath('avatar-panel.png') });
});

test('lost avatar acknowledgement is reconciled and can be cancelled without another submission', async ({ page }) => {
  const scene = await fixture(page, { lost: true });
  await scene.panel.getByLabel('Como deve ser a apresentação?').fill('Postura tranquila, gestos discretos e fala clara.');
  await scene.panel.getByRole('button', { name: 'Preparar apresentação', exact: true }).click();
  await expect(scene.panel.getByText('Pedido recuperado. Acompanhe a apresentação abaixo.')).toBeVisible();
  await expect(scene.panel.getByRole('alert')).toHaveCount(0);
  expect(scene.submissions).toHaveLength(1);
  expect(scene.submissions[0].body.performanceDirection).toContain('gestos discretos');
  expect(scene.submissions[0].body).not.toHaveProperty('schemaVersion');
  await scene.panel.getByRole('button', { name: 'Cancelar apresentação', exact: true }).click();
  await expect(scene.panel.getByRole('status').filter({ hasText: 'Apresentação cancelada' })).toBeVisible();
  await page.reload();
  await expect(page.locator('.ds-avatar').getByLabel('Como deve ser a apresentação?')).toHaveValue('Postura tranquila, gestos discretos e fala clara.');
  expect(scene.submissions).toHaveLength(1);
});

test('completed avatar has scoped private playback and download', async ({ page }, testInfo) => {
  const filename = testInfo.outputPath('silent-fixture.mp4');
  const encoded = spawnSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=0x334031:s=160x90:r=25:d=0.4',
    '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-shortest', '-threads', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-y', filename]);
  expect(encoded.status, encoded.stderr?.toString()).toBe(0);
  await page.route('**/api/v1/assets/private-avatar-fixture/content', route => {
    expect(route.request().headers()['x-clicko-studio-module']).toBe('create-video');
    return route.fulfill({ contentType: 'video/mp4', body: readFileSync(filename) });
  });
  const scene = await fixture(page, { complete: true });
  await scene.panel.getByRole('button', { name: 'Preparar apresentação', exact: true }).click();
  await expect(scene.panel.getByRole('status').filter({ hasText: 'Apresentação disponível' })).toBeVisible();
  await scene.panel.getByRole('button', { name: 'Ver apresentação', exact: true }).click();
  const video = scene.panel.getByLabel('Apresentação com a aparência e a voz escolhidas');
  await expect(video).toHaveAttribute('src', /^blob:/);
  await expect(video).toHaveJSProperty('videoWidth', 160);
  const download = page.waitForEvent('download');
  await scene.panel.getByRole('link', { name: 'Baixar apresentação', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('apresentacao.mp4');
  expect(scene.submissions).toHaveLength(1);
});
