# Plano profundo de implementação — 57 telas aprovadas do Stitch

> **Estado em 2026-08-15:** implementado e validado. A direção final trata os 57 frames como estados de uma única obra: componentes e navegação compartilhados, dashboard com lógica editorial preservada dentro do visual Stitch e nenhum iframe no produto.

## 1. Objetivo e limite desta fase

Este documento planeja a implementação integral das telas aprovadas nos dois projetos válidos do Stitch:

- `Clicko — Telas Finais Aprovadas` (`17470294547707956073`): **38 telas**.
- `Clicko — Creative Lab — Social Media OS` (`15926565735319496264`): **19 telas**.
- Total: **57 telas reais**.

Ficam fora do escopo:

- `Clicko — Creative OS Redesign v1` (`17888498704441547684`), marcado como descartável.
- Os três nós de paleta/`DESIGN.md` e a imagem de referência existentes nos canvases; eles não são telas.

Esta fase é somente de planejamento. Nenhuma funcionalidade ou tela é implementada por este documento.

### Precedência de requisitos

O documento anterior de inteligência funcional continua válido para regras de negócio, persistência, rastreabilidade e jornada conectada. A solicitação atual, porém, autoriza explicitamente implementar as telas aprovadas do Stitch. Portanto, a proibição anterior de criar telas deixa de se aplicar às 57 telas deste inventário. Continuam válidas as seguintes regras:

- preservar dados e funcionalidades saudáveis;
- não substituir dados reais por métricas inventadas;
- manter o contexto `workspace → marca → oportunidade → campanha → conteúdo → resultado`;
- não recolorir ou alterar o logotipo oficial;
- evitar reescritas de backend que não tenham justificativa técnica;
- tratar o Stitch como fonte visual, e os contratos de domínio como fonte funcional.

## 2. Critérios definidos para lacunas do Stitch

Quando o Stitch não especificar um comportamento, aplicar estes critérios:

1. **Desktop canônico:** fidelidade visual em 1280×1024 e 1440×900.
2. **Responsividade derivada:** abaixo de 1024 px, preservar tarefas e hierarquia, transformando painéis laterais em drawers; abaixo de 768 px, usar uma coluna e navegação compacta. Não criar novos módulos por causa da responsividade.
3. **Idioma:** interface em português-BR. IDs técnicos, formatos e nomes próprios podem permanecer em inglês.
4. **Tema:** o tema escuro é a referência de aceite das 57 telas. O tema claro existente não será removido, mas sua paridade visual será uma fase posterior.
5. **Acessibilidade:** navegação completa por teclado, foco visível, semântica adequada e contraste WCAG AA para texto e controles.
6. **Interação:** nenhum controle principal poderá ser decorativo. Ações ainda dependentes de terceiros deverão produzir um estado honesto de indisponibilidade ou simulação explicitamente marcada em desenvolvimento.
7. **Dados:** cada métrica deve declarar sua origem como `real`, `informada pelo usuário` ou `hipótese`. Dados de demonstração só podem existir em fixtures de desenvolvimento/teste.
8. **Estados:** toda tela de dados terá `loading`, `empty`, `error`, `permission denied`, `stale` e `success` quando aplicável.
9. **Estados visuais repetidos:** frames como menu aberto/fechado, inspector ativo e focus mode serão estados do mesmo componente, não páginas duplicadas.
10. **Assets:** imagens e HTML do Stitch servem como referência; a aplicação final será construída com componentes, dados e assets persistidos, nunca com screenshots embutidos.

## 3. Diagnóstico técnico atual

### Frontend ativo na `main`

- React 19, TypeScript, Vite 6, Tailwind 4 e Express.
- Navegação atual controlada por `currentTab` em `src/App.tsx`; não há URLs profundas nem restauração de rota após reload.
- Há 22 valores em `NavigationTab` e 34 componentes de tela, vários parcialmente sobrepostos.
- `OperationsContext` concentra marca, clientes, campanhas, posts, assets, handoff e aprendizado em `localStorage`.
- `GovernanceContext` usa endpoints Express em memória, complementados por `localStorage`.
- Endpoints de IA estão no `server.ts`; vários componentes chamam `/api/ai/*` diretamente.
- O TypeScript está saudável no baseline: `npm run lint` passa.

