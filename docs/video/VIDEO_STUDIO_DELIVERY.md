# Studio de Vídeo — entrega e validação

Data: 17/10/2026. Repositório: `C:\Users\pedro\Downloads\res`. Base Git: `5cab414dd942c721f8e6fdf65dcd82b4ade28722`, acrescida das alterações locais já existentes. Esta entrega é um **MVP de montagem e exportação real**, não uma declaração de equivalência funcional com Premiere/CapCut.

## 1. Arquitetura encontrada e preservada

- React/TypeScript: `ClickoStudioView` e a interface local `VideoStudio` já organizavam briefing, materiais, projetos, criação assistida, editor Craft, motion e anúncios.
- Node/Express: sessão Clicko, governança, workspace/cliente, autorização e proxy assinado para Studio. Essas continuam sendo as autoridades de acesso; não há novo login.
- Python/FastAPI: documentos `CreativeDocumentV1`, timeline `MediaTimelineV1`, SQLAlchemy, catálogo `LibraryAsset`, armazenamento, eventos e jobs existentes.
- Runtimes FilmCraft/EffectCraft: presentes como código e contratos, mas sem runtime saudável/configurado neste ambiente. A rota antiga `video_render` estava expressamente aposentada. Restaurá-la sem análise não resolveria o fluxo.
- Biblioteca: a visualização global anterior e os ativos do serviço Studio não eram o mesmo catálogo. A integração adicionada é somente uma leitura autorizada dos vídeos exportados, sem duplicá-los em localStorage.

O caminho novo é explícito: documento **não nativo** → timeline canônica → job `timeline_render` → provedor `ffmpeg.timeline-v1` → FFmpeg/ffprobe → asset persistido → monitor/Biblioteca. Documentos com `nativeEditorState` permanecem no editor original; não são migrados ou sobrescritos pelo editor CPU.

## 2–5. Histórico, referências, SHAs e licenças

O inventário completo, com SHAs exatos, caminhos examinados, decisões e licenças, está em [OPEN_SOURCE_PROVENANCE.md](./OPEN_SOURCE_PROVENANCE.md).

Internos consultados: `5cab414dd942c721f8e6fdf65dcd82b4ade28722`, `cfa5f2b5cb4eda1dbd6edfed91221eb12cdddaa9`, `a5735d9e15988f966fd9488539b66275538faa5e`, `b91f7172feaef6b007736d44869ecb423f7d2ef1`, `4af887309bbb1f28e34fd77e4f5165df91a03d81`. Houve inspeção de status, branches, log, histórico de caminhos, reflog e diffs candidatos, sem reset/cherry-pick.

Externos consultados: OpenCut Classic, OpenCut atual, FFmpeg, OpenTimelineIO, Remotion, Shotcut e Kdenlive. **Nenhum código desses editores foi copiado.** OpenCut/OTIO foram referências arquiteturais; Shotcut/Kdenlive, referências funcionais; Remotion não foi adotado. O executável FFmpeg é a integração externa efetiva. Não há nova dependência npm/Python.

A distribuição local verificada é LGPL-3.0-or-later, sem `enable-gpl`/`enable-nonfree`, com OpenH264 e AAC. Licença, DLLs e documentação originais foram preservadas fora do Git. Isso não dispensa as obrigações do distribuidor caso esse pacote venha a ser redistribuído. Não se pressupõe que outras builds FFmpeg tenham a mesma licença.

## 6. Arquivos desta etapa e justificativa

