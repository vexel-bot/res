import { test, expect, type Page } from '@playwright/test';
import type { DepartmentProject } from '../../src/studios/department/departmentApi';

// The session and UI are local; identity, provider and job are explicit fixtures.
async function fixture(page: Page, available: boolean) {
  const project: DepartmentProject = {
    id: 'appearance-project-fixture', workspaceId: 'pending', revision: 3, brandName: 'Marca de teste',
    title: 'Café de origem', objective: 'Explicar a origem e os critérios de escolha.', audience: 'Clientes da marca',
    tone: 'Claro', evidence: '', format: 'image', front: 'content', intent: 'education',
    identityVersionId: 'appearance-v1', casting: { identity: { id: 'appearance-v1', version: 1, consentGrantId: null } },
    directionId: 'guide', documentId: null, jobId: null, status: 'direction', planningBasis: 'Fixture',
    updatedAt: new Date().toISOString(), directions: [{ id: 'guide', title: 'Compare a origem', rationale: 'Teste',
      opening: 'De onde vem?', beats: ['Conheça a origem'], cta: 'Guarde', basis: 'fixture', knowledgeRefs: [] }],
  };
  const submissions: string[] = [];
  let accepted = false;
  await page.route('**/api/v1/studios/v1/identity-library?**', route => {
    project.workspaceId = new URL(route.request().url()).searchParams.get('workspace_id')!;
    return route.fulfill({ json: { workspaceId: project.workspaceId, consents: [], voices: [], identities: [{
      profile: { id: 'identity-fixture', displayName: 'Personagem de teste', identityType: 'synthetic_character', status: 'active' },
      versions: [{ id: 'appearance-v1', version: 1, status: 'active', capabilities: ['avatar.generate'] }],
      selectedVersionId: 'appearance-v1', previewAssetId: null, unavailableReason: null,
    }] } });
  });
  await page.route('**/api/v1/studios/v1/projects?**', route => {
    project.workspaceId = new URL(route.request().url()).searchParams.get('workspace_id')!;
    return route.fulfill({ json: [project] });
  });
  const base = `**/api/v1/studios/v1/projects/${project.id}`;
  await page.route(base, route => route.fulfill({ json: project }));
  await page.route(base + '/appearance/plan', route => route.fulfill({ json: { projectRevision: project.revision,
    planDigestSha256: 'a'.repeat(64), request: { direction: route.request().postDataJSON().direction, seed: 0 } } }));
  await page.route(base + '/appearance', route => {
    if (route.request().method() === 'POST') {
      const key = route.request().headers()['idempotency-key']; submissions.push(key);
      if (submissions.length === 1) return route.abort('failed');
      accepted = true;
      return route.fulfill({ status: 202, json: { id: 'fixture-job', status: 'queued', progress: 0, idempotencyKey: key } });
    }
    return route.fulfill({ json: { selection: null, availability: { available, reason: available ? null : 'appearance_provider_unavailable' },
      job: accepted ? { id: 'fixture-job', status: 'queued', progress: 0, idempotencyKey: submissions.at(-1), result: null, errorCode: null } : null } });
  });
  await page.goto(`/studios/tools/editorial?format=image&identityVersion=appearance-v1&project=${project.id}`);
  const panel = page.locator('.ds-appearance');
  await expect(panel.getByLabel('Como a pessoa deve aparecer?')).toBeVisible();
  return { panel, submissions };
}

test('shows unavailable model before sending an image request', async ({ page }) => {
  const scene = await fixture(page, false);
  await expect(scene.panel.getByText('A criação de imagens com esta aparência ainda não está disponível neste ambiente.')).toBeVisible();
  await expect(scene.panel.getByRole('button', { name: 'Preparar imagem' })).toBeDisabled();
  expect(scene.submissions).toHaveLength(0);
});

test('reload preserves an uncertain request and retries the same key', async ({ page }) => {
  const scene = await fixture(page, true);
  await scene.panel.getByLabel('Como a pessoa deve aparecer?').fill('Pessoa no cenário escolhido.');
  await scene.panel.getByRole('button', { name: 'Preparar imagem' }).click();
  await expect(scene.panel.getByRole('button', { name: 'Conferir o mesmo pedido' })).toBeEnabled();
  await page.reload();
  const panel = page.locator('.ds-appearance');
  await expect(panel.getByRole('button', { name: 'Conferir o mesmo pedido' })).toBeEnabled();
  await expect(panel.getByLabel('Como a pessoa deve aparecer?')).toHaveValue('Pessoa no cenário escolhido.');
  await panel.getByRole('button', { name: 'Conferir o mesmo pedido' }).click();
  await expect(panel.getByText('Preparando imagem', { exact: false })).toBeVisible();
  expect(scene.submissions).toHaveLength(2);
  expect(scene.submissions[1]).toBe(scene.submissions[0]);
});
