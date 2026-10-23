# Auditoria técnica — Imagens, Vídeos e IA da Clicko

Data: 20/10/2026. Repositório: C:/Users/pedro/Downloads/res. Branch: codex/klic-atualizacao-20260823. HEAD: 5cab414dd942c721f8e6fdf65dcd82b4ade28722, mais alterações locais preexistentes.

## Resumo executivo

A Clicko tem uma base real de edição, persistência, autorização e processamento audiovisual, mas **não está comprovada como um estúdio autônomo de geração profissional de ponta a ponta**. O frontend atual reúne caminhos com maturidades diferentes: editor canônico com FFmpeg, motores Craft, geração remota Gemini/Runway e pipelines editoriais parcialmente migrados.

Principais conclusões:

1. **Existem duas rotas antigas simuladas ainda registradas.** Image-edit afirma editar, mas retorna a própria imagem ou uma foto pública. Video-edit afirma cortar, legendar e remover 3,8 segundos de silêncio, mas retorna o vídeo original ou um exemplo. Ambas consomem cota. Não encontrei chamadas dessas rotas nos componentes atuais de Studios; isso limita a exposição pela UI atual, mas não torna essas APIs reais.
2. **O backend local de Studios está fora do ar.** A porta 3018 responde, mas 8000/8018 não estavam escutando. As verificações públicas de saúde do Node continuam retornando “ready” porque não verificam Studios.
3. **Geração de imagens/vídeos não foi comprovada contra fornecedores reais.** A configuração Python local lida está desativada, sem as credenciais específicas de Studios e sem orçamento de testes. A KLIC do Node, separadamente, declara Gemini 3.8 Flash configurado; isso não habilita os geradores Python.
4. **A edição canônica com FFmpeg é real.** O teste exercitou arquivo MP4 com cortes, overlay, título, animação, áudio/fade, entrega autenticada, Range, reabertura e recuperação. Não é prova de geração por IA nem de qualidade cinematográfica.
5. **Os motores Craft têm código e protocolos, mas faltam runtimes locais.** Sem binários configurados, Docker/Cargo no PATH ou os módulos WASM esperados em public/craft. As três URLs de adaptadores retornam HTML, não JavaScript.
6. **Há divergências entre intenção e execução.** Proporção de imagem entra no prompt, mas não no parâmetro nativo da API; resolução de geração fica fixada em 1K; limite de planejamento de 16.384 é reduzido a 8.192 no transporte Gemini. A crítica editorial ainda exige um job video_render, embora os renders novos sejam craft_render.
7. **Custos e quotas não formam uma contabilidade única.** O fluxo novo de imagens conta corretamente solicitações aceitas, inclusive falhas/cancelamentos. Os renders reais de vídeo não foram encontrados conciliando minutos/armazenamento com a governança. Reservas de teste não equivalem a limites financeiros em produção.
8. **Trocar o LLM sozinho não resolverá esses problemas.** Claude Opus via OpenRouter é viável para planejamento, com bastante infraestrutura reutilizável. Ele não substitui gerador de mídia, editor, fila, armazenamento ou validação audiovisual.

Recomendação: primeiro tornar a execução honesta e disponível, corrigir os contratos e o controle de gastos; depois qualificar geradores com uma bateria real e pequena de referências; só então ampliar a autonomia e comparar LLMs.

## Escopo, método e limites de evidência

Esta etapa não alterou código da aplicação, modelos, dependências, configuração persistente, banco operacional, deploy ou GitHub. Este Markdown é o artefato de diagnóstico. Build/testes produziram apenas seus artefatos locais e temporários.

Foram usadas quatro classes de evidência:

- **T — teste atual:** teste local executado nesta auditoria. Fornecedor simulado é explicitamente identificado.
- **R — runtime atual:** HTTP/portas/arquivos/configuração local observados, sem operação paga.
- **C — código:** comportamento identificado nos arquivos. Não certifica funcionamento em produção.
- **D — documentação oficial:** capacidade anunciada pelo fornecedor; não certifica acesso da conta Clicko.

A leitura de Settings reflete o ambiente do processo de diagnóstico e arquivos locais, não o ambiente secreto de um serviço remoto. Não foram lidas tabelas operacionais de clientes nem revelados segredos. Testes Python usaram SQLite/objetos descartáveis em diretório temporário, com limpeza prevista no conftest; não usaram o banco nem o armazenamento da aplicação. Os testes de IA interceptaram os transportes: não representam inferência real.

Não foram feitos testes pagos, benchmark artístico, stress test em carga, deploy, teste S3 real, uso físico de microfone ou inspeção de uma produção remota. Não se atribui percentual fictício de conclusão aos módulos.

# A. Resumo geral

| Área | Situação comprovada | Nível atual |
| --- | --- | --- |
| Interface Studios | React/TypeScript; navegação, permissões, recuperação de formulários e projetos | Implementada; depende do backend para operar |
| Imagem generativa | Solicitação durável e privada, autorização de referências e revisão testadas com gerador interceptado | Integração parcial; qualidade/acesso real não validados |
| Edição de imagem com IA | Mesmo fluxo, com original e até três referências | Contrato testado; preservação visual não certificada |
| Editor avançado de imagem | PhotoCraft integrado via adaptadores Rust/WASM | Não operacional neste ambiente sem runtime |
| Edição de vídeo canônica | Compilação própria para FFmpeg e MP4 H.264/AAC | Funcional no teste local de mídia real |
| Editor nativo / motion | FilmCraft e EffectCraft com comandos e jobs próprios | Código existente; runtime local indisponível |
| Vídeo generativo | Adaptadores Gemini/Runway; Sora bloqueado pela data do próprio código | Não comprovado com conta/saída reais; não é o fluxo padrão da tela |
| Avatar, clonagem, ASR e voz de produção | Contratos, admissão, consentimentos e adaptadores candidatos | Não habilitados como serviço completo neste checkout |
| Direção e produção autônoma | Planejamento/cenas/materiais/revisão em serviços existentes | Parcial, com rotas não expostas e contratos antigos |
| APIs antigas image-edit/video-edit | Retorno de sucesso sem transformação | Simuladas; risco de confiança e cobrança |

**Diagnóstico central:** a Clicko já contém mais ferramentas reais do que uma interface de chat com um único modelo. O problema é a distância entre interfaces, contratos, runtimes provisionados e resultados validados.

# B. Arquitetura atual

## B1. Componentes e comunicação

~~~text
Navegador React
  ├─ Studios → ImageStudio / VideoStudio / editor canônico / Craft
  │    ↓ sessão cookie + módulo + contexto do cliente + idempotência
  ├─ Express → proxy Studios + governança/cota
  │    ↓ JWT de ponte com expiração de 60 s
  └─ FastAPI app.studio_app
       ├─ documentos / assets / jobs / timeline / Craft
       ├─ SQLAlchemy → SQLite local ou PostgreSQL provisionado
       ├─ armazenamento local ou S3
       └─ execução
            ├─ local eager / executor limitado da timeline
            ├─ Celery + Redis / filas especializadas
            ├─ FFmpeg/ffprobe / adaptadores Rust
            └─ Gemini / Runway / sidecars explicitamente habilitados

Em paralelo: KLIC Node → Google GenAI / voz Google Cloud;
             APIs antigas Express → caminhos próprios, alguns simulados.
~~~

A autoridade de documentos não é o localStorage: são CreativeDocument e sua composição/estado nativo no backend. O navegador guarda preferências, formulários e identidades de recuperação. Salvar briefing não é gerar mídia.

Referências: [StudiosWorkspace](C:/Users/pedro/Downloads/res/src/studios/StudiosWorkspace.tsx:17), [seleção de módulos](C:/Users/pedro/Downloads/res/src/studios/ClickoStudioView.tsx:20), [proxy](C:/Users/pedro/Downloads/res/server/studios/proxy.ts:43), [API de ponte](C:/Users/pedro/Downloads/res/backend/app/studio_app.py:67).

## B2. Stack e persistência

