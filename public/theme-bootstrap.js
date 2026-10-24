/* Runs before the application/CSS loads. This metadata controls appearance only,
   never identity or permissions. Keep asset/theme resolution in this one place. */
(function () {
  const settingsKey = 'clicko-studio:user-settings';
  const accountKey = 'clicko-studio:active-account-id';
  const assets = {
    dark: { expanded: '/branding/logo_escuro.png', compact: '/branding/simbolo_escuro.png' },
    light: { expanded: '/branding/logo_claro.png', compact: '/branding/simbolo_claro.png' },
  };
  const authenticationAssets = {
    expanded: '/clicko-ai-studios-logo-stacked.png', compact: '/clicko-ai-studios-logo-compact.png',
  };
  const isAuthPath = path => ['/login', '/signup', '/forgot-password', '/reset-password', '/verify-email'].includes(path.replace(/\/+$/, '') || '/');
  const storedTheme = accountId => {
    try {
      const id = accountId === undefined ? localStorage.getItem(accountKey) : accountId;
      if (!id) return 'dark';
      const settings = JSON.parse(localStorage.getItem(`${settingsKey}:${id}`) || '{}');
      return settings?.appearance?.theme === 'light' ? 'light' : 'dark';
    } catch { return 'dark'; }
  };
  const apply = (theme, authentication = false) => {
    const effective = authentication ? 'dark' : theme;
    const canvas = effective === 'light' ? '#f5f5f3' : '#000000';
    const root = document.documentElement;
    root.dataset.theme = effective;
    root.style.colorScheme = effective;
    root.style.backgroundColor = canvas;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', canvas);
  };
  const authentication = isAuthPath(location.pathname);
  const initialTheme = authentication ? 'dark' : storedTheme();
  window.clickoTheme = { assets, authenticationAssets, settingsKey, storedTheme, initialTheme, isAuthPath, apply };
  apply(initialTheme, authentication);
  const preload = src => {
    const link = document.createElement('link');
    link.rel = 'preload'; link.as = 'image'; link.href = src;
    document.head.appendChild(link);
  };
  // Prioritize the correct brand before React mounts; warm the other theme too.
  const selected = authentication ? authenticationAssets : assets[initialTheme];
  [...new Set([selected.expanded, selected.compact, ...Object.values(assets).flatMap(pair => Object.values(pair))])].forEach(preload);
})();