| Arquivo/camada | Alteração e motivo |
| --- | --- |
| `backend/app/domain/studios/timeline_editor.py` | Contratos limitados de motion, keyframes e pedidos com revisão. |
| `backend/app/domain/studios/contracts.py` | Campos aditivos de motion nos títulos, fonte `system` explícita e tipo/provedor de job. Contratos anteriores preservados. |
| `backend/app/domain/studios/execution.py` | Encaminhamento do novo job para `media_cpu`. |
| `backend/app/providers/studios/timeline_ffmpeg.py` | Readiness real, probe, compilação controlada da timeline, composição e validação do MP4. |
| `backend/app/services/studios/timeline_editor.py` | Autorização dos materiais, CAS, recibos idempotentes, snapshot imutável, exportação e recuperação de entrega já persistida. |
| `backend/app/routers/studio_video.py` | Rotas específicas de vídeo, catálogo, conteúdo com Range, despacho local limitado e recuperação após reinício. |
| `backend/app/services/studios/jobs.py`, `backend/app/routers/studios.py` | Integração/retry na infraestrutura atual, sem reativar renderizador aposentado. Identificação do processo local evita interromper um worker ainda ativo. |
| `backend/app/studio_app.py` | Registro das rotas, fronteira de módulos e correção da corrida de bootstrap de identidade observada nos pedidos concorrentes. Preservadas as alterações de Imagem preexistentes. |
| `server/studios/proxy.ts` | Contexto de entrega de vídeo para elementos de mídia, mantendo sessão e assinatura de escopo. Imagens não foram redirecionadas para esse caminho. |
| `server.ts` | Host opcional da prévia, para manter o ambiente de QA em loopback. Padrão existente preservado. |
| `src/studios/video/canonicalTimeline.ts` | Operações sobre o mesmo contrato persistido: corte, frames, origem, transformações, presets e movimentação entre faixas compatíveis. |
| `src/studios/video/CanonicalVideoEditor.tsx`, `canonical-video.css` | Materiais, monitor real, inspetor, timeline multipista, salvamento seguro, recuperação local e jobs. Tokens e fonte nativos da Clicko. |
| `src/studios/video/canonicalVideoApi.ts` | URL estável de conteúdo autenticado, sem credenciais de backend no navegador. |
| `src/studios/video/VideoStudio.tsx` | Seleção explícita entre editor CPU e editor nativo, disponibilidade real e preservação da revisão mais recente. O arquivo já existia localmente antes desta etapa. |
| `src/studios/video/VideoLibraryExports.tsx`, `src/components/LibraryView.tsx` | Catálogo de exportações na Biblioteca e supressão do estado vazio quando existem vídeos. Demais ações da Biblioteca preservadas. |
| `workers/media-cpu/worker.manifest.json`, `backend/tests/test_worker_runtime.py` | Novo job/provedor no manifesto versionado e no teste correspondente. |
| `backend/tests/test_video_timeline_real.py`, `src/studios/video/canonicalTimeline.test.ts` | Cobertura de contrato, tempo, mídia real, isolamento, repetição e recuperação. |
| `scripts/video/install-ffmpeg.ps1` | Instalação local opcional, fixada por release e SHA-256, sem alterar variáveis globais. O script de reinstalação foi escrito; a instalação efetivamente exercitada está descrita no documento de procedência. |
| `scripts/video/acceptance.py` | Fluxo HTTP real pela porta Node de QA, incluindo arquivo final, replay e Biblioteca. |
| `scripts/run-audit-tests.cjs` | Concorrência de teste opcional e limitada por `CLICKO_TEST_CONCURRENCY`; padrão anterior mantido. Permite executar a suíte sem competição de recursos com build/render nesta máquina. |
| `docs/video/*.md` | Procedência, reprodução, evidências, status e limites. |

`server/governance.ts`, cota/rotas de Imagem, `ClickoStudioView`, testes anteriores e outros arquivos já modificados foram encontrados no checkout. Não se atribui toda a diferença contra HEAD a esta entrega. Nenhum arquivo de Imagem foi reconstruído, nem foram modificadas conexões sociais.

## 7. Renderização concreta

O compilador recebe o snapshot da timeline canônica, não uma descrição aproximada de como a tela parece. Resolve somente assets do workspace autorizado, confere checksums, materializa arquivos e faz probe dos streams. Entradas locais são limitadas; rede/protocolos arbitrários e filtros fornecidos pelo usuário não são aceitos.