### Design system atual

- `src/index.css` possui mais de 100 mil bytes e várias camadas de override.
- Existem definições duplicadas de tokens de tema.
- Há **554 ocorrências** do verde legado `#8bd132` no CSS/TSX.
- A paleta aprovada no sistema real e aplicada ao Stitch é:
  - fundo: `#080808`;
  - superfícies: `#0F0F0F`, `#151515`, `#1C1C1C`, `#222222`;
  - controles: `#111111`;
  - bordas: `#282828` e `#353535`;
  - texto: `#F5F5F5`, `#A0A0A0`, `#666666`;
  - ação primária coral: `#FF5C5C`, hover `#FF7070`, active `#E94E4E`;
  - criação/dados laranja: `#FF7A00`, hover `#FF8F2A`, active `#E66E00`;
  - perigo: `#E87979`;
  - logo: preto sólido `#000000`, sem filtros ou recoloração.

### Backend preservado, mas não ativo na `main`

- A `main` contém apenas restos não rastreados do backend Python: bancos SQLite, caches, bytecode e cobertura. Os fontes `.py` não estão presentes no working tree.
- A base funcional FastAPI está preservada na branch `codex/vps-production-foundation`.
- As extensões mais recentes estão no stash `stash@{0}` e no commit de untracked files `stash@{0}^3`:
  - migrations `0007_workspace_features`, `0008_approval_events`, `0009_brand_versions`;
  - routers de analytics e workspace features;
  - serviço de marca;
  - testes de jornada, prontidão, aprovações, analytics e Radar.
- `backend/nexus.db` possui 19 tabelas, incluindo workspaces, marca, oportunidades, campanhas, posts, documentos criativos, assets, lineage/feedback, métricas, auditoria e jobs.
- A maioria das tabelas do fluxo principal está vazia; os quatro workspaces e perfis de marca são o principal conteúdo persistido atualmente.

### Conclusão do diagnóstico

Não é seguro montar 57 telas diretamente sobre `currentTab`, contextos monolíticos e armazenamento local. O primeiro gate do modo meta deve recuperar o backend fonte, preservar a UI atual e criar uma camada de navegação, contratos e design system antes de expandir telas.

## 4. Arquitetura-alvo

### 4.1 Organização do frontend

Estrutura desejada, adotada incrementalmente:

```text
src/
  app/
    router/
    shell/
    providers/
  design-system/
    tokens.css
    primitives/
    patterns/
  features/
    workspace/
    brand-memory/
    radar/
    campaigns/
    content/
    creative-editor/
    library/
    approvals/
    publishing/
    analytics/
    automations/
    governance/
  api/
    client.ts
    contracts/
  test/
    fixtures/
    factories/
```

Regras:

- migrar componentes existentes por feature, sem big-bang rewrite;
- usar um manifesto único de rotas e permissões;
- usar URLs reais e parâmetros (`workspaceId`, `campaignId`, `contentId`, `documentId`);
- separar estado de servidor, estado efêmero de UI e estado transacional do editor;
- impedir fetches dispersos nos componentes por meio de uma camada de API tipada;
- manter contextos globais somente para sessão, workspace ativo, tema e comandos globais;
- usar reducers/command stack no editor para undo/redo, autosave e histórico.

### 4.2 Rotas canônicas

```text
/login
/workspaces/new
/today
/discover
/radar
/brand-memory
/campaigns
/campaigns/new
/campaigns/:campaignId
/campaigns/:campaignId/world
/campaigns/:campaignId/moodboard
/campaigns/:campaignId/studio
/content
/content/dashboard
/content/new
/content/:contentId
/content/:contentId/edit
/content/:contentId/variations
/content/:contentId/remix
/library
/library/assets
/library/lineage
/templates
/calendar
/approvals
/approvals/:contentId
/publish
/publish/:campaignId
/analytics
/analytics/learning
/automations
/automations/:automationId
/settings/profile
/settings/team
/settings/channels
/settings/ai-governance
/settings/billing
/settings/audit
```