- Frontend: React 19, TypeScript 5.8, Vite 6; componentes compartilhados Clicko. Npm build transforma e empacota a UI/Express, mas não compila motores Rust/WASM.
- BFF: Express 4; SDK Google GenAI; armazenamento de governança em snapshot JSON atômico neste caminho. Integrações sociais têm seu próprio repositório/driver, que não deve ser confundido com o banco audiovisual.
- Backend Studios: FastAPI 0.129, Pydantic, SQLAlchemy 2.0, Alembic, Celery 5.6/Redis, httpx, Pillow/fonttools, jsonschema, PyJWT e cryptography/Fernet.
- Bancos: Settings usa SQLite como padrão local; validação do app principal exige PostgreSQL em produção. Existem tabelas para documentos, biblioteca, jobs, ingest, transcrições, decisões de edição, motion graphs, eventos, reviews, consentimentos, identidade/voz e conexões LLM.
- Objetos: LocalObjectStorage e S3ObjectStorage. Chaves por workspace/zona; cópia imutável, checksum SHA-256, materialização temporária, download autenticado ou URL S3 assinada.
- Runtimes nativos: PhotoCraft/FilmCraft/EffectCraft. Fonte vendorizada e adaptadores Rust próprios; runner de desenvolvimento usa contêiner com rede desativada e recursos limitados.

Referências: [dependências Python](C:/Users/pedro/Downloads/res/backend/requirements.txt:1), [banco](C:/Users/pedro/Downloads/res/backend/app/database.py:13), [tabelas](C:/Users/pedro/Downloads/res/backend/app/models.py:240), [object storage](C:/Users/pedro/Downloads/res/backend/app/services/object_storage.py:81), [governança](C:/Users/pedro/Downloads/res/server/governance.ts:470), [runner Craft](C:/Users/pedro/Downloads/res/workers/craft/run_adapter.py:73).

## B3. Endpoints relevantes

Prefixo S = /api/v1/studios/v1. Todos os caminhos abaixo exigem os controles do respectivo app; não são URLs públicas de geração.

| Grupo | Métodos/caminhos | Responsabilidade e observação |
| --- | --- | --- |
| Sessão | GET S/bridge/session | Resolve identidade/workspace/cliente da ponte |
| Documentos | GET/POST S/documents; GET/PUT S/documents/{id}; versions/restore | Projetos canônicos, revisão, histórico |
| Imagem/IA | GET S/editing/ai; S/editing/gemini; S/editing/usage | Configuração declarada; não é benchmark |
| Imagem/IA | POST S/documents/{id}/editing-ai-jobs | Geração/edição ou planejamento conforme adaptador |
| Recursos | POST S/editing/resources/upload; S/documents/{id}/editing-resources; S/editing/resources/{id}/review | Upload, associação e revisão humana |
| Jobs | GET S/jobs e S/jobs/{id}; POST cancel/retry | Estado durável e recuperação |
| Timeline | GET S/video/capabilities; PUT S/video/documents/{id}/timeline; POST .../render-jobs | Edição/renderização canônica, sem projeto nativo |
| Vídeo entregue | GET S/video/library; S/video/library/{asset}/content; S/video/assets/{asset}/probe | Catálogo e MP4 autenticado |
| Craft | GET S/craft/engines; POST S/documents/{id}/craft/migrate, commands, ai-commands, preview, render-jobs | Motores e comandos nativos |
| Modelos de planejamento | GET S/craft/llm-catalog; GET/POST/PUT/DELETE S/craft/llm-connections | Conexões administradas por workspace |
| Departamento | GET/POST/PATCH S/projects; POST S/projects/{id}/produce | Direção determinística e preparação de projeto; não geração integral |
| Mídia/transcrição | S/media-ingests, S/transcripts, .../apply-captions e S/edit-decision-sets | Contratos e execução dependente de provedores |
| Geração de cenas | GET S/scene-generation-capability; POST S/documents/{id}/scene-generation-jobs | Sidecar local, experimental |
| Binário | GET /api/v1/assets/{id}/content | Arquivo privado; Range exercitado no teste local |
| Produção avançada | S/documents/{id}/production-runs, resume, revise, evidence | Está em editing_resources, mas não na whitelist montada pelo studio_app |
| Legado Express | POST /api/ai/generate-image, image-edit, video-edit | Caminho separado; os dois últimos são simulados |
| Legado Python | POST /api/ai/generate-image | Retorna 501; não confundir com o endpoint Express de mesmo nome |

**Divergência dos entrypoints:** app.main monta editing_resources completo, mas não monta studio_video. app.studio_app monta studio_video e apenas sete rotas escolhidas de editing_resources. A simples presença de uma rota no arquivo de origem não significa disponibilidade na aplicação usada pelo proxy.

Referências: [montagem da aplicação ponte](C:/Users/pedro/Downloads/res/backend/app/studio_app.py:157), [montagem do app principal](C:/Users/pedro/Downloads/res/backend/app/main.py:142), [rotas de recursos](C:/Users/pedro/Downloads/res/backend/app/routers/editing_resources.py:265), [rotas da timeline](C:/Users/pedro/Downloads/res/backend/app/routers/studio_video.py:57), [imagem Python 501](C:/Users/pedro/Downloads/res/backend/app/routers/ai.py:68).

## B4. Jobs, filas, concorrência e erros

StudioGenerationJob guarda pedido, hash/idempotência, usuário solicitante, documento, provedor, estado, tentativas, saída e erro. Eventos registram transições. A entrega valida referências e checksums antes de declarar conclusão. Estados incluem queued/running/retrying/cancel_requested/succeeded/failed/cancelled.

Há perfis control, media_cpu, speech_cpu, speech_gpu, vision_gpu e llm_gpu. Com filas isoladas, enqueue_job_task envia fila, capability e limites de tempo. Sem isolamento, usa task.delay e os limites genéricos do Celery; o padrão global é 300 s. Isso não equivale aos 1.800–7.200 s declarados nos perfis especializados.

Desenvolvimento pode usar eager. O novo render de timeline evita bloquear HTTP com ThreadPoolExecutor de dois workers e semáforo de oito vagas. Essa proteção específica não torna todos os outros caminhos eager assíncronos: geração de imagem pode continuar dentro da chamada HTTP quando delay executa localmente.

Existem controles para resultado de submissão desconhecido, cancelamento e reuso de saída; é positivo não repetir POST pago cegamente. KLIC tem retry limitado para falhas transitórias; isso é diferente de executar novamente geração de vídeo. Gemini/Runway normalizam erros e restringem destinos de download. Nenhum fallback automático de mídia foi encontrado habilitado como garantia de sucesso.

Referências: [criação/execução de jobs](C:/Users/pedro/Downloads/res/backend/app/services/studios/jobs.py:578), [despacho](C:/Users/pedro/Downloads/res/backend/app/services/studios/jobs.py:809), [Celery](C:/Users/pedro/Downloads/res/backend/app/celery_app.py:6), [perfis](C:/Users/pedro/Downloads/res/backend/app/domain/studios/execution.py:27), [executor local](C:/Users/pedro/Downloads/res/backend/app/routers/studio_video.py:116), [recuperação de submissão](C:/Users/pedro/Downloads/res/backend/app/services/studios/gemini_editing.py:1079).

## B5. Autenticação, observabilidade e deploy

O browser usa sessão Clicko. Express verifica módulo, permissão, escopo de cliente/workspace e assina uma credencial de ponte HS256 de 60 segundos; não repassa cookie nem aceita bearer arbitrário do browser como autorização Python. A ponte deriva IDs determinísticos por workspace/cliente e aplica verificações adicionais de operação.

Existem request/correlation IDs, eventos de domínio, JobAudit, logs estruturados no app principal, traces de modelo/uso e recibos de mídia. Não foi encontrada, nesse caminho, uma visão consolidada comprovada de custo real, qualidade, fila, p95, memória e SLA por geração.

O studio_app não reaproveita automaticamente o lifespan, rate limiter e logging middleware de app.main; faz create_all no startup sem chamar validate_for_startup. Isso é uma lacuna de paridade para produção, não uma exploração demonstrada. O serviço deve ficar atrás do BFF e de rede privada, com endurecimento explícito antes de exposição.

O Dockerfile raiz entrega Node/Express apenas; Python, Redis, FFmpeg e motores nativos não surgem desse build. Nenhum deploy foi validado nesta auditoria.

Referências: [JWT e escopos](C:/Users/pedro/Downloads/res/server/studios/proxy.ts:25), [startup da ponte](C:/Users/pedro/Downloads/res/backend/app/studio_app.py:132), [startup/middlewares completos](C:/Users/pedro/Downloads/res/backend/app/main.py:59), [container Node](C:/Users/pedro/Downloads/res/Dockerfile:1).

# C. Modelos utilizados e modelos apenas previstos

## C1. Integrações que podem ser selecionadas no código

