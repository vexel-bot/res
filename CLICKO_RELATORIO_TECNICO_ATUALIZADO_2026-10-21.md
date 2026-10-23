# Clicko — relatório técnico completo e atualizado

**Data:** 21/10/2026 — America/Sao_Paulo.

**Checkout examinado:** `C:/Users/pedro/Downloads/res`.

**Referência Git:** `5cab414dd942c721f8e6fdf65dcd82b4ade28722`, branch `codex/klic-atualizacao-20260823`, com alterações locais extensas, inclusive arquivos não rastreados. O commit, isoladamente, não representa o código auditado.

**Natureza desta etapa:** exclusivamente auditoria, testes e documentação; nenhuma correção de código ou configuração foi aplicada.

Referências históricas: [auditoria de 20/10](docs/audits/IMAGE_VIDEO_TECHNICAL_AUDIT_2026-10-20.md), [recuperação estrutural](docs/audits/MEDIA_RECOVERY_2026-10-21.md) e [validação anterior de 21/10](docs/audits/FINAL_MEDIA_VALIDATION_2026-10-21.md). Resultados anteriores são identificados como históricos, não reclassificados como testes novos.

## 1. Resumo executivo

**A Clicko possui uma base local comprovada para importar, editar e exportar vídeo com FFmpeg, além de persistência, permissões e armazenamento privado testados. Não está comprovada como plataforma profissional de produção audiovisual autônoma por IA, nem está homologada para produção.**

As melhorias recentes eliminaram sucessos falsos de edição, corrigiram fronteiras de cotas, restauraram a montagem canônica, unificaram rotas e melhoraram a prontidão. A correção mais recente do contrato `originalAudioEnabled` permite renderizar timelines normais do frontend e respeita o desligamento do áudio do vídeo-fonte.

O diagnóstico tem limites importantes:

- A montagem publicitária de referência é material procedural próprio, com roteiro/timeline preparados manualmente. Um MP4 real não é prova de geração por IA, reprodução fiel de um estilo ou qualidade publicitária profissional.
- Gemini/Runway têm transportes e contratos, mas não houve inferência remota autorizada nesta rodada. Catálogo, chave presente e testes HTTP interceptados não comprovam operação comercial.
- PhotoCraft, FilmCraft e EffectCraft não têm runtimes locais compilados nem bundles de navegador presentes. Composição avançada de imagens e motion nativo continuam bloqueados.
- Na sondagem desta auditoria, **não havia listeners em 3018, 8018, 5432 ou 6379**. Os acessos HTTP a Express/Studios recusaram conexão. Não reiniciei serviços com dados existentes; os testes usam ambientes temporários. Isso não invalida a exportação anterior, mas impede apresentar aquela prontidão como estado ativo agora.
- TypeScript, build e testes frontend passaram novamente. Lint completo do backend não está limpo. A suíte Python completa é tratada separadamente na seção 11, sem substituir falhas por aprovação de um recorte.
- O controle USD do Studios Python não deve ser apresentado como teto financeiro universal da plataforma: chamadas Node da KLIC/TTS têm outro caminho, com lacunas descritas na seção 10.

### Cinco problemas mais importantes

1. **Execução nativa e distribuída não provisionada:** Craft ausente, PostgreSQL/Redis/workers não homologados e serviços da prévia parados nesta sondagem.
2. **Geração por IA sem qualificação real:** faltam acesso validado, baterias de qualidade e comprovação de preservação de referências; Veo Preview tem retirada anunciada e Sora está aposentado.
3. **Ciclo autônomo incompleto:** o planejador universal é textual e não fecha aquisição, percepção audiovisual, correção e entrega de ponta a ponta.
4. **Qualificação global pendente:** falhas backend, artefatos de benchmark ausentes e lint residual impedem afirmar estabilidade de toda a plataforma.
5. **Governança financeira fragmentada:** reservas Python, créditos KLIC, cota comercial, métricas e faturas não formam hoje uma conciliação única; não há prova de teto USD cobrindo chat/TTS Node.

## 2. Estado geral da plataforma

### 2.1 Critério de evidência

| Marca | Significado | Não significa |
| --- | --- | --- |
| **C** | Código/contrato inspecionado no checkout atual | Funcionalidade executada ou fornecedor acessível |
| **T** | Teste local novo, com resultado registrado | Cobertura exaustiva ou produção homologada |
| **R** | Processamento real de arquivo/banco/FFmpeg, sem motor de mídia substituído | Inferência por IA ou avaliação artística |
| **D** | Double, fixture ou transporte HTTP interceptado | Resposta real do provedor, GPU ou runtime Craft |
| **H** | Evidência preservada de uma execução anterior | Serviço ativo no instante desta auditoria |
| **O** | Documentação/catálogo público oficial consultado | Acesso da conta Clicko ou preço efetivamente faturado |
| **NV** | Não validado nesta rodada | Ausência definitiva de implementação |

Nenhum subsistema é chamado de “100% pronto” fora do comportamento delimitado efetivamente testado. O relatório separa código disponível, contrato testado, execução real e operação externa.

### 2.2 Matriz funcional

| Área | Estado real e evidência | Limite atual |
| --- | --- | --- |
| Shell React, navegação e Studios unificado | C/T: React/TypeScript, permissões de ferramentas, navegação e modelos de estado compilam e têm testes | Sem nova inspeção visual/responsiva de todas as telas; build não valida cada botão |
| Login, sessão, equipe, clientes e planos | C/T: governança Node, hash de senha, sessão, escopos, permissões, persistência e testes isolados | SMTP, pagamentos reais, fluxo completo de cada papel em navegador e concorrência multi-instância não homologados aqui |
| Dashboard | C/T: projeções de semana, próximos conteúdos, métricas e integração de contexto KLIC | Não produz dados de redes sem conexão; sem nova prévia visual ao vivo nesta rodada |
| Calendário e aprovações | C/T: estado editorial, regras de aprovação, escopo e contratos de agendamento | Publicação depende do provedor, token, escopos e executor; não houve publicação externa |
| Conexões sociais e Analytics | C/T/D: adapters OAuth, refresh, publicação, snapshots, erros e idempotência | Nenhuma conta externa conectada ou sincronizada nesta auditoria; métricas vazias/demonstração não são dados reais |
| Automações/Jornadas | C/T: configurações salvas e validadas | **Executor de gatilhos não conectado**. A própria interface informa que ativar não dispara ações |
| Biblioteca | C/T/R: uploads, referências, privacidade, checksum, vínculos, download e Range | S3 real, retenção, cobrança comercial e escala não homologados |
| Video Studio canônico | C/T/R: projetos, revisões, cortes, títulos, camadas, keyframes, áudio e MP4 | Subset CPU explicitamente limitado; não equivale a FilmCraft/EffectCraft completo |
| Geração de vídeo | C/T/D: adapters Gemini/Runway, jobs e negativas | Sem arquivo novo gerado por esses fornecedores nesta rodada |
| Image Studio — documentos/materiais | C/T/R: referências reais, proporção e armazenamento privado | Não comprova edição de pixels ou nova composição |
| Image Studio — geração/edição Gemini | C/T/D: contrato nativo, budget, review, referências e persistência | Inferência real, latência e fidelidade ainda NV |
| PhotoCraft/FilmCraft/EffectCraft | C/H: fontes, adapters, tipos e indisponibilidade explícita | Runtimes/bundles ausentes; sem execução nativa real |
| KLIC chat e voz | C/T/D: contexto, ações preparadas, conversas, retry, autorização, estados visuais e adapters | Configuração em disco não prova serviço ativo, qualidade de fala, microfone ou resposta real |
| Pesquisa/Radar/planejamento de campanha | C/T/D: providers e regras próprios | Dependem de fontes/API/chaves e disponibilidade; sem consulta remota funcional feita pelo sistema nesta rodada |
| Checkout/assinatura | C/T: integração Stripe, webhooks e idempotência em código | Chave Stripe não encontrada na configuração inspecionada; sem transação ou webhook de produção validado |

Bases adicionais: `src/App.tsx`, `src/studios/StudiosWorkspace.tsx`, `src/context/GovernanceContext.tsx`, `src/context/OperationsContext.tsx`, `src/components/dashboardOperationalModel.ts`, `src/components/AutomationBuilderView.tsx`, `server/integrations.ts`, `server/integrations/publishing.ts`, `server/governance.ts` e `server/klic/adapters.ts`. O adapter `automations.start` retorna explicitamente `unavailable`; KLIC pode preparar handoff de mídia, não afirmar execução inexistente.

## 3. Comparação dos problemas F01–F21

As descrições originais abaixo preservam a causa e o impacto da auditoria de 20/10, resumidos. “Arquivos” identifica onde a correção é encontrada hoje, não atribui autoria nem implica que foram modificados nesta auditoria.

