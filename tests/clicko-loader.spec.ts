import { expect, test } from '@playwright/test';
import sharp from 'sharp';

test.use({ channel: 'chrome' });

test('session loading uses only the official Clicko symbol across themes and reduced motion', async ({ page }, testInfo) => {
  let releaseSession: (() => void) | undefined;
  await page.route('**/api/governance/auth/session', async route => {
    await new Promise<void>(resolve => {
      releaseSession = () => { void route.continue().finally(resolve); };
    });
  });

  try {
    await page.goto('http://127.0.0.1:3000/dashboard');
    const loader = page.locator('.clicko-session-loading .clicko-loader');
    await expect(loader).toBeVisible();
    await expect(loader).toHaveAttribute('role', 'status');
    await expect(page.locator('.clicko-session-loading .clicko-logo')).toHaveCount(0);
    await expect(loader.locator('.clicko-loader__symbol')).toHaveCSS('mask-image', /simbolo_escuro\.png/);
    await expect(loader.locator('.clicko-loader__symbol')).toHaveCSS('animation-duration', '1.2s');
    await page.screenshot({ path: testInfo.outputPath('loader-dark.png') });

    // The authenticated shell applies legacy toast backgrounds to role=status.
    // Exercise that CSS context too: session loading alone did not reveal it.
    await loader.evaluate(element => {
      const shell = document.createElement('div');
      shell.className = 'clicko-app-shell clicko-loader-regression-shell';
      shell.dataset.theme = 'dark';
      const splash = document.createElement('div');
      splash.className = 'clicko-splash';
      splash.style.cssText = 'position:fixed;inset:0;display:grid;place-items:center;background:#000;z-index:200';
      splash.append(element.cloneNode(true));
      shell.append(splash);
      document.body.append(shell);
    });
    const shell = page.locator('.clicko-loader-regression-shell');
    const shellLoader = shell.locator('.clicko-loader');
    await expect(shellLoader).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
    await expect(shellLoader).toHaveCSS('border-top-width', '0px');
    await expect(shellLoader).toHaveCSS('box-shadow', 'none');
    expect(await shellLoader.evaluate(element => getComputedStyle(element, '::before').content)).toBe('none');
    expect(await shellLoader.evaluate(element => getComputedStyle(element, '::after').content)).toBe('none');
    const verifyCorners = async (expected: number) => {
      const { data, info } = await sharp(await shellLoader.screenshot({ animations: 'disabled' })).removeAlpha().raw().toBuffer({ resolveWithObject: true });
      for (const [x, y] of [[0, 0], [info.width - 1, 0], [0, info.height - 1], [info.width - 1, info.height - 1]]) {
        const offset = (y * info.width + x) * info.channels;
        expect([...data.subarray(offset, offset + 3)], 'the loader corners must match the page with no opaque box').toEqual([expected, expected, expected]);
      }
    };
    await verifyCorners(0);
    await page.screenshot({ path: testInfo.outputPath('loader-shell-dark.png') });
    await shell.evaluate(element => { element.setAttribute('data-theme', 'light'); });
    await expect(shellLoader).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
    await expect(shellLoader).toHaveCSS('color', 'rgb(17, 17, 17)');
    await verifyCorners(255);
    await page.screenshot({ path: testInfo.outputPath('loader-shell-light.png') });
    await shell.evaluate(element => element.remove());

    await page.locator('.clicko-session-loading').evaluate(element => { element.setAttribute('data-theme', 'light'); });
    await expect(loader).toHaveCSS('color', 'rgb(17, 17, 17)');
    await page.screenshot({ path: testInfo.outputPath('loader-light.png') });

    await page.emulateMedia({ reducedMotion: 'reduce' });
    await expect(loader.locator('.clicko-loader__symbol')).toHaveCSS('animation-name', 'none');
  } finally {
    releaseSession?.();
  }
});