| Modelo/serviço | Responsável | Função/API | Evidência operacional nesta auditoria |
| --- | --- | --- | --- |
| Gemini 3.8 Flash | Google | KLIC Node: SDK Google GenAI, texto/conversa; também default de planejamento em Studios | GET /api/capabilities declara Node configurado; nenhuma inferência chamada. Python Studios desativado |
| Gemini 2.5 Flash | Google | Default de chat caso KLIC_CHAT_MODEL não seja definido | Default de código, não modelo declarado pelo processo Node atual |
| Gemini 3.5 Flash | Google | Default independente para transcrição KLIC; override KLIC_TRANSCRIPTION_MODEL | Código; modelo efetivo de transcrição/qualidade não testados |
| gemini-3.1-flash-lite-image | Google | Imagem/edição: generateContent; também rota antiga Node | Default Python; transporte offline testado; inferência real não validada |
| gemini-3.1-flash-image | Google | Alternativa permitida para imagem no Settings | Opção de configuração; não foi selecionada/testada |
| gemini-omni-1.1-flash | Google | Default de vídeo, API Interactions | Adaptador presente; desativado localmente |
| veo-3.1-lite-generate-preview / veo-3.1-fast-generate-preview | Google | Texto→vídeo em predictLongRunning e polling | Adaptadores; sem chamada real. Implementação limita a 4/6/8 s, 9:16 e 720p, sem referências |
| gen4.5 / aleph2 | Runway | Texto/imagem→vídeo e vídeo→vídeo, API nativa /tasks | Código de transporte; chave/flag locais ausentes; pending_real_media_validation |
| sora-2 | OpenAI | /videos, geração curta de 4 s | O próprio código bloqueia a partir de 24/09/2026; indisponível na data desta auditoria por esse gate |
| Endpoint “compatible” | Empresa depende do endpoint/modelo configurado | Planejamento JSON via Chat Completions; não gera mídia | Sem binding local operacional comprovado |
| LLMConnection / UniversalLLMPlanner | Empresa depende da conexão | Chat Completions, Responses, Claude Messages, Gemini, Cohere, Ollama ou custom JSON | 20 testes de contrato passaram com transportes/runtimes interceptados; sem inferência real |
| pt-BR-Chirp3-HD-Charon / Kore | Google Cloud | Voz da conversa KLIC, Cloud Text-to-Speech | Código separado de narração para filmes; chamada e faturamento não testados |

Integrações: [configuração de modelos Studios](C:/Users/pedro/Downloads/res/backend/app/config.py:89), [configuração KLIC](C:/Users/pedro/Downloads/res/server/klic/providerConfig.ts:1), [Gemini](C:/Users/pedro/Downloads/res/backend/app/providers/studios/gemini_editing.py:14), [Runway](C:/Users/pedro/Downloads/res/backend/app/providers/studios/runway_editing.py:19), [bloqueio Sora](C:/Users/pedro/Downloads/res/backend/app/providers/studios/openai_video.py:62), [LLM universal](C:/Users/pedro/Downloads/res/backend/app/providers/studios/universal_llm.py:84), [vozes KLIC](C:/Users/pedro/Downloads/res/server/voice/config.ts:1).