| ID / descrição original | Classificação atual | Correção, arquivos e evidência de teste | Pendência / limite |
| --- | --- | --- | --- |
| **F01** — image-edit/video-edit Node retornavam sucesso sem processar e consumiam cota | **Resolvido e testado** | `server.ts`, `server/studios/legacyEditing.ts::retiredEditing`; testes Node dos handlers confirmam HTTP 410 sem entrega falsa nem consumo | Não é implementação de um novo editor legado; clientes devem migrar ao fluxo canônico |
| **F02** — readiness 200 com Studios sem listener | **Resolvido e testado** | `server/studios/readiness.ts::studiosReadiness`, `server.ts`, `backend/app/routers/health.py::ready`, `server/studios/runtime.ts::startLocalStudios`; testes rejeitam HTML/200 enganoso e dependências indisponíveis | Serviços 3018/8018 estão parados na sondagem atual. Correção do health não os mantém permanentemente ligados |
| **F03** — motores/binários ausentes e URLs WASM devolviam HTML 200 | **Parcialmente resolvido** | `server.ts` devolve 404 JSON para `/craft`; descoberta em `providers/studios/craft.py::engine_capability` e builder explicam indisponibilidade. Testes de contrato cobrem a negativa | `workers/craft/bin` e `public/craft` ausentes; Docker/Cargo/Rust não encontrados no PATH. Compilação e smoke tests nativos continuam bloqueados |
| **F04** — crítica exigia `video_render`, mas produção criava `craft_render` | **Resolvido e testado** | `services/studios/gemini_editing.py::critique_artifact`; `test_studios_recovery.py::test_current_renderers_supply_a_real_video_artifact_to_critique` aceita `craft_render`/`timeline_render` preservando revisão/checksum | Teste do contrato de crítica usa fixture de job, não avaliação remota de qualidade nem aprovação artística |
| **F05** — superfície de rotas diferente entre entrypoints FastAPI | **Resolvido e testado** | `backend/app/studio_routes.py::include_studio_routes`, `main.py`, `studio_app.py`; teste compara rotas dos dois entrypoints e fronteiras da ponte | Autenticações distintas são intencionais. Paridade de rotas não significa que todas as capacidades têm infraestrutura |
| **F06** — geradores desligados, sidecars ausentes e registries ASR/voz vazios | **Bloqueado por dependência externa** | Configuração, contratos e negativas presentes em `config.py`, `domain/studios/providers.py`, adapters de voz/avatar e testes de gates | Sem promoção de modelos, pesos, runtimes, conta e credenciais válidas. Código de provider não é instalação operacional |
| **F07** — reserva de teste não protegia produção e orçamento podia ser infinito | **Parcialmente resolvido** | `external_policy.py::reserve_monthly/committed/billing_scope`, `gemini_editing.py::reserve_test_request`, `llm_connections.py::reserve_request`; testes de teto global/empresa/membro, mês e resultado desconhecido | Conciliação com fatura, modalidades e controle USD Node KLIC/TTS ainda faltam; ver seção 10. Não certifica faturamento completo |
| **F08** — vídeo Gemini podia ignorar flags gerais e limite externo | **Resolvido e testado** | `external_policy.py::assert_operation`, `jobs.py`, `editing_resources.py`; `test_direct_gemini_video_respects_operator_flags_and_native_limits` testa admissão e execução antes de submissão | Só delimita esse gate. Não comprova geração ao vivo nem conta habilitada |
| **F09** — medição/cota de vídeo e armazenamento divergentes; legado confiava nos minutos do cliente | **Parcialmente resolvido** | `server/studios/videoQuota.ts`, `governance.ts::reserveStudioVideoUsage/reconcileStudioVideoJob`, `services/studios/media_usage.py::metrics`; ensaio real registra geração=0 e saída=18 s; testes de replay/reserva | Somente cenas de IA consomem minutos, conforme política confirmada. Há medição de bytes, mas não prova de reconciliação universal com `storage_bytes`, tarifa CPU ou fatura |
| **F10** — imagem fixava 1K e omitia aspectRatio apesar da UI | **Parcialmente resolvido** | `providers/studios/gemini_editing.py::image_config`, `services/studios/gemini_editing.py`; teste de transporte verifica proporção e 1K/2K/4K por modelo; imagem local 4:5 real preservada | Não houve saída Gemini real. Subset Clicko não inclui todas as opções atuais do fornecedor; canvas não é resolução de inferência |
| **F11** — preservação de rosto/produto era apenas instrução/revisão | **Bloqueado por dependência externa** | Persistência de referências e revisão humana existem; código não fornece garantia pixel a pixel | Exige benchmark autorizado e inspeção humana de identidade/marca; material oficial deve ser composto deterministicamente quando a exatidão for obrigatória |
| **F12** — adapter cortava 16.384 tokens para 8.192 | **Resolvido e testado** | `config.py`, `providers/studios/gemini_editing.py::plan`; `test_native_image_transport_and_output_token_contract` confirma cap solicitado sem corte oculto | O limite interno continua até 16.384, deliberadamente menor que o máximo de alguns modelos; planos grandes ainda precisam de particionamento |
| **F13** — `libx264`/caminho fixos incompatíveis com FFmpeg local | **Parcialmente resolvido** | `providers/studios/media_runtime.py::resolve_tool/h264_encoder`, `ffmpeg_utility.py`, `services/studios/gemini_editing.py`; renders FFmpeg/H.264/AAC reais e testes de áudio | `ugc_acceptance.py::encode_animatic` ainda usa `shutil.which("ffmpeg")` e seu teste falha com `ffmpeg_not_available`. A descoberta comum ainda não cobre todo caminho legado; geração remota e imagem Linux NV |
| **F14** — capabilities amplas não correspondiam ao modelo/operação | **Parcialmente resolvido** | Gates em `external_policy.py`, `editing_ai.py`, bindings Gemini/Runway e testes de duração/operação | `material_providers.py`/`hybrid_video.py` ainda carregam perfis históricos; há rótulos Veo com limites amplos e IDs substituíveis. Descoberta não é contrato operacional unificado; retirada Veo exige tratamento |
| **F15** — IA só alterava projeto nativo e planejador não via mídia | **Parcialmente resolvido** | `services/studios/timeline_ai.py::capability/apply`, `craft_ai.py::ai_commands`, `CanonicalVideoEditor.tsx`; teste aplica `timeline.replace` validado uma vez, com resposta LLM double | `UniversalLLMPlanner.plan` rejeita mídia. Falta percepção real integrada, aquisição e ciclo de correção; trocar modelo não resolve isso sozinho |
| **F16** — contratos defasados, Ruff e cobertura npm fragmentada | **Parcialmente resolvido** | Testes antigos `/derive`/App ajustados anteriormente; nova rodada Node e sete casos Craft separados aprovados. Ruff backend/app agora tem 11 ocorrências, não 80 | Suíte global não verde; sete testes externos continuam fora do script npm principal e foram executados à parte. Ruff completo não aprovado |
| **F17** — eager prendia HTTP e timeout de fila não acompanhava jobs | **Parcialmente resolvido** | `local_queue.py` limita pool/admissão; `jobs.py::execute_job_once/enqueue_job_task`, `production_queue.py`, `studio_video.py::recover_interrupted_local_jobs`; testes de claim, cancelamento e recuperação | Pool não é broker durável. Falta execução Celery/Redis real, carga, morte de worker e qualificações de filas especializadas |
| **F18** — manifests/benchmarks/modelos especializados referenciados ausentes | **Bloqueado por dependência externa** | Ausência reconfirmada por filesystem; falhas globais identificam arquivos/políticas sem fornecê-los artificialmente | Restaurar artefatos de origem verificável e provisionar runtimes; criar fixtures “aprovadas” para apagar falhas não seria correção |
| **F19** — leituras amplas, base64/PNG por título e CPU sem escala medida | **Pendente** | `external_policy.py::reserve_monthly` hidrata jobs; governança JSON é de servidor único; títulos são rasterizados pelo compilador. Há limites locais, não benchmark de escala | Paginação, índices, retenção, consolidação de custos e testes RAM/latência necessários; sem extrapolar 18 s para produção longa |
| **F20** — ponte não tinha startup/hardening equivalente ao principal | **Parcialmente resolvido** | `studio_app.py::lifespan`, `http_middleware.py::install_http_middleware`, validação Settings; testes de paridade, startup, rate limiting e erros | TLS/reverse proxy, Redis real, isolamento de rede, failover e observabilidade de produção não homologados |
| **F21** — geração de imagem Node cobrava só após sucesso e anunciava fallback inexistente | **Resolvido e testado** | `server.ts` aposenta `/api/ai/generate-image` com 410. `imageQuota.ts::forwardMeteredImageRequest` e testes Node impõem uma unidade por solicitação aceita, inclusive falha/cancelamento; replay não duplica | Gerar/editar imagens depende do endpoint canônico e provider real; o fluxo antigo não retorna uma imagem substituta |

**Placar:** 7 resolvidos e testados, 10 parcialmente resolvidos, 3 bloqueados por dependência externa e 1 pendente. Nenhum item foi classificado apenas como “corrigido, mas não validado”; onde falta validação de uma parte essencial, o item ficou parcial ou bloqueado. Esse placar não é um percentual de prontidão do produto.

Testes de regressão centrais: `backend/tests/test_studios_recovery.py`, `test_image_frontend_contract.py`, `test_video_frontend_contract.py`, `test_video_timeline_real.py`, `test_media_final_validation.py`, `test_studio_llm_connections.py`; Node: `server/studios/*.test.ts`, governança, integração, KLIC e segurança. A seção 11 registra resultados e distingue doubles de execução real.

## 4. Arquitetura atual

```text
React/TypeScript — App, Governança, Operações, Studios, KLIC
  └─ Express BFF (server.ts)
      ├─ governança/sessão/RBAC/cotas → AtomicJsonStore local
      ├─ integrações sociais → JSON local OU repositório PostgreSQL
      ├─ KLIC Node → contexto/conversas/SDK Gemini e Google Cloud TTS
      └─ ponte Studios → JWT curto, escopo e recibo comercial assinados
           └─ FastAPI app.studio_app (app.main é outro entrypoint autenticado)
                ├─ SQLAlchemy → SQLite local / PostgreSQL exigido em produção
                ├─ documentos, revisões, operações e jobs
                ├─ armazenamento → local / adapter S3
                ├─ executor local limitado OU Celery/Redis
                ├─ timeline canônica → compilador Clicko → FFmpeg/FFprobe
                ├─ nativeEditorState → adapters Rust Photo/Film/EffectCraft
                └─ LLM/media adapters → provedores externos, quando autorizados
```

### 4.1 Fronteiras que precisam permanecer distintas

- **Governança Node não é o banco Studios.** Dados SaaS/assinatura/sessão vivem em outro repositório. A ponte deriva identidades isoladas por cliente, mas preserva empresa/membro SaaS para orçamento. Uma migração PostgreSQL de uma área não migra todas as outras.
- **KLIC Node não é o planejador Python.** O SDK de conversa e as conexões administrativas de edição têm contratos, credenciais e medição diferentes.
- **Timeline canônica não é projeto nativo Craft.** FFmpeg executa o subset declarado; não substitui silenciosamente o arquivo `.pcraft/.fcproj/.ecproj` ou inventa comandos nativos.
- **Capacidade, configuração, acessibilidade e qualificação são estados distintos.** Um manifest que diz `commercial_use=approved` é metadado interno; não substitui revisão de licença nem comprova infraestrutura/qualidade.

### 4.2 Autenticação, isolamento e segredos

`server/governance.ts` implementa credenciais com scrypt, sessões armazenadas por hash, autorização de módulos/ações/escopo e origem de mutações. `server/studios/proxy.ts` encaminha contexto autorizado e JWT da ponte; `studio_app.py::bridge_claims/bridge_user` valida assinatura, audiência, emissor e módulo. IDs por cliente são derivados no servidor. `app.main` conserva autenticação própria; não é correto usar uma chave da ponte como se fosse login público.

`services/studios/llm_connections.py::encrypt/decrypt/access` cifra segredos com Fernet vinculado a workspace/conexão/endpoint/protocolo; `public` devolve `hasCredential`. Somente Owner/Admin cadastra/altera. Testes verificam cifragem, escopo, revisão e negativas. O segredo mestre, rotação, backup e acesso operacional continuam responsabilidade do servidor.

**Limite:** isso não é pentest completo. Não foram auditados todos os caminhos por exploração, executadas mudanças em permissões reais, extraídas sessões nem realizadas operações com contas de usuários. Transporte social/S3 e configuração de produção exigem sua própria qualificação.

