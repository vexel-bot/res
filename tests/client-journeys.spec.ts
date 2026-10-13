import { test, expect } from '@playwright/test';

test.use({ channel: 'chrome', viewport: { width: 1365, height: 900 } });

test('client portfolio distinguishes CRM record from licensed operation and explains activation', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/clients');
  await expect(page.getByRole('heading', { name: 'Clientes' })).toBeVisible();
  await expect(page.getByText('Cliente cadastrado').first()).toBeVisible();
  await page.locator('.cx-client-row').first().click();
  await expect(page.getByRole('button', { name: /Ativar operação na Clicko/ })).toBeVisible();
  await page.getByRole('button', { name: /Ativar operação na Clicko/ }).click();
  await expect(page.getByRole('dialog', { name: 'Ativar operação na Clicko' })).toBeVisible();
  await expect(page.getByText('O cliente assina diretamente')).toBeVisible();
  await expect(page.getByText('Eu gerencio e pago por ele')).toBeVisible();
});

test('journeys begin with goals and show the licence requirement in operational playbooks', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/automations');
  await expect(page.getByRole('heading', { name: 'Jornadas Clicko' })).toBeVisible();
  await page.getByRole('button', { name: 'Escolher objetivo' }).click();
  await expect(page.locator('.au-journey-card')).toHaveCount(11);
  await page.locator('.au-journey-card').filter({ hasText: 'Aprovar custos acima do limite' }).getByRole('button', { name: 'Usar jornada' }).click();
  await expect(page.getByText('Para operar separadamente em nome deste cliente')).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Cliente relacionado' })).toBeVisible();
});
