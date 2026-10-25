import { test, expect } from '@playwright/test';

// UI contract tests: previews, catalog, uploads and decisions are fixtures.
// These tests make no claim about voice synthesis or face/avatar quality.
test('voice review persists observations and requires a separate explicit decision', async ({ page }) => {
  let active = false;
  let evaluations: Record<string, unknown>[] = [];
  let evaluationBody: Record<string, unknown> | undefined;
  let reviewBody: Record<string, unknown> | undefined;
  const path = '**/api/v1/studios/v1/voices/voice-fixture/versions/voice-v1';
  await page.route('**/api/v1/studios/v1/identity-library?**', route => route.fulfill({ json: {
    workspaceId: new URL(route.request().url()).searchParams.get('workspace_id'), permissions: { canReview: true },
    identities: [], consents: [], voices: [{
      profile: { id: 'voice-fixture', displayName: 'Voz de teste', voiceType: 'cloned', status: active ? 'active' : 'draft' },
      versions: [{ id: 'voice-v1', version: 1, status: active ? 'active' : 'draft' }],
      selectedVersionId: active ? 'voice-v1' : null, previewAssetId: null, unavailableReason: active ? null : 'Pending review',
    }],
  } }));
  await page.route(`${path}/evaluations`, async route => {
    if (route.request().method() === 'GET') return route.fulfill({ json: evaluations });
    evaluationBody = route.request().postDataJSON() as Record<string, unknown>;
    const value = { ...evaluationBody, id: 'evaluation-fixture', evaluatedAt: new Date().toISOString(), evaluatedBy: 'reviewer-fixture' };
    evaluations = [value, ...evaluations];
    return route.fulfill({ status: 201, json: value });
  });
  await page.route('**/api/v1/assets/upload', route => route.fulfill({ json: { id: 'private-preview-fixture' } }));
  await page.route(`${path}/review`, route => {
    reviewBody = route.request().postDataJSON() as Record<string, unknown>;
    active = true;
    return route.fulfill({ json: { id: 'voice-v1', status: 'active' } });
  });
  const openReview = async () => {
    await page.getByRole('button', { name: /^Vozes/ }).click();
    await page.getByText('1 versão(ões) · histórico', { exact: true }).click();
    await page.getByRole('button', { name: 'Avaliar versão 1', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Voz de teste · versão 1' })).toBeVisible();
  };
  await page.goto('/library/identities');
  await openReview();
  const approve = page.getByRole('button', { name: 'Aprovar versão para seleção' });
  await expect(approve).toBeDisabled();
  await page.getByLabel('Prévia privada desta versão', { exact: true }).setInputFiles({
    name: 'preview.wav', mimeType: 'audio/wav', buffer: Buffer.from('fixture-not-a-generated-voice'),
  });
  await page.getByLabel('Examinei a prévia e confirmei que ela pertence a esta versão.').check();
  await page.getByLabel('A voz corresponde à referência autorizada.').check();
  await page.getByLabel('Conferi a pronúncia em português e a qualidade do áudio.').check();
  await page.getByLabel('Observações da avaliação').fill('Contrato de teste; não qualifica síntese de voz.');
  await page.getByRole('button', { name: 'Registrar avaliação', exact: true }).click();
  await expect(page.getByText('Avaliação registrada. A aprovação da versão é uma decisão separada, abaixo.')).toBeVisible();
  expect(evaluationBody).toMatchObject({ evaluatorKind: 'human', status: 'passed', previewAssetIds: ['private-preview-fixture'] });
  expect(evaluationBody).not.toHaveProperty('qualityMetrics');
  expect(reviewBody).toBeUndefined();
  await expect(approve).toBeDisabled();
  await page.reload();
  await openReview();
  await expect(page.getByText('Contrato de teste; não qualifica síntese de voz.')).toBeVisible();
  await page.getByLabel('Comentário da decisão').fill('Prévia conferida pelo responsável de teste.');
  await expect(approve).toBeDisabled();
  await page.getByLabel('Conferi a avaliação mais recente e suas prévias para aprovar esta versão.').check();
  await approve.click();
  await expect(page.getByText('Versão aprovada para seleção. A geração depende de um motor disponível e das autorizações vigentes.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Usar em vídeo', exact: true })).toBeVisible();
  expect(reviewBody).toMatchObject({ action: 'approve', comment: 'Prévia conferida pelo responsável de teste.' });
});

test('a failed latest evaluation cannot activate a face and avatar version', async ({ page }) => {
  await page.route('**/api/v1/studios/v1/identity-library?**', route => route.fulfill({ json: {
    workspaceId: new URL(route.request().url()).searchParams.get('workspace_id'), permissions: { canReview: true },
    voices: [], consents: [], identities: [{
      profile: { id: 'person-fixture', displayName: 'Pessoa de teste', identityType: 'natural_person', status: 'draft' },
      versions: [{ id: 'face-v1', version: 1, status: 'draft', capabilities: ['image.use', 'avatar.generate'] }],
      selectedVersionId: null, previewAssetId: null, unavailableReason: 'Pending review',
    }],
  } }));
  await page.route('**/api/v1/studios/v1/identities/person-fixture/versions/face-v1/evaluations', route => route.fulfill({ json: [
    { id: 'failed', status: 'failed', evaluatedAt: new Date().toISOString(), evaluatedBy: 'fixture', notes: 'Movimento precisa de ajustes.', checks: [], previewAssetIds: [] },
    { id: 'older-pass', status: 'passed', evaluatedAt: '2026-10-01T10:00:00Z', evaluatedBy: 'fixture', checks: [], previewAssetIds: [] },
  ] }));
  await page.goto('/library/identities');
  await page.getByText('1 versão(ões) · histórico', { exact: true }).click();
  await page.getByRole('button', { name: 'Avaliar versão 1', exact: true }).click();
  await expect(page.getByText('Movimento precisa de ajustes.')).toBeVisible();
  await expect(page.getByLabel('Prévia privada desta versão', { exact: true })).toHaveAttribute('accept', 'video/*');
  await page.getByLabel('Comentário da decisão').fill('Não aprovar uma avaliação anterior.');
  await page.getByLabel('Conferi a avaliação mais recente e suas prévias para aprovar esta versão.').check();
  await expect(page.getByRole('button', { name: 'Aprovar versão para seleção' })).toBeDisabled();
});