O Settings também permite Gemini 3.5/3.6/3.7 Flash para planejamento. São alternativas declaradas, não três modelos rodando simultaneamente. Os nomes oficiais principais Google/Runway foram conferidos em suas documentações; visibilidade e autorização da conta continuam pendentes. [Modelos Gemini](https://ai.google.dev/gemini-api/docs/models), [modelos Runway](https://docs.dev.runwayml.com/guides/models/).

## C2. Catálogo não é integração operacional

O llm_catalog sugere modelos de OpenAI, Anthropic, Google, Mistral, DeepSeek, xAI, Cohere, Groq, Together, Fireworks, OpenRouter e Ollama. Exemplos cadastrados: GPT-6.1 Sol/GPT-6 Astra/GPT-6 Luna; Claude Sonnet/Opus/Haiku 5.5 e Fable 5.1; Mistral Large 4/Small 2603; DeepSeek Flash/V4 Pro; Grok 4.7; Command A+; GPT-OSS; Qwen; Kimi e GLM.

Esses itens são **sugestões de seleção**. O catálogo não comprova credencial, saldo, licença da Clicko, endpoint acessível, suporte a JSON/mídia nem benchmark. O próprio retorno usa qualification pending. Modelos hospedados por Groq/Together/Fireworks não foram todos requalificados documentalmente nesta etapa; seus nomes acima reproduzem o código, não atestam disponibilidade comercial.

Credenciais de conexões são criptografadas e vinculadas a workspace, conexão, endpoint e protocolo. Só Owner/Admin pode gerenciar. A ausência local da chave mestra de criptografia impede cadastrar conexões com segredo de forma operacional nessa instalação sem provisionamento posterior.

Referências: [catálogo](C:/Users/pedro/Downloads/res/backend/app/providers/studios/llm_catalog.py:17), [gestão e criptografia](C:/Users/pedro/Downloads/res/backend/app/services/studios/llm_connections.py:39), [seletor na UI](C:/Users/pedro/Downloads/res/src/studios/craft/CraftModelPicker.tsx:21).

## C3. Candidatos/contratos de pesquisa, não serviços prontos

- Kokoro-82M (repo hexgrad/Kokoro-82M): adaptador stock pt-BR offline, vozes permitidas e manifests/digests. Pacote kokoro ausente no Python examinado; SPEECH_PROVIDERS inicia vazio.
- WhisperX/ASR: contrato, jobs e validação temporal; TRANSCRIPTION_PROVIDERS inicia vazio. Não há serviço de transcrição de vídeo automaticamente habilitado.
- Chatterbox multilingual/OpenVoice V2/Kokoro+OpenVoice: interfaces de sidecar candidato para clonagem; exigem manifests, consentimento, custo e promoção. Não são a voz já operacional de uma produção.
- LongCat-Video-Avatar-1.5 (repo meituan-longcat): adaptador loopback e perfil experimental, com limites de segmentos; serviço/flag locais ausentes.
- AnimateDiff-Lightning/SD1.5 e Wan2.1: perfis curtos de geração local; o diretório workers/media-generation-local referenciado não existe neste checkout. Não há torch/diffusers no Python examinado.
- Wan2.2, MuseTalk e LatentSync: entradas de capabilities/hybrid com blockers, não motores aprovados em execução. O código classifica alguns usos como indisponíveis/condicionais/rejeitados.
- SmolVLM-500M-Instruct (repo HuggingFaceTB): inspeção visual local; exige worker em diretório ausente e Python específico.
- U2NetP via rembg: remoção local de fundo com modelo/checksum fixos; desabilitada, pacote ausente no Python examinado.
- Supervision/detector, OpenCV e análise acústica: adapters e contratos especializados; não equivalem a detecção/ASR validados em toda produção.
- Higgsfield: transporte para Kling/Ideogram com quote e submissão desligada por padrão; não registrado como gerador funcional do fluxo ImageStudio/VideoStudio.
- Qwen self-hosted: há adapter/probe, mas llm_tasks declara explicitamente não registrar uma tarefa de inferência Qwen/Kimi.

Os autores/empresas de cada candidato devem ser confirmados no inventário de licenças de sua futura implantação; não atribuo fornecedor comercial operacional a um nome de pesquisa não provisionado.

Referências: [registries vazios](C:/Users/pedro/Downloads/res/backend/app/domain/studios/providers.py:495), [Kokoro](C:/Users/pedro/Downloads/res/backend/app/providers/studios/kokoro_stock.py:28), [clonagem](C:/Users/pedro/Downloads/res/backend/app/providers/studios/voice_clone_sidecar.py:31), [perfis híbridos](C:/Users/pedro/Downloads/res/backend/app/services/studios/hybrid_video.py:36), [difusão local](C:/Users/pedro/Downloads/res/backend/app/providers/studios/local_diffusion.py:16), [SmolVLM](C:/Users/pedro/Downloads/res/backend/app/services/studios/local_material_inspection.py:17), [Higgsfield](C:/Users/pedro/Downloads/res/backend/app/providers/studios/higgsfield.py:1), [LLM worker](C:/Users/pedro/Downloads/res/backend/app/llm_tasks.py:13).

## C4. Erros, fallbacks e adequação do LLM

- KLIC diferencia falhas de configuração, autenticação, quota, modelo, timeout e saída vazia; retry transitório tem limite. Não há prova de qualidade audiovisual apenas porque a conversa responde.
- Gemini/Runway mantêm identidade do job, resposta/operation ID, checksums e revisão. Submissão paga de resultado desconhecido exige conciliação.
- compatible é planejador, não gerador. UniversalLLMPlanner rejeita mídia binária: enxerga JSON de inspeção/comandos/manifesto, não o vídeo inteiro.
- Planejamento editorial Gemini pode receber imagens/amostras. Há limite de 24 clipes amostrados e registro explícito notFullVideoAnalysis; isso não é percepção audiovisual integral.
- Não foi encontrado fallback remoto pago automático garantido. É correto não trocar provedor silenciosamente quando isso alteraria custo, identidade ou direitos.

O LLM pode propor comandos válidos e estruturar cenas, mas só controla as ferramentas disponibilizadas. Se o projeto usa a timeline canônica, o controle assistido da tela atual não foi conectado a esse executor: a seção de IA é exibida apenas quando existe nativeEditorState. Trocar Gemini por Claude melhora potencialmente a direção, mas não cria ferramentas ausentes.

# D. Sistema de vídeos

## D1. Fluxo real da tela

1. O usuário escolhe tipo, proporção, duração planejada, público/objetivo/roteiro e materiais.
2. “Salvar e continuar” cria/atualiza documento e abre o editor. Não chama um gerador de filmagem.
3. Projeto canônico sem nativeEditorState abre CanonicalVideoEditor; projeto nativo abre VideoEditor/Craft.
4. Edição canônica envia PUT da timeline com expectedRevision e Idempotency-Key. Backend valida faixas, mídias, limites e identidade.
5. Render envia snapshot imutável para job timeline_render; FFmpeg produz MP4; ffprobe confere duração/streams/dimensões; biblioteca recebe asset com checksum.
6. O usuário reproduz/baixa o arquivo confirmado. A prévia canônica é o mesmo MP4 do render, não um compositor de efeitos em tempo real.
7. No caminho Craft, comandos/migração/render passam pelo motor nativo. IA de montagem só aparece no projeto nativo e exige runtime/conexão disponíveis.

Referências: [salvar briefing](C:/Users/pedro/Downloads/res/src/studios/video/VideoStudio.tsx:318), [IA nativa](C:/Users/pedro/Downloads/res/src/studios/video/VideoStudio.tsx:477), [escolha de editor](C:/Users/pedro/Downloads/res/src/studios/video/VideoStudio.tsx:1224), [timeline backend](C:/Users/pedro/Downloads/res/backend/app/services/studios/timeline_editor.py:84), [compilador](C:/Users/pedro/Downloads/res/backend/app/providers/studios/timeline_ffmpeg.py:140).

## D2. Edição, renderização e limites comprovados

O compilador canônico implementa cortes via source ranges/trim, posicionamento temporal, sobreposição, ajuste de enquadramento sem distorcer, escala, deslocamento X/Y, opacidade, rotação estática, velocidade e fades. Keyframes de X/Y/escala/opacidade são lineares. Dissolve exige sobreposição/fades; não existe catálogo irrestrito de transições.

Áudio: trilhas reais, áudio dos clipes, resample, ganho em dB, atempo, delay, fade e mixagem com limitador. Se não há fonte, uma trilha técnica de silêncio pode acompanhar o MP4; isso não é música/narração gerada. Não há masterização universal certificada nem sincronização semântica automática comprovada.

Texto/legendas: cues com tempos em frames; Pillow rasteriza texto em PNG com alfa, que FFmpeg compõe. Existe serviço de transcrições com segmentos/timestamps e apply-captions. ASR automático exige provedor qualificado inexistente no registry padrão. O retorno “subtitlesGenerated:true” da API antiga não representa esse mecanismo.

Limites canônicos validados no código:

- Até 600 segundos, 16 faixas e 32 itens; até 60 fps.
- Dimensões pares, de 320 a 1920 em cada eixo; não 4K de saída.
- Até 32 keyframes por item, com parâmetros específicos.
- Soma de mídias referenciadas até 1 GiB; fontes de vídeo acima de 3840×2160 são rejeitadas.
- Saída MP4, H.264, AAC, YUV420p, faststart; bitrate fixo de vídeo 6 Mbit/s e áudio 192 kbit/s no compilador.
- Não suporta filtros arbitrários, pan, máscaras avançadas, speed ramp, rotoscopia, tracking ou curvas Bézier nesse caminho. Projetos Craft não são editados por esse compilador.

Dez minutos é um limite de admissão, **não benchmark de um render de dez minutos**. O teste real desta auditoria foi curto, com saída de aproximadamente dois segundos. Não se comprovou produtividade em longas-metragens nem em lotes concorrentes.

Referências: [limites](C:/Users/pedro/Downloads/res/backend/app/services/studios/timeline_editor.py:28), [filtros e export](C:/Users/pedro/Downloads/res/backend/app/providers/studios/timeline_ffmpeg.py:140), [legendas de transcrição](C:/Users/pedro/Downloads/res/backend/app/services/studios/transcripts.py:631), [teste real](C:/Users/pedro/Downloads/res/backend/tests/test_video_timeline_real.py:116).

## D3. Geração por IA, cenas, referências e estilo

Existe geração de vídeo por IA no código, não apenas edição. Mas não é uma geração integral habilitada e validada pela tela atual:

- Gemini Omni usa Interactions com entrada multimodal, prompt de tomada contínua e duração textual; sem manter contexto de conversa/previous_interaction_id nesse adaptador. A duração deve ser conferida depois; pedir em texto não obriga o fornecedor a obedecer.
- Veo no adapter atual aceita apenas texto sem referência, 4/6/8 s, 9:16, 720p. O manifest híbrido anuncia image_to_video, mas o transporte rejeita media: há desalinhamento de capacidade.
- Runway gen4.5 aceita texto ou uma imagem; Aleph2 exige um vídeo e permite uma referência de imagem. Inputs inline ficam abaixo de 3,7 MB; maiores exigem um upload adapter ainda ausente nessa implementação. Duração é limitada a 2–10 s, mais restrita que a capacidade atual de alguns modelos.
- Sora é caminho legado bloqueado por data; não é opção ativa a restaurar automaticamente.
- Difusão local tem perfis de aproximadamente 1–2 s e exige worker/modelos/hardware não presentes.
- O vídeo gerado vira candidato; não é automaticamente uma montagem final com narrativa completa. Revisão/seleção, áudio, composição e entrega são etapas diferentes.

Há contratos de storyboard, beats, direção cinematográfica, aquisição/inspeção de materiais e composição semântica. Isso permite decomposição planejada em cenas, mas não prova segmentação automática confiável de qualquer vídeo nem coerência de personagem/estilo entre todas as gerações. Amostragem visual parcial e referências com limite de tamanho reduzem a compreensão de movimento/ritmo.

O Departamento Criativo usa direções determinísticas: registra “esboço sem geração por LLM”; para vídeo exige material da biblioteca, importa-o no FilmCraft e agenda export. Não é um diretor generativo completo.

Referências: [transporte Gemini](C:/Users/pedro/Downloads/res/backend/app/providers/studios/gemini_editing.py:117), [limites Runway](C:/Users/pedro/Downloads/res/backend/app/providers/studios/runway_editing.py:74), [geração local](C:/Users/pedro/Downloads/res/backend/app/domain/studios/scene_generation.py:16), [Departamento](C:/Users/pedro/Downloads/res/backend/app/routers/studio_department.py:154), [produção do Departamento](C:/Users/pedro/Downloads/res/backend/app/routers/studio_department.py:331).

A documentação oficial distingue geração/edição multimodal Omni da execução de um editor. A implementação Clicko usa parte dessa capacidade, não toda a experiência descrita pelo fornecedor. [Gemini Omni](https://ai.google.dev/gemini-api/docs/omni). Os limites nativos de Runway também não devem ser confundidos com os limites mais estreitos do adapter Clicko. [Inputs Runway](https://docs.dev.runwayml.com/assets/inputs/).

## D4. Problemas que afetam qualidade de vídeo

- Motores, backend e workers ausentes impedem execução antes de discutir inteligência do LLM.
- A crítica editorial rejeita craft_render por esperar video_render; corrigir o plano não resolve esse contrato.
- Algumas fases de produção só existem no app principal e não estão expostas no app de ponte.
- Edit_video usa ffmpeg no PATH e libx264 fixo; o caminho canônico acha um build local com libopenh264. Uma configuração que renderiza canônico não garante que edite vídeo generativo.
- Não há inferência/benchmark temporal atual que comprove ausência de flicker, anatomia correta, identidade, naturalidade do movimento ou qualidade sonora.
- Sem pipeline completo de ASR/alinhamento/TTS qualificado, legendas automáticas e fala por cena não estão prontas só porque existem campos na UI.
- Roteiro e prompts da UI são curtos; planejamento detalhado tem contratos extensos e teto de resposta menor no transporte, aumentando truncamento/correções.
- A prévia exige render; não é equivalente à edição audiovisual interativa de uma ferramenta profissional.

# E. Sistema de imagens

## E1. Fluxo de geração e edição

1. ImageStudio coleta descrição, finalidade, estilo, proporção, instruções adicionais/preservação e contexto de marca opcional.
2. Cria/atualiza CreativeDocument, sem destruir composição ou estado nativo preexistente.
3. Original e referências são assets privados, com checksum e escopo. O usuário confirma direitos e envio ao provedor; material gerado não revisado não pode ser reutilizado livremente.
4. Guarda identidade exata do pedido antes da submissão, permitindo reconciliar falhas de transporte sem gerar outro consumo.
5. POST editing-ai-jobs passa pela reserva de uma unidade comercial no Express. FastAPI cria job vinculado à revisão/checksums.
6. Gemini recebe prompt+imagens inline, retorna mídia; o resultado é armazenado como asset imutável.
7. Existe verificação visual automática, mas machine_passed é deliberadamente falso até qualificação: o asset fica candidate_pending_review.
8. O usuário revisa e anexa o resultado. Download usa asset real, não uma URL de exemplo.

Esse fluxo passou em testes de contrato com imagens PNG reais no storage, **mas a resposta do gerador foi fabricada pelo teste**. Portanto foram comprovados persistência, privacidade, estados e revisão, não qualidade generativa ou consistência de produto.

Referências: [submissão frontend](C:/Users/pedro/Downloads/res/src/studios/image/ImageStudio.tsx:496), [API imagem](C:/Users/pedro/Downloads/res/src/studios/image/imageApi.ts:74), [pedido](C:/Users/pedro/Downloads/res/src/studios/image/imageModel.ts:237), [execução](C:/Users/pedro/Downloads/res/backend/app/services/studios/gemini_editing.py:1034), [política de review](C:/Users/pedro/Downloads/res/backend/app/services/studios/gemini_editing.py:2361).

## E2. Referências, preservação, resolução e qualidade

- Upload no frontend: PNG/JPEG/WebP, até 12 MB. Endpoint genérico de recursos aceita até 100 MB; o provider inline tem seu próprio limite de 20 MB por arquivo. Limites variam conforme a rota.
- Até três referências, além do original da edição. São enviadas como imagens, não apenas nomes de arquivo.
- O prompt compõe finalidade/estilo/proporção/preservação/marca; não há LoRA, treinamento de identidade ou mecanismo determinístico de travamento de personagem/produto nesse caminho.
- Preservar rosto, logo ou embalagem é uma instrução e uma revisão, não uma garantia geométrica/pixel a pixel. Use materiais oficiais em camada quando a fidelidade exata for obrigatória.
- A UI cria canvas 1080×1080, 1080×1350, 1080×1920 ou 1920×1080. **Essas dimensões de documento não são a resolução entregue pelo gerador.**
- O adapter Gemini fixa imageSize em 1K e não envia aspectRatio. A escolha 9:16 aparece apenas no prompt. Um teste de transporte offline confirmou esse payload.
- Não há opção nativa propagada para 2K/4K, qualidade, seed, batch de variações ou múltiplos geradores nessa API pública específica.
- O modelo Lite é voltado a velocidade/custo/1K. A documentação oficial não o caracteriza como a escolha de maior consistência para múltiplas referências ou edições sequenciais. Isso é limitação potencial do gerador, não prova de que o LLM de chat seja fraco. [Modelo Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-image), [família de geração de imagens](https://ai.google.dev/gemini-api/docs/generate-content/image-generation).

## E3. Edição avançada e multi-modelo

PhotoCraft reutiliza composição nativa, camadas, comandos, histórico, prévia e export. Módulos WASM no navegador e adaptador Rust no backend são previstos; nenhum deles foi confirmado operacional neste ambiente. O endpoint antigo /assets/{id}/derive retorna 410 por substituição pelo PhotoCraft: os dois testes antigos que ainda esperam derivação falham por esse motivo.

A arquitetura tem uma boa separação por adapters/operations, mas **não permite trocar livremente gerador de imagem pelo seletor LLM**. Hoje o papel image aceita apenas none/gemini e os IDs de imagem são limitados pelo Settings. Integrar outro gerador é viável preservando jobs/assets/reviews, mas exige adapter, contrato de capacidades/custos/erros, parâmetros e qualificação próprios.

Higgsfield/Ideogram é transporte isolado; sua existência não torna ImageStudio multi-provider operacional.

Referências: [PhotoCraft](C:/Users/pedro/Downloads/res/backend/app/providers/studios/craft.py:83), [WASM](C:/Users/pedro/Downloads/res/src/studios/craft/craft.worker.ts:31), [rota aposentada](C:/Users/pedro/Downloads/res/backend/app/routers/assets.py:336), [providers por papel](C:/Users/pedro/Downloads/res/backend/app/providers/studios/editing_ai.py:126), [Settings imagem](C:/Users/pedro/Downloads/res/backend/app/config.py:45).

# F. Problemas encontrados, gravidade, causa e impacto

Gravidade: Crítica = resultado falso/cobrança indevida potencial; Alta = bloqueia funcionalidade ou controle financeiro/segurança; Média = limita qualidade, manutenção ou capacidade. “Alta” não significa exploração de segurança comprovada.

| ID | Gravidade | Evidência / causa | Impacto e recomendação diagnóstica |
| --- | --- | --- | --- |
| F01 | Crítica | T/C: server.ts image-edit/video-edit retornam sucesso sem processar; handler isolado reproduziu isso e a dedução de cota | Resultado falso e consumo sem serviço. Retirar da superfície operacional ou fazer falhar explicitamente numa etapa autorizada; nunca mantê-las como edição real |
| F02 | Alta | R: 3018 ativa; 8000/8018 sem listener; GET /api/ready ainda 200 | Studios indisponível mascarado por saúde do BFF. Readiness deve acompanhar dependências necessárias |
| F03 | Alta | R/C: adapters nativos sem binário/Docker e /craft/...js retorna HTML 200 nas três variantes; arquivos WASM ausentes | Editor avançado/motion não executam. Provisionamento e smoke tests de runtime precisam preceder promessa de capacidade |
| F04 | Alta | C: editorial_production cria craft_render; gemini_editing exige job_type video_render na crítica | Laço autônomo de validação bloqueado mesmo após render correto. Unificar contrato sem afrouxar revisão |
| F05 | Alta | C: studio_app limita editing_resources; main não inclui studio_video | Recursos dependem do entrypoint usado. Definir/montar superfície canônica e testes de rotas do app de produção |
| F06 | Alta | C/R: geradores Python desativados, credenciais/sidecars ausentes; registries de fala/transcrição vazios | Geração, narrador, avatar e ASR não são serviços prontos nessa instalação |
| F07 | Alta | C: reserve_test_request retorna imediatamente em production; budget_remaining retorna infinito; status usage productionLimit=None | Há controle de teste, mas não teto financeiro equivalente para todo fluxo de produção. Precisam ledger, reserva/reconciliação e limites explícitos |
| F08 | Alta | C: admissão/execução direta Gemini de vídeo verifica studio_gemini_enabled/key, mas não GEMINI_VIDEO_GENERATION_ENABLED/GEMINI_OUTBOUND_ENABLED nem cap externo específico | Habilitar imagem Gemini pode deixar vídeo direto elegível se houver permissão de vídeo. Manifest híbrido não protege automaticamente essa rota; gate central antes de qualquer submissão |
| F09 | Alta | C: renders reais não encontrados consumindo video_minutes/storage_bytes; legado vídeo cobra minutos enviados pelo cliente | Divergência comercial, margem e abuso de recursos. Medir/conciliar nos jobs e definir evento faturável |
| F10 | Média/alta | T/C: imageConfig só 1K, sem aspectRatio, enquanto UI apresenta proporções e canvas maiores | Enquadramento/resolução não garantidos. Propagar capacidades/parâmetros e conferir saída real |
| F11 | Média/alta | C/D: Lite orientado à eficiência; preservação é prompt+revisão | Não garantir personagem/produto idêntico. Benchmark com referência e composição determinística de marca |
| F12 | Média/alta | T/C: pedido maxOutputTokens=16.384 vira 8.192 no adapter Gemini | Truncamento de planos extensos e retrabalho. Alinhar limite efetivo e dividir planejamento por etapas |
| F13 | Média/alta | C/R: edit_video fixa libx264 e FFmpeg do Settings; canônico usa libopenh264 encontrado fora do PATH | Render canônico funcionar não implica edição generativa funcionar. Resolver capacidade de codec/caminho por perfil |
| F14 | Média | C: status/ADAPTERS anuncia generate/edit video amplos; Veo rejeita referências e só aceita 4/6/8 s; manifest anuncia image_to_video | Descoberta de capacidade diverge do transporte. Contrato deve depender do modelo+operação, não só da marca |
| F15 | Média | C: IA da tela só aparece em nativeEditorState; UniversalLLMPlanner não recebe mídia | Troca de LLM não automatiza editor canônico nem dá percepção do filme. Precisam tools/observações específicas |
| F16 | Média | T/C: 2 testes /derive falham por HTTP 410; 1 teste adicional espera markup antigo em App; Ruff acusa 80 problemas; suíte npm não inclui tests/unit | Contratos/testes defasados e cobertura fragmentada. Não declarar CI toda verde só pelo npm test |
| F17 | Média/alta | C: eager pode prender HTTP em image job; proxy aborta em 180 s; sem filas isoladas Celery usa 300 s global | Timeouts e jobs sem resultado visível; filas reais, recibo rápido e limites coerentes |
| F18 | Média | C/R: workers/benchmarks referenciados ausentes; pacotes GPU/ASR não instalados no ambiente examinado | Aprovação/provisão incompletas; mais nomes de pesquisa não resolvem falta de artefatos e evidência |
| F19 | Média | C: loops de custo/recibos/biblioteca fazem leituras amplas; amostras/inline base64 e PNG por título; apenas CPU canônica | Custo cresce com histórico/mídia; risco de latência/RAM. Ainda precisa medição, paginação/índices e limites por recurso |
| F20 | Alta condicional | C: studio_app não chama validação de startup nem reaproveita rate limiter/log estruturado do app principal | Endurecimento depende da topologia privada; corrigir paridade antes de produção exposta |
| F21 | Média | C: /api/ai/generate-image Node tem cota só após sucesso e texto que afirma fallback de estúdio sem retornar imagem | Regra comercial/status divergente do novo fluxo. Não confundir erro com fallback efetivo |

### Evidências diretas dos achados mais importantes

- F01: [imagem simulada](C:/Users/pedro/Downloads/res/server.ts:706), [vídeo simulado](C:/Users/pedro/Downloads/res/server.ts:720). Nenhum POST real foi enviado: os callbacks foram extraídos da AST e executados isoladamente com autorização/consumo interceptados.
- F04: [render novo](C:/Users/pedro/Downloads/res/backend/app/services/studios/editorial_production.py:1054), [crítica antiga](C:/Users/pedro/Downloads/res/backend/app/services/studios/gemini_editing.py:1095), [executor rejeita video_render legado](C:/Users/pedro/Downloads/res/backend/app/services/studios/jobs.py:982).
- F07/F08: [reserva só fora de produção](C:/Users/pedro/Downloads/res/backend/app/services/studios/gemini_editing.py:813), [binding/admissão](C:/Users/pedro/Downloads/res/backend/app/services/studios/gemini_editing.py:506), [status/enqueue direto](C:/Users/pedro/Downloads/res/backend/app/routers/editing_resources.py:265).
- F09/F21: [quota nova](C:/Users/pedro/Downloads/res/server/studios/imageQuota.ts:20), [dedução legada](C:/Users/pedro/Downloads/res/server.ts:601), [minutos de vídeo legados](C:/Users/pedro/Downloads/res/server.ts:720).
- F10/F12: [payloads nativos](C:/Users/pedro/Downloads/res/backend/app/providers/studios/gemini_editing.py:92).
- F17/F20: [timeout proxy](C:/Users/pedro/Downloads/res/server/studios/proxy.ts:105), [limite Celery](C:/Users/pedro/Downloads/res/backend/app/celery_app.py:17), [startup ponte](C:/Users/pedro/Downloads/res/backend/app/studio_app.py:132).

## F1. Duplicidade, dependências e manutenção

Há três transportes de planejamento Python com responsabilidades parcialmente sobrepostas: OpenAICompatibleProvider genérico, CompatibleEditingPlanner editorial e UniversalLLMPlanner nativo; KLIC Node ainda usa seu SDK separado. Também coexistem /editing-gemini-jobs e /editing-ai-jobs, imagem Express/Python, render legado/Craft/timeline e múltiplas representações de capabilities.

Não recomendo apagar tudo: a duplicidade precisa primeiro ser classificada como contrato público, compatibilidade de documentos ou experimento aposentado. O armazenamento histórico e a migração nativa devem ser preservados.

O package.json não traz Three.js/Remotion para gerar vídeo no navegador. FFmpeg e fontes Craft são recursos externos ao bundle. Arquivos aposentados de Remotion/Motion Canvas/Alight no repo não os tornam editores executáveis: vários flags são forçados a false e o registry antigo de renderer está vazio. Não há base para instalar outra stack pesada antes de consertar os caminhos existentes.

## F2. Resultados dos testes atuais

| Teste/verificação | Resultado | O que comprova / o que não comprova |
| --- | --- | --- |
| npm test, concorrência 2 | 223 + 2 = 225 aprovados; zero falhas | Modelos de frontend, governança, cota, proxy, segurança/contratos; fornecedores interceptados não validam IA real |
| node --import tsx --test tests/unit/craftState.test.ts | 6 aprovados, 1 falha | O teste na linha 69 espera ClickoStudioView diretamente em App.tsx, anterior à unificação em StudiosWorkspace. Falha de expectativa estrutural; não prova, sozinha, defeito funcional de navegação |
| npm run lint | Aprovado | Script executa tsc --noEmit; não é lint completo de estilo |
| npm run build | Aprovado; Vite + dois bundles esbuild | Compilação React/Express; não compila Rust nem provisiona backend/Redis |
| pytest em 6 arquivos de ponte/imagem/vídeo/timeline/LLM/derive | 37 coletados: 35 aprovados, 2 falhas | Contratos e um fluxo FFmpeg real; falhas exclusivamente /derive aposentado |
| test_video_timeline_real.py | 4 aprovados dentro do recorte | Revisão/isolamento/restart e render real curto com pixels/áudio/MP4/download/replay |
| test_image_frontend_contract.py | 5 aprovados dentro do recorte | Uploads/storage/privacidade/idempotência/review com PNG; Gemini substituído por função de teste |
| test_studio_llm_connections.py | 20 aprovados dentro do recorte | Protocolos, segredo criptografado, permissões, reserva e comandos; runtime nativo/fornecedor interceptados |
| Ruff backend/app | 80 ocorrências: 67 E501, 11 I001, 1 B905, 1 UP037 | Qualidade estática pendente; não 80 falhas de geração |
| Transporte Gemini offline com httpx.MockTransport | Confirmado 1K sem aspectRatio; cap 16.384→8.192 | Payload exato do adapter; zero inferência/rede externa |
| Handlers Express legados em VM isolada | Sucesso com mídia inalterada, legendas/silêncio constantes e chamada de quota | Simulação comprovada sem alterar governança operacional |
| HTTP local /api/health, /api/ready, /api/capabilities | 200; KLIC Node declara gemini-3.8-flash configurado | Saúde Node/configuração declarada; não saúde Studios nem resposta do modelo |
| Portas locais | 3018 ativa; 8000/8018/6379/8094/8095 sem listener | Snapshot local, não inventário de infraestrutura remota |
| URLs /craft/{engine}/clicko_{engine}_adapter.js | 3 respostas 200 text/html | Fallback SPA em vez de módulo; não disponibilidade WASM |
| ffmpeg.timeline-v1 capability | Disponível; FFmpeg n9.0.2-28, libopenh264, AAC, LGPL-3.0-or-later | Binário local encontrado pelo compilador; FFmpeg/ffprobe não estão no PATH global |
| Hash de fontes/configurações auditadas | 608 arquivos, zero modificações entre snapshots | Código preservado; este relatório é novo artefato |

Comando Python executado:

~~~powershell
$env:PYTHONPATH='backend'
$env:GEMINI_OUTBOUND_ENABLED='false'
$env:GEMINI_VIDEO_GENERATION_ENABLED='false'
$env:STUDIO_GEMINI_ENABLED='false'
.venv\Scripts\python.exe -m pytest -q backend/tests/test_clicko_studio_bridge.py backend/tests/test_image_frontend_contract.py backend/tests/test_video_frontend_contract.py backend/tests/test_video_timeline_real.py backend/tests/test_studio_llm_connections.py backend/tests/test_image_derivation.py
~~~

Os seis arquivos foram novamente coletados para confirmar contagens. Não foi reexecutada nesta auditoria a suíte Python inteira, os testes Rust/WASM ou todos os testes de pesquisa que exigem fixtures/modelos ausentes. Não se declara “todo o backend aprovado”. Tampouco houve QA visual de geração real em navegador, pois esse serviço estava offline.

Referências: [isolamento de testes](C:/Users/pedro/Downloads/res/backend/tests/conftest.py:12), [cenário de mídia real](C:/Users/pedro/Downloads/res/backend/tests/test_video_timeline_real.py:116), [gerador interceptado](C:/Users/pedro/Downloads/res/backend/tests/test_image_frontend_contract.py:50), [escopo de npm test](C:/Users/pedro/Downloads/res/scripts/run-audit-tests.cjs:9).

# G. O que pode ser aproveitado

1. UI/rotas unificadas Studios, componentes Clicko, permissões e recuperação por usuário/workspace.
2. CreativeDocument, revisão otimista, snapshots/versões e estado nativo: não reconstruir persistência.
3. Biblioteca privada e ObjectStorage com checksum/proveniência. Preservar links antigos e migrações.
4. Jobs duráveis/idempotência, cancelamento, recibos e política de não repetir submissão incerta.
5. Compilador FFmpeg canônico, validadores técnicos e prova com mídia real.
6. Adaptadores e fontes Craft fixadas em sources.lock, sem substituir silenciosamente documentos nativos.
7. Gestão LLM, criptografia e controle Owner/Admin, seletor já implementado para comandos nativos.
8. Contratos de roteiro/cenas/materiais, consentimento e review humano.
9. Quota nova de imagem: regra de uma solicitação aceita, falha ou cancelamento conta; replay/retry do mesmo job não duplica.
10. Princípio fail-closed: não aprovar identidade, voz, licença ou qualidade apenas porque um LLM produziu texto convincente.

Linhagem dos motores: PhotoCraft 0.7.0 (a7f26522...), FilmCraft 0.6.0 (0800a8b0...), EffectCraft 0.8.0 (67434e90...), via fontes vendorizadas e adaptadores próprios. Os manifests Cargo principais declaram MIT OR Apache-2.0; dependências, codecs, modelos e eventual redistribuição exigem inventário completo, não uma licença presumida para tudo.

Referência: [linhagem fixada](C:/Users/pedro/Downloads/res/workers/craft/sources.lock.json:1). Esta auditoria não baixou nem substituiu fontes externas.

# H. O que precisa ser melhorado

## H1. Produto e verdade operacional

- Uma resposta de sucesso deve apontar para mídia realmente produzida e validada.
- Exibir separadamente: briefing salvo, job aceito, processamento, candidato, revisão e export final.
- Capabilities devem considerar entrypoint, runtime, modelo/conta, licenças, parâmetros e medição recente.
- Tela de vídeo deve dizer claramente se é montagem de material ou geração de tomadas novas.
- API legada precisa de política explícita de desativação/compatibilidade, sem renovar simulação.

## H2. Qualidade artística e validação

- Construir conjunto de referência autorizado com produto, personagem, tipografia, cenas em movimento e áudio pt-BR.
- Medir aderência ao briefing, identidade, texto, enquadramento, continuidade temporal, flicker, sincronia, duração e qualidade técnica.
- Preservar logo/embalagem oficiais como ativos de composição quando a exigência é exatidão, não confiar só em prompt.
- Não chamar uma nota do próprio modelo de certificado de qualidade. Manter review e comparar artefatos reais.
- Separar roteiro, direção por cena e compilação de operações; evitar um único JSON enorme.
- Corrigir pipeline/contratos antes de atribuir todo fracasso ao LLM.

## H3. Custos operacionais e contabilidade

Há custos potenciais de tokens de planejamento/crítica/transcrição, geração de mídia, voz Cloud TTS, CPU/GPU de render/modelos locais, armazenamento, tráfego/egress, Redis/PostgreSQL, observabilidade e backups. “Modelo local” não significa custo zero; billingMode local_free só significa que esse binding não cobra tokens de uma API externa.

O que existe:

- Quota comercial image_generations por workspace/membro/periodicidade, com recibos persistidos.
- Por job: modelo/provedor, usuário solicitante, uso retornado, outputImages/outputVideoSeconds, storageBytes, processingSeconds e reservas de teste em vários caminhos.
- Planejamento: tarifas configuráveis e cálculo de token medido quando há dados/tarifas válidos.
- Conexões LLM: teto por conexão e reserva conservadora, inclusive resultado desconhecido. O teto soma reservas históricas, não apenas valor final faturado.
- Produção experimental: envelopes e limites por categoria, mais orçamento mensal de infraestrutura fora de produção.

O que falta/é incompleto:

- Ledger único de custo real por chamada/cena/projeto/usuário, incluindo geração, verificação, retries e subtarefas.
- Limite financeiro de produção independente da quota comercial e aplicado antes de qualquer submissão.
- Conciliação com fatura/provedor e tratamento de impostos, câmbio, créditos, cache/reasoning/batch e fornecedor roteado.
- Medição/contabilização dos renders reais e storage/egress nas quotas de governança.
- Política para custo ainda desconhecido, cancelamento no fornecedor e liberação de reservas.
- Dashboard com custo por geração bem-sucedida, custo de falhas, latência e margem por plano.

A verificação de imagem faz outra chamada de modelo e guarda verificationUsage, mas o envelope não demonstra uma reserva financeira independente para essa chamada em todos os caminhos. Já vídeo evita esconder uma verificação adicional dentro da geração e a deixa para etapa própria. Essa diferença merece revisão.

As constantes de preço/reserva do código são **estimativas internas**, não comprovantes de fatura. Exemplos: imageReservationUsd, tarifas videoUsdPerSecond e valores estimatedCostUsd em material discovery. Não devem ser usadas como custo real da Clicko sem conferir modelo, data, resolução, áudio e conta.

Sem volumes reais, tokens de entrada/saída/reasoning/cache, cenas/tentativas por projeto, duração/resolução de cada geração, tempo/hardware do render, retenção e tráfego, não é possível calcular o custo mensal ou margem com rigor.

Fórmula recomendada para posterior medição:

~~~text
custo do projeto =
  soma(chamadas de planejamento + geração + inspeção + crítica + voz)
  + CPU/GPU efetivamente utilizado
  + GB-mês armazenados + tráfego
  + parcela operacional explicitamente definida

custo por entrega aprovada =
  todos os custos da coorte (inclusive falhas/revisões)
  ÷ quantidade de entregas aprovadas
~~~

Não foram inventadas estimativas financeiras. Tarifas atuais devem ser capturadas com versão e unidade da tabela oficial do fornecedor. [Preços Gemini](https://ai.google.dev/gemini-api/docs/pricing), [catálogo/tarifas OpenRouter](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties). Esses links não representam gasto já realizado pela Clicko.

# I. Arquitetura recomendada — somente avaliação, não implementação

## I1. Pipeline proposto

~~~text
Pedido/contexto autorizado
  → intérprete de intenção e restrições
  → diretor/roteirista → plano de cenas com orçamento e identidade
  → resolução de materiais → gerar/adquirir somente o que falta
  → executor determinístico (timeline ou Craft)
  → render e QC técnico + verificação audiovisual
  → correção limitada por orçamento/rodadas
  → revisão humana quando exigida → entrega/versionamento
~~~

“Agentes” podem ser papéis/etapas de uma máquina de estados durável. Não é obrigatório introduzir um framework multiagente, nem permitir que modelos executem comandos arbitrários. Cada etapa deve receber contrato, ferramentas permitidas, orçamento e recibo.

| Etapa | Já existe | Ainda precisa |
| --- | --- | --- |
| Interpretação/contexto | KLIC, permissões, handoff e briefing | Tradutor único para um plano de produção audiovisual versionado |
| Roteiro/cenas | EditorialDirection, beats, planos V1/V2 | Contrato consolidado e geração incremental alinhada ao executor ativo |
| Geração de ativos | Gemini/Runway adapters; biblioteca; direitos | Provisionamento/benchmark, parâmetros completos e seleção por capacidade |
| Execução de edição | FFmpeg canônico + comandos Craft | Ferramentas LLM para timeline canônica; runtimes Craft disponíveis |
| Voz/legendas | Cues, transcrições, contratos/consentimento | TTS/ASR/alinhamento qualificados e integrados à produção |
| Validação/correção | ffprobe, reviews e produção por etapas | Corrigir contratos craft_render; benchmark visual/temporal/audio e evidência real |
| Entrega | Assets privados, export e download | SLO, observabilidade e custo reconciliado por entrega |

## I2. Claude Opus via OpenRouter

**Viável; não implementado nem ativado nesta auditoria.**

OpenRouter oferece Chat Completions e catálogo com IDs/preços/modalidades. Na consulta oficial de 20/10/2026 há anthropic/claude-opus-5.5. O ID OpenRouter com prefixo anthropic/ não deve ser confundido com claude-opus-5-5 da API direta Anthropic. [Modelo Opus no OpenRouter](https://openrouter.ai/anthropic/claude-opus-5.5), [Chat Completions](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion).

Para **comandos nativos Craft**, já existem quase todas as peças de conexão: preset OpenRouter, URL base, protocolo openai_chat, credencial criptografada, modelos permitidos, orçamento e ModelPicker. Precisam chave mestra/credencial provisionadas, runtime funcional e qualificação real do JSON/comandos. Um retorno de catálogo “configured” ainda não prova isso.

Para **planejamento editorial por cenas**, CompatibleEditingPlanner pode apontar para OpenRouter via configuração. Porém usa JSON mode genérico e igualdade exata do response.model; aliases/roteamento precisam ser qualificados. Ele não é automaticamente o mesmo binding gerenciado pelo seletor Craft.

OpenRouter permite JSON Schema em endpoints/modelos compatíveis; o adapter universal atual usa json_object, não a garantia estrita de schema para todos os destinos. Validar JSON no backend continua obrigatório. [Saída estruturada OpenRouter](https://openrouter.ai/docs/guides/features/structured-outputs).

Claude Opus seria um planejador/diretor/crítico textual/visual conforme entradas suportadas e adapter; não um gerador de vídeo ou substituto do FFmpeg. Sua superioridade para os casos Clicko precisa de teste A/B com os mesmos materiais e executor, medindo qualidade, tempo, custo e taxa de correção. Não há evidência nesta auditoria para prometer melhora automática.

## I3. Outros LLMs e geradores especializados

- LLMs: reutilizar a gestão universal para casos em que basta inspeção estruturada; adaptar entrada multimodal e schemas quando necessário, sem enviar filmes inteiros a protocolos que só aceitam texto.
- Imagem: preservar o adapter Gemini, mas permitir capacidades/versionamento por modelo e benchmark. Modelo mais forte só vale se parâmetros de referência/resolução e composição chegarem ao executor.
- Vídeo: Gemini Omni/Veo e Runway são alternativas já próximas do caminho existente; qualificar apenas um recorte de operação por vez. Extensões, keyframes e geração multi-cena exigem contratos explícitos, não só nome de modelo.
- Modelos locais: ativar somente com hardware, artifacts, licença e custo medido. Atualmente não são substituição grátis pronta para a nuvem.
- Roteamento/fallback: precisa autorização de custo, direitos, retenção e identidade; nunca repetir geração em outro fornecedor após timeout desconhecido sem conciliar a primeira.

## I4. Troca pelo painel administrativo

Hoje é possível gerenciar conexões/modelos **de planejamento nativo** pela UI existente, com RBAC e revisão. Não há painel único comprovado para trocar simultaneamente KLIC, diretor editorial, gerador de imagem/vídeo, TTS e ASR.

Evolução recomendada: configurações separadas por papel, com versão e capabilities qualificadas; segredos só no servidor; teste sem gasto/estimativa antes de ativar; teto de custo; aprovação admin; trilha de auditoria; rollback. Jobs em andamento permanecem presos à configuração/modelo/versão originais. Não mudar modelo retroativamente durante retry.

# J. Plano de implementação priorizado — não executado

Custos abaixo são relativos de engenharia/infraestrutura, não orçamentos monetários. A autorização de implementação e de chamadas pagas deve ser uma etapa posterior.

| Prioridade | Entrega | Dependências | Custo relativo | Impacto/critério de aceite |
| --- | --- | --- | --- | --- |
| P0.1 | Neutralizar sucesso/cobrança simulados das rotas antigas, com política de compatibilidade | Inventário de consumidores e decisão do produto | Baixo/médio | Nenhuma API afirma editar/legendar sem asset transformado; teste de quota e estado |
| P0.2 | Limites financeiros e flags centralizados antes de submissão | Definir evento faturável, política de reservas e escopo | Médio | Limite/flag desativado impede chamada; timeout não duplica cobrança |
| P0.3 | Readiness honesto e topologia de serviços | Definir app FastAPI oficial, Redis/storage e runtime | Médio | UI distingue BFF vivo de Studios pronto; health aponta dependência indisponível |
| P1.1 | Corrigir entrada/rotas/contratos video_render→craft_render sem alterar evidências | P0.3; mapear contratos legados e migrações | Médio | Plano→render→crítica→review completo em teste integrado |
| P1.2 | Provisionar Craft nativo e WASM, com identidade de build | Rust/build/artefatos fixados; deploy de workers | Médio/alto | JS/WASM corretos, comandos/preview/export reais; sem dependência do ambiente de desenvolvimento |
| P1.3 | Unificar capacidades e parâmetros efetivos de imagem/vídeo | Contratos e adapter escolhido | Médio | Aspecto/duração/resolução solicitados são enviados e saída é conferida; não anunciar operação rejeitada |
| P1.4 | Padronizar FFmpeg/codecs/timeouts/filas por perfil | Workers de CPU e armazenamento compartilhado | Médio | Mesmo comportamento local/produção; render extenso não morre no timeout genérico |
| P1.5 | Ledger de custo e quotas de vídeo/storage | P0.2, medição nos jobs | Médio/alto | Custo e consumo explicáveis por usuário/job, incluindo falhas/reviews |
| P2.1 | Bateria de qualidade com mídia autorizada e orçamento limitado | Serviços operacionais; autorização paga específica | Médio + API | Relatório comparativo objetivo, sem prometer personagem/produto apenas por prompt |
| P2.2 | Conectar LLM às ferramentas canônicas e consolidar diretor | P1.1/P1.3; schema/limites consistentes | Médio/alto | Pedido vira operações válidas e resultado reproduzível; sem script/shell gerado |
| P2.3 | Qualificar Claude Opus/OpenRouter contra planejador atual | P2.1/P2.2; chave/tarifas/contrato | Médio + tokens | Ganho medido de qualidade/custo/tempo, com opção de não adotar |
| P2.4 | Narração/ASR/alinhamento e legendas automáticas | Consentimento quando aplicável; provider/modelo licenciado | Alto + CPU/GPU/API | Texto/tempos correspondem ao áudio produzido; testes reais pt-BR |
| P3.1 | Autonomia por etapas, reparos limitados e admin por papel | Todos os controles/qualificações anteriores | Alto | Retomada de jobs, orçamento fechado, review e entrega auditável |
| P3.2 | Escala, longos, 4K e efeitos avançados | Benchmarks CPU/GPU/RAM e políticas comerciais | Alto | Medições/SLO sustentam capacidade; sem apenas elevar um limite numérico |

## Conclusão de atribuição de causa

- **LLM:** pode limitar roteiro/direção, mas não houve comparação real de modelos. Não há fundamento para tratá-lo como culpado único.
- **Geradores:** modelo Lite/1K, adapters de vídeo restritos e referência incompleta limitam qualidade; acesso/qualidade reais ainda precisam ser qualificados.
- **Prompts/contratos:** existem instruções extensas, amostragem parcial, limites incoerentes de saída e preservação apenas semântica.
- **Backend/execução:** há bloqueios verificáveis de runtime/entrypoint/contrato/custo e rotas simuladas. São prioridades anteriores à troca do LLM.
- **Ferramentas:** FFmpeg canônico funciona no recorte testado; Craft tem implementação reaproveitável, mas está sem runtime; ASR/TTS de produção e geradores locais não estão prontos nesta instalação.

**Decisão sugerida:** preservar o núcleo útil, fazer a execução real corresponder ao que a plataforma anuncia e só então escolher novos modelos com evidência. A auditoria está concluída; as correções acima não foram implementadas por respeito ao escopo solicitado.
