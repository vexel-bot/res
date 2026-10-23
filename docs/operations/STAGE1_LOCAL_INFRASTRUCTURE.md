# Etapa 1 · infraestrutura local audiovisual

Data da verificação original: 21/10/2026. Atualização de perfil: 23/10/2026.
Esta configuração não é um deploy de produção.

## Perfil gratuito, persistente e isolado

Na raiz do checkout, com Node/npm, `.venv` e as dependências já instaladas:

```powershell
npm run dev:local
```

Em outro terminal:

```powershell
npm run dev:status
npm run dev:stop
```

O supervisor usa `3018` para Express e `8018` para FastAPI, ambos loopback. Dados
do perfil DEV atual: `.codex-runtime/clicko-dev`. O QA histórico
`.codex-runtime/stage1-local` foi preservado. Não reutiliza clientes em `.clicko-data`.
`PORT`, `CLICKO_LOCAL_STUDIO_PORT` e `CLICKO_LOCAL_DATA_DIR` permitem outro perfil.
Use o mesmo diretório ao consultar ou encerrar esse perfil. Não apague a pasta se
precisar dos projetos e arquivos de QA. Uma porta ocupada não é liberada à força.

O encerramento usa IPC para Express e stdin para o Python que ele próprio criou.
Após o limite de encerramento, somente esse processo Python é terminado. Jobs
interrompidos são marcados no próximo boot; submissões pagas não são repetidas.
A prontidão exige banco, armazenamento, FFmpeg e executor local. `status` distingue
um processo iniciado de um serviço realmente pronto.

Atualização de 23/10/2026: `dev:local` configura explicitamente o novo
`CLICKO_DEV_MODE=true`, emite sessão local temporária e provisiona Cliente DEV
na governança e na ponte. Não utiliza o bypass antigo. Consulte o README e
`CLICKO_MODO_DESENVOLVEDOR_2026-10-23.md` para ativação, isolamento e limpeza
recuperável confirmada. Não exponha por túnel ou proxy público. Para exigir login
comercial, pare o DEV antes de definir `CLICKO_DEV_MODE=false` (ou o alias
`CLICKO_LOCAL_REQUIRE_LOGIN=true`) e iniciar o perfil histórico.

As flags pagas Node, TTS e Python são sobrescritas somente no ambiente dos filhos,
não no `.env`. Chaves eventualmente presentes no `.env` não autorizam geração.
O pool local é limitado a duas threads e oito admissões; não é Celery distribuído.

## Renderização e persistência reais

Os comandos desta seção são do QA histórico, com ponte de fixture, não da nova
sessão DEV do navegador. Para repeti-los, use `CLICKO_DEV_MODE=false` e
`CLICKO_LOCAL_DATA_DIR=.codex-runtime/stage1-local` no supervisor. Os ensaios das
Etapas 2/3 recusam outra pasta deliberadamente. Para o DEV atual, veja a aceitação
e os projetos reais documentados no relatório de 23/10/2026. Não misture perfis.

```powershell
$env:PYTHONPATH='backend'
$env:CLICKO_VALIDATION_ARTIFACT_DIR=Join-Path (Get-Location) '.codex-runtime/stage1-validation'
.venv\Scripts\python.exe -m pytest backend/tests/test_media_final_validation.py
.venv\Scripts\python.exe scripts/video/stage1_acceptance.py create
npm run dev:stop
# Reinicie npm run dev:local em seu terminal e aguarde ready:
npm run dev:status
.venv\Scripts\python.exe scripts/video/stage1_acceptance.py verify
```

O primeiro teste produz uma montagem própria de 18 s. O teste HTTP importa os
materiais, salva dois cortes e texto animado, renderiza 16 s, confere H.264/AAC,
exporta vídeo/imagem, verifica replay do job e recusa de acesso fora de escopo.
O segundo comando `verify` confere bytes e revisão depois do reinício. A ponte
assinada usada pelo ensaio é de serviço em dados de QA: não homologa pagamento,
assinatura comercial, login de navegador ou qualidade de geração remota.

## Craft: dependências e procedimento reproduzível

Estado desta máquina: sem executável Docker, daemon Linux, Cargo/Rust ou bundles
Craft. PhotoCraft 0.7.0, FilmCraft 0.6.0 e EffectCraft 0.8.0 têm fontes completas e
revisões fixadas em `workers/craft/sources.lock.json`. O FFmpeg não depende deles.

