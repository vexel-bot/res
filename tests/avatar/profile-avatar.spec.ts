import { test, expect } from '@playwright/test';
import sharp from 'sharp';
import { createHmac } from 'node:crypto';

test('profile preview, save, reload, logout/login and a new browser session', async ({ page, context, browser }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  const credentials = { name: 'Avatar Validation', email: `avatar-${Date.now()}@example.test`, password: 'PhotoTest123', confirmation: 'PhotoTest123', termsAccepted: true, privacyAccepted: true, remember: true };
  const signup = await context.request.post('/api/governance/auth/signup', { data: credentials });
  expect(signup.status()).toBe(201);
  // A new account has no plan. Activate only this isolated fixture through the
  // existing signed test webhook, preserving the production subscription gate.
  const created = await signup.json();
  const checkoutResponse = await context.request.post('/api/governance/billing/checkout', { data: { planId: 'solo' } });
  expect(checkoutResponse.status()).toBe(201);
  const checkout = await checkoutResponse.json();
  const body = JSON.stringify({
    id: `evt_avatar_${Date.now()}`,
    type: 'checkout.session.completed',
    data: { object: {
      id: String(checkout.checkoutUrl).split('/').pop(),
      payment_status: 'paid', customer: 'cus_avatar_fixture', subscription: 'sub_avatar_fixture',
      metadata: { checkoutId: checkout.checkoutSessionId, workspaceId: created.account.workspaceId, planId: 'solo' },
    } },
  });
  const timestamp = Math.floor(Date.now() / 1000);
  const signature = createHmac('sha256', 'whsec_avatar_fixture_only').update(`${timestamp}.${body}`).digest('hex');
  const activated = await context.request.post('/api/governance/billing/webhook', {
    headers: { 'Content-Type': 'application/json', 'stripe-signature': `t=${timestamp},v1=${signature}` }, data: body,
  });
  expect(activated.status()).toBe(200);
  const billingStatus = await context.request.get('/api/governance/billing/status');
  expect((await billingStatus.json()).accessAllowed).toBe(true);
  await page.goto('/settings');
  const input = page.getByLabel('Alterar foto de perfil');
  await expect(input).toBeAttached();
  const buffer = await sharp({ create: { width: 700, height: 500, channels: 3, background: '#ff7f50' } }).png().toBuffer();
  const file = { name: 'profile.png', mimeType: 'image/png', buffer };
  const chooserEvent = page.waitForEvent('filechooser');
  await input.click();
  await (await chooserEvent).setFiles(file);
  const avatar = page.locator('.clicko-profile-photo img');
  await expect(avatar).toHaveAttribute('src', /^blob:/);
  // Native picker return triggers the same focus verification as production.
  const checked = page.waitForResponse(r => r.url().endsWith('/auth/session'));
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await checked;
  await expect(avatar).toHaveAttribute('src', /^blob:/);
  await expect(avatar).toHaveCSS('object-fit', 'cover');
  const upload = page.waitForResponse(r => r.url().endsWith('/profile/avatar') && r.request().method() === 'PUT');
  await page.getByRole('button', { name: 'Salvar alterações', exact: true }).first().click();
  expect((await upload).status()).toBe(200);
  await expect(avatar).toHaveAttribute('src', /\/api\/governance\/users\/.+\/avatar\?v=/);
  const saved = await avatar.getAttribute('src');
  await expect.poll(() => avatar.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  expect(await page.locator('header img.clicko-profile-avatar').getAttribute('src')).toBe(saved);
  await page.reload();
  await expect(avatar).toHaveAttribute('src', saved!);
  await expect.poll(() => avatar.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  await page.screenshot({ path: testInfo.outputPath('profile-saved.png'), fullPage: false });
  await page.locator('header').getByRole('button').filter({ hasText: 'Avatar Validation' }).click();
  await page.getByRole('button', { name: 'Sair da Clicko', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByPlaceholder('voce@empresa.com').fill(credentials.email);
  await page.getByPlaceholder('Sua senha', { exact: true }).fill(credentials.password);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto('/settings');
  await expect(avatar).toHaveAttribute('src', saved!);

  // A browser with no localStorage still gets the server-saved photo.
  const fresh = await browser.newContext();
  try {
    const login = await fresh.request.post('http://127.0.0.1:3109/api/governance/auth/login', { data: credentials });
    expect(login.status()).toBe(200);
    const reopened = await fresh.newPage();
    await reopened.goto('http://127.0.0.1:3109/settings');
    await expect(reopened.locator('.clicko-profile-photo img')).toHaveAttribute('src', saved!);
    await expect.poll(() => reopened.locator('.clicko-profile-photo img').evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  } finally { await fresh.close(); }

  await input.setInputFiles({ name: 'invalid.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') });
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(avatar).toHaveAttribute('src', saved!);
  await input.setInputFiles({ name: 'large.png', mimeType: 'image/png', buffer: Buffer.alloc(5 * 1024 * 1024 + 1) });
  await expect(page.getByRole('alert')).toContainText('5 MB');
  await expect(avatar).toHaveAttribute('src', saved!);
  expect(errors).toEqual([]);
});
