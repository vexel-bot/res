/** One Claude Code session outside the repository, without the Clicko runtime. */
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const dotenv = require('dotenv');

const directory = path.resolve(process.argv[2] || '');
if (!process.argv[2] || directory === process.cwd()) throw Error('Provide a separate experiment directory.');
fs.mkdirSync(directory, { recursive: true });
const logPath = path.join(directory, 'claude-session.jsonl');
if (fs.existsSync(logPath)) {
  const receipt = JSON.parse(fs.readFileSync(path.join(directory, 'recibo.json')));
  const preflightFailure = /anthropic-workspace-id|does not support this model/.test(receipt.result || '');
  if (receipt.reportedCostUsd !== 0 || !preflightFailure) {
    throw Error('An attempt already exists. Preserve its evidence.');
  }
  const archive = path.join(directory, 'preflight-' + Date.now());
  fs.mkdirSync(archive);
  for (const name of ['claude-session.jsonl', 'claude-stderr.log', 'recibo.json']) {
    fs.renameSync(path.join(directory, name), path.join(archive, name));
  }
}
const config = dotenv.parse(fs.readFileSync('.env'));
if (!config.API_CLAUDE) throw Error('The existing Anthropic key is missing.');

const prompt = `Produza um anúncio motion graphics original para ÓRBITA, mostra fictícia de curtas de ficção científica, destinado ao celular em 9:16.

Copy aprovada: “O futuro cabe num curta.” “ÓRBITA, mostra de curtas de ficção científica.” “Confira a programação.”

Você escolhe toda a direção de arte, duração, cenas, cortes, ritmo, animação, tipografia, luz, efeitos e som. Pode produzir e revisar a peça com as ferramentas e bibliotecas que escolher. Os dados da mostra disponíveis são somente a copy acima.

Entregue nesta pasta um MP4 com áudio e os arquivos-fonte que permitam editar e reproduzir sua criação. Faça você mesmo a produção e a exportação.

Ambiente disponível: Windows, Git Bash, Python com Pillow e NumPy, Node.js, ffmpeg e ffprobe no PATH. As bibliotecas Playwright e sharp estão disponíveis por require através de NODE_PATH. Chromium está instalado. Trabalhe nesta pasta e use a internet para obter materiais caso sua direção necessite.`;
fs.writeFileSync(path.join(directory, 'briefing.txt'), prompt);
fs.writeFileSync(path.join(directory, 'empty-mcp.json'), JSON.stringify({ mcpServers: {} }));
const environment = {};
for (const name of ['PATH', 'SystemRoot', 'WINDIR', 'COMSPEC', 'USERPROFILE', 'APPDATA',
  'LOCALAPPDATA', 'TEMP', 'TMP', 'PATHEXT', 'PROGRAMFILES', 'PROGRAMFILES(X86)']) {
  const key = Object.keys(process.env).find(key => key.toUpperCase() === name.toUpperCase());
  if (key) environment[key] = process.env[key];
}
Object.assign(environment, {
  ANTHROPIC_API_KEY: config.API_CLAUDE,
  ANTHROPIC_CUSTOM_HEADERS: 'anthropic-workspace-id: ' + config.ANTHROPIC_WORKSPACE_ID,
  CLAUDE_CODE_GIT_BASH_PATH: 'C:/Program Files/Git/bin/bash.exe',
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: '1',
  NODE_PATH: path.resolve('node_modules'),
  PYTHONIOENCODING: 'utf-8',
});
const binary = path.join(process.env.USERPROFILE, '.local/bin/claude.exe');
const args = ['-p', '--bare', '--safe-mode', '--model', 'claude-opus-5-5',
  '--effort', 'high', '--output-format', 'stream-json', '--verbose', '--no-session-persistence',
  '--max-budget-usd', '3', '--strict-mcp-config', '--mcp-config', path.join(directory, 'empty-mcp.json'),
  '--setting-sources', '', '--permission-mode', 'acceptEdits',
  '--tools', 'Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch',
  '--allowedTools', 'Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch'];
const stdout = fs.openSync(logPath, 'wx');
const stderr = fs.openSync(path.join(directory, 'claude-stderr.log'), 'wx');
const started = Date.now();
const child = spawn(binary, args, { cwd: directory, env: environment, stdio: ['pipe', stdout, stderr], windowsHide: true });
child.stdin.end(prompt);
child.on('error', error => console.error(error.message));
child.on('close', code => {
  fs.closeSync(stdout);
  fs.closeSync(stderr);
  const result = { model: 'claude-opus-5-5', code, ceilingUsd: 3,
    budgetEnforcement: 'Claude Code checks max-budget-usd between requests; a final request may exceed it.',
    elapsedSeconds: (Date.now() - started) / 1000 };
  for (const line of fs.readFileSync(logPath, 'utf8').split('\n')) {
    try {
      const event = JSON.parse(line);
      if (event.type === 'result') Object.assign(result, {
        subtype: event.subtype, reportedCostUsd: event.total_cost_usd,
        usage: event.usage, modelUsage: event.modelUsage, turns: event.num_turns, result: event.result,
      });
    } catch {}
  }
  fs.writeFileSync(path.join(directory, 'recibo.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  process.exitCode = code || 0;
});
console.log(JSON.stringify({ directory, childPid: child.pid, ceilingUsd: 3 }));