O plano usa argv/subprocess, **sem shell**. Há corte de origem, posicionamento em frames, velocidade, escala, enquadramento, sobreposições, rotação estática, opacidade/fades, keyframes lineares X/Y/escala/opacidade, mixagem, ganho e fades de áudio. Títulos são rasterizados por Pillow em transparência com fonte local explícita; texto do usuário não vira comando FFmpeg. Fundos de título compõem gráficos básicos. Transições desta versão são sobreposição com fades, não um catálogo de efeitos artificiais.

Saída: H.264 + AAC, MP4, YUV420p e faststart. ffprobe confere codec, dimensões, fps e duração antes de persistir o resultado. O job só conclui após o ativo real estar entregue no armazenamento. Se a confirmação do job falhar depois da gravação, a repetição recupera o ativo existente em vez de renderizar novamente.

**Prévia não é tempo real:** o monitor reproduz exatamente o MP4 exportado. Após editar, é necessário gerar a nova revisão; a interface identifica uma prévia antiga. Assim não existe uma animação de preview que desapareça no render final.

## 8. Testes executados

### Automatizados de contrato/lógica

- `npm test` com `CLICKO_TEST_CONCURRENCY=1`: **178/178 aprovados**, sem skips. A execução concorrente sob build/testes de mídia simultâneos causou timeouts em testes existentes de autenticação/KLIC; a repetição serial completa passou, sem desabilitá-los.
- `npm run lint`: aprovado (`tsc --noEmit`).
- `npm run build`: frontend, servidor e worker compilados com êxito. Logs locais em `.codex-runtime/video-qa/`.
- Conjunto Python direcionado: **40/40 aprovados**, sem skip nesta máquina. Inclui os quatro testes novos de timeline real, os contratos existentes de Imagem/Vídeo, bridge, Craft/lifecycle, Studio e dois testes de manifesto/runtime CPU.
- O conjunto **inteiro** de `test_worker_runtime.py` também foi tentado. Não está globalmente verde: exige manifestos GPU/voz ausentes do checkout, por exemplo `workers/vision-gpu/worker.manifest.json`, também ausente em HEAD. Não foram criados manifestos fictícios para esconder essa lacuna. Os testes CPU pertinentes foram executados separadamente.
- `git diff --check`: sem erros de whitespace; avisos locais de conversão LF/CRLF não são falhas de execução.

### Testes com motor/mídia reais — sem mock de saída

`backend/tests/test_video_timeline_real.py` cria mídia com FFmpeg, importa vídeo, áudio e PNG pelos endpoints, aplica cortes de origem, ordenação, sobreposição animada, título, keyframes, rotação e mixagem/fades. Renderiza de verdade, verifica pixels vermelhos/azuis/verdes e texto, decodifica amostras de áudio e mede a redução de amplitude do fade. Confere H.264/AAC, duração, download parcial HTTP 206 e recusa a outro workspace/cliente. Reabre sessões, recupera projeto/job/ativo, verifica replay e recuperação de interrupção/cancelamento.

Há mocks somente para controlar despacho de jobs e falhas específicas nos testes. O teste do caminho normal **não** substitui FFmpeg/ffprobe por resultado simulado. O teste de replay pós-gravação bloqueia propositalmente um segundo render para comprovar reaproveitamento do MP4 já entregue.

`scripts/video/acceptance.py` também passou pelo Node `3018` e Python `8018`, não apenas por TestClient:

