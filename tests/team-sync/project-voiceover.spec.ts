import { test, expect, type Page } from '@playwright/test';
import type { DepartmentProject } from '../../src/studios/department/departmentApi';

async function setup(page: Page) {
  let project: DepartmentProject | undefined;
  const saved: any[] = [];
  await page.route('**/api/v1/studios/v1/bridge/session', async route => {
    const response = await route.fetch();
    expect(response.ok()).toBeTruthy();
    const session = await response.json();
    session.assets = [
      { id: 'brand-image', title: 'Imagem da marca', type: 'image', mediaType: 'image/png', tags: [] },
      { id: 'brand-video', title: 'Vídeo da marca', type: 'video', mediaType: 'video/mp4', tags: [] },
    ];
    await route.fulfill({ response, json: session });
  });
  await page.route('**/api/v1/studios/v1/identity-library?**', route => route.fulfill({ json: {
    workspaceId: new URL(route.request().url()).searchParams.get('workspace_id'), consents: [],
    voices: [{ profile: { id: 'voice-profile', displayName: 'Narradora de teste', voiceType: 'stock', status: 'active' },
      versions: [{ id: 'voice-v1', version: 1, status: 'active' }], selectedVersionId: 'voice-v1', previewAssetId: null, unavailableReason: null }],
    identities: [{ profile: { id: 'person-profile', displayName: 'Personagem de teste', identityType: 'synthetic_character', status: 'active' },
      versions: [{ id: 'person-v1', version: 1, status: 'active', capabilities: ['avatar.generate'] }], selectedVersionId: 'person-v1', previewAssetId: null, unavailableReason: null }],
  } }));
  await page.route('**/api/v1/studios/v1/projects?**', route => route.fulfill({ json: project ? [project] : [] }));
  await page.route('**/api/v1/studios/v1/projects', route => {
    const input = route.request().postDataJSON(); saved.push(input);
    project = { ...input, id: 'voiceover-ui-project', revision: 2, brandName: 'Marca de teste', directionId: 'guide',
      documentId: null, jobId: null, status: 'direction', updatedAt: new Date().toISOString(), planningBasis: 'Fixture editorial.',
      casting: { voice: { id: input.voiceVersionId, version: 1, consentGrantId: null } },
      directions: [{ id: 'guide', title: 'Uma explicação clara', rationale: 'Partir da origem do café.', opening: 'De onde vem o café?',
        beats: ['Veja a origem.'], cta: 'Guarde para consultar.', basis: 'fixture', knowledgeRefs: ['F01'] }] };
    return route.fulfill({ status: 201, json: project });
  });
  await page.route('**/api/v1/studios/v1/projects/voiceover-ui-project', route => route.fulfill({ json: project }));
  await page.route('**/api/v1/studios/v1/projects/voiceover-ui-project/narration', route => route.fulfill({ json: {
    project, text: 'Uma fala final para a marca.', canGenerate: false, blocker: 'selected_voice_runtime_unavailable',
    assetId: null, job: null, requestKey: null,
  } }));
  await page.route('**/api/v1/studios/v1/projects/voiceover-ui-project/produce', route => route.fulfill({ status: 422,
    json: { detail: { code: 'voiceover_final_narration_required' } } }));
  await page.goto('/studios/video/create?format=video&voiceVersion=voice-v1');
  await expect(page.getByLabel('Voz do projeto')).toHaveValue('voice-v1');
  return { saved };
}

test('a selected narrator enables images and incompatible selections are cleared explicitly', async ({ page }, testInfo) => {
  await setup(page);
  const material = page.getByLabel('Material de origem', { exact: true });
  await expect(material.locator('option[value="brand-image"]')).toHaveCount(1);
  await material.selectOption('brand-image');
  await expect(page.getByText('A montagem usa a voz escolhida', { exact: false })).toBeVisible();
  await expect(material).toHaveJSProperty('required', true);
  await page.getByLabel('Voz do projeto').selectOption('');
  await expect(material).toHaveValue('');
  await expect(material.locator('option[value="brand-image"]')).toHaveCount(0);
  await page.getByLabel('Voz do projeto').selectOption('voice-v1');
  await material.selectOption('brand-image');
  await page.getByLabel('Pessoa ou personagem').selectOption('person-v1');
  await expect(material).toHaveValue('');
  await expect(material).toHaveJSProperty('required', false);
  await expect(page.getByText('O vídeo de apoio é opcional', { exact: false })).toBeVisible();
  await page.locator('.department-studio').screenshot({ path: testInfo.outputPath('voiceover-materials.png') });
});

test('image and narrator are saved together and the project explains a missing final narration', async ({ page }) => {
  const scene = await setup(page);
  await page.getByLabel('Assunto', { exact: true }).fill('A origem do café');
  await page.getByLabel('O que você quer que o público entenda ou faça?', { exact: true }).fill('Comparar a origem com o seu gosto.');
  await page.getByLabel('Para quem?', { exact: true }).fill('Pessoas que preparam café em casa');
  await page.getByLabel('Material de origem', { exact: true }).selectOption('brand-image');
  await page.getByRole('button', { name: 'Explorar direções', exact: true }).click();
  await expect(page.locator('.ds-narration')).toContainText('O áudio original continua no arquivo de origem.');
  expect(scene.saved).toHaveLength(1);
  expect(scene.saved[0]).toMatchObject({ format: 'video', sourceAssetId: 'brand-image', voiceVersionId: 'voice-v1' });
  expect(scene.saved[0].identityVersionId).toBeUndefined();
  await page.getByRole('button', { name: 'Preparar primeira versão', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Conclua a narração com a voz escolhida antes de preparar a montagem.' })).toBeVisible();
  await expect(page.locator('.ds-narration').getByLabel('Texto da narração')).toHaveValue('Uma fala final para a marca.');
});
