import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { readFileSync } from 'node:fs';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [
      {
        name: 'clicko-theme-before-paint',
        transformIndexHtml: {
          order: 'pre',
          handler: html => html.replace('<script src="/theme-bootstrap.js"></script>', () => {
            const source = readFileSync(path.resolve(__dirname, 'public/theme-bootstrap.js'), 'utf8');
            // Inline the shared source so first-paint branding never waits on a
            // separate network request, in either development or production.
            return `<script data-clicko-theme-bootstrap>${source.replace(/<\/script/gi, '<\\/script')}</script>`;
          }),
        },
      },
      react(), tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      fs: {
        // Never serve local governance records, backups, or pending writes.
        deny: ['.env', '.env.*', '*.{crt,pem,key}', '**/.git/**', '**/.secrets/**', '**/.clicko-data/**', '**/.codex-runtime/**', '**/.venv/**', '**/backend/**', '**/*.sqlite*', '**/*.db',
          '**/*service-account*.json', '**/*service_account*.json', '**/*oauth-credentials*.json', '**/*oauth_credentials*.json', '**/google-credentials*.json',
          ...(process.env.CLICKO_GOVERNANCE_DATA_FILE
            ? [`${path.resolve(process.env.CLICKO_GOVERNANCE_DATA_FILE).replace(/\\/g, '/')}*`]
            : []),
        ],
      },
      // Allow resource-constrained environments to disable HMR and file watching.
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {
        // Runtime persistence is not source code. Its atomic writes must never reload an active chat.
        ignored: ['**/.secrets/**', '**/.clicko-data/**', '**/.codex-runtime/**', '**/.venv/**', '**/third_party/**', '**/workers/**', '**/backend/**', ...(process.env.CLICKO_GOVERNANCE_DATA_FILE
          ? [`${path.resolve(process.env.CLICKO_GOVERNANCE_DATA_FILE).replace(/\\/g, '/')}*`]
          : [])],
      },
    },
  };
});
