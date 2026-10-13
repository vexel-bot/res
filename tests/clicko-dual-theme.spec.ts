import { expect, test } from '@playwright/test';

test.use({ channel: 'chrome' });

const routes = [
  'dashboard', 'klic', 'connected-accounts', 'calendar', 'library',
  'clients', 'approvals', 'analytics', 'automations', 'team',
  'settings', 'subscription', 'create',
];

for (const theme of ['dark', 'light'] as const) {
  test(`${theme} palette remains coherent across the workspace`, async ({ page }) => {
    test.setTimeout(180_000);
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setViewportSize({ width: 1365, height: 900 });
    await page.goto('http://127.0.0.1:3000/settings');
    await page.getByRole('radiogroup', { name: 'Tema da interface' }).getByRole('radio', { name: theme === 'dark' ? 'Escuro' : 'Claro' }).click();
    await expect(page.locator('.clicko-app-shell')).toHaveAttribute('data-theme', theme);

    for (const route of routes) {
      await page.goto(`http://127.0.0.1:3000/${route}`);
      const shell = page.locator('.clicko-app-shell');
      await expect(shell).toHaveAttribute('data-theme', theme);
      await expect(shell).toHaveClass(/clicko-creative-workspace/);
      await expect(page.locator('.clicko-splash')).toBeHidden();
      const surface = await shell.evaluate(element => ({
        blue: getComputedStyle(element).getPropertyValue('--cw-clicko-blue').trim(),
        canvas: getComputedStyle(element).getPropertyValue('--cw-canvas').trim(),
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      }));
      expect(surface.blue).toBe('#6eb8f5');
      expect(surface.canvas).toBe(theme === 'dark' ? '#080809' : '#f5f5f6');
      expect(surface.overflow, `${theme}/${route} has horizontal overflow`).toBeLessThanOrEqual(1);
      const sidebarColors = await page.locator('.clicko-sidebar').evaluate(element => ({
        sidebar: getComputedStyle(element).backgroundColor,
        brand: getComputedStyle(element.querySelector('.clicko-sidebar-brand')!).backgroundColor,
        logo: getComputedStyle(element.querySelector('.clicko-sidebar-brand .clicko-logo')!).backgroundColor,
      }));
      const expectedSidebar = theme === 'dark' ? 'rgb(0, 0, 0)' : 'rgb(255, 255, 255)';
      expect(sidebarColors, `${theme}/${route} sidebar and logo must be seamless`).toEqual({
        sidebar: expectedSidebar,
        brand: expectedSidebar,
        logo: expectedSidebar,
      });
      if (theme === 'light' && route === 'subscription') {
        await expect(page.locator('.cb-scene-panel').first()).toHaveCSS('background-image', /rgb\(255, 255, 255\)/);
      }
      if (process.env.CLICKO_CAPTURE_THEMES === '1') {
        await page.screenshot({ path: `test-results/theme-audit/${theme}-${route}.png` });
      }
    }

    await page.reload();
    await expect(page.locator('.clicko-app-shell')).toHaveAttribute('data-theme', theme);
    expect(errors).toEqual([]);
  });
}

test('Clicko controls use coral, KLIC keeps blue, and media routes stay isolated', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/dashboard');
  const selected = page.locator('.clicko-nav-item[aria-current="page"]');
  await expect(selected).toHaveCount(1);
  await expect(selected.locator('svg')).toHaveCSS('color', 'rgb(255, 148, 112)');
  await expect(selected).toHaveCSS('background-color', /^rgba\(255, 127, 80, 0\.10[56]\)$/);
  await page.goto('http://127.0.0.1:3000/settings');
  const activeSettingsTab = page.getByRole('navigation', { name: 'Navegação das Configurações' }).getByRole('button', { name: 'Minha Conta' });
  await expect(activeSettingsTab).toHaveAttribute('aria-current', 'page');
  await expect(activeSettingsTab).toHaveCSS('color', 'rgb(255, 148, 112)');
  await page.goto('http://127.0.0.1:3000/klic');
  await expect(page.locator('.clicko-nav-item[aria-label="Klic AI"] > [aria-hidden="true"]')).toHaveCSS('color', 'rgb(141, 202, 255)');
  await expect(page.getByRole('button', { name: 'Enviar mensagem' })).toHaveCSS('background-color', 'rgb(110, 184, 245)');
  await expect(page.getByRole('group', { name: 'Modo da KLIC' }).getByRole('button', { name: 'Criar' })).toHaveCSS('border-color', 'rgba(110, 184, 245, 0.25)');
  for (const route of ['image', 'video']) {
    await page.goto(`http://127.0.0.1:3000/${route}`);
    await expect(page.locator('.clicko-app-shell')).not.toHaveClass(/clicko-creative-workspace/);
  }
});

