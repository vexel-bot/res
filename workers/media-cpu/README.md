# Clicko media CPU worker — Craft

Este worker executa `craft_render` com PhotoCraft, FilmCraft e EffectCraft,
além de inspeção, proxies, waveforms e aquisição de materiais. FFmpeg permanece
como utilitário. Os renderizadores anteriores e suas dependências foram retirados.

## Build

Primeiro gere os três executáveis e a imagem base:

```bash
python scripts/craft/build.py
docker build --file workers/media-cpu/Dockerfile --tag clicko-media-cpu:craft .
```

Para distribuição, use `--build-arg CRAFT_RUNTIME_IMAGE=<imagem@sha256:digest>`
com a imagem Craft publicada e fixada. Registre o digest OCI final, SBOM,
provenance, `pip freeze`, versões Debian, `ffmpeg -buildconf` e os checksums
dos executáveis de `.codex-runtime/craft/runtime-manifest.json`.

Cada adaptador suporta `--version`. O manifest confere os três motores e as
ferramentas antes de consumir jobs, incluindo a fila exclusiva `studio.media.cpu`.
As configurações `STUDIO_CRAFT_*_BINARY` apontam para os executáveis da imagem.
Plugins/scripts que exigem isolamento adicional não ficam disponíveis nesse
transporte direto; o runner por job oferece um container sem rede.

## Execução

- Usuário 10001, filesystem somente leitura, um job por processo e recursos limitados.
- `/tmp/clicko-craft` efêmero e gravável pelo usuário do worker.
- Bucket privado, credenciais por prefixo, rede limitada a dependências privadas.
- `STUDIO_ISOLATED_QUEUES_ENABLED=true`, `STUDIO_WORKER_MANIFEST_PATH` e
  `STUDIO_WORKER_CAPABILITY=media_cpu`; em produção, também
  `STUDIO_WORKER_IMAGE_DIGEST=sha256:<64 hex>`.
- Secrets fornecidos pelo orchestrator; não entram na imagem.

Os builds e testes locais não promovem uma imagem nem alteram a VPS Nexus.
As evidências dos workers anteriores estão em
`docs/studios/archive/media-cpu-runtime-pre-craft.md` e não atestam este runtime.

## Validação reproduzível

Após a aceitação HTTP com banco e storage de QA isolados:

```bash
python scripts/craft/worker_acceptance.py
docker pull redis:8.2.1-alpine
python scripts/craft/queue_acceptance.py
```

O primeiro teste confere usuário, filesystem, versões e checksums dos motores
na imagem real e gera attestation e inventário CycloneDX em
`.codex-runtime/craft/media-worker-*.json`. O inventário reúne pacotes instalados
Python/Debian e dependências dos locks Rust; não é uma lista apenas das bibliotecas
Rust efetivamente ligadas nos executáveis.

O segundo cria API, Redis e worker descartáveis, usa uma cópia do banco de QA,
exporta MP4 pela fila e cancela um processo nativo em andamento. O worker tem
somente rede interna; os recursos criados pelo teste são removidos ao final.
SQLite fica em volume Linux compartilhado entre API e worker: não use o mesmo
arquivo SQLite por Windows e Linux em bind mount NTFS. `STORAGE_PATH` seleciona
o storage de QA existente; os projetos originais não entram nesse teste.
