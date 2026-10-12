import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {realpathSync} from 'node:fs';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    cacheDir: '.codex-runtime/vite',
    plugins: [react({exclude: [/node_modules/, /\.codex-runtime/, /third_party/, /docs\/studios\/archive/]}), tailwindcss()],
    optimizeDeps: { entries: ['index.html'] },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      fs: {allow: [__dirname, realpathSync(path.resolve(__dirname, 'node_modules'))]},
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Middleware mode still creates Vite's websocket server unless `ws` is
      // explicitly disabled. Keep isolated E2E runs away from user HMR.
      ws: process.env.CLICKO_E2E === 'true' ? (false as const) : undefined,
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {
        ignored: ['**/third_party/**', '**/workers/**', '**/backend/**', '**/.codex-runtime/**', '**/data/**', '**/scripts/**', '**/.github/**', '**/docs/studios/archive/**'],
      },
    },
  };
});