Estados que não viram rotas independentes:

- menu essencial aberto/fechado;
- Tool Atlas aberto, busca por intenção e personalização;
- dropdown `Criar`;
- Spotlight global;
- Workspace Switcher;
- Copilot contextual;
- focus mode do editor;
- inspectors de tipografia, elementos, efeitos e motion.

### 4.3 Design system

Antes das telas, criar uma camada de tokens sem hexadecimais espalhados:

- cores semânticas: `background`, `surface`, `surfaceElevated`, `border`, `text`, `textMuted`, `action`, `creative`, `danger`, `success`, `warning`;
- tipografia Geist para interface e JetBrains Mono apenas onde a especificação pedir metadados/títulos técnicos;
- primitives: Button, IconButton, Input, Select, Tabs, Badge, Card, Dialog, Drawer, Tooltip, Table, EmptyState, Skeleton e Toast;
- patterns: AppShell, CampaignShell, EditorShell, InspectorPanel, CommandPalette, DataTable e MetricCard;
- proibir novo `#8bd132` e remover as 554 ocorrências durante a migração;
- manter o componente `ClickoLogo` como único ponto de renderização da marca.

## 5. Modelo de domínio e contratos

### Núcleo já existente a reaproveitar

- `workspaces`, `memberships`, `users`;
- `brand_profiles` e versões;
- `external_signals`, `radar_sources`, `opportunities`;
- `campaigns` com origem em oportunidade;
- `posts`, `creative_documents`, `library_assets`;
- `approval_events`, `audit_events`, `feedback_events`;
- `post_metric_snapshots`, `job_audits`, `workspace_resources`.

### Evoluções necessárias

1. **Campanha:** status, owner, objetivo, budget, progresso, world, moodboard, canais, janela e kit planejado.
2. **Conteúdo:** relação explícita com campanha, oportunidade, post de origem e documento criativo.
3. **Lineage:** grafo de derivação entre conteúdos/versões, sem depender apenas de JSON embutido.
4. **Editor:** documento por camadas versionado; autosave otimista com controle de versão; histórico de comandos; export jobs.
5. **Variações:** presets de formato, safe areas, resultado de validações e racional da variação.
6. **Assets:** origem, direitos, tags, hash, dimensões, aprovação de marca e armazenamento privado.
7. **Publicação:** contas conectadas, permissões, tokens cifrados, publish jobs, retries, idempotência e status por canal.
8. **Aprovação:** comentários, sign-offs, solicitação de mudanças, comparação de versões e transições auditadas.
9. **Analytics:** métricas por snapshot, baseline, fonte, confiança e insights derivados sem inventar dados.
10. **Automação:** definição versionada do grafo, nodes, runs, eventos e logs.
11. **Capacidade:** limites de plano calculados no servidor, nunca apenas na UI.

### Contratos de fluxo prioritários

```text
BrandContext
  → RadarState
  → Opportunity
  → CampaignDraft
  → Campaign
  → ContentBrief
  → CreativeDocument
  → Approval
  → PublishJob
  → MetricSnapshot
  → LearningInsight
```

Toda transição carrega `workspaceId`, versão da memória da marca, origem e timestamps. Geração de IA e jobs usam chave de idempotência e guardam versão do prompt/modelo.

## 6. Matriz de rastreabilidade das 57 telas

Legenda: **Reusar** = componente atual aproveitável; **Evoluir** = existe parcialmente; **Novo estado** = novo estado de módulo compartilhado; **Nova tela** = rota ainda inexistente.

### Projeto A — Telas Finais Aprovadas (38)