1. O operador deve conferir os requisitos e termos do [Docker Desktop Windows](https://docs.docker.com/desktop/setup/install/windows-install/), incluindo licença comercial quando aplicável.
2. Instalar WSL 2 e uma distribuição Ubuntu compatível, habilitar virtualização se necessário e concluir os reinícios solicitados pelo instalador. São mudanças de sistema não executadas nesta etapa.
3. Instalar Docker Desktop da fonte oficial, selecionar Linux containers/WSL 2 e verificar `docker version` e `docker info --format '{{.OSType}}'` (`linux`). Não usar Windows containers.
4. Não é necessário instalar Rust no host para o builder atual. O contêiner utiliza Rust **1.95.0**, target `wasm32-unknown-unknown`, lockfiles Cargo e wasm-bindgen **0.2.129**. Pacotes Linux necessários estão em `workers/craft/Dockerfile.builder`: build-essential, pkg-config, clang/libclang, ALSA, fontconfig, xkbcommon, GTK3, OpenSSL, EGL, FFmpeg, Python e Node/npm.
5. Executar na raiz:

```powershell
.venv\Scripts\python.exe scripts/craft/provenance.py
.venv\Scripts\python.exe scripts/craft/runtime_preflight.py
.venv\Scripts\python.exe scripts/craft/build.py
.venv\Scripts\python.exe scripts/craft/build.py --wasm
```

O build nativo monta a imagem `clicko-craft-runtime:local`; o browser produz
`public/craft/<motor>/clicko_<motor>_adapter.js`, `_bg.wasm` e `manifest.json`.
O build coleta licenças/proveniência e valida o checksum do release wasm-bindgen.
Não copiar um binário Linux para ser executado como `.exe` no Windows. No host,
o adaptador é acionado pelo runner Docker existente; binários diretos são opção
somente em um worker Linux compatível. Não alterar as versões antigas de FilmCraft
exigidas por EffectCraft. As imagens de base ainda usam tags, não digest imutável;
fixar/arquivar seus digests verificados faz parte da promoção de release.

Depois do build, executar os testes nativos, `scripts/craft/acceptance.py`,
`media_acceptance.py` e os ensaios browser/native descritos em
`workers/craft/README.md`. Presença de arquivos não significa homologação.
O preflight nunca baixa, compila nem substitui um motor.

## Redis/Celery: caminho compatível e ainda não homologado

[Celery não oferece suporte oficial ao Windows desde 4.x](https://docs.celeryq.dev/en/stable/faq.html#windows).
Não tratar `--pool=solo` no Windows como equivalente ao worker Linux homologado.

Para desenvolvimento distribuído futuro, usar **API e workers no mesmo ambiente
Linux WSL2/Docker**, PostgreSQL e Redis acessíveis apenas pela rede privada local,
com banco e armazenamento compartilhados. Usar `backend/requirements.txt` e as
migrações existentes sobre um banco de QA novo, nunca sobre dados de clientes.

Configuração mínima comum (segredos privados provisionados pelo operador):

```text
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://<usuario>:<senha>@<postgres>/<banco-qa>
REDIS_URL=redis://<redis>:6379/0
CELERY_TASK_ALWAYS_EAGER=false
STUDIO_ISOLATED_QUEUES_ENABLED=false
GEMINI_OUTBOUND_ENABLED=false
STUDIO_GEMINI_ENABLED=false
STUDIO_RUNWAY_ENABLED=false
OPENAI_OUTBOUND_ENABLED=false
```

Um worker local Linux não isolado pode consumir a fila padrão com
`celery -A app.celery_app:celery_app worker --loglevel=INFO --queues=celery --concurrency=2 --prefetch-multiplier=1`.
Com filas isoladas, usar o worker `workers/media-cpu/Dockerfile`, manifesto e
atestação reais e a fila `studio.media.cpu`, além do consumidor de controle exigido
por `/health/ready`. Não desabilitar verificações de versões/manifest para promover
uma imagem diferente. O worker media-cpu atual depende do runtime Craft compilado.

Antes de promover: ping do broker, filas ativas, renderização real, duplicação de
entrega, cancelamento, morte/reinício do worker, limite de concorrência e recuperação
de arquivos precisam passar no ambiente Linux. Nada disso foi declarado distribuído
nesta máquina sem Docker/Redis. O executor local permanece a opção validada aqui.
