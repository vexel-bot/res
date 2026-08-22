import { mkdir, rm, writeFile } from 'node:fs/promises';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { stitch } from '@google/stitch-sdk';
import { STITCH_SCREENS, type StitchProject } from '../src/product/screenManifest.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUTPUT_ROOT = join(ROOT, 'public', 'stitch');
const BRIDGE_SCRIPT = String.raw`(() => {
  const normalize = (value) => value.replace(/\s+/g, ' ').trim().toLocaleLowerCase('pt-BR');
  const exactRoutes = new Map([
    ['hoje', '/today'],
    ['descobrir', '/discover'],
    ['planejar', '/campaigns/active'],
    ['criar', '/content/new'],
    ['aprovar', '/approvals/post-1'],
    ['publicar', '/publish/active'],
    ['aprender', '/analytics/learning'],
    ['radar', '/radar'],
    ['calendário', '/calendar'],
    ['templates', '/templates'],
    ['automações', '/automations/active'],
    ['configurações', '/settings/ai-governance'],
    ['biblioteca', '/library/assets'],
  ]);
  const containsRoutes = [
    ['transformar em campanha', '/campaigns/new?source=radar'],
    ['nova campanha', '/campaigns/new'],
    ['criar campanha', '/campaigns/new'],
    ['campaign room', '/campaigns/active'],
    ['approval room', '/approvals/post-1'],
    ['content command', '/content/dashboard'],
    ['novo conteúdo', '/content/new'],
    ['novo post', '/content/new?type=post'],
    ['brand memory', '/brand-memory'],
    ['memória da marca', '/brand-memory'],
    ['ver calendário', '/calendar'],
    ['ver aprovações', '/approvals/post-1'],
    ['ver todas', '/content/dashboard'],
    ['descobrir', '/discover'],
    ['planejar', '/campaigns/active'],
    ['criar', '/content/new'],
    ['aprovar', '/approvals/post-1'],
    ['publicar', '/publish/active'],
    ['aprender', '/analytics/learning'],
    ['+ novo', '/content/new'],
  ];

  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target.closest('a,button,[role="button"]') : null;
    if (!target) return;
    const label = normalize(target.getAttribute('aria-label') || target.textContent || '');
    const route = exactRoutes.get(label) || containsRoutes.find(([text]) => label.includes(text))?.[1];
    if (!route) return;
    event.preventDefault();
    window.parent.postMessage({ type: 'clicko:stitch-navigate', route }, window.location.origin);
  }, true);
})();`;

const PROJECT_IDS: Record<StitchProject, string> = {
  approved: '17470294547707956073',
  'creative-lab': '15926565735319496264',
};

type RemoteScreen = {
  screenId: string;
  data?: {
    deviceType?: string;
    height?: string;
    title?: string;
    width?: string;
  };
  getHtml(): Promise<string>;
  getImage(): Promise<string>;
};

type ArtifactEntry = {
  id: string;
  project: StitchProject;
  projectId: string;
  screenId: string;
  title: string;
  route: string;
  state?: string;
  width: number;
  height: number;
  htmlPath: string;
  screenshotPath: string;
};

function normalizeTitle(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/^clicko\s*[—–-]\s*/i, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

async function download(url: string) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Download failed (${response.status}) for ${new URL(url).hostname}`);
  }
  return Buffer.from(await response.arrayBuffer());
}

async function main() {
  if (process.argv.includes('--bridge-only')) {
    await mkdir(OUTPUT_ROOT, { recursive: true });
    await writeFile(join(OUTPUT_ROOT, 'bridge.js'), `${BRIDGE_SCRIPT}\n`);
    console.log('Updated Stitch navigation bridge.');
    return;
  }

  if (!process.env.STITCH_API_KEY) {
    throw new Error('STITCH_API_KEY must be supplied through the process environment.');
  }

  await rm(OUTPUT_ROOT, { recursive: true, force: true });
  await mkdir(OUTPUT_ROOT, { recursive: true });

  const artifacts: ArtifactEntry[] = [];

  for (const project of Object.keys(PROJECT_IDS) as StitchProject[]) {
    const projectId = PROJECT_IDS[project];
    const remoteScreens = await stitch.project(projectId).screens() as RemoteScreen[];
    const validScreens = remoteScreens.filter((screen) => screen.data?.deviceType === 'DESKTOP');
    const expected = STITCH_SCREENS.filter((screen) => screen.project === project);

    if (validScreens.length !== expected.length) {
      throw new Error(`${project}: expected ${expected.length} valid screens, received ${validScreens.length}.`);
    }

    for (const expectedScreen of expected) {
      const normalizedFrame = normalizeTitle(expectedScreen.frame);
      const matches = validScreens.filter((screen) => normalizeTitle(screen.data?.title ?? '') === normalizedFrame);
      if (matches.length !== 1) {
        throw new Error(`${project}/${expectedScreen.id}: expected one match for "${expectedScreen.frame}", received ${matches.length}.`);
      }

      const remote = matches[0];
      const title = remote.data?.title ?? expectedScreen.frame;
      const artifactDir = join(OUTPUT_ROOT, project, remote.screenId);
      const htmlFile = join(artifactDir, 'index.html');
      const screenshotFile = join(artifactDir, 'screenshot.png');
      await mkdir(artifactDir, { recursive: true });

      const [htmlUrl, imageUrl] = await Promise.all([remote.getHtml(), remote.getImage()]);
      const [html, screenshot] = await Promise.all([download(htmlUrl), download(imageUrl)]);
      const htmlSource = html.toString('utf8');
      const integratedHtml = htmlSource.includes('</body>')
        ? htmlSource.replace('</body>', '<script src="/stitch/bridge.js"></script></body>')
        : `${htmlSource}<script src="/stitch/bridge.js"></script>`;
      await Promise.all([writeFile(htmlFile, integratedHtml), writeFile(screenshotFile, screenshot)]);

      artifacts.push({
        id: expectedScreen.id,
        project,
        projectId,
        screenId: remote.screenId,
        title,
        route: expectedScreen.route,
        state: expectedScreen.state,
        width: Number(remote.data?.width ?? 2560),
        height: Number(remote.data?.height ?? 2048),
        htmlPath: `/${relative(join(ROOT, 'public'), htmlFile).replaceAll('\\', '/')}`,
        screenshotPath: `/${relative(join(ROOT, 'public'), screenshotFile).replaceAll('\\', '/')}`,
      });

      console.log(`${expectedScreen.id}  ${title}`);
    }
  }

  artifacts.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
  await writeFile(
    join(OUTPUT_ROOT, 'manifest.json'),
    `${JSON.stringify({ generatedAt: new Date().toISOString(), projects: PROJECT_IDS, screens: artifacts }, null, 2)}\n`,
  );
  await writeFile(join(OUTPUT_ROOT, 'bridge.js'), `${BRIDGE_SCRIPT}\n`);
  const generatedModule = `/* This file is generated by scripts/import-stitch.ts. */\n`
    + `export const STITCH_ARTIFACTS = ${JSON.stringify(artifacts, null, 2)} as const;\n\n`
    + `export type StitchArtifact = (typeof STITCH_ARTIFACTS)[number];\n`;
  await writeFile(join(ROOT, 'src', 'product', 'stitchArtifacts.generated.ts'), generatedModule);
  console.log(`Imported ${artifacts.length} Stitch screens into ${relative(ROOT, OUTPUT_ROOT)}.`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
