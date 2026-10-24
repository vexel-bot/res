import { expect, test } from '@playwright/test';

test.use({ channel: 'chrome' });

test('Dashboard ambient background follows both themes without changing the hero layout', async ({ page }, testInfo) => {
  for (const theme of ['dark', 'light'] as const) {
    await page.setViewportSize({ width: 1365, height: 900 });
    await page.goto('http://127.0.0.1:3000/settings');
    await page.getByRole('radiogroup', { name: 'Tema da interface' }).getByRole('radio', { name: theme === 'dark' ? 'Escuro' : 'Claro' }).click();
    await page.goto('http://127.0.0.1:3000/dashboard');
    const hero = page.locator('.cd-hero');
    await expect(hero).toBeVisible();
    await expect(hero.getByRole('heading', { name: /O que vamos criar hoje/ })).toBeVisible();
    await expect(page.locator('.clicko-session-loading')).toBeHidden();
    await expect(page.locator('.clicko-splash')).toBeHidden();
    const before = await hero.evaluate(element => getComputedStyle(element, '::before').backgroundImage);
    expect(before).toContain('radial-gradient');
    expect(before).toContain('255, 127, 80');
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    await hero.screenshot({ path: testInfo.outputPath(`hero-${theme}.png`) });
  }

  await page.setViewportSize({ width: 390, height: 780 });
  await page.goto('http://127.0.0.1:3000/dashboard');
  await expect(page.locator('.cd-hero')).toBeVisible();
  await expect(page.locator('.clicko-session-loading')).toBeHidden();
  await expect(page.locator('.clicko-splash')).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  await page.locator('.cd-hero').screenshot({ path: testInfo.outputPath('hero-mobile.png') });

  await page.emulateMedia({ reducedMotion: 'reduce' });
  expect(await page.locator('.cd-hero').evaluate(element => getComputedStyle(element, '::before').animationName)).toBe('none');
});