## 5. Sistema de vídeos

### 5.1 O que é geração, edição e montagem

| Conceito | Comportamento da Clicko hoje |
| --- | --- |
| Geração por IA | Solicita uma cena nova a Gemini/Runway ou runtime local específico. Há adapters/gates/jobs; sem inferência comprovada nesta auditoria |
| Edição audiovisual determinística | Usa materiais existentes e parâmetros tipados para produzir um novo MP4 real com FFmpeg. Comprovada em testes R |
| Montagem automática | Código pode aplicar uma timeline recebida de planejador e renderizá-la. Contrato/replay testados com LLM double; direção autônoma real ainda NV |
| Edição generativa remota | Modifica vídeo por Gemini Omni/Runway Aleph, se suportado e habilitado. Transporte não equivale a resultado visual qualificado |
| Motion nativo | Projeto/composição EffectCraft; bloqueado pelo runtime. Keyframes simples FFmpeg não são um motor completo de motion |

### 5.2 Operações e limites

| Operação | Implementação / prova | Situação |
| --- | --- | --- |
| Criar/salvar/reabrir projeto | `VideoStudio.tsx`, `videoModel.ts`, rotas de documentos e revisões | T/R; persistência real e isolamento |
| Importar materiais | Biblioteca privada, vínculo asset/documento, checksum e direitos | T/R; não precisa de geração remota |
| Cortes/trim | Intervalos de fonte e timeline tipados | T/R em arquivo real |
| Velocidade | Velocidade estática, limites validados | C/T; não confundir com speed ramp |
| Camadas e composição | Vídeo/imagem, escala/pad/overlay, ordem de faixas | T/R; sem máscara/tracking avançado nesse compilador |
| Animações | Keyframes X/Y/escala/opacidade; rotação estática | T/R em subset; curvas/filtros arbitrários não aceitos |
| Transições | Fades de clipes/camadas e sobreposição; ensaio usa passagem pelo preto | T/R; não foi testado todo efeito que o frontend ou legado menciona |
| Títulos e legendas fornecidas | Rasterização de texto e composição na timeline | T/R; texto fornecido não é transcrição automática |
| Áudio | Trilha importada, trim, mix, ganho, fades e áudio original habilitado/desabilitado | T/R; PCM verifica som/silêncio. Não prova voz/música gerada por IA |
| Planejamento de cenas | Brief/roteiro persistem; `craft_ai` pode devolver comandos validados | C/T/D para LLM; decisão editorial da publicidade foi manual |
| Estilo de referência | Recursos/repertório/inspeção e direção em código | C/D/NV para fidelidade real; não há benchmark que autorize prometer “igual à referência” |
| Render/export | `timeline_editor`, `timeline_ffmpeg`, H.264/AAC e FFprobe | T/R; preview e export usam o mesmo compilador |
| Assíncrono/recuperação | Job durável no banco, claim, pool limitado, cancelamento e recuperação explícita | T/R local; fila distribuída não homologada |
| FilmCraft/EffectCraft | Adapters, estado nativo, comandos e frontend preservados | Indisponíveis nesta instalação; nenhuma prova real de processamento nativo |

`timeline_ffmpeg.capability` declara no máximo 600 s, 32 camadas, dimensão 1920 e 60 fps, condicionados a codec/filtros presentes. São limites de admissão, não garantia de RAM, latência ou 60 fps de renderização. Não houve carga até esses máximos. Fontes, blend modes, máscaras, keyframes de rotação, efeitos temporais complexos, ASR e estabilização não podem ser inferidos dos nomes de filtros ou dos fontes upstream.

### 5.3 Evidência concreta

`test_real_eighteen_second_advertising_reference` cria fonte local de 24 s, PNG geométrico e áudio próprios. Envia uploads/documento/timeline às APIs reais, monta três cenas de 6 s, títulos, overlay animado, fades e ganho. Executa o worker e FFmpeg reais; valida dimensões/duração, pixels de três cenas, áudio, checksum, biblioteca, Range, isolamento e replay sem job duplicado. O arquivo retido nesta rodada é identificado na seção 11.

**Histórico H separado:** a validação anterior importou o MP4 de 18 s no navegador, criou `QA · Validação final · 18s` e reexportou a revisão 2 em 1920×1080/30 fps/H.264/AAC. Evidências: `.codex-runtime/final-validation-2026-10-21/browser-evidence.json` e `browser-export-validado.jpg`. São evidências verdadeiras preservadas, mas não uma nova navegação nesta rodada. A fonte era 720p; a exportação 1080p é redimensionamento, não ganho de detalhe por IA.

## 6. Sistema de imagens

### 6.1 Fronteiras de funcionamento

| Recurso | Código / evidência | Conclusão |
| --- | --- | --- |
| Documento, canvas e proporção | `src/studios/image/ImageStudio.tsx`, modelo de draft e documentos canônicos | Persistência e referência 960×1200 reais; canvas não controla sozinho o gerador |
| Upload/referências | Recursos com prova de uso, biblioteca e assets privados | Teste real recupera bytes/dimensões/SHA; outro cliente recebe 404 |
| Preservação do original | Edição mantém fonte e gera candidato separado | T/R no armazenamento; T/D no resultado Gemini |
| Geração/edição Gemini | `editing_resources.py`, `services/studios/gemini_editing.py`, `providers/studios/gemini_editing.py` | Implementadas em adapter/job, porém apenas contrato com HTTP doubles; nenhuma inferência nova |
| Proporção/resolução | `image_config`: dez proporções; Lite 1K, Flash Image 1K/2K/4K | Transporte validado; arquivo real retornado pelo fornecedor ainda NV |
| Revisão | Candidato e aprovação humana preservados | Testes de estado; não é aprovação automática da fidelidade |
| Composição/edição avançada | PhotoCraft, camadas, comandos nativos e WASM previstos | Bloqueada por binário/runtime/bundle ausente |
| Exportação | Download de upload original funciona; export de composição depende de motor | Não tratar download do original como edição ou exportação PhotoCraft |
| Erros | Provider desligado, orçamento insuficiente, revisão/escopo inválidos e runtime ausente falham explicitamente | Testados; sem fallback/imagem fictícia |

### 6.2 O que foi validado com imagem verdadeira

O caso `test_reference_image_import_storage_download_and_explicit_native_block` utiliza um PNG procedural próprio 4:5. Verifica upload, armazenamento, download, dimensões 960×1200, hash e isolamento. Um vínculo sem prova de uso é recusado corretamente; o upload por `/editing/resources/upload` com evidência de autoria pode ser vinculado. A tentativa `/craft/preview` sem projeto/runtime nativo falha controladamente e o original permanece intacto.

Isso comprova o fluxo documental e de materiais. **Não comprova remoção de fundo, retoque, novo enquadramento, composição em camadas ou exportação de um bitmap editado.** Os testes `test_image_frontend_contract.py` exercitam direitos, persistência, review, orçamento e idempotência com respostas do gerador substituídas; essa parte é D, não inferência.

### 6.3 Identidade, qualidade e referências

Rosto, embalagem, marca e texto de logo não têm preservação exata garantida. Os modelos podem receber referências, mas isso não assegura geometria, tipografia ou identidade constantes. Para marca que deve permanecer exata, a solução recomendada é composição determinística do asset oficial após gerar o entorno, com revisão humana. Nenhuma qualificação de produto/personagem foi obtida nesta etapa.

O fornecedor oferece opções além do subset Clicko. Por exemplo, a documentação de Flash Image lista resoluções/formatos que não estão todos no adapter atual; isso é limite de integração, não prova de defeito no modelo. [Modelo oficial Flash Image](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image), [Lite Image](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-image).

## 7. Modelos e provedores de inteligência artificial

### 7.1 Configuração observável, sem revelar segredos

Foi lida apenas uma projeção permitida de nomes de modelos, flags e **presença** de credenciais na configuração raiz/shell. Valores de chaves, tokens, certificados e arquivos de credenciais não são reproduzidos. Essa projeção **não é o ambiente de um processo em execução**, nem consulta conexões salvas de usuários.

- KLIC em disco: `KLIC_CHAT_MODEL=gemini-3.8-flash`, modo Developer API; `GEMINI_API_KEY` presente, **não validada**. O fallback no código é `gemini-2.5-flash`, mas não é a seleção observada em disco.
- `KLIC_GOOGLE_TTS_ENABLED=true`; referência a credencial Google Cloud presente, **não autenticada nem aberta**. Estar habilitado não prova que o serviço TTS responda.
- Chaves Studios Gemini/Runway de teste/produção e `STUDIO_LLM_CREDENTIAL_KEY` ausentes nessa projeção; flags de mídia e tetos mensais USD não definidos. Defaults Python fecham geração paga. Chaves em outro secret manager/processo/servidor não foram investigadas.
- OpenAI e `AI_API_KEY` ausentes nessa projeção. Não houve tentativa de login, criação de chave, validação paga ou leitura de segredo cifrado do banco.
- O autostart local desliga providers pagos **Python**, mas não é um disjuntor de todo o SDK **Node**. É necessário tratar a governança Node explicitamente antes de um piloto.

### 7.2 Catálogo LLM e protocolos

Fonte: `backend/app/providers/studios/llm_catalog.py::PROVIDERS`, `universal_llm.py::PATHS/UniversalLLMPlanner` e `services/studios/llm_connections.py`. A marca interna `verifiedAt=2026-10-12` é uma anotação do código, não uma verificação nova desta auditoria. Todos os IDs desta tabela são inventário literal de sugestões; **não foi comprovado acesso atual às contas desses fornecedores**.

