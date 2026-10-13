export type ThemeMode = 'dark' | 'light';
type BrandAssets = { expanded: string; compact: string };

declare global {
  interface Window {
    clickoTheme: {
      assets: Record<ThemeMode, BrandAssets>;
      authenticationAssets: BrandAssets;
      settingsKey: string;
      initialTheme: ThemeMode;
      storedTheme: (accountId?: string | null) => ThemeMode;
      isAuthPath: (path: string) => boolean;
      apply: (theme: ThemeMode, authentication?: boolean) => void;
    };
  }
}

// The blocking head script initializes this before the React entry module.
export const appearance = window.clickoTheme;