- Documento: `a31f336b-6ccb-4ddf-87f1-b87c1d68c5c6`, revisão 2.
- Job: `b0ef41a9-6a75-4869-8ebf-aa3e45b7fa09`.
- Asset: `7c3905e5-8bf2-4707-81da-08c6f4a8fc06`.
- Saída: **640 × 360, 24 fps, 3 segundos, H.264/AAC**, 923.613 bytes.
- SHA-256: `21d153b80495e8cfdf8ae4ca77a38a4976ab8eb1a080b1b9eeebf7fc2a8a3c36`.
- Evidências: `.codex-runtime/video-qa/evidence.json`, `final.mp4`, `frame.png`. O frame extraído foi inspecionado visualmente: padrão de teste real com o título **Crie. Edite. Clicko.** sobreposto. São materiais técnicos de QA, não vídeos de cliente nem geração de cenas por IA.

### Navegador

Na prévia isolada foi criado/salvo um segundo projeto pela interface; o projeto exportado foi reaberto; o monitor carregou o MP4 com `readyState=4`, 640×360, duração 3s e sem erro de mídia. A reprodução foi iniciada e o cursor chegou ao final. A Biblioteca global exibiu o ativo e o link de download autorizado.

A inspeção DOM em desktop 1440px não indicou overflow horizontal (scrollWidth 1425px). Foram conferidos o tema escuro e a troca para claro pelas Configurações da prévia. No tema claro, o painel do monitor computou fundo branco e texto `rgb(32,32,32)`, mantendo o vídeo carregado. Em mobile 390×844, a página mediu scrollWidth 375px, editor/painéis 287px; apenas a timeline teve rolagem interna intencional (340px em uma área de 261px). O MP4 permaneceu com readyState 4. A dimensão temporária foi removida ao terminar o teste.

**A captura de tela do navegador falhou repetidamente**, inclusive com a aba visível: não se declara aqui uma inspeção pixel a pixel completa nem uma gravação visual do editor em todos os tamanhos. Isso é uma limitação de QA da interface, não um MP4 simulado. A mídia exportada foi visualmente inspecionada por frame extraído.

## 9. Ambiente e reprodução

- Prévia isolada: `http://127.0.0.1:3018/video`; Biblioteca: `http://127.0.0.1:3018/library`.
- API isolada: `127.0.0.1:8018`. Dados separados em `.codex-runtime/video-qa/`, ignorados pelo Git.
- O ambiente principal `3000`/`8000` não foi reiniciado: havia um briefing não salvo na aba original. A prévia de QA não substitui nem apaga esse rascunho.
- A API **8018** foi efetivamente reiniciada depois da implementação. Pelo proxy Node, o documento manteve revisão 2, o job continuou `succeeded` e o MP4 respondeu HTTP 206 com 100 bytes solicitados. Portanto há também prova de persistência depois de um reinício real do serviço, além da reabertura de sessões no teste automatizado.
- Node QA: `PORT=3018`, `CLICKO_PREVIEW_HOST=127.0.0.1`, `CLICKO_STUDIOS_ORIGIN=http://127.0.0.1:8018`, `CLICKO_GOVERNANCE_DATA_FILE=<repo>/.codex-runtime/video-qa/governance.json` e uma bridge secret **local de teste**, igual na API. O bypass de autenticação de desenvolvimento limita-se a esse ambiente local de QA; não é configuração de produção.
- Python QA: `ENVIRONMENT=development`, SQLite e storage sob a pasta de QA, `CELERY_TASK_ALWAYS_EAGER=true`, `STUDIO_ISOLATED_QUEUES_ENABLED=false`, bridge secret local correspondente; iniciar `python -m uvicorn app.studio_app:app --app-dir backend --host 127.0.0.1 --port 8018`.
- FFmpeg/ffprobe: configurar os caminhos já previstos pelo serviço/PATH ou usar a instalação local verificada em `.codex-runtime/ffmpeg/`. `scripts/video/install-ffmpeg.ps1` permite reinstalação fixada. Não foi alterado PATH global.
- Após iniciar apenas esses ambientes isolados: `.venv/Scripts/python.exe scripts/video/acceptance.py`. O script cria novos projetos/ativos de teste; não deve ser apontado à conta de produção.
- Produção exige provisionar worker `media_cpu`, fila Celery/Redis, FFmpeg/ffprobe, fontes e armazenamento durável, além de backups/observabilidade. Instalar os binários não equivale a esse provisionamento.
- O Dockerfile CPU atual parte de `clicko-craft-runtime:local` e seu manifesto também exige os três adapters Craft. Não foi realizado build/atestado dessa imagem nesta máquina. Liberar o caminho FFmpeg em produção exige fornecer essa base completa (e as fontes locais usadas pelos títulos), ou separar esse perfil operacional em outra etapa; o fluxo local validado não demonstra que essa imagem já esteja publicada/pronta.

