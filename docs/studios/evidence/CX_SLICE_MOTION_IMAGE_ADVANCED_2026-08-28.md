# Evidência — slice CX Motion + Image Lab — 2026-08-28

## Resultado

Motion deixou de ser uma aba decorativa do Visual e passou a ser uma capability contextual do mesmo `CreativeDocument`. Image Lab ganhou rota canônica própria para editar um `LibraryAsset` e devolver uma nova derivação ao ponto de origem. Os dois fluxos preservam o original, falham fechados e exigem ação humana antes de transformar sugestão em saída utilizável.

## Motion Inspector

- rota preservada: `/content/:contentId/edit?mode=visual&tool=motion`;
- o documento Visual recebe `MediaTimelineV1` provider-neutral; documentos anteriores ganham a timeline no próximo save, sem migração destrutiva;
- camada alvo é resolvida pelo ID persistido; camada ausente ou bloqueada desabilita a mutation com motivo;
- presets `Sutil`, `Equilibrado` e `Ênfase`, duração em frames, antes/depois e preferência de movimento reduzido são controles funcionais;
- a prévia é local e explicitamente não altera o documento;
- `Salvar sugestão` cria `MotionGraphV1` ligado a `documentId + revision + layerId + frameRate + canvas`;
- constraints de overshoot são avaliadas no backend; `Revisar e aplicar` é uma mutation humana separada;
- a projeção HyperFrames só deixa de ser `previewOnly` depois da revisão;
- reload recupera o último grafo; se a revisão do documento mudou, a UI marca a sugestão como histórica e bloqueia aplicação stale;
- reset afeta apenas a prévia local e preserva registros auditáveis.

## Image Lab

- rota canônica: `/library/assets/:assetId/edit?mode=image&returnTo=...`;
- `returnTo` aceita somente Biblioteca ou editor interno; entrada externa é descartada;
- mídia privada é carregada por Blob autenticado, sem converter o endpoint protegido em URL pública;
- brilho, contraste, máscara retangular/elíptica, antes/depois e locks explícitos de rosto/produto/logo são funcionais;
- locks são regiões normalizadas reais: seus pixels são copiados do original durante a composição;
- a UI declara honestamente que esses locks são definidos pelo usuário; detecção automática não é alegada;
- `POST /api/v1/assets/{assetId}/derive` valida tenant, lifecycle, MIME, checksum esperado e checksum materializado;
- o request e o port `ImageEditProvider` são provider-neutral; Pillow é apenas o adapter determinístico local v1;
- saída é um novo PNG privado no zone `derived`; o source nunca é regravado;
- ID derivado é determinístico por workspace/idempotency key; repetição com payload divergente falha com `409`;
- metadata e evento preservam source asset/checksum, operation digest, mask, regiões protegidas, provider/versão e `reviewRequired=true`;
- a volta entrega `derivedAsset` ao editor de origem e não insere/publica automaticamente.

## Contratos e navegação

- nova rota única `ROUTE-IMAGE-LAB` e telas `SCREEN-LIBRARY-ASSETS`/`SCREEN-IMAGE-LAB`;
- ações novas com telemetria: `VISUAL-OPEN-MOTION`, `MOTION-PREVIEW`, `MOTION-SAVE-SUGGESTION`, `MOTION-APPLY`, `HOME-OPEN-LIBRARY`, `LIBRARY-OPEN-IMAGE-LAB`, `LIBRARY-INSERT-EDITOR`, `IMAGE-COMPARE`, `IMAGE-CREATE-DERIVATION` e `IMAGE-RETURN`;
- o grafo executável cobre Home → Biblioteca → Image Lab → Visual;
- a Biblioteca mantém dois handoffs distintos: editar o original de forma não destrutiva no Image Lab ou inserir explicitamente o asset selecionado no Visual Studio;
- `npm run audit:cx`: 45 registros, 59 URLs conhecidas, zero issues/órfãs/conflitos e 50 controles com Action ID.

## Evidência executável

- `npm run lint` — aprovado.
- `npm run test:cx-contracts` — 6/6.
- `python -m pytest tests/test_studio_motion_graph.py tests/test_studio_motion_graph_api.py tests/test_hyperframes_adapter.py -q` — 11 aprovados e 1 integração opcional ignorada.
- `python -m pytest tests/test_image_derivation.py -q` — 2/2.
- Playwright `Motion Inspector|Image Lab autenticado` — 2/2: reduced motion, demo honesta, upload PNG real, derivação privada, lineage e retorno.
- Playwright móvel 390×844 — Motion e Image Lab concluíram a tarefa sem overflow horizontal; o teste inicialmente expôs o inspector oculto abaixo de 1350 px e o layout foi corrigido para painel contextual empilhado.
- Playwright `Studio autenticado persiste Visual` — 1/1, agora incluindo criação/revisão real do MotionGraph e projeção HyperFrames.
- `npm run test:e2e` — 26/26 jornadas aprovadas após a correção do handoff Biblioteca → Visual e do seletor inequívoco do rótulo de demonstração.
- `npm run build` — aprovado; permanece apenas o warning conhecido de chunk JavaScript acima de 500 kB.

## Limites deliberados

- presets de Motion cobrem opacity/scale; editor de keyframes, bezier livre, Motion Canvas runtime e paridade visual ampla continuam posteriores;
- o adapter Pillow é síncrono e adequado a ajustes locais limitados; operações pesadas devem migrar para job/worker sem alterar o contrato;
- locks automáticos por visão computacional permanecem bloqueados até benchmark, política e revisão de falsos negativos;
- smart crop, generative fill, inpainting e remoção de fundo não foram simulados por botões;
- Figma permanece pendente porque o MCP Figma não está exposto nesta sessão; nenhuma automação via navegador foi usada como substituto.
