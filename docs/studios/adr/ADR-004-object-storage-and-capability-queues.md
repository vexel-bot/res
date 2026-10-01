# ADR-004 — Object storage e filas por capability

**Status:** aceito; worker `media_cpu` provado localmente, rollout de produção condicionado  
**Data:** 2026-08-24

## Contexto

Uploads e exports eram gravados diretamente em `storage_path`, e routers/serviços conheciam o filesystem. Esse desenho não atende mídia grande, workers externos, checksum/proveniência, retenção nem troca de infraestrutura. Ao mesmo tempo, a VPS Nexus atual é control plane com recursos limitados e não pode receber carga de render, fala ou visão.

## Decisão de armazenamento

Adotar um port `ObjectStorage` provider-neutral com dois adapters:

- `LocalObjectStorage`: fallback compatível para desenvolvimento e rollback;
- `S3ObjectStorage`: bucket privado S3-compatible, download autenticado seguido de URL assinada curta e credenciais por ambiente/role.

Objetos novos usam chave `<workspace>/<zone>/<uuid>.<ext>`, sem nome original ou dado pessoal. `LibraryAsset` persiste backend, MIME, bytes, SHA-256 e metadados mínimos de linhagem. O endpoint autenticado continua sendo a URL pública do produto; bucket/endpoint nunca vira referência canônica no `CreativeDocument`.

Zonas iniciais: `raw`, `derived`, `exports`, `identity`, `voice` e `temporary`. Quarantine, multipart, lifecycle e deleção em DAG entram antes de cargas biométricas; a interface atual não declara essas capacidades como prontas.

## Decisão de execução

Cada `GenerationJob` recebe placement imutável na criação:

| Capability | Fila lógica | Classe | Exemplos |
| --- | --- | --- | --- |
| `control` | `studio.cpu` | `cpu.standard` | snapshot, orquestração curta |
| `media_cpu` | `studio.media.cpu` | `cpu.media` | ingestão, FFmpeg, render |
| `speech_gpu` | `studio.gpu.speech` | `gpu.speech` | transcrição e clonagem de voz |
| `vision_gpu` | `studio.gpu.vision` | `gpu.vision` | lip-sync e avatar |

`STUDIO_ISOLATED_QUEUES_ENABLED=false` é o estado seguro de rollout e preserva `.delay()` no worker atual. Quando a flag for ativada, o dispatcher usa fila e time limits explícitos persistidos no job. A ativação exige workers por capability, health/capacity, broker smoke, autoscaling/cotas e dead-letter/reconciliação. A VPS atual não será usada como worker de mídia/GPU.

Emenda de 25/08/2026: a ADR-011 entrega manifest/boot gate, probe, health, attestation persistida e smoke físico local de `media_cpu` com Redis. Isso remove a lacuna de separação por processo no laboratório, mas não autoriza ativação em produção sem PostgreSQL/S3/IAM, observabilidade, reconciliação/dead-letter, quotas e imagem promovida/assinada.

## Segurança e isolamento

- autorização acontece antes de resolver arquivo local ou assinar URL;
- a chave é validada contra traversal e escopada por workspace;
- assets legados continuam legíveis pelo adapter `local`, mesmo se o backend ativo mudar;
- credenciais parciais e S3 sem bucket falham na validação de startup;
- metadados não contêm prompts completos, biometria ou segredos;
- downloads S3 não tornam o bucket público.

## Migração e rollback

Migration `0015_object_storage` adiciona lineage aos assets e placement aos jobs com defaults compatíveis. Upgrade/downgrade/upgrade foi validado em SQLite novo.

Rollback operacional:

1. manter/desligar `STUDIO_ISOLATED_QUEUES_ENABLED`;
2. selecionar `OBJECT_STORAGE_BACKEND=local` para novos objetos;
3. preservar `storage_backend` por asset para ler objetos antigos no adapter correto;
4. drenar jobs antes de retirar um worker;
5. não apagar bucket/objetos durante rollback de schema.

## Consequências e gates restantes

Ganho imediato: routers e exportadores deixam de depender do filesystem, outputs recebem checksum/linhagem e o placement CPU/GPU vira dado auditável.

Antes de produção de vídeo/identidade ainda faltam: bucket provisionado fora da VPS, TLS/IAM/KMS, CORS, multipart/resume, quarantine/scan, lifecycle/quotas, teste S3 real, deleção derivada, observabilidade de storage e workers dedicados. Portanto esta ADR não declara infraestrutura de mídia pronta.