## 10. Status funcional

| Recurso | Situação |
| --- | --- |
| Criar/reabrir projeto, importar mídia e persistir | Concluído e exercitado em HTTP/interface. |
| Corte, duração, ordem, múltiplas faixas e overlays | Implementado no contrato único; cortes/ordem/overlay exercitados com mídia real. Arraste possui alternativa numérica no inspetor. |
| Título/CTA, gráficos básicos e motion | Implementação própria, persistida e renderizada. Presets usam os mesmos keyframes/fades, não plugins externos. |
| Keyframes X/Y/escala/opacidade | Lineares, com controles de início/fim; sem editor de curvas complexo. |
| Áudio real, ganho, fades e mixagem | Implementado; waveform da saída validado. Síntese de nova voz não foi inventada. |
| Jobs, replay, cancelamento, revisão e recuperação | Implementado/testado; progresso exibido é do serviço, não simulação de geração. |
| MP4 validado, reprodução, download e Biblioteca | Concluído com saída real. Catálogo remoto tem busca/ordenação; gestão avançada desses assets não foi adicionada à Biblioteca. |
| Preview interativo de efeitos sem render | Não implementado; monitor usa o MP4 exato por revisão. |
| FilmCraft/EffectCraft nativo | Preservado; depende de runtime saudável no ambiente. Não afirmado como validado end-to-end. |
| Geração integral de cenas por IA/Klic | Integração separada; depende de provedor/configuração. Nenhuma chamada paga nem simulação feita para apresentar esse recurso como pronto. |
| Máscaras, GPU, curvas, tracking, chroma, OTIO | Não implementados nesta etapa; parâmetros não suportados são rejeitados. |
| Disponibilidade em produção distribuída | Pendente de provisionamento e validação operacional. |

Limites explícitos de segurança do MVP: 10 minutos, 16 faixas, 32 itens, até 1920px por dimensão, 60fps, 32 keyframes por item e limites de materialização. Não é exportação 4K. A política comercial de minutos/armazenamento para esse novo tipo de render **não foi inventada**; precisa ser definida antes de liberá-lo comercialmente. A regra anteriormente confirmada para solicitações de **imagem** não foi reinterpretada como regra de vídeo.

## 11–12. Procedência e próximas etapas concretas

1. Provisionar e atestar worker CPU/armazenamento em homologação, testar concorrência, cancelamento de render longo e recuperação por reinício real do cluster.
2. Definir e aplicar no Node a regra comercial de minutos de render e armazenamento, com conciliação idempotente. Não há decisão de cobrança implicitamente tomada nesta entrega.
3. Completar QA visual capturável de desktop/mobile, teclado/toque e temas; o bloqueio da ferramenta de captura está relatado acima.
4. Adicionar preview incremental/proxies e thumbnails/waveform somente a partir do mesmo modelo canônico e de comparação automatizada com o render final.
5. Evoluir motion/curvas/transições/legendas e formatos de entrega com novos contratos e provas de mídia real, antes de exibir novos controles.
6. Integrar IA/Klic como produtor de comandos validados sobre a timeline, preservando confirmação, custos, revisões e a separação entre geração de cenas e montagem.

Não houve push ou publicação externa nesta etapa. Alterações locais anteriores foram preservadas.
