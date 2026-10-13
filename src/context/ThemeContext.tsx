import React from 'react';
import { useAuth } from './AuthContext';
import { visualTransition } from '../motion/visualTransition';
import { appearance, type ThemeMode } from '../theme/appearance';

export type { ThemeMode } from '../theme/appearance';

const SETTINGS_KEY = appearance.settingsKey;

type ThemeContextValue = {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
};

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const auth = useAuth();
  const accountId = auth.account?.id;
  const [selection, setSelection] = React.useState<{ accountId?: string; theme: ThemeMode }>(() => ({ theme: appearance.initialTheme }));
  // A changed account is resolved during render, not one effect/frame later.
  const theme = auth.loading ? selection.theme : !auth.authenticated ? 'dark'
    : selection.accountId === accountId ? selection.theme : appearance.storedTheme(accountId);

  React.useLayoutEffect(() => {
    if (auth.loading) return;
    setSelection(previous => previous.accountId === accountId && previous.theme === theme ? previous : { accountId, theme });
  }, [accountId, auth.loading, theme]);

  React.useLayoutEffect(() => {
    // Pending internal sessions retain the pre-paint preference; actual login
    // and recovery screens continue to use the unchanged authentication brand.
    appearance.apply(theme, auth.loading ? appearance.isAuthPath(location.pathname) : !auth.authenticated);
  }, [auth.loading, auth.authenticated, theme]);

  React.useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === `${SETTINGS_KEY}:${accountId}`) visualTransition('theme', () => setSelection({ accountId, theme: appearance.storedTheme(accountId) }));
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, [accountId]);

  const setTheme = React.useCallback((next: ThemeMode) => {
    if (!auth.authenticated || !accountId) return;
    visualTransition('theme', () => {
      // Keep the document chrome, browser theme-color and React shell in the
      // same transaction so no intermediate frame mixes both palettes.
      appearance.apply(next, false);
      setSelection({ accountId, theme: next });
    });
    try {
      const key = `${SETTINGS_KEY}:${accountId}`;
      const settings = JSON.parse(localStorage.getItem(key) || '{}') as Record<string, unknown> & { appearance?: Record<string, unknown> };
      localStorage.setItem(key, JSON.stringify({ ...settings, appearance: { ...settings.appearance, theme: next } }));
    } catch {
      // Theme remains active for this session when storage is unavailable.
    }
  }, [accountId, auth.authenticated]);

  const value = React.useMemo(() => ({ theme, setTheme }), [theme, setTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export function useTheme() {
  const context = React.useContext(ThemeContext);
  if (!context) throw new Error('useTheme precisa estar dentro de ThemeProvider.');
  return context;
}
