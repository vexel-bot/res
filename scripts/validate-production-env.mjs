import 'dotenv/config';
import { spawnSync } from 'node:child_process';

const result = spawnSync(process.execPath, ['--import', 'tsx', '-e', "import('./server/production.ts').then(({validateProductionEnvironment})=>{validateProductionEnvironment();console.log('PRODUCTION_ENVIRONMENT_VALID')})"], {
  cwd: new URL('..', import.meta.url),
  stdio: 'inherit',
  env: { ...process.env, NODE_ENV: 'production' },
});
process.exitCode = result.status ?? 1;
