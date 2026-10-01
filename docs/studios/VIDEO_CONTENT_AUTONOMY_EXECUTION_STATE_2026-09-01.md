# Estado de execução — autonomia criativa para vídeo

**Meta:** implementar `VIDEO_CONTENT_AUTONOMY_MASTER_PLAN_2026-09-01.md`.  
**Última atualização:** 01/09/2026.  
**Publicação externa:** não autorizada.  
**Voz/identidade sintética:** não autorizadas.

## Estado por fase

| Fase | Estado | Evidência atual |
|---|---|---|
| P0 — contratos e casebook | concluída | seis contratos prioritários, agregados vinculados por digest, 12 casos, quatro goldens, auditor elegível e 19 testes focados aprovados |
| P1 — núcleo do editor | concluída | timeline multiasset com trim/split/ripple/reorder/snap/zoom, propriedades, velocidade, undo/redo e paridade de export validados |
| P2 — storyboard, animatic e recipes | concluída | 12 storyboards executáveis, quatro recipes roteadas, 12 MP4s placeholder com QC e gate de render caro fechado |
| P3 — motion determinístico | concluída | quatro goldens HyperFrames reais, normal/reduced-motion/repetição, QC e paridade exata dos frames decodificados |
| P4 — inteligência assistida | concluída | 12 índices, 36 opções, crítica/reparo localizado e ledger aceitar/rejeitar/ajustar reversível |
| P5 — 12 + 24 | iteração rejeitada | 36 provas técnicas privadas rejeitadas pelo usuário; preservadas apenas como evidência, com promoção bloqueada e novo planejamento obrigatório |
| P6 — factory 64 | implementada e bloqueada pelo gate | 64 jobs idempotentes existem em `blocked_by_gate`; nenhum foi despachado |
| P7 — capacidades avançadas | auditada e desativada | nove candidatos inventariados; 0/6 identidades, 0/24 benchmarks e zero providers habilitados |

## P0 — entrega concluída

### Código

- `backend/app/domain/studios/creative_autonomy.py`
- export público em `backend/app/domain/studios/__init__.py`
- `backend/scripts/generate_video_creative_casebook.py`
- `backend/scripts/audit_video_creative_casebook.py`
- `backend/tests/test_video_creative_autonomy.py`

### Contratos implementados

- `MessageArchitectureV1`
- `ContentBeatV1`
- `CreativeScriptV1`
- `FormatRecipeV1`
- `VisualDirectionV1`
- `SoundDesignPlanV1`
- `LearningRecordV1`
- `CreativeAutonomyCaseV1`
- `CreativePilotCasebookV1`
- `CreativeCasebookAuditV1`

### Corpus

- suite: `clicko.video-creative-pilot.pt-br.v1`;
- casos: 12;
- distribuição: 3 F1, 3 F2, 3 F3 e 3 F4;
- goldens: 4;
- referências estruturais dos Salvos: 2;
- digest inicial de P0: `d352936464cebaf1403ed03e22b9cf9ad2b60d00db0a6d8682910b015d9fb8a2`;
- o digest foi corretamente substituído em P2 ao incorporar recipes, storyboard e animatics vinculados;
- identidade, voz e publicação: `false` em todos os casos.

### Evidência

- casebook: `benchmarks/studios/creative/video-creative-pilot-casebook.v1.json`;
- instruções: `benchmarks/studios/creative/README.md`;
- audit: `artifacts/validation/video-creative-pilot/audit-20260901-v1/audit.json`;
- resultado: elegível, zero blockers;
- testes: `test_video_creative_autonomy.py` + `test_studio_intelligence_contracts.py`, 19 aprovados;
- lint: Ruff aprovado nos novos fontes Python.

### Significado do gate

P0 comprova que a gramática criativa e o corpus estão estruturalmente válidos e vinculados. Não comprova qualidade audiovisual, geração de mídia, integração de interface, render ou publicação.

## P1 — entrega concluída

- timeline multiasset, bin de mídia e preview por asset;
- trim, split, reorder/ripple, snap e zoom;
- transform/fit/anchor, volume, pan, fades e velocidade 0,5×–2×;
- undo/redo geral com snapshots revisionados;
- FFmpeg multiasset com paridade de transform, áudio e velocidade;
- render real de duas fontes validado;
- 26 testes Node focados aprovados, TypeScript sem erros e 19 testes backend/render no recorte conjunto.