| # | Frame do Stitch | Destino técnico | Estratégia |
|---:|---|---|---|
| A01 | Campaign Room V3 | `/campaigns/:campaignId` | Evoluir `StrategyView` para `CampaignShell` com overview, peças, calendário, aprovações e resultados. |
| A02 | Contextual Copilot V5.1 | `CopilotPanel` global contextual | Evoluir `FloatingAIAssistant` e `AIChatContext`; manter contexto, citações e ações. |
| A03 | Lineage Library V5 | `/library/lineage` | Nova tela sobre grafo de origem, derivados, versões e desempenho. |
| A04 | Tool Atlas V7.2 — Atlas completo aberto | `ToolAtlasOverlay(open)` | Novo estado global baseado em manifesto de ferramentas e permissões. |
| A05 | Newsroom V3 | `/discover` | Nova tela de sinais editoriais priorizados, filtros, janela e risco. |
| A06 | Settings Command V5 | `/settings/ai-governance` | Evoluir Settings com autonomia, retenção, fontes e reindexação. |
| A07 | Navigation V6.5 — Visual Editor / Focus Mode | `EditorShell(focus)` | Novo estado do shell; remove distrações sem perder navegação de saída. |
| A08 | Channel Connections V5 | `/settings/channels` | Evoluir ConnectedAccounts com conexão, permissões, saúde e renovação. |
| A09 | Reuse Workshop V5 | `/content/:contentId/remix` | Evoluir handoff de reutilização para preview, aprendizado e formatos. |
| A10 | Tool Atlas V7.3 — Busca por intenção | `ToolAtlasOverlay(search)` | Novo estado com intenção, melhor correspondência e itens recentes. |
| A11 | Tool Atlas V7.4 — Personalizar e retomar | `ToolAtlasOverlay(customize)` | Novo estado com fixados persistidos e trabalhos recentes. |
| A12 | Template Systems V5 | `/templates` | Evoluir Templates com taxonomia, governança, variantes e inspector. |
| A13 | Essential Menu V8.2 — Aberto | `EssentialMenu(open)` | Novo estado responsivo do shell; conteúdo vem do manifesto. |
| A14 | Approval Room V5 | `/approvals/:contentId` | Evoluir Approvals com comparação, evidências, comentários e sign-offs. |
| A15 | Radar Room V4 | `/radar` | Nova tela conectada ao backend de sinais, fontes, scoring e feedback. |
| A16 | Studio Composer V5 | `/campaigns/:campaignId/studio` | Evoluir Studio para kit multiformato ligado à campanha. |
| A17 | Team Access Room V5 | `/settings/team` | Evoluir TeamManagement com escopos, convites e approval flows. |
| A18 | Navigation V6.1 — Hoje / Descobrir | `AppShell(today)` | Substituir navegação por `currentTab` por shell orientado ao ciclo. |
| A19 | Publisher Control V5 | `/publish/:campaignId` | Evoluir Publisher com canais, permissões, preview e agendamento. |
| A20 | Navigation V6.4 — Campaign Room contextual | `CampaignShell` | Novo estado contextual de navegação dentro da campanha. |
| A21 | Top Dropdown V9 — Criar aberto | `CreateDropdown(open)` | Novo overlay com criação, reutilização, inteligência e retomada. |
| A22 | Subscription Capacity V5 | `/settings/billing` | Evoluir Subscription com limites e uso calculados pelo servidor. |
| A23 | Workspace Entry V5 | `/workspaces/new` | Evoluir onboarding para inicialização de marca, canais e objetivos. |
| A24 | Workspace Switcher V5 | `WorkspaceSwitcherDialog` | Evoluir seletor com saúde, último evento e troca transacional. |
| A25 | Global Spotlight V5 | `GlobalSpotlightDialog` | Evoluir Spotlight com busca remota, comandos e permissões. |
| A26 | Audit Trail V5 | `/settings/audit` | Evoluir AuditLogs com filtros, diffs e origem humana/IA/sistema. |
| A27 | Brand Memory V4.1 | `/brand-memory` | Evoluir BrainView com prontidão, versões, fontes e governança. |
| A28 | Automation Workshop V5 | `/automations/:automationId` | Evoluir AutomationBuilder para grafo persistido e runs auditáveis. |
| A29 | Essential Menu V8.1 — Fechado | `EssentialMenu(closed)` | Estado padrão do mesmo componente de A13. |
| A30 | Editorial Calendar V5 | `/calendar` | Evoluir Calendar com campaign lanes, drag/drop e conflitos. |
| A31 | Tool Atlas V7.1 — Menu fechado | `ToolAtlasOverlay(closed)` | Estado fechado/trigger do mesmo componente de A04. |
| A32 | Navigation V6.2 — Etapa Criar aberta | `/content/new` + shell | Novo create hub que distribui para post, carrossel, visual e vídeo. |
| A33 | Video Studio V5 | `/content/:contentId/edit?mode=video` | Evoluir VideoEditor com timeline, captions, layers e export. |
| A34 | Performance Observatory V5.3 | `/analytics/learning` | Evoluir Analytics para telemetry, insights e evidência. |
| A35 | Carousel Builder V5 | `/content/:contentId/edit?mode=carousel` | Evoluir criação de slides com narrative spine e validações. |
| A36 | Campaign Intake V4.1 | `/campaigns/new` | Nova revisão curta; recebe oportunidade e cria campanha sem formulário vazio. |
| A37 | Visual Editor V5 | `/content/:contentId/edit?mode=visual` | Evoluir editor por camadas, inspector, copilot, autosave e export. |
| A38 | Navigation V6.3 — Workspace Switcher | `WorkspaceSwitcherMenu` | Estado compacto de A24 integrado ao shell. |