test('compact workspace routes remain within the viewport in both themes', async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 390, height: 844 });
  for (const theme of ['dark', 'light'] as const) {
    await page.goto('http://127.0.0.1:3000/settings');
    await page.getByRole('radiogroup', { name: 'Tema da interface' }).getByRole('radio', { name: theme === 'dark' ? 'Escuro' : 'Claro' }).click();
    for (const route of routes) {
      await page.goto(`http://127.0.0.1:3000/${route}`);
      await expect(page.locator('.clicko-splash')).toBeHidden();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${theme}/${route} overflows compact viewport`).toBeLessThanOrEqual(1);
    }
  }
});

test('connection picker keeps a readable panel and backdrop in both themes', async ({ page }) => {
  await page.setViewportSize({ width: 1365, height: 900 });
  for (const theme of ['dark', 'light'] as const) {
    await page.goto('http://127.0.0.1:3000/settings');
    await page.getByRole('radiogroup', { name: 'Tema da interface' }).getByRole('radio', { name: theme === 'dark' ? 'Escuro' : 'Claro' }).click();
    await page.goto('http://127.0.0.1:3000/connected-accounts');
    await expect(page.locator('.clicko-splash')).toBeHidden();
    await page.getByRole('button', { name: 'Conectar conta' }).first().click();
    const dialog = page.getByRole('dialog', { name: 'Conectar uma conta' });
    await expect(dialog).toBeVisible();
    await page.waitForTimeout(250);
    if (process.env.CLICKO_CAPTURE_THEMES === '1') {
      await page.screenshot({ path: `test-results/theme-audit/${theme}-connection-picker.png` });
    }
    const colors = await dialog.evaluate(element => ({
      backdrop: getComputedStyle(element).backgroundColor,
      panel: getComputedStyle(element.querySelector('section')!).backgroundColor,
      bounds: element.getBoundingClientRect().toJSON(),
    }));
    expect(colors.backdrop).not.toBe('rgb(255, 255, 255)');
    expect(colors.panel).not.toBe(theme === 'dark' ? 'rgb(255, 255, 255)' : 'rgb(17, 17, 17)');
    expect(colors.bounds.x).toBeLessThanOrEqual(1);
    expect(colors.bounds.y).toBeLessThanOrEqual(1);
    expect(colors.bounds.width).toBeGreaterThanOrEqual(1364);
    expect(colors.bounds.height).toBeGreaterThanOrEqual(899);
  }
});

test('KLIC mini chat keeps its blue controls in both themes', async ({ page }) => {
  for (const theme of ['dark', 'light'] as const) {
    await page.goto('http://127.0.0.1:3000/settings');
    await page.getByRole('radiogroup', { name: 'Tema da interface' }).getByRole('radio', { name: theme === 'dark' ? 'Escuro' : 'Claro' }).click();
    await page.getByRole('button', { name: 'Abrir Klic AI' }).click();
    await expect(page.locator('.klic-floating-panel')).toBeVisible();
    await expect(page.locator('.klic-floating-panel')).toHaveCSS('opacity', '1');
    await expect(page.locator('.klic-floating-composer .klic-mini-send')).toHaveCSS('background-color', 'rgb(110, 184, 245)');
    await page.locator('.klic-floating-actions button[aria-pressed]').click();
    await expect(page.locator('.klic-floating-actions button[aria-pressed="true"]')).toHaveCSS('background-color', theme === 'dark' ? 'rgba(110, 184, 245, 0.106)' : 'rgba(74, 150, 209, 0.106)');
    await expect(page.locator('.klic-floating-panel')).toHaveCSS('background-color', theme === 'dark' ? 'rgb(9, 9, 9)' : 'rgb(255, 255, 255)');
    if (process.env.CLICKO_CAPTURE_THEMES === '1') {
      await page.screenshot({ path: `test-results/theme-audit/${theme}-mini-chat.png` });
    }
  }
});

test('team capacity indicator keeps its solid coral fill in both themes', async ({ page }) => {
  for (const theme of ['dark', 'light'] as const) {
    await page.goto('http://127.0.0.1:3000/settings');
    await page.getByRole('radiogroup', { name: 'Tema da interface' }).getByRole('radio', { name: theme === 'dark' ? 'Escuro' : 'Claro' }).click();
    await page.goto('http://127.0.0.1:3000/team');
    await expect(page.locator('.clicko-main-stage .h-full.rounded-full[class~="bg-[#FF7F50]"]')).toHaveCSS('background-color', 'rgb(255, 127, 80)');
  }
});

test('Dashboard Radar remains readable when expanded in both themes', async ({ page }) => {
  for (const theme of ['dark', 'light'] as const) {
    await page.goto('http://127.0.0.1:3000/settings');
    await page.getByRole('radiogroup', { name: 'Tema da interface' }).getByRole('radio', { name: theme === 'dark' ? 'Escuro' : 'Claro' }).click();
    await page.goto('http://127.0.0.1:3000/dashboard');
    await expect(page.locator('.clicko-splash')).toBeHidden();
    await page.getByRole('button', { name: /Ampliar Radar/ }).click();
    const dialog = page.getByRole('dialog', { name: 'Assuntos em alta' });
    await expect(dialog).toBeVisible();
    await expect(dialog.locator('.clicko-klic-radar')).toBeVisible();
    await expect(page.locator('body')).toHaveCSS('overflow', 'hidden');
    if (process.env.CLICKO_CAPTURE_THEMES === '1') {
      await page.screenshot({ path: `test-results/theme-audit/${theme}-radar.png` });
    }
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
  }
});
