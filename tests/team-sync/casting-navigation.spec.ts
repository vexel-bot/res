import { test, expect } from '@playwright/test';

for (const format of ['image', 'video'] as const) {
  test(`library cast reaches the current ${format} Studio and survives reloading`, async ({ page }) => {
    await page.route('**/api/v1/studios/v1/identity-library?**', route => route.fulfill({ json: {
      workspaceId: new URL(route.request().url()).searchParams.get('workspace_id'),
      identities: [{ profile: { id:'person', displayName:'Pessoa de teste', identityType:'natural_person', status:'active' },
        versions:[{id:'face-v1', version:1, status:'active'}], selectedVersionId:'face-v1', previewAssetId:null, unavailableReason:null }],
      voices: [{ profile: { id:'voice', displayName:'Narradora de teste', voiceType:'cloned', status:'active' },
        versions:[{id:'voice-v1', version:1, status:'active'}], selectedVersionId:'voice-v1', previewAssetId:null, unavailableReason:null }],
      consents: [],
    } }));
    await page.goto('/library/identities');
    await page.getByRole('button', { name: format === 'image' ? 'Usar em imagem' : 'Usar em vídeo', exact:true }).click();
    await expect(page).toHaveURL(new RegExp(`${format === 'image' ? '/studios/tools/editorial' : '/studios/video/create'}\\?format=${format}&identityVersion=face-v1`));
    await expect(page.getByLabel('Pessoa ou personagem')).toHaveValue('face-v1');
    await page.getByLabel('Voz do projeto').selectOption('voice-v1');
    await page.reload();
    await expect(page.getByLabel('Pessoa ou personagem')).toHaveValue('face-v1');
    await expect(page.getByLabel('Voz do projeto')).toHaveValue('voice-v1');
  });
}