### Projeto B — Creative Lab (19)

| # | Frame do Stitch | Destino técnico | Estratégia |
|---:|---|---|---|
| B01 | Campaign Moodboard | `/campaigns/:campaignId/moodboard` | Nova tela ligada à campanha e à biblioteca de assets. |
| B02 | Visual Content Board V2 | `/content` | Evoluir Library/Inventory para board visual, filtros e ações em lote. |
| B03 | Pro Composition Canvas V2 | editor visual compartilhado | Estado base do editor de A37, não outro editor. |
| B04 | Campaign World | `/campaigns/:campaignId/world` | Nova tela de narrativa, referências, direção e coerência da campanha. |
| B05 | Editorial Creation Desk V2 | `/content/:contentId/edit?mode=editorial` | Evoluir CreationStudio com copy, preview, referências e contexto. |
| B06 | Creative Review Room V2 | `/approvals/:contentId?view=creative` | Estado criativo de A14 com original, variação, sinais e comentários. |
| B07 | Precision & Type (Canvas State) | `InspectorPanel(typography)` | Estado do editor compartilhado; posição, constraints e tipografia. |
| B08 | Content Inventory V1 | `/content?view=inventory` | Estado tabular/lista de B02 com lote, status e campanha. |
| B09 | Brand Asset Library | `/library/assets` | Evoluir Library com DAM, guardrails, metadados e seleção no editor. |
| B10 | Format & Variation Board | `/content/:contentId/variations` | Nova tela de formatos, safe areas, risco e smart resize. |
| B11 | Visual Composition Handoff V1 | `CampaignContentHandoff` | Novo estado entre brief editorial e documento visual, com aceite explícito. |
| B12 | Visual Remix Lab V2 | `/content/:contentId/remix` | Estado avançado de A09 com derivações e racional de teste. |
| B13 | Carousel Builder | editor de carrossel compartilhado | Variante visual de A35; mesma rota e mesmo modelo de documento. |
| B14 | Motion Studio (Canvas State) | `InspectorPanel(motion)` | Estado do editor visual/vídeo com reduced motion e stagger. |
| B15 | Post Detail & Performance V1 | `/content/:contentId` | Nova tela de detalhe, versões, comentários, métricas e lineage. |
| B16 | Content Command Dashboard V1 | `/content/dashboard` | Nova visão operacional de produção, filas e saúde. |
| B17 | Post Creation Workspace V1 | `/content/new?type=post` | Evoluir CreationStudio para draft persistente com contexto de Radar/marca. |
| B18 | Element Vault (Canvas State) | `InspectorPanel(elements)` | Estado do editor com elementos aprovados e guardrails. |
| B19 | Effects & Light (Canvas State) | `InspectorPanel(effects)` | Estado do editor com presets, fills, sombras, blur e grain. |

## 7. Sequência de implementação no modo meta

### Fase 0 — Recuperação e baseline