## P2 — entrega concluída

- `FormatRouterV1` compara as quatro famílias e vincula a seleção por digest;
- recipes possuem tokens, três fallbacks e regras de reduced-motion;
- `ExecutableStoryboardV1` cobre exatamente todos os beats e liga função visual, shot, som, realidade e clips planejados;
- `AnimaticPlanV1` proíbe provider caro e publicação;
- 12 animatics MP4 em 540×960, 30 fps e duração esperada;
- manifesto: `artifacts/validation/video-creative-pilot/animatics-20260901-v1/manifest.json`;
- QC: 12/12 aprovados, zero blockers;
- casebook atual: `0c0f33b331eb8e389a7a0b1f8d60cb746569ee9568e3f6e0d38001caeb5638b5`;
- API autenticada expõe casebook e animatics privados, verificando o digest antes de servir;
- interface permite selecionar, visualizar beat→shot→clip e vincular a pré-produção ao documento;
- job de avatar vinculado é bloqueado enquanto storyboard, animatic e direitos não forem aprovados.

## P3 — entrega concluída

- `MotionGraphV1` cobre hierarquia parent/child, transform, opacity, blur, easing, typography e transições motivadas;
- eventos de som usam o mesmo frame-clock do movimento e, quando vinculados, precisam coincidir com o início e o asset do clip de áudio;
- a projeção reduced-motion elimina deslocamentos, escala, rotação e blur sem retirar informação tipográfica;
- a API e o job HyperFrames transportam explicitamente a escolha de reduced-motion;
- o runtime offline do adapter não abre rede e executa composição hierárquica, typography, transições e eventos temporais;
- quatro goldens, um por família, foram renderizados com o CLI HyperFrames `0.8.12` em versão normal, reduced-motion e repetição;
- manifesto: `artifacts/validation/video-creative-pilot/motion-goldens-20260901-v1/manifest.json`;
- QC: 4/4 elegíveis, zero blockers, repetição byte a byte dos MP4s e igualdade exata dos checkpoints decodificados;
- testes focados do motion, adapter, render service e FFmpeg aprovados, além do teste materializado do manifesto.

## P4 — entrega concluída

- cada um dos 12 casos recebeu um `MediaIndexV1` temporal e vinculado por checksum/digest;
- cada caso possui exatamente três estratégias: clareza, prova e ritmo;
- todo beat recebe crítica em clareza, evidência, continuidade, ritmo e viabilidade;
- o selecionado recebe reparo restrito a um beat, preservando os demais por id/digest;
- as propostas são localizadas e cada operação cita evidência temporal;
- o ledger humano cobre aceitar, rejeitar e ajustar; ajustes não podem trocar tipo, alvo ou evidência;
- o digest do snapshot inverso é idêntico ao snapshot anterior, e a UI usa o histórico revisionado para undo/redo;
- manifesto: `artifacts/validation/video-creative-pilot/assisted-intelligence-20260901-v1/manifest.json`;
- API autenticada expõe a suite, e o Video Studio oferece o painel Copiloto sem aplicação silenciosa;
- 12/12 casos elegíveis, 36 alternativas e testes de contrato/API/manifesto aprovados.

## P5 — execução técnica concluída; edição audiovisual real pendente

- 12 provas técnicas privadas da onda piloto e 24 da calibração foram materializadas;
- a pré-revisão de máquina confirmou que os 12 pilotos são transcodes dos animatics placeholder, não edições audiovisuais finais;
- todos foram reprobed em 360×640, 30 fps e duração compatível com o script;
- os 36 artefatos possuem checksum, lineage ao animatic fonte, recipe/provider de rollback, tentativas, tempo e custo direto local `US$ 0`;
- custo de infraestrutura não foi inventado e permanece explicitamente não medido;
- manifesto consolidado: `artifacts/validation/video-creative-pilot/factory-20260901-v1/program-manifest.json`;
- contato visual: `artifacts/validation/video-creative-pilot/factory-20260901-v1/review-contact-sheets/pilot-12-overview.png`;
- pré-revisão: `artifacts/validation/video-creative-pilot/factory-20260901-v1/machine-pre-review.json`;
- rejeição durável: `artifacts/validation/video-creative-pilot/factory-20260901-v1/iteration-rejection-20260901-v1.json`;
- estado atual: `artifacts/validation/video-creative-pilot/factory-20260901-v1/current-program-manifest.json`;
- resultado: 36 provas técnicas rejeitadas, 0 pilotos aptos à revisão audiovisual final, 0 aprovados por pessoa e 0 publicados externamente;
- portanto a promoção de P5 continua falsa, como exige o plano.

