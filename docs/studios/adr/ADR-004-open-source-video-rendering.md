# ADR-004 — Renderização de vídeo open source

**Status:** adapter local aceito; ativação em produção pendente  
**Data:** 2026-08-24

## Contexto

O Studio de Vídeo precisa de composição reproduzível, preview, render headless, progresso, cancelamento e saída independente de provider. A Clicko decidiu avaliar somente tecnologias efetivamente open source; código público com restrições comerciais não é suficiente.

## Candidatos auditados

- **FFmpeg:** infraestrutura base para probe, codecs, transcode e mux; a licença efetiva depende da build.
- **HyperFrames:** Apache-2.0; composição HTML/CSS, animações seekable, Chrome headless, FFmpeg, CLI, player, Studio e render distribuído.
- **Remotion:** source-available com licença própria e elegibilidade por tipo/tamanho da organização.
- **HyperFrames Launch Video:** projeto de referência sem licença própria para reutilização de composição e mídia.

## Decisão

1. FFmpeg permanece a camada commodity obrigatória atrás de adapter e build auditada.
2. HyperFrames será o primeiro spike de render programático atrás de `VideoRenderProvider`.
3. O `CreativeDocument` continua canônico; HTML HyperFrames é uma projeção descartável e reconstruível.
4. Remotion não será incorporado enquanto a regra for “somente open source”.
5. O launch video será usado apenas para estudar estrutura e definir casos de benchmark; nenhum asset ou trecho será copiado.

## Evidência do primeiro smoke local

- composição própria e sintética; nenhum asset ou trecho do launch video foi reutilizado;
- HyperFrames `0.8.12`, lint com zero erros e zero warnings;
- saída H.264 1080×1920, 30 fps, 60 frames, duração 2 s e 843.884 bytes;
- dois renders byte a byte idênticos, SHA-256 `EE5F09C01D0FFE67C5164670F15D514EDABA423AF58A437E8A55A6A34AE9C74F`;
- timeline seekable própria, sem GSAP, para manter o spike dentro da regra “somente open source”;
- primeira execução baixou Chrome e fontes; a imagem/worker de produção precisa trazer browser, FFmpeg e fontes pré-fixados e passar teste sem egress;
- o FFmpeg local é uma build GPLv3 de desenvolvimento e não foi aprovado para redistribuição.

## Orquestração entregue

A fronteira assíncrona agora possui endpoint dedicado, `CreateVideoRenderJobRequest`, snapshot integral e imutável do `CreativeDocument`, `VideoRenderRequestV1`, placement `media_cpu`, idempotência e persistência do resultado/asset com checksum e lineage. O teste altera o documento após o enqueue e comprova que o provider recebe a revisão fixada.

`VideoRenderProvider` recebe documento/request provider-neutral, destination temporário, progresso e cancelamento, e devolve somente metadados do encode; storage e `LibraryAsset` permanecem responsabilidades Clicko. O registry de produção começa vazio. `hyperframes.cli` só pode criar job quando um adapter for explicitamente registrado após os gates; caso contrário a API falha com `video_render_provider_unavailable`.

O adapter `HyperFramesCliVideoRenderProvider` foi implementado sem incorporar o repositório: projeta páginas/layers e tracks canônicas para HTML efêmero, materializa apenas assets privados do workspace, usa CSP `connect-src 'none'`, lint zero-error/zero-warning, processo cancelável, timeout e probe da saída. O registry só é preenchido com `HYPERFRAMES_ENABLED=true`; startup recusa ativação sem fila isolada e CLI configurada.

Smoke real do adapter com HyperFrames `0.8.12`: Node `22.15.0`, MP4 H.264 360×640, 30 fps, 1 s, 15.043 bytes e SHA-256 `A0D65A68D662A274DA34C548CFA793D6030C9B4BA23B7505D097F3754DB658BA`. Nenhum asset remoto ou configuração da VPS foi usado.

## Imagem isolada comprovada

O runtime `workers/media-cpu` fixa Node/base AMD64 por digest, HyperFrames por lockfile e executa Celery como UID `10001`. A imagem local tem digest OCI `sha256:bbfdabed4b7e9f0049d57c2877b6f1146886d89b3c864fe320c929b6c2cb7595` e 861.962.598 bytes. Seu CycloneDX contém 809 componentes e SHA-256 `AF5531A3CF188EEBC95E70F41D601CE5566A3DD5A3070D86D3392ED2E0E65204`.

O smoke de contêiner passou sem rede, com root filesystem read-only, usuário não-root, home efêmero e tmpfs executável de 4 GiB em `/tmp/clicko-hyperframes`: lint limpo e MP4 H.264 1080×1920/30 fps/2 s/548.089 bytes em 24,4 s. O teste mostrou que `noexec` é incompatível com o HyperFrames e que montar `/tmp` inteiro oculta o `TMPDIR`; a montagem operacional deve ser exatamente no subdiretório configurado.

## Critérios do spike

- render 1080×1920 e 1080×1350 com texto PT-BR;
- captions, áudio, imagens, vídeo e pelo menos uma transição;
- saída determinística e hash/lineage registrados;
- progresso monotônico, cancelamento e timeout pelo worker Clicko;
- isolamento de filesystem/rede e assets por workspace/job;
- medição de duração, CPU, RAM, disco e custo em worker dedicado; a VPS atual permanece control plane;
- comparação com pipeline FFmpeg direto;
- remoção do adapter sem migração do documento canônico.

## Consequências

O adapter, a imagem local e o smoke no-egress encerram a prova mínima de empacotamento, mas não autorizam produção. Ainda faltam fixar os pacotes Debian por snapshot/versão, revisar a build/licença efetiva do FFmpeg, emitir provenance/SBOM na CI, executar benchmark multimídia com limites reais e provisionar worker dedicado externo. O launch video falhou no lint atual (`8 errors`, `32 warnings`) e permanece somente referência.