1. Criar branch de trabalho `codex/stitch-implementation` a partir da `main` atual.
2. Registrar hashes da `main`, branch funcional e stashes; não aplicar stash destrutivamente.
3. Restaurar seletivamente o backend rastreado de `codex/vps-production-foundation`.
4. Restaurar os fontes adicionais de `stash@{0}^3` e reconciliar imports/migrations.
5. Não trazer automaticamente as versões antigas dos componentes visuais da branch funcional.
6. Remover bytecode/caches/bancos não rastreados somente depois de backup e validação do banco necessário.
7. Executar frontend lint/build, backend lint/test, migrations em banco temporário e smoke test.
8. Criar ADRs para router, camada de server state, storage de assets e estratégia de autosave.

**Gate:** fontes completos, migrations `0001–0009`, testes reproduzíveis e dados existentes preservados.

### Fase 1 — Fundação visual, navegação e contratos

1. Consolidar tokens e primitives.
2. Migrar a paleta e bloquear verde legado com verificação automática.
3. Criar router, manifesto de módulos, permissões e breadcrumbs.
4. Implementar `AppShell`, `CampaignShell` e `EditorShell`.
5. Criar cliente de API tipado, tratamento uniforme de erro e correlation IDs.
6. Criar fixtures apenas para Storybook/testes e modo de desenvolvimento explícito.

**Gate:** shell navegável, deep links, reload preservando rota e zero novos hexadecimais fora dos tokens.

### Fase 2 — Navegação e superfícies globais

Implementar A04, A07, A10, A11, A13, A18, A20, A21, A24, A25, A29, A31, A32 e A38.

**Gate:** todos os overlays fecham por Escape/clique externo, possuem foco preso quando modal e restauram o foco no trigger.

### Fase 3 — Workspace, marca, Radar e campanha

Implementar A05, A06, A15, A17, A22, A23, A27, A36, A01, B01 e B04.

Ordem funcional:

```text
Workspace Entry → Brand Memory → Radar/Newsroom → Campaign Intake → Campaign Room → Campaign World/Moodboard
```

**Gate:** três workspaces isolados produzem prontidão, oportunidades e campanhas diferentes; oportunidade chega à campanha sem perda de contexto.

### Fase 4 — Conteúdo, biblioteca, lineage e reutilização

Implementar A03, A08, A09, A12, B02, B08, B09, B10, B12, B15 e B16.

**Gate:** conteúdo pode ser criado, pesquisado, versionado, derivado, comparado e reaberto; lineage é auditável.

### Fase 5 — Creative Lab e editores

Implementar A16, A33, A35, A37, B03, B05, B07, B11, B13, B14, B17, B18 e B19.

Editor compartilhado:

- documento por camadas;
- undo/redo baseado em comandos;
- autosave debounced e salvamento explícito;
- conflito de versão detectável;
- safe areas e formatos;
- elementos de marca, tipografia, efeitos e motion;
- preview fiel e export job;
- nenhum estado de canvas implementado como editor separado.

**Gate:** criar → editar → autosave → fechar → reabrir → exportar funciona para post, carrossel e vídeo.

### Fase 6 — Revisão, publicação, analytics, automação e copilot

Implementar A02, A14, A19, A26, A28, A30, A34 e B06.

**Gate:** aprovação controla publicação, logs registram decisões, métricas exibem origem e o aprendizado influencia recomendações futuras sem fabricar números.

### Fase 7 — Fechamento das 57 telas

1. Rodar a matriz de rastreabilidade e garantir 57/57.
2. Capturar baseline visual por frame e comparar em CI.
3. Executar E2E do caminho crítico nos três workspaces.
4. Auditar teclado, leitores de tela, contraste e reduced motion.
5. Auditar isolamento de workspace, permissões e vazamento de dados.
6. Remover mocks do bundle de produção.
7. Documentar limitações reais e backlog não bloqueante.

## 8. Estratégia de testes

### Unitários

- prontidão da marca e classificação de lacunas;
- scoring, risco e elegibilidade do Radar;
- transições de campanha/conteúdo/aprovação/publicação;
- reducers de editor, undo/redo e serialização;
- resoluções de permissão e capacidade;
- lineage e aprendizado.

