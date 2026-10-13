import { expect, test } from '@playwright/test';

test.use({ channel: 'chrome' });

test('Dashboard presents operational content in the first desktop viewport and pauses decorative motion', async ({ page }) => {
  await page.setViewportSize({ width: 1365, height: 900 });
  await page.goto('http://127.0.0.1:3000/dashboard');
  await expect(page.locator('.clicko-app-shell')).toHaveClass(/clicko-creative-workspace/);
  await expect(page.getByRole('heading', { name: 'Visão geral' })).toBeInViewport();
  await expect(page.locator('.cd-motion.is-playing')).toHaveCount(0);
  await page.locator('.cd-hero').hover();
  await expect(page.locator('.cd-motion.is-playing')).toHaveCount(1);
  await page.locator('.clicko-sidebar-brand').hover();
  await expect(page.locator('.cd-motion.is-playing')).toHaveCount(0);
});

test('Image and Video retain their original shell and shared navigation styling', async ({ page }) => {
  await page.setViewportSize({ width: 1365, height: 900 });
  await page.goto('http://127.0.0.1:3000/dashboard');
  for (const route of ['image', 'video']) {
    await page.locator('.clicko-sidebar').getByRole('button', { name: route === 'image' ? 'Imagem' : 'Vídeo' }).click();
    await expect(page).toHaveURL(new RegExp(`/${route}$`));
    await expect(page.locator('.clicko-app-shell')).not.toHaveClass(/clicko-creative-workspace/);
    await expect.poll(() => page.evaluate(() => ({
      sidebar: getComputedStyle(document.querySelector('.clicko-sidebar')!).backgroundColor,
      topbar: getComputedStyle(document.querySelector('.clicko-topbar')!).backgroundColor,
      stage: getComputedStyle(document.querySelector('.clicko-main-stage')!).backgroundColor,
    }))).toEqual({ sidebar: 'rgb(5, 5, 5)', topbar: 'rgb(5, 5, 5)', stage: 'rgb(0, 0, 0)' });
  }
});

test('compact layouts do not expose the wide subscription widget or overflow horizontally', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of ['dashboard', 'calendar', 'clients', 'automations', 'settings']) {
    await page.goto(`http://127.0.0.1:3000/${route}`);
    await expect(page.locator('.clicko-plan-widget')).toBeHidden();
    const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width);
  }
});

test('the empty approval queue explains the next step without removing navigation', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/approvals');
  await expect(page.getByRole('heading', { name: 'Nenhuma decisão pendente' })).toBeVisible();
  await page.getByRole('button', { name: 'Ver calendário' }).click();
  await expect(page).toHaveURL(/\/calendar$/);
  await expect(page.getByRole('heading', { name: 'Calendário' })).toBeVisible();
});

test('filtered empty states offer a direct way back to the content', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/library');
  await page.getByPlaceholder('Buscar por nome, descrição ou etiqueta…').fill('sem-resultados-aqui');
  await page.getByRole('button', { name: 'Limpar filtros' }).click();
  await expect(page.getByPlaceholder('Buscar por nome, descrição ou etiqueta…')).toHaveValue('');

  await page.goto('http://127.0.0.1:3000/team');
  await page.getByPlaceholder('Buscar por nome ou e-mail').fill('sem-resultados-aqui');
  await page.getByRole('button', { name: 'Limpar filtros' }).click();
  await expect(page.getByPlaceholder('Buscar por nome ou e-mail')).toHaveValue('');
});