| Provedor / protocolo | IDs existentes no catálogo | Integração e configuração / funcionamento | Credencial e custo |
| --- | --- | --- | --- |
| OpenAI / Responses | `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-luna` | Transporte universal e sugestões; nenhuma conexão operacional validada. IDs não requalificados individualmente nesta rodada | Chave backend; tarifas/limites por conexão; custo efetivo desconhecido |
| Anthropic / Messages | `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-haiku-5-5`, `claude-fable-5-1` | Sugestões para endpoint direto; não confundir esses slugs com o ID OpenRouter. Sem chamada real | Chave Anthropic e preço configurado; não medido |
| Google / GenerateContent | `gemini-3.8-flash`, `gemini-3.5-flash-lite` | Transporte universal textual; primeiro também confirmado em documentação oficial. Não implica geração de imagem/vídeo | Chave Google; tokens faturáveis, se pago |
| Mistral / Chat Completions | `mistral-large-4`, `mistral-small-2603` | Catálogo + protocolo; sem endpoint/conta qualificados aqui | Chave e tarifa próprias; desconhecido |
| DeepSeek / Chat Completions | `deepseek-flash`, `deepseek-v4-pro` | Catálogo + protocolo; sem execução real | Chave e tarifa próprias; desconhecido |
| xAI / Responses | `grok-4.7` | Catálogo + protocolo; sem execução real | Chave e tarifa próprias; desconhecido |
| Cohere / Chat | `command-a-plus-05-2026`, `command-a-reasoning-08-2025` | Catálogo + protocolo; sem execução real | Chave e tarifa próprias; desconhecido |
| Groq / Chat Completions | `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` | Catálogo + protocolo; sem execução real | Chave/contrato Groq; não é uso gratuito local por ter pesos abertos |
| Together / Chat Completions | `Qwen/Qwen3.8-2.4T-A95B`, `moonshotai/Kimi-K3` | Catálogo + protocolo; sem execução real | Chave/contrato Together; desconhecido |
| Fireworks / Chat Completions | `accounts/fireworks/models/kimi-k3`, `accounts/fireworks/models/glm-5p3-flash` | Catálogo + protocolo; sem execução real | Chave/contrato Fireworks; desconhecido |
| OpenRouter / Chat Completions | Preset não fixa modelos. `anthropic/claude-opus-5.5` foi conferido publicamente | Endpoint compatível existente; slug deve ser cadastrado explicitamente. Nenhuma conexão ativada nesta auditoria | Chave OpenRouter, crédito e teto; referência tarifária na seção 10 |
| Ollama / Chat | `qwen3:8b`, `gpt-oss:20b` | Sugestões locais; nenhum servidor/peso/inferência local validado | Pode dispensar chave em loopback; computação não é custo operacional zero |
| Endpoint personalizado / JSON ou protocolo suportado | IDs administrativos arbitrários, explicitamente registrados | Mapeamento de request/response e endpoint validado; sem garantia de compatibilidade sem ensaio | Chave backend quando exigida; `local_free` só aceita loopback |

Há sete protocolos em `UniversalLLMPlanner`: Chat Completions, Responses, Anthropic Messages, Gemini GenerateContent, Cohere Chat, Ollama Chat e JSON customizado. Testes locais serializam requests e normalizam respostas; **não executam todos esses modelos**. Limites de payload, JSON, modelo registrado e ausência de redirects reduzem risco, mas a conexão continua sem qualificação real.

### 7.3 Integrações especializadas e estado de operação

| Modelo/provider ID | Papel e local da integração | Estado verificável / limitações / credenciais |
| --- | --- | --- |
| Gemini chat KLIC: seleção `gemini-3.8-flash`; fallback `gemini-2.5-flash` | SDK `@google/genai`, `server.ts`, `server/klic/providerConfig.ts` | Configuração em disco presente; nenhuma resposta real nesta rodada. Usa Developer API ou Vertex, conforme ambiente; não é a conexão de edição Python |
| `gemini-3.5-flash` | Fallback de transcrição de anexos KLIC, `klicTranscriptionModel` | Código não prova ASR Studios. Precisa acesso Google; sem áudio real enviado |
| `pt-BR-Chirp3-HD-Charon`, `pt-BR-Chirp3-HD-Kore` / Google Cloud TTS | `server/voice/config.ts`, `providers/googleCloudTtsProvider.ts` | Voz Node implementada; flag em disco habilitada, credencial referenciada não validada. Sem síntese paga ou microfone testado |
| `gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.8-flash` | Allowlist de planejamento em `config.py` e adapter Gemini | Contrato e cap testados; nenhuma inferência. Possível alias/roteamento do fornecedor não substitui registrar identidade de resposta |
| `gemini-3.1-flash-lite-image`, `gemini-3.1-flash-image` | Geração/edição em `providers/studios/gemini_editing.py`, jobs e Image Studio | Adapters existentes; chaves Studios ausentes na projeção; resolução/proporção testadas com doubles; sem qualidade/preservação qualificadas |
| `gemini-omni-1.1-flash` | Vídeo via Interactions, adapter Gemini | Modelo oficial confirmado; transportes/jobs presentes, mas acesso e mídia reais NV; cenas curtas, não filme completo de uma vez |
| `veo-3.1-lite-generate-preview`, `veo-3.1-fast-generate-preview` | Transporte `predictLongRunning`, Settings e perfis híbridos | **Retirada anunciada para 22/10/2026** na Gemini Developer API. Não são base recomendada para nova integração; não chamados |
| `gen4.5`, `aleph2` / `runway.editing-video` | `runway_editing.py::runway_binding/RunwayEditingProvider`, geração e edição | Binding escolhe Gen-4.5 para gerar, Aleph2 para editar; versão de API `2024-11-06`, tarefas/poll/cancel/download. Sem chave Studios ou mídia real qualificada. Catálogo amplo Runway não está todo integrado |
| `sora-2` / `openai.sora-2` | `openai_video.py`, `sora_editing.py`, registro histórico | **Aposentado**: gate bloqueia a partir de 24/09/2026; documentação oficial confirma retirada. Não é um gerador elegível para o próximo piloto |
| `kling-video/v3.0/std/text-to-video`, `kling-video/v3.0/std/image-to-video`, `ideogram/v4.0` / `higgsfield.media` | Transporte e contratos em `providers/studios/higgsfield.py` | Existe preparação/quote/receipt, mas não foi demonstrado roteamento integral pela UI pública e execução real. Depende de credenciais/quote/conta; custo desconhecido |
| `animatediff-lightning-sd15-a-v1`, `animatediff-lightning-sd15-b-v1`, `wan21-t2v-local-experimental-v1` | Perfis `scene_generation.py`, adapter `local_diffusion.py` | Cenas experimentais de 1–2 s; diretório `workers/media-generation-local` ausente. Não há inferência GPU local aprovada |
| `wan2.2-ti2v-5b-serverless-experimental-v1` | Manifest híbrido | Registro de candidato, worker não implantado, GPU serverless não autorizada; não é serviço |
| `meituan-longcat/LongCat-Video-Avatar-1.5` / `local.longcat-avatar-1.5` | `longcat_avatar.py`, `hybrid_video.py` | Adapter e revisão fixada; worker/ativos ausentes, recursos e licenças dependentes; sem avatar real qualificado |
| `musetalk-1.5-evidence-v1`, `latentsync-1.6-evidence-v1`, `heygem-visual-only`, `musetalk-v1.5-local` | Perfis híbridos e cast de avatar | Candidatos/contratos; sem provider promovido. LatentSync está marcado como uso comercial rejeitado **no perfil interno**, não é uma conclusão jurídica nova sobre todas as versões |
| `kokoro-82m-stock`; vozes `pf_dora`, `pm_alex`, `pm_santa` | `kokoro_stock.py` | Adapter de TTS local; registry de fala inicia vazio e depende de pesos, runtime e benchmark. Sem síntese real nesta rodada |
| `chatterbox-multilingual-v3`, `chatterbox-pt-br`, `kokoro-openvoice-v2` | `voice_clone_sidecar.py` e manifests tipados | Factories de candidatos, não promoção automática. Pesos/sidecars/consentimento/benchmark obrigatórios; infraestrutura ausente |
| `local.rembg-u2netp`, modelo `u2netp.onnx` | `background_removal.py`, `rembg_worker.py` | Hash fixado e processo local; não qualificado com inferência nesta rodada. Precisa runtime ONNX/arquivo compatível; não baixar pesos automaticamente |
| VLM local de inspeção | Flag/config e integração editorial | Não há modelo/worker operacional identificado nesta instalação; ID efetivo não comprovado, não inventado |
| `evaluation.qwen-openai-compatible`; referências WhisperX/ASR e YAMNet/VAD | Adapter de planejamento compatível vLLM/SGLang em `openai_compatible_planning.py`; ports e comentários de pesquisa acústica | Sem endpoint Qwen/peso identificado como operacional; ASR/acústica não têm provider promovido. Nomes em pesquisa/testes não viram recursos de produção |
| `opensource.opencv-geometry`, `opensource.opencv-point-tracking`, `toolkit.supervision-detection-projection` | Adapters de visão em `opencv_reality.py`, `supervision_detection.py` | Ferramentas de análise/projeção, não geradores. Detecção aprendida depende do modelo fornecido; sem inferência completa homologada |
| `builtin.snapshot`, FFprobe/proxy/waveform/QC, `ffmpeg.timeline-v1` | Providers técnicos locais | Snapshot é determinístico, não IA. FFmpeg real comprovado no subset de montagem; isso não promove ASR/voz/avatar |

Registries `AVATAR_VIDEO_PROVIDERS`, `GENERATIVE_VIDEO_PROVIDERS`, `SPEECH_PROVIDERS`, `VOICE_CLONE_PROVIDERS`, `TRANSCRIPTION_PROVIDERS` e `ACOUSTIC_ANALYSIS_PROVIDERS` começam vazios em `domain/studios/providers.py`. Adapters pagos específicos podem ter seu fluxo próprio; registro vazio não apaga esses transportes, mas impede afirmar que uma rota genérica tem todos os motores. Não foi executado runner de promoção/injeção.

### 7.4 Verificação oficial e preparação futura