### Contratos e integração

- schemas de API frontend/backend;
- migrations do zero e upgrade de banco existente;
- isolamento por `workspaceId` em toda query;
- idempotência de refresh, geração, export e publish;
- uploads privados e autorização;
- concorrência/autosave com versão otimista.

### E2E obrigatório

```text
Login
→ escolher/criar workspace
→ configurar marca
→ abrir Radar
→ transformar oportunidade em campanha
→ revisar Campaign Intake
→ gerar kit no Studio Composer
→ editar post e carrossel
→ enviar para aprovação
→ aprovar
→ agendar/publicar
→ registrar métrica
→ visualizar aprendizado
→ reutilizar conteúdo vencedor
```

Executar com restaurante local, clínica e creator/infoproduto.

### Regressão visual

- 57 snapshots de referência, um por frame/estado;
- viewports 1280×1024 e 1440×900;
- estados loading/empty/error onde não houver frame específico;
- máscaras apenas para timestamps e conteúdo genuinamente dinâmico;
- aprovação humana para diferenças estruturais; tolerância automática somente para antialiasing.

## 9. Gates de qualidade e definição de concluído

Uma tela conta como implementada somente se:

1. possui rota ou trigger de estado documentado;
2. corresponde visualmente ao frame aprovado com a paleta nova;
3. usa dados reais ou fixture explicitamente de teste;
4. todos os controles principais têm comportamento;
5. possui estados de carga, vazio e erro aplicáveis;
6. respeita permissão e isolamento de workspace;
7. preserva contexto de origem;
8. passa teste de teclado e contraste;
9. possui pelo menos um teste de comportamento ou E2E;
10. está marcada na matriz 57/57 com evidência de screenshot e teste.

O trabalho completo exige ainda:

- frontend lint/build verde;
- backend lint/test verde;
- migrations verificadas em banco novo e banco existente;
- zero dependência do `localStorage` no fluxo principal;
- zero métricas inventadas no modo produção;
- zero telas do projeto descartável;
- zero ocorrências do verde legado em componentes migrados;
- nenhuma perda de dados, histórico ou lineage.

## 10. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Backend fonte fora da `main` | Bloqueia dados reais e testes | Recuperação seletiva na Fase 0, sem trazer UI antiga por acidente. |
| Stash e branch divergentes | Perda de migrations ou regressão | Inventário de hashes, restauração por arquivo e banco temporário. |
| 57 frames tratados como páginas independentes | Duplicação e inconsistência | Rotas canônicas + estados compartilhados + matriz de rastreabilidade. |
| CSS legado com 554 verdes | Paridade visual frágil | Tokens primeiro, lint de cores e migração por feature. |
| Contextos monolíticos/localStorage | Corridas, vazamento e dados obsoletos | API tipada, estado de servidor separado e stores locais por feature. |
| Editores duplicados | Manutenção inviável | Um `CreativeDocument` e um editor modular com inspectors. |
| Integrações sociais indisponíveis | Botões mortos ou promessas falsas | Adapters, status honesto, sandbox e publish jobs auditados. |
| IA não determinística | Regressão e falta de auditoria | Prompt versionado, provider trace, fixtures gravadas e aprovação humana. |
| Frames sem HTML incorporado | Lacuna de detalhe visual | Captura/export individual antes do desenvolvimento e aceite por screenshot. |
| Mudança visual involuntária em áreas existentes | Perda de funcionalidade aprovada | Entregas incrementais, feature flags e regressão visual. |

## 11. Ordem operacional recomendada para o próximo modo meta

Ao iniciar o modo meta, a primeira execução deve terminar apenas quando houver:

1. branch de trabalho segura;
2. backend fonte recuperado e testável;
3. inventário 57/57 versionado;
4. tokens oficiais consolidados;
5. router e shells funcionando;
6. primeiro vertical slice real:

```text
Workspace/Marca → Radar → Campaign Intake → Campaign Room → Post Creation → Approval
```

Depois desse slice, avançar pelas fases 4–7 sem pular nenhuma linha da matriz.
