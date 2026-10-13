import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import path from 'node:path';

const script = readFileSync(path.resolve('public/theme-bootstrap.js'), 'utf8');
const html = readFileSync(path.resolve('index.html'), 'utf8');
const faviconPaths = [...html.matchAll(/<link\b[^>]*rel="icon"[^>]*href="([^"]+)"/g)].map(match => match[1]);
const expectedFavicons = ['/branding/favicon-clicko-32.png', '/branding/favicon-clicko-16.png', '/branding/favicon-clicko.ico'];
function boot(values: Record<string, string>, pathname = '/settings', unavailable = false) {
  const root = { dataset: {} as Record<string, string>, style: {} as Record<string, string> };
  const icons = faviconPaths.map(href => ({ href }));
  const preloads: Array<{ href: string }> = [];
  const sandbox = {
    window: {} as any,
    location: { pathname },
    localStorage: { getItem: (key: string) => { if (unavailable) throw new Error('Storage denied'); return values[key] ?? null; } },
    document: {
      documentElement: root,
      querySelectorAll: () => icons.map(icon => ({ setAttribute: (_: string, value: string) => { icon.href = value; } })),
      querySelector: () => ({ setAttribute: () => {} }),
      createElement: () => ({}),
      head: { appendChild: (link: { href: string }) => preloads.push(link) },
    },
  };
  runInNewContext(script, sandbox);
  return { root, icons, preloads, api: sandbox.window.clickoTheme };
}

for (const theme of ['light', 'dark']) {
  test(`${theme} branding resolves synchronously before React/CSS and survives a new boot`, () => {
    const values = {
      'clicko-studio:active-account-id': 'account-company',
      'clicko-studio:user-settings:account-company': JSON.stringify({ appearance: { theme } }),
    };
    for (const route of ['/settings', '/dashboard', '/library', '/']) {
      const { root, icons, preloads, api } = boot(values, route);
      assert.equal(root.dataset.theme, theme);
      assert.equal(root.style.backgroundColor, theme === 'light' ? '#f5f5f3' : '#000000');
      assert.equal(api.initialTheme, theme);
      assert.equal(preloads[0].href, api.assets[theme].expanded);
      assert.deepEqual(icons.map(icon => icon.href), expectedFavicons);
      assert.equal(new Set(preloads.map(link => link.href)).size, 4);
      api.apply(theme === 'light' ? 'dark' : 'light');
      assert.deepEqual(icons.map(icon => icon.href), expectedFavicons);
      assert.equal(root.dataset.theme, theme === 'light' ? 'dark' : 'light');
      assert.equal(boot(values, route).root.dataset.theme, theme);
    }
  });
}

test('theme lookup stays per-account and treats corrupt/missing storage safely', () => {
  const values = {
    'clicko-studio:active-account-id': 'personal',
    'clicko-studio:user-settings:personal': '{"appearance":{"theme":"light"}}',
    'clicko-studio:user-settings:company': '{"appearance":{"theme":"dark"}}',
    'clicko-studio:user-settings:broken': 'null',
    'clicko-studio:user-settings:invalid': '{',
  };
  const { api } = boot(values);
  assert.equal(api.storedTheme('personal'), 'light');
  for (const id of ['company', 'broken', 'invalid', 'missing', null]) assert.equal(api.storedTheme(id), 'dark');
  assert.equal(boot({}).root.dataset.theme, 'dark');
  assert.equal(boot(values, '/settings', true).root.dataset.theme, 'dark');
});

test('login, signup and recovery retain the original dark authentication brand', () => {
  for (const route of ['/login', '/signup/', '/forgot-password', '/reset-password', '/verify-email']) {
    const { root, icons, api } = boot({
      'clicko-studio:active-account-id': 'personal',
      'clicko-studio:user-settings:personal': '{"appearance":{"theme":"light"}}',
    }, route);
    assert.equal(root.dataset.theme, 'dark');
    assert.deepEqual(icons.map(icon => icon.href), expectedFavicons);
    assert.equal(api.authenticationAssets.expanded, '/clicko-ai-studios-logo-stacked.png');
  }
});