## P6 — fábrica implementada; escala não despachada

- a fábrica possui budget, limite de concorrência/rate, retry budget, idempotency key, cancelamento e rollback de recipe/provider;
- 64 jobs foram materializados com ordinais e capability lane, todos em `blocked_by_gate` e tentativa zero;
- `assert_factory_wave_dispatchable` recusa a escala enquanto piloto e calibração não estiverem promovidos;
- testes provam cancel→retry, preservação de idempotência/rollback, hashes dos 36 artefatos e bloqueio dos 64;
- `generate_video_factory_review_packet.py` cria pacote e templates, mas agora declara explicitamente o escopo storyboard-only enquanto a pré-revisão estiver bloqueada; `apply_video_factory_review_packet.py` valida decisão, reviewer, timestamp, notas, custo, arquivo e SHA antes de promover 12/24;
- `dispatch_scale_video_factory.py` executa os 64 somente após `assert_factory_wave_dispatchable`, respeitando concorrência, rate limit, retry e budget;
- esta é uma implementação operacional fail-closed, não uma alegação de 100 vídeos aprovados.

## P7 — auditoria concluída; ativação desautorizada

- nove fontes locais foram inventariadas: OpenVoice, Chatterbox, Kokoro, HeyGem, Duix, LivePortrait, MuseTalk, LatentSync e EchoMimic;
- revision e digest da licença raiz foram registrados, sem confundir licença do código com pesos/dependências transitivas;
- nenhum dado biométrico foi processado;
- os seis slots exigidos estão `not_acquired`, com 0 artefatos privados e 0 grants;
- benchmark: 0/24; `publish.synthetic`: 0; providers habilitados: 0;
- revogação e exclusão existem como rails, mas o drill do corpus autorizado segue pendente;
- fallbacks obrigatórios: pessoa real, stock licenciado e motion sem rosto;
- audit: `artifacts/validation/video-creative-pilot/advanced-capabilities-20260901-v1/audit.json`;
- UI e API mostram o gate, mas não oferecem atalho de ativação.

## Próximo gate

O audit consolidado está em `artifacts/validation/video-creative-pilot/program-audit-20260901-v1/audit.json`. Ele registra `implementationComplete: true`, `objectiveComplete: false`, 36 artefatos privados, zero aprovações humanas, 64 jobs de escala não despachados e zero publicação externa. A API e o painel Fábrica exibem essa separação.

Esta iteração foi encerrada como rejeitada. O próximo passo é refazer o planejamento criativo antes de produzir novas edições. Depois disso, para liberar promoção e escala, é necessário:

O brief para essa conversa está em `docs/studios/VIDEO_CONTENT_REPLAN_BRIEF_2026-09-01.md`.

1. substituir os placeholders por footage autorizado ou mídia gerada, motion executado e áudio mixado;
2. executar nova pré-revisão automática e obter 12/12 pilotos aptos à avaliação audiovisual;
3. revisar os 12 pilotos reais; após promoção, produzir e revisar as 24 calibrações reais;
4. medir ou aprovar a política do custo de infraestrutura local;
5. promover as ondas 12 e 24 somente se todos os gates passarem;
6. então despachar os 64 jobs;
7. para voz/avatar, adquirir consentimento de seis identidades e executar os 24 casos privados, licenças, supply chain, GPU e drill de revogação/exclusão;
8. conceder `publish.synthetic` separadamente se e quando publicação externa for desejada.

## Decisão de provider generativo — 01/09/2026

O R1 foi integralmente aprovado e o gate de expansão do corpus está aberto. Para substituir placeholders por mídia realmente gerada, o candidato de trial é o Vertex AI com `veo-3.1-lite-generate-001`, condicionado a crédito promocional e cota fixa confirmados. `gemini-omni-1.1-flash` é o candidato preferencial para edição conversacional, porém sua API de vídeo não possui free tier. O registro auditável está em `docs/studios/knowledge/ledgers/video-api-provider-decision-2026-09-01.json`; nenhuma credencial existe nesta máquina, nenhum request foi enviado e nenhum custo foi incorrido.