Claude Opus 5.5 foi localizado no OpenRouter com slug **`anthropic/claude-opus-5.5`**. A conexão universal Chat Completions existente é aproveitável; exige cadastro administrativo, chave cifrada, tarifas, limites, validação de resposta e benchmark. Isso não exige reconstruir o sistema nem torna o LLM diretor audiovisual completo. [Catálogo oficial OpenRouter](https://openrouter.ai/anthropic/claude-opus-5.5/providers).

Gemini Flash aceita entradas multimodais na API e produz texto; **o transporte universal Clicko atual não aceita mídia**. Gemini Omni usa Interactions e tem saída documentada de 3–10 s; seu contrato é distinto do planejador. Nenhuma característica da documentação foi tratada como funcionalidade da Clicko sem adapter e teste. [Flash oficial](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Omni oficial](https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash).

Os previews Veo listados têm desligamento anunciado para **22/10/2026**. A disponibilidade de Veo em outra plataforma Google empresarial não implica que as mesmas credenciais/endpoints/contratos funcionem aqui. [Deprecações Google](https://ai.google.dev/gemini-api/docs/deprecations). Sora/Videos API foram retirados em **24/09/2026**; o gate local é coerente com a documentação oficial OpenAI. [Deprecações OpenAI](https://developers.openai.com/api/docs/deprecations).

Modelos do catálogo não essenciais ao piloto não foram revalidados um a um no provedor. Permanecem **sugestões não qualificadas**, mesmo quando o nome parece atual. Acesso da conta, região, saldo, quota, licença e política de dados só podem ser confirmados no contexto autorizado do operador.

## 8. Infraestrutura e backend

| Componente | Observação atual / prova | Operação de produção ainda necessária |
| --- | --- | --- |
| Express | Build aprovado e testes locais de contratos. Portas 3000/3018 sem listener na sondagem | Processo supervisionado, configuração consistente e readiness real |
| FastAPI Studios | Rotas compartilhadas e lifespan testados com TestClient; 8000/8018 sem listener | Serviço separado. Dockerfile raiz contém Node, não implanta Python/Redis/PostgreSQL por si só |
| SQLite | Banco temporário real utilizado pela suíte; perfil local anterior persistia projetos de QA | Não é homologação de carga/concorrência distribuída |
| PostgreSQL | SQLAlchemy e repositório social existem; produção exige PostgreSQL | Nenhum listener local 5432; serviço remoto não configurado/provado nessa projeção; migrations/backup/restore NV |
| Governança JSON | `AtomicJsonStore` usa lock, arquivo temporário, fsync, rename e detecção de conflito | Servidor único, limite de 50 MB e lock órfão exigindo operador; não é DB multi-instância |
| Redis/Celery | Conf, ack tardio, prefetch 1, boot gate e limites por job em código | Nenhum listener local 6379 nem cluster/consumidor qualificado. Pacote instalado não significa worker ativo |
| Pool local | Duas threads, oito admissões, estado do job no banco | Não substitui durabilidade do broker; recuperação de tarefas é explícita e não reenvia provider desconhecido automaticamente |
| FFmpeg/FFprobe | Executáveis reais n9.0.2-28 no diretório `.codex-runtime/ffmpeg`; não encontrados pelo PATH. Descoberta comum os encontra | Empacotamento/versionamento por ambiente. Perfil Linux/manifest usa outro conjunto de versões; precisa ensaio próprio |
| Photo/Film/EffectCraft | Fontes e adapters Rust presentes | `workers/craft/bin` e `public/craft` ausentes; Docker/Cargo/Rust não encontrados. Sem build realizado |
| Rust/WASM | Fonte/worker frontend e bridge previstos | Nenhum artefato compilado entregue nessa instalação; build Vite não os compila |
| Armazenamento local | APIs reais, chaves seguras, SHA e isolamento testados | Retenção, quotas em disco, restauração e proteção operacional ainda requerem validação |
| S3 | Adapter com bucket, metadata/hash, materialização e URL assinada; testes de contrato | Nenhum bucket real acessado nesta auditoria; permissões, egress, lifecycle, backup e custo NV |
| Workers especializados | Diretórios speech-cpu, speech-gpu, vision-gpu, media-generation-local e longcat-avatar ausentes | Runtimes/modelos/manifests/atestação/capacidade real; não preencher com aprovação fictícia |
| Logs/erros | Correlação, status/latência, headers, mensagens de provider saneadas e rate limiter por perfil | Sem stack central de métricas/alertas/SLO/tracing comprovada; logs locais não bastam para conciliar produção |
| Startup/readiness | `validate_for_startup`, SQL `SELECT 1`, storage probe descartável, FFmpeg e fila verificados pelo handler | Nova sondagem recusou conexão porque os processos não estavam ativos, não porque um 200 falso foi retornado |

Ausências adicionais verificadas: `benchmarks/studios`, além dos diretórios de workers acima. O único manifest media-cpu presente lista caminhos Linux de adapters e versões fixadas; sua existência não atesta esta máquina Windows nem as filas/modelos ausentes.

Não fiz restart, deploy, alteração de serviço, migração, instalação ou teste destrutivo de indisponibilidade nesta rodada. Os testes de falha/restart atuam em banco temporário e mocks de fronteira, conforme cada caso. Não se inferiu indisponibilidade de servidores remotos apenas pela ausência de uma porta local.

## 9. Automação audiovisual

| Etapa do fluxo desejado | Componente existente | Integração / impedimento atual |
| --- | --- | --- |
| Solicitação do usuário | KLIC, brief e editores Studios | Entrada e estado existem. Chat Node pode preparar handoff; não comprova execução de produção |
| Interpretação por IA | SDK Gemini Node; planners Python e conexão universal | Protocolos implementados; nenhum modelo real exercitado nesta rodada. Contexto universal é textual |
| Roteiro | Brief, drafting e `editorial_production` | Schema/persistência e testes D; publicidade de QA teve roteiro manual |
| Planejamento de cenas | Fluxo editorial, materialNeeds, timeline/commands | Pode validar planos/IDs/capacidades. Fidelidade editorial e identificação audiovisual reais NV |
| Selecionar materiais | Biblioteca, recursos com direitos, registry de materiais | Importação/vínculo funcionam. Descoberta remota depende de conta; candidato descoberto não vira asset autorizado automaticamente |
| Gerar materiais | Adapters Gemini/Runway, perfis locais/híbridos | Chave, budget, recibo comercial, operação e qualidade precisam de qualificação. Aquisição autônoma sem admissão assinada é bloqueada |
| Editar automaticamente | `craft_ai::ai_commands`, `timeline_ai::apply`, `timeline_editor` | Aplicação canônica/revisão/replay comprovados com proposta LLM double; não é um filme dirigido ao vivo por IA |
| Renderizar | FFmpeg canônico ou runtime Craft | FFmpeg real funciona; Craft ausente. Produção editorial nativa não é automaticamente convertida para FFmpeg |
| Validar | Probe/checksum, direitos, revisão, QC, observações e crítica | Validação técnica real existe. Crítica semântica/artística remota e observadores especializados não homologados |
| Corrigir | Revisão/retry e loop editorial em código | Falta fechamento real de percepção → decisão → ferramenta → nova evidência; execução paga desconhecida não deve ser repetida |
| Entregar | Biblioteca/download privado, resultado do job | MP4 canônico real comprovado. Entrega autônoma do ciclo completo e distribuição social não comprovadas |

**Autonomia comprovada hoje:** dado um projeto com assets vinculados e uma timeline válida, o backend executa a montagem/renderização e entrega um arquivo validado, sem precisar de intervenção por quadro. O ato de criar esse plano a partir de uma solicitação aberta, gerar/selectar materiais adequados, julgar o resultado e corrigi-lo sozinho **não foi comprovado**.

O fluxo pode parar antes do LLM por falta de configuração; antes da geração por falta de admissão/credencial; no nativo por ausência de Craft; na inspeção por falta de workers; ou na revisão por exigência de aprovação humana. Não há evidência de um único clique completando todos esses gates hoje.

## 10. Custos operacionais e controle de consumo

### 10.1 O que é contado e o que é dinheiro

| Grandeza | Situação atual |
| --- | --- |
| Cota de imagens | Uma unidade por solicitação **aceita**, mesmo falha/cancelada. Rejeição confirmada antes da admissão libera reserva; replay/retry do mesmo job não é nova solicitação |
| Cota de vídeo | Somente segundos de cenas geradas por IA. Export/preview/edição locais não consomem minutos. Reserva com tolerância técnica é conciliada com saída validada; resultado desconhecido retém proteção |
| Créditos KLIC | Unidade comercial por operação, não dólares nem token exato do fornecedor |
| Tokens | Uso reportado é normalizado; candidatos + raciocínio Gemini entram uma vez na estimativa. Não foi medido consumo real remoto nesta rodada |
| USD de mídia/planner Python | Reservas conservadoras, teto mensal global/empresa/membro e teto da conexão; identidade SaaS preservada entre clientes e períodos |
| CPU/render | `processingSeconds` mede tempo de processamento, não necessariamente CPU-h faturável. Não há tarifa do hardware contratada |
| Armazenamento | `storedBytes`/tamanho e hashes reais. Não há prova de sincronização universal com a cota comercial Node `storage_bytes`, nem conta GB-mês/retenção/egress fechada |
| Custo por usuário/projeto | Jobs têm autor/documento/correlação e métricas; há agregação workspace/usuário. Falta visão consolidada e fatura reconciliada por produção/cena/tentativa |
| Fatura do fornecedor | `providerReportedCostUsd` continua nulo onde não há dado verificável; estimativa, reserva e medição interna não são fatura |

Fontes de código: `server/studios/imageQuota.ts`, `videoQuota.ts`, `server/governance.ts::reserveStudioImageUsage/settleStudioImageUsage/reserveStudioVideoUsage/reconcileStudioVideoJob`, `external_policy.py::committed/reserve_monthly`, `llm_connections.py::reserve_request`, `gemini_editing.py::measured_request_cost` e `media_usage.py::metrics`.

### 10.2 Proteções e riscos restantes

Proteções testadas: chave idempotente e fingerprint; validação antes de submissão; recibo comercial assinado; revisão/escopo; claim atômico do worker; reserva retida quando a resposta externa é desconhecida; não reenviar automaticamente um POST de mídia possivelmente aceito. A trava de orçamento é global em PostgreSQL e de escrita em SQLite. Isso não certifica cenários multi-região nem conciliação de falha real em fornecedor.

Riscos atuais, **sem correção nesta etapa**:

1. **Cobertura USD fora do Studios (C, não exploração remota):** `server.ts` chama o SDK Gemini Node; `server/klic/router.ts` cobra créditos comerciais; `server/voice/router.ts` limita taxa/texto e chama TTS. Não foi encontrado vínculo desses fluxos ao ledger USD Python, nem fatura/token multimodal unificada. Um limite do Studios não pode ser anunciado como limite de toda a plataforma. A flag TTS e referência de chave Node estão presentes em disco, portanto esse gate deve preceder habilitação operacional.
2. **Crédito KLIC antes da validação (C):** `/api/klic/chat` chama `consumeKlic(actor)` antes de validar mensagem/anexos e antes de obter resposta. Pedido inválido ou falha posterior pode consumir crédito; não há rollback/idempotência visível nesse handler. É diferença de regra comercial que precisa de decisão e teste isolado; não foi reproduzida em conta real nem tratada como débito monetário comprovado.
3. **Tarifa incompleta:** uma tarifa textual única não cobre corretamente cache, ferramentas, multimodalidade, entrada de mídia e preços/resolução variáveis. `measuredCostUsd` histórico pode ser estimativa por tarifa; deve ser rotulado, nunca exibido como fatura.
4. **Reserva conservadora pode bloquear cedo:** o ledger retém o maior valor entre reserva/estimativa/custo reportado. Isso protege contra gasto desconhecido, mas exige conciliação/operador para liberar orçamentos com evidência; não afrouxar para “fazer passar”.
5. **Custo/capacidade desatualizados:** preços de perfis híbridos têm versões fixadas, incluindo Veo em retirada. Configurar outro modelo não deve herdar a tarifa/capacidade de um perfil antigo.
6. **Créditos entre dois serviços:** governança Node JSON e job Python não formam uma única transação ACID. Os recibos/idempotência reduzem duplicação; falta homologação distribuída de queda entre admissão e confirmação e reconciliação operacional visível.
7. **Custos invisíveis de infraestrutura:** CPU/GPU, temporários, cópias, S3, egress, logs, backups e retenção não estão precificados. Uma API não chamada tem gasto externo zero nesta rodada, não custo de operação zero.

### 10.3 Referências oficiais para um futuro piloto

**USD, Standard, consulta em 21/10/2026, sem impostos/câmbio/infraestrutura; não são faturas ou preços comerciais da Clicko.**

| Modelo | Unidade de referência |
| --- | --- |
| Opus 5.5 / OpenRouter | US$4 entrada / US$20 saída por milhão de tokens |
| Gemini 3.8 Flash | US$0,75 entrada / US$3,75 saída por milhão até 31/12/2026; tabela anuncia US$1,50/US$7,50 em 01/01/2027 |
| Gemini Lite Image | US$0,0336 por imagem 1K de saída; entrada US$0,25/milhão |
| Gemini Flash Image | Saída 1K/2K/4K: US$0,067 / 0,101 / 0,151; entrada US$0,50/milhão |
| Gemini Omni | 720p: 5.792 tokens/s × US$17,50/milhão = US$0,10136/s; entrada US$1,50/milhão |
| Runway Gen-4.5 | 12 créditos/s × US$0,01 = US$0,12/s |
| Runway Aleph2 | 28 créditos/s; mínimo 56 créditos por geração; edição não deve ser orçada como geração Gen-4.5 |

Fontes: [OpenRouter Opus](https://openrouter.ai/anthropic/claude-opus-5.5/providers), [preços Google](https://ai.google.dev/gemini-api/docs/pricing), [preços Runway](https://docs.dev.runwayml.com/guides/pricing/). Entrada de mídia, texto/thinking adicional, reprocessamentos, ferramentas e taxas precisam de parcela própria. Não extrapolar a tarifa Omni 720p para 4K. Custos dos demais modelos catalogados, TTS Cloud e infraestrutura não foram orçados individualmente; devem ser obtidos no contrato/plano efetivo antes de ativação.

Exemplos aritméticos: 10 mil tokens de entrada + 2 mil de saída custam US$0,08 no Opus ou US$0,015 no Flash, nas tarifas acima. Uma cena de 5 s custa aproximadamente US$0,60 no Gen-4.5 ou US$0,5068 no Omni 720p, antes de entradas/adicionais. Repetir uma cena é outra operação faturável, mesmo que o usuário a considere “correção”.

Mantém-se como **proposta não aplicada** o teto de inferência de US$15 da validação anterior, em gates de até US$5 para planejamento/imagens e até US$10 para cenas. Quantidade de testes deve caber nas reservas conservadoras; não é autorização para gastar, comprar créditos ou ativar uma API. Priorizar primeiro ensaios locais gratuitos e não incluir previews em retirada.

## 11. Resultados dos testes desta auditoria

### 11.1 Segurança e escopo da execução

Não houve implementação, instalação, alteração de `.env`, ativação de provider, edição de conta real, deploy, commit ou push. `backend/tests/conftest.py` força `ENVIRONMENT=test`, cria SQLite e storage em diretório temporário exclusivo e limpa somente esse ambiente. Flags externas foram também desligadas no processo de teste; o gerador da referência é FFmpeg local, com materiais próprios.

O build gera arquivos derivados `dist/`; os testes geram temporários e artefatos de QA. Isso não modifica fonte ou configuração persistente do sistema. A consulta `npm audit` busca advisories, não instala nem corrige dependências e não executa inferência. Não foram baixados modelos/pesos nem usadas credenciais reais em requests de IA.

Conferência de preservação: o SHA-256 agregado da lista e dos bytes dos arquivos existentes em `backend`, `server`, `src`, `scripts`, `tests`, `workers`, `package.json`, `package-lock.json`, `tsconfig.json` e `vite.config.ts` coincidiu antes/depois: `DE71426C582C857A0A76345C988F4EF941DD24BE0D16F4BE82A379AE8E7AA068`. O relatório novo e os artefatos ignorados de QA não fazem parte desse inventário. Alterações locais anteriores foram preservadas.

A rodada completa foi iniciada a partir da raiz com pytest, portanto coletou **backend, scripts, testes do wrapper Craft e testes upstream de empacotamento Linux**. Não confundir seu escopo com a rodada anterior restrita a `backend/tests`. O recorte backend abaixo foi calculado a partir do mesmo XML, não é uma segunda execução.

### 11.2 Contagem exata

| Verificação | Resultado novo | Interpretação |
| --- | --- | --- |
| `npm run lint` | Exit 0 | Executa `tsc --noEmit`, não ESLint nem auditoria visual |
| `npm run build` | Exit 0; Vite 6.4.5, build cliente 50,48 s + bundles esbuild | Compila frontend/BFF, não Rust/WASM nem provisionamento de serviços |
| `npm test` | **227 + 2 = 229 aprovados**, 0 falhas, 0 pulados | Testes Node/modelos de frontend/segurança. Parte das integrações usa doubles |
| `node --import tsx --test tests/unit/craftState.test.ts` | **7 aprovados**, 0 falhas, 0 pulados | Casos fora do discovery npm principal; não omitir essa separação |
| pytest a partir da raiz | **847 aprovados, 294 falhas, 113 pulados, 0 erros de coleta/setup no XML; 18 avisos** | Exit 1. Terminal: 651,18 s; JUnit: 651,006 s e 1.254 testes/subcasos contabilizados |
| Dentro desse XML: `backend/tests` | **1.229 casos: 838 aprovados, 279 falhas, 112 pulados** | Escopo próprio da aplicação, incluindo os dois testes finais de áudio |
| Recorte crítico de oito módulos, extraído do mesmo XML | **96 casos: 78 aprovados, 0 falhas, 18 pulados** | Não é aprovação de toda a suíte. Detalhamento abaixo |
| Seis casos de `test_media_final_validation.py` | **6 aprovados**, 0 falhas, 0 pulados | Incluídos nos números acima; não somar novamente |
| `ruff check --no-cache backend/app` | Exit 1; **11 ocorrências: 9 E501, 1 I001, 1 UP037** | Lint completo do app Python não aprovado; nenhum `--fix` executado |
| `pip check` | Exit 0, sem requisitos quebrados | Não é auditoria de CVEs, GPU ou pesos instalados |
| `npm audit --json --ignore-scripts` | Exit 1; **0 críticas, 0 altas, 3 moderadas** | Cadeia Mammoth → argparse → sprintf-js; sem correção automática aplicada |
| Portas/endpoints da prévia | Sem listeners nos alvos 3000/3018/8000/8018; requests 3018/8018 recusados | Sem HTTP status válido; recusa não deve ser registrada como HTTP 500/503 |

A diferença entre XML e terminal em duração é a própria medição das ferramentas. A contagem raiz inclui subtestes unittest do upstream: há **15 ocorrências de falha de empacotamento Linux**, em cinco casos pais, no Windows sem a ferramenta de shell esperada. Elas não são 15 novas regressões do backend Clicko. Há ainda um caso upstream pulado. O log/XML integral é a fonte das contagens; não somar pais/subcasos manualmente.

No backend, os **279 IDs de falha coincidem** com os 279 da validação anterior, normalizando o prefixo do módulo causado pelo diretório de coleta. A rodada anterior tinha 1.227 casos e 836 aprovados; os dois casos extras de áudio agora também estão dentro da execução global atual. Isso remove a ressalva anterior de snapshot global anterior à correção de áudio, mas **não torna o CI global verde**, nem prova ausência de toda regressão possível.

### 11.3 Recorte crítico, sem esconder skips

| Módulo backend | Casos | Aprovados | Falhas | Pulados | Evidência principal |
| --- | ---: | ---: | ---: | ---: | --- |
| `test_editing_ai_providers.py` | 20 | 12 | 0 | 8 | Gates/adapters, majoritariamente contratos D; cenários condicionais não executados |
| `test_editing_resources.py` | 28 | 18 | 0 | 10 | Recursos/contratos; casos legados/condicionais pulados não viram aprovação nativa |
| `test_image_frontend_contract.py` | 5 | 5 | 0 | 0 | Estado privado/idempotência/review com fornecedor substituído |
| `test_media_final_validation.py` | 6 | 6 | 0 | 0 | Referência real 18 s, PNG e áudio ligado/desligado; tokens são regressão de contrato |
| `test_studio_llm_connections.py` | 20 | 20 | 0 | 0 | Protocolos/segredos/RBAC/orçamento; LLM/runtime interceptados |
| `test_studios_recovery.py` | 10 | 10 | 0 | 0 | F01–F21 delimitados, admissão/flags/ledger/timeline/planner D |
| `test_video_frontend_contract.py` | 3 | 3 | 0 | 0 | Draft, materiais e fronteira de permissão reais |
| `test_video_timeline_real.py` | 4 | 4 | 0 | 0 | Revisão, isolamento, recuperação e render FFmpeg real |

Casos adicionais no mesmo global: `test_api.py` **9/9**, `test_clicko_studio_bridge.py` **3/3**, `test_object_storage.py` **7/7**, `test_rate_limit.py` **2/2** aprovados. Cadastro/login, alteração de senha em conta de teste, upload privado e isolamento foram exercitados sem tocar contas reais. Aprovação de `object_storage` não comprova bucket S3 remoto: seus adapters externos são interceptados nos casos pertinentes.

### 11.4 Falhas atuais: o que realmente indicam

- **244 dos 279 traces backend contêm `FileNotFoundError`**: políticas/corpora/atestados/manifests/artefatos de validação ausentes. Essa busca textual é evidência de ausência, não classificação definitiva da causa de cada caso; múltiplos testes podem depender do mesmo arquivo.
- Exemplos: `benchmarks/studios/acoustic/acoustic-presence-ptbr-policy.v1.json`, políticas de avatar, `workers/speech-gpu/chatterbox.artifacts.json`, `openvoice-v2.artifacts.json` e inventários `vision-gpu`. Não foram fabricados arquivos para satisfazer essas expectativas.
- Há também contratos/integrações incompletos ou defasados: import de `AlightGraphicsProvider` aposentado; expectativa de motor antigo contra `editor_replaced_by_effectcraft`; fluxo de produto esperando endpoint hoje 410; export/review/captions nativos recebendo 422; API de pré-produção recebendo 503 por evidência ausente.
- Caminho UGC/animatic ainda depende de `shutil.which("ffmpeg")`, apesar do compilador canônico encontrar o executável fora do PATH. Sua falha `ffmpeg_not_available` é limitação remanescente concreta, não prova de que o render canônico falhou.
- `test_visual_quality_program::test_indicator_is_flagged_and_owner_only` recebe 500. Isso exige triagem própria antes de liberar o indicador; não deve ser descartado como “só teste antigo”.
- Supply chain/voz/visão têm wheels/verifiers/atestados ausentes; instalar um pacote qualquer ou remover um gate não comprovaria a promoção.
- Testes de empacotamento Linux upstream falham por `WinError 2`/shell ausente. Devem rodar no SO-alvo ou ter seleção explícita de plataforma; não foram alterados nesta auditoria.

Módulos com maior concentração: inventário de artefatos (14 falhas), freeze AI0 (13), benchmarking Studio (13), autonomia de vídeo (12), contratos de realidade (11), aceitação de publicidade UGC (10). Essas quantidades não são recursos independentes ou uma estimativa de esforço. IDs e traces completos permanecem no XML/log; não há comprovação suficiente para declarar todas as 279 falhas “apenas configuração”.

### 11.5 Lint e dependências

Ruff: duas E501 em `domain/studios/contracts.py`; uma em `domain/studios/editorial_production.py`; UP037 em `domain/studios/image_edit.py`; I001 em `providers/studios/motion_canvas_projection.py`; cinco E501 em `services/studios/editorial_components.py`; uma E501 em `services/studios/production_audit.py`. São 11 ocorrências estáticas, não 11 falhas de geração. O histórico de 80 ocorrências da auditoria original não deve ser usado como resultado novo.

Instalações observadas: Node **24.15.0**, Python **3.12.14**, Vite **6.4.5**, Mammoth **1.12.2**, argparse **1.0.10**, sprintf-js **1.0.3**. Auditoria npm aponta três nós moderados por uma cadeia de dependência, não três incidentes. A sugestão automática de downgrade Mammoth 0.3.29 é incompatível e não foi aplicada. A vulnerabilidade alta anterior do Vite deixou de aparecer; não foi instalada dependência nesta etapa.

Não executei auditoria completa de CVEs Python, licenças de todos os pesos, `cargo test/clippy`, build WASM, GPU, teste de carga, inspeção de microfone, pagamento, publicação social ou inferência remota. Ausência desses resultados está explicitamente preservada.

### 11.6 Artefatos reproduzidos nesta rodada

Diretório: `.codex-runtime/technical-audit-2026-10-21/`.

- [MP4 real de 18 s](.codex-runtime/technical-audit-2026-10-21/publicidade-local-18s.mp4): **1280×720, 30 fps, H.264/AAC, 18,000 s, 1.660.945 bytes**. FFprobe independente do teste confirmou esses valores.
- SHA-256: `67d953e13e2a2b6723f1a9029fa4603f32651a71101050c84e9997a8bbdbc971`.
- `evidence.json`: job `77d9ab56-aade-475c-96e7-06e6dfefeb1a`, documento `6ad11a88-381e-472a-8041-18fbc74887bb`, revisão 2; processamento medido **11,891 s**, saída 18 s e geração IA **0 s**. São IDs do banco temporário já descartado, não URLs funcionais da sessão do usuário.
- `scene-1.png`, `scene-2.png`, `scene-3.png`: extraídos do vídeo e inspecionados visualmente; três textos legíveis e alteração de cenas/escala presentes. Geometria/compressão da fixture é simples, não um criativo premium nem benchmark de acabamento.
- `reference-4x5.png`: referência real usada no teste de imagem, sem alegar edição PhotoCraft.
- `backend-full.xml`, `backend-full.log`, `frontend-tests.log`, `craft-unit.log`, `typescript.log`, `build.log`, `ruff-app.json`, `npm-audit.json`: evidência bruta dos resultados atuais.

Comando de processamento seguro utilizado (variáveis somente no processo de teste):

```powershell
$env:PYTHONPATH='backend'
$env:GEMINI_OUTBOUND_ENABLED='false'
$env:STUDIO_GEMINI_ENABLED='false'
$env:GEMINI_VIDEO_GENERATION_ENABLED='false'
$env:STUDIO_RUNWAY_ENABLED='false'
$env:OPENAI_OUTBOUND_ENABLED='false'
$env:OPENAI_VIDEO_GENERATION_ENABLED='false'
$env:CLICKO_VALIDATION_ARTIFACT_DIR=Join-Path (Get-Location) '.codex-runtime/technical-audit-2026-10-21'
.venv\Scripts\python.exe -m pytest -q --tb=short --junitxml=.codex-runtime/technical-audit-2026-10-21/backend-full.xml
```

Para repetir somente a suíte própria, delimitar explicitamente `backend/tests`. Para reproduzir o recorte real, selecionar `backend/tests/test_media_final_validation.py` e `test_video_timeline_real.py`; esses são testes com FFmpeg, não um comando para ativar IA. A reprodução futura deve respeitar a mesma revisão e os mesmos gates; a pasta de artefatos pode conter resultados que precisam ser preservados.

## 12. Pendências consolidadas

Complexidade: **P** = pequena/localizada; **M** = vários contratos/componentes; **G** = infraestrutura, segurança ou integração multietapa. São estimativas qualitativas, não prazo contratado. “Sem investimento externo” significa sem API/hardware novo contratado, não desenvolvimento gratuito. Cada ID abaixo é único; F01/F02/F04/F05/F08/F12/F21 resolvidos não são reapresentados como tarefas pendentes.

### Prioridade crítica — gates antes de operação paga/produção

| ID | Problema e impacto | Solução recomendada e dependências | Complexidade / investimento | Critério objetivo de conclusão |
| --- | --- | --- | --- | --- |
| P01 | Qualificação global não aprovada: 279 falhas backend; não é seguro anunciar a plataforma inteira estável | Restaurar evidências legítimas; triar contratos aposentados, falhas reais e testes de plataforma; owners por domínio, sem remover proteções para obter verde | G; inicialmente sem API paga; algum benchmark pode exigir hardware/dados | Toda falha classificada com causa e decisão; suíte suportada verde ou bloqueios explicitamente fora da oferta; nenhum teste obrigatório ocultado |
| P02 | Tetos USD não cobrem comprovadamente chat/TTS Node; risco de gasto fora do orçamento Studios | Medição/limite/reserva por tentativa para SDKs Node e vínculo ao usuário/empresa/projeto, mantendo crédito comercial separado; conciliação de resultados desconhecidos | G; implementação/testes fake sem gasto; homologação real exige autorização | Falta de orçamento impede chamada antes da rede em todos os caminhos; retries contabilizados; teste de queda/concorrência e registro de uso/custo verificável |
| P03 | Falta de ambiente operacional homologado e preview parado | Em ambiente isolado, supervisionar Node/FastAPI e configurar banco, Redis/workers/storage; ensaiar restart, recuperação, backups e restauração | G; possível infraestrutura; primeiro smoke local pode ser sem contratação | Readiness verdadeiro, job assíncrono real, morte/retomada e restore aprovados; segregação de dados e nenhum resultado externo reenviado indevidamente |

### Prioridade alta — funcionalidade anunciada, geração e automação

| ID | Problema e impacto | Solução recomendada e dependências | Complexidade / investimento | Critério objetivo de conclusão |
| --- | --- | --- | --- | --- |
| P04 | Craft ausente bloqueia imagem avançada, edição nativa e motion | Compilar/provisionar fontes/adapters/bundles existentes em Linux/Docker adequado; smoke de Photo/Film/EffectCraft e recuperação de projetos | G; toolchain local pode não ter taxa; hardware/host pode exigir investimento | Cada motor anuncia identidade real e executa projeto → comando → preview/export sem double; arquivo decodifica e revisão/histórico preservados |
| P05 | Gemini/Runway sem mídia real qualificada; preservação desconhecida | Matriz pequena de imagens e cenas com materiais autorizados, benchmarks de identidade/formato/latência e revisão humana | M/G; chamadas pagas só com autorização após P02 | Conta/modelo confirmados, saída decodificável, custo registrado, critério de qualidade atingido e falhas/retries tratados |
| P06 | Veo Preview em retirada e perfis/capabilities/tarifas históricos divergentes | Versionar capacidades por modelo/operação/endpoint; tratar fim de vida; qualificar Omni/Runway existentes em vez de assumir substituição | M; atualização de catálogo sem inferência; teste real pago depois | Nenhum modelo aposentado elegível; limites e tarifas coincidem com binding efetivo; UI não anuncia capacidade recusada pelo adapter |
| P07 | LLM universal não observa vídeo/imagem e não fecha o ciclo autônomo | Acrescentar observações autorizadas de frames/áudio/transcrição e ferramentas limitadas ao executor existente; um run rastreável | G; desenvolvimento local primeiro; percepção externa/GPU depende de investimento | Brief aberto completa plano → materiais → edição → render → evidência → correção limitada → entrega, sem IDs inventados ou aprovação humana forjada |
| P08 | Cadastro administrativo de geradores incompleto; troca de mídia exige ambiente/código | Evoluir cadastro LLM existente para catálogo por função, cifragem/RBAC/revisão e preços/capacidades versionados; não criar serviço duplicado | M/G; sem custo de API para construir | Admin muda provider permitido sem edição manual; segredo nunca retorna; validação e rollback auditáveis, teste de cada função |
| P09 | Voz/clone/avatar/ASR/visão especializada sem workers/pesos/promovações | Recuperar supply chain, licenças, consentimento e benchmarks; escolher só os recursos necessários ao MVP, não provisionar todos os candidatos | G; GPU/host/dados podem custar; auditoria inicial sem inferência | Provider promovido após atestação e benchmark real; job, output e direitos rastreáveis. Recurso excluído do MVP fica claramente indisponível |
| P10 | Caminhos legados ainda falham: animatic fora do resolver, exports/reviews 422, indicador 500 | Triar testes/funções indicados na seção 11; reaproveitar resolver/contratos atuais quando correto; não reativar motor aposentado | M; sem API paga para reproduzir | Casos reproduzidos em isolamento com resultado correto/erro intencional documentado; sem 500 não tratado e sem export falso |

### Prioridade média — governança operacional e escala

| ID | Problema e impacto | Solução recomendada e dependências | Complexidade / investimento | Critério objetivo de conclusão |
| --- | --- | --- | --- | --- |
| P11 | Faturas/custos por tentativa/projeto e armazenamento não conciliados | Agregar ledger/métricas já existentes, importar uso verificável, retenção e tarifação de CPU/GB/egress; conciliação administrativa de reservas | G; contrato de infraestrutura/provider necessário para valores reais | Reserva/estimativa/fatura visíveis e distintos; totais reconciliados por projeto/usuário; bytes reais batem com cota comercial |
| P12 | Crédito KLIC pode ser consumido antes de rejeição local; regra de cobrança ambígua | Definir evento faturável de chat/anexos/erro e testar idempotência/rollback quando aplicável; não alterar unilateralmente a regra | M; sem API paga para teste isolado | Pedido inválido, timeout, replay e falha têm comportamento aprovado e teste; sem dedução surpresa em conta real |
| P13 | F19: scans de jobs/JSON, títulos rasterizados e leitura ampla podem crescer em RAM/latência | Medir carga e volumes reais, índices/paginação, retenção, cache seguro e limites de assets/títulos/temporários | M/G; ensaio local primeiro; carga representativa pode precisar host | Orçamento de RAM/latência/throughput definido e cumprido em dados representativos; falha por limite previsível |
| P14 | Sem homologação de S3, monitoramento central e operação distribuída | Bucket isolado, políticas mínimas, expiração/download, restore e alertas por estado; métricas sem prompt/segredo | M/G; serviço externo somente quando contratado/autorizado | Teste real de acesso indevido, checksum, expiração, recuperação e alerta; custo/egress medidos |
| P15 | Jornada/automação de produto ainda não executa gatilhos; integrações sociais só contratos nesta rodada | Manter indisponibilidade explícita; desenvolver executor com aprovação/idempotência e qualificar publicação por rede/escopo | G; rede/conta e eventual plano externo; testes locais gratuitos | Gatilho autorizado produz ação confirmada uma vez; falha externa auditável; nenhuma ativação meramente visual |
| P16 | Checkout/email/OAuth/voz/UI completa sem E2E externo/visual atual | Matriz de papéis, fluxos de recuperação, fontes reais e dispositivos; ambientes sandbox e autorização específica | M/G; depende dos provedores; sem transação real nesta etapa | Jornadas críticas aprovadas com escopo/consentimento, estado real e acessibilidade; sem tratar demonstração como produção |

### Prioridade baixa — higiene e reprodutibilidade

| ID | Problema e impacto | Solução recomendada e dependências | Complexidade / investimento | Critério objetivo de conclusão |
| --- | --- | --- | --- | --- |
| P17 | Onze ocorrências Ruff e descoberta fragmentada de testes | Ajustes mecânicos autorizados futuramente; script de CI com escopo explícito incluindo sete testes Craft, e lanes Linux separadas | P/M; sem API paga | Lint limpo e inventário CI explica exatamente o que executa/pula |
| P18 | Três advisories moderados na cadeia Mammoth | Acompanhar versão compatível/isolamento do caminho vulnerável; avaliar alcançabilidade real; não aplicar downgrade cego | M; sem API paga | Remediação compatível ou aceitação de risco fundamentada, testes DOCX e auditoria atualizada |
| P19 | Mudanças locais/não rastreadas não representam entrega reproduzível no Git/produção | Após autorização separada, revisar diff, preservar licenças/fontes, separar artefatos e preparar snapshot reprodutível | M; sem API paga | Checkout limpo/reproduzível em ambiente novo com mesmas versões e evidências; publicação só após autorização |

## 13. Próximas implementações recomendadas

**Primeiro investimento recomendado é consolidar o que já existe, não contratar uma nova stack de editor.**

Cinco próximas ações, na ordem:

1. **Fechar o inventário de falhas e evidências do MVP.** Distinguir ausências recuperáveis, contratos aposentados e defeitos atuais; não exigir todos os experimentos como pré-requisito para um MVP restrito, mas não chamá-los de prontos.
2. **Reproduzir o ambiente audiovisual suportado.** FFmpeg canônico deve continuar independente de IA; Craft precisa de uma decisão explícita de provisionamento para habilitar composição/motion. Criar ambiente de homologação, não mexer diretamente em clientes.
3. **Fechar tetos financeiros de ponta a ponta.** Estender controles aos SDKs Node, registrar tentativas/custos e tratar configurações em disco que já permitiriam chat/TTS. Só depois autorizar inferência.
4. **Qualificar planejamento antes de geração cara.** Comparar Flash econômico e Opus via conexão OpenRouter existente em briefs idênticos, JSON validado, ferramentas limitadas, latência/custo/qualidade medidos. Não escolher por marketing do modelo.
5. **Qualificar um gerador de imagem e um de cena; depois integrar o ciclo.** Começar pelo adapter Gemini Image já existente e um entre Gen-4.5/Omni; preservar assets, direitos, jobs, revisão e orçamento. Expandir depois de obter evidência real.

Reutilizar: governança/sessão, biblioteca privada, documento canônico, revisões, recibos/idempotência, fila local/contratos Celery, FFmpeg, conexões LLM, schemas de comandos, review e adapters existentes. Não duplicar APIs de geração nem reconstruir o frontend.

Desenvolvimento ainda necessário: observações multimodais entregues ao planejador; orquestração por produção/cena/asset com admissão comercial; routing por capacidade/custo; aprovação humana explícita; correção limitada por evidência; custos/faturas e operação administrativa; executor das Jornadas, se mantido no escopo do produto.

Nenhum teste pago é necessário para começar as ações 1–3, alinhar contratos, criar schemas, validar ferramentas ou melhorar CI. Inferência representativa, benchmark com fornecedor e qualificação de acesso passam a exigir conta/budget e autorização após os gates de segurança. Não há garantia de que free tier seja elegível, privado ou suficiente para dados de marca.

## 14. Roadmap por fases

| Fase | Entrega e dependências | Gate de saída | Uso financeiro |
| --- | --- | --- | --- |
| **0 — Diagnóstico fechado** | Adotar este inventário; definir MVP suportado e owners; preservar artefatos e casos de falha | Nenhum recurso anunciado sem classificação/evidência; prioridades aceitas | Sem API paga |
| **1 — Base reprodutível** | P01/P03/P04/P10/P17/P19; ambiente isolado, FFmpeg, Craft quando parte do MVP, contratos e CI por plataforma | Importar → editar → salvar → recuperar → renderizar → baixar em novo ambiente; testes críticos verdes e limites conhecidos | Pode usar infraestrutura local já existente; contratação só se necessária/autorizada |
| **2 — Governança e catálogo** | P02/P06/P08/P11/P12; modelo/capacidade/tarifa por função, ledger comum e admin seguro | Ausência de saldo impede rede; trocas/erros/replays não geram duplicação nem vazam segredo | Testes locais sem inferência |
| **3 — Planejamento qualificado** | Flash como referência econômica; Opus como comparação controlada via OpenRouter; dados sintéticos/autorizados | Roteiro/plano/commands válidos, orçamento/latência e avaliação humana registrados | Primeiro gate proposto até US$5, somente após autorização |
| **4 — Mídia qualificada** | Um gerador de imagem e um de cena entre integrações existentes; referência/direitos/formatos/poll/download | Artefatos reais, qualidade/preservação mensuradas, resultado desconhecido conciliável | Segundo gate proposto até US$10; não ativado nesta auditoria |
| **5 — Ciclo fechado limitado** | P07: material real → observação → plano → tool → render → QC → correção aprovada → entrega | Produção representativa completa com trilha de evidência, limite de tentativas e aprovação humana quando exigida | Cada nova chamada/correção tem orçamento explícito |
| **6 — Operação profissional** | P09/P13/P14/P15/P16 conforme MVP; carga, monitoramento, S3, backup, papéis, redes e serviços | SLO, segurança, custo, restauração e jornadas de produto homologados | Tarifas reais de infraestrutura e APIs contratadas; sem estimativas fictícias |

Voz/clonagem/avatar não precisam bloquear uma primeira versão de imagem + cenas + montagem com trilha importada. Se forem obrigatórios para a oferta, P09 e seus gates de licença/consentimento tornam-se pré-requisitos da fase de entrega, não atalhos por material simulado.

## 15. Conclusão técnica

A evolução recente é verificável: a Clicko deixou de depender de respostas falsas nas rotas antigas, passou a montar timelines canônicas reais e ganhou fronteiras melhores de autenticação, cotas, orçamento, revisão e prontidão. **Existe um núcleo audiovisual local utilizável dentro do subset testado.**

A evidência atual não sustenta chamar a plataforma inteira de pronta, autônoma ou profissional em todos os módulos. O backend global continua com falhas; motores Craft, infraestrutura distribuída, percepção/voz/modelos especializados e geração remota não estão homologados. O processo de desenvolvimento também não estava ativo nos endpoints da prévia durante esta auditoria.

Trocar o LLM por Opus ou Gemini não supre motor, assets, percepção, ferramentas, dinheiro, qualidade e operação. O caminho mais curto é qualificar a base existente, fechar o controle financeiro de todos os serviços, validar um planejador e poucos geradores e só então unir o fluxo com evidências e correções limitadas.

**Esta etapa entregou análise e documentação, não novas implementações.** Não foram alterados código, dependências ou configurações persistentes; não houve operação paga, deploy, commit, push ou edição de dados de usuários. Foram gerados somente o relatório, logs/artefatos de QA e saídas normais de teste/build. Credenciais não são incluídas neste documento.

### Referências técnicas principais para continuidade

- Entrada/navegação: `src/App.tsx`, `src/studios/StudiosWorkspace.tsx`, `src/studios/studioNavigation.ts`.
- Edição: `src/studios/video/CanonicalVideoEditor.tsx`, `videoModel.ts`, `canonicalTimeline.ts`, `src/studios/image/ImageStudio.tsx`.
- Governança: `server/governance.ts`, `server/atomicJsonStore.ts`, `server/studios/proxy.ts`, `imageQuota.ts`, `videoQuota.ts`.
- KLIC: `server/klic/router.ts`, `conversationRouter.ts`, `providerConfig.ts`, `providerRetry.ts`, `server/voice/router.ts`.
- API/infra: `backend/app/main.py`, `studio_app.py`, `studio_routes.py`, `http_middleware.py`, `config.py`, `database.py`, `celery_app.py`, `routers/health.py`.
- Execução: `services/studios/jobs.py`, `local_queue.py`, `production_queue.py`, `timeline_editor.py`, `timeline_ai.py`, `craft_ai.py`, `editorial_production.py`.
- Motores/provedores: `providers/studios/timeline_ffmpeg.py`, `media_runtime.py`, `craft.py`, `gemini_editing.py`, `runway_editing.py`, `universal_llm.py`, `llm_catalog.py`, `material_providers.py`.
- Custo/estado: `services/studios/external_policy.py`, `llm_connections.py`, `gemini_editing.py`, `media_usage.py`, `hybrid_video.py`.
- Persistência: `services/object_storage.py`, `server/integrations/repository.ts`, `postgresRepository.ts`, manifests em `workers/media-cpu` e fontes fixadas em `workers/craft/sources.lock.json`.
