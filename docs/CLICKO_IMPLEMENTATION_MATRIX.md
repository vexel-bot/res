# Matriz de implementação — Clicko 26 superfícies canônicas

**Repositório funcional:** `C:\Users\edugu\Downloads\res`  
**Referências visuais:** `C:\Users\edugu\Documents\Codex\2026-07-30\new-chat\outputs\clicko-prototype-program\telas-finais-aprovadas`  
**Baseline auditado em:** 2026-08-17  
**Estado:** em execução; esta matriz é atualizada durante implementação e validação.

## 1. Inventário do sistema preservado

- Frontend: React 19, TypeScript 5.8, Vite 6, Tailwind 4 e Express/tsx.
- Backend: FastAPI, SQLAlchemy, Alembic e SQLite; API sob `/api/v1` e IA sob `/api`.
- Autenticação: bearer token com registro, login, perfil e troca de senha.
- Escopo: `workspaceId` em workspaces, marca, posts, campanhas, oportunidades, documentos criativos, assets, histórico, métricas, auditoria e preferências.
- Domínio persistido: usuários, memberships, workspaces, perfis/revisões de marca, posts/versões, aprovação, sinais/fontes/oportunidades do Radar, campanhas/versões/decisões, documentos criativos/versões, assets, conhecimento, feedback, snapshots de métricas, jobs, recursos e auditoria.
- Capacidades a preservar: criação e atualização de campanhas/posts; kit idempotente; Radar com fontes, ranking e feedback; editor por camadas; autosave com conflito; versões/restauração; exportação; assets privados; aprovação/comentários; agenda; histórico/reúso; analytics com procedência; Brand Memory versionada; equipe, billing, auditoria, automações, imagem, vídeo e configurações legadas.
- Limites reais: publicação externa, conectores sociais completos, smart resize, layout generativo, coedição e motion avançado não estão disponíveis de ponta a ponta.
- Estado local atual: sem token, a UI utiliza dados locais. A reconstrução deve rotular explicitamente esse estado como demonstração; autenticado, o backend é a fonte de verdade.

## 2. Baseline de qualidade antes da reconstrução

| Verificação | Resultado em 2026-08-17 |
|---|---|
| `npm run lint` | passou |
| `npm run test:stitch` | passou; cobertura legada 38 + 19 = 57 |
| `npm run test:backend` | 39 passaram; 2 warnings |
| `npm run build` | passou; aviso de chunk JS 705,68 kB |
| `npm run test:e2e` | 6 passaram |
| Auditoria 1440×900 | concluída para as 26 rotas/estados candidatos |
| Evidência baseline | `artifacts/visual-validation/baseline-audit/screenshots/` |

## 3. Componentes compartilhados alvo

- `CanonicalAppShell`: sidebar expandida/compacta/drawer, header, busca, notificações, conta e workspace.
- Primitives: `Button`, `IconButton`, `Input`, `SearchField`, `Tabs`, `StatusPill`, `Badge`, `Avatar`, `Tooltip`, `Dialog`, `Drawer`, `Sheet`, `EmptyState`, `AsyncState`.
- Patterns: `MediaCard`, `ProjectCard`, `ContentRow`, `MetricEvidence`, `CampaignNav`, `ContentArtwork`, `Inspector`, `QualityGate`, `Lineage`, `FocusEditorShell`.
- Superfícies globais: `CreateLauncher`, `GlobalSpotlight`, `ActivityCenter`, `WorkspaceSwitcher`.
- Estado: `ProductDataContext`/API tipada para servidor; estado efêmero local apenas para overlays, foco, filtros e preferências.

## 4. Matriz das 26 superfícies

Legenda de status: **ausente**, **parcial**, **em implementação**, **implementada**, **validada**.

| # | Tela | Rota/estado canônico | Componentes compartilhados | Backend / entidades | Feature existente preservada | Lacuna baseline e estados obrigatórios | Status / evidência |
|---:|---|---|---|---|---|---|---|
| 01 | Home/Hoje | `/dashboard` e `/today` (alias) | AppShell, Composer, MediaCard, ProjectCard, ActivitySummary | bootstrap, campaigns, posts, analytics, radar | Dashboard editorial, retomada, agenda, decisões, aprendizado | Shell 76px e mídia genérica; demo não rotulada; loading/empty/error/stale/offline | **validada** — `canonical-1536/01-home.png` |
| 02 | Launcher Criar | overlay global por botão e `?create=open` | Dialog, SearchField, CreateIntent, RecentWork | active workspace; create campaign/post; history | menu Criar existente | muito pequeno e orientado por formato; foco contido, Esc, permission/disabled | **validada** — `canonical-1536/02-create.png` |
| 03 | Radar Room | `/radar` | AppShell, OpportunityQueue, EvidencePanel, StatusPill | radar state/sources/feedback; opportunities | ranking, fontes, feedback, estados honestos | estado vazio domina e composição é KPI/admin; loading/no_sources/collecting/error/brand_incomplete | **validada** — `canonical-1536/03-radar.png` |
| 04 | Opportunity Detail | `/radar/opportunities/:opportunityId` e estado selecionado do Radar | OpportunityBridge, EvidenceList, Guardrails | opportunity dentro de radar snapshot; feedback; campaign create | seleção atual e handoff para intake | query atual não muda UI; expirada/inelegível/fonte indisponível/permission | **validada** — `canonical-1536/04-opportunity.png` |
| 05 | Campaign Intake | `/campaigns/new?opportunity=:id` | CampaignContext, OfferAudience, InitialKit, Guardrails | campaigns POST; brand revision; opportunity lineage | criação real e kit idempotente | formulário genérico, sem preview/kit; offline draft, workspace conflict, mutation pending/error | **validada** — `canonical-1536/05-intake.png` |
| 06 | Campaign Room | `/campaigns/:campaignId` | CampaignNav, HeroMedia, ProductionKit, DecisionFeed | campaigns, posts, versions, decisions | tabs e campanha persistida | cards administrativos e pouca mídia; draft/planned/active/completed/conflict/readonly | **validada** — `canonical-1536/06-campaign.png` |
| 07 | Create Hub/Inventário | `/content` | CreateShortcuts, ContentBoard, ContentRow, WinnerRail | posts, creatives, assets, campaigns | grid/lista e criação | sem mídia real/atalhos/vencedores; empty/filter-empty/loading/readonly | **validada** — `canonical-1536/07-content.png` |
| 08 | Editorial Desk | `/content/:contentId/edit?mode=editorial` | FocusEditorShell, CopyDesk, LivePreview, ContextInspector | posts PATCH, campaign/brand context, versions | edição editorial e handoff | usa editor visual genérico; save/error/asset-missing/readonly/review | **validada** — `canonical-1536/08-editorial.png` |
| 09 | Visual Editor | `/content/:contentId/edit?mode=visual` | FocusEditorShell, LayerPanel, Canvas, Inspector, SlideStrip | creative documents, assets, versions, export | camadas, autosave, conflito, exportação | canvas vazio e painel genérico; 65% canvas, saved/saving/conflict/export/error/readonly | **validada** — `canonical-1536/09-visual.png` |
| 10 | Creative Review Room | `/approvals/:postId?view=creative` | ReviewCanvas, DecisionPanel, VersionTabs, Context | approval actions/events, post versions | aprovar/ajustar/rejeitar/comentar | peça sem mídia e pouca versão/contexto; concurrent decision, comment error, readonly | **validada** — `canonical-1536/10-review.png` |
| 11 | Calendário Editorial | `/calendar` | CalendarGrid, ContentDrawer, ConflictState | posts scheduledAt/status | semana editorial e agenda | sem campanha/preflight/drawer; empty/gap/conflict/permission | **validada** — `canonical-1536/11-calendar.png` |
| 12 | Publisher Control | `/publish/:postId` | ChannelPreview, PreflightChecklist, ManualHandoff | post approval/schedule; workspace resources | fila e status | baseline oferece “Publicar agora” sem conector; disconnected/token/error/manual export | **validada** — `canonical-1536/12-publisher.png` |
| 13 | Post Detail/Performance | `/content/:postId` | ContentPreview, MetricEvidence, LearningBench, Lineage | posts, metric snapshots, feedback, approval events | versões, lineage e métricas honestas | preview abstrato, sem tabs e pouco aprendizado; no-metrics/manual/stale/readonly | **validada** — `canonical-1536/13-post.png` |
| 14 | Reuse & Variation Lab | `/content/:postId/remix` e `?view=variations` | OriginalPreview, DerivationPlan, FormatPreview, Lineage | history reuse posts/creatives; metrics | reúso persistido e handoff | adaptação superficial e visual genérico; no-metrics/incompatible/manual-work/readonly | **validada** — `canonical-1536/14-remix.png` |
| 15 | Campaign World | `/campaigns/:campaignId/world` | CampaignNav, WorldFlow, CoherenceInspector | campaign strategy/decisions/versions | mundo contextual | texto em cards sem relações/mídia; draft/approved/brand-stale/conflict | **validada** — `canonical-1536/15-world.png` |
| 16 | Campaign Moodboard | `/campaigns/:campaignId/moodboard` | CampaignNav, MoodboardGrid, VisualBrief | assets, campaign links/tags | referências e upload | placeholders sem mídia/origem; empty/upload/error/license/readonly | **validada** — `canonical-1536/16-moodboard.png` |
| 17 | Carousel Builder | `/content/:contentId/edit?mode=carousel` | FocusEditorShell, NarrativeRail, Canvas, Inspector | post slides, creative document, versions/export | modo de editor e slides | é o mesmo canvas genérico; overflow/asset-missing/conflict/export/manual-safe-area | **validada** — `canonical-1536/17-carousel.png` |
| 18 | Brand Memory | `/brand-memory` | ReadinessMap, BrandSections, SourceList, RevisionHistory | workspace brand readiness/versions; knowledge | memória, fontes, revisões, permissões | composição rasa e sem prontidão auditável; incomplete/ready/processing/lexical/permission | **validada** — `canonical-1536/18-brand.png` |
| 19 | Biblioteca Unificada | `/library/assets` com tabs Templates/Marca/Linhagem | LibraryGrid, AssetInspector, Lineage | assets, creatives, history | uploads, templates, marca e linhagem | mídia genérica, sem inspector/proveniência; upload/error/missing/private/readonly | **validada** — `canonical-1536/19-library.png` |
| 20 | Performance Observatory | `/analytics/learning` | EvidenceRanking, TrendChart, LearningBench | analytics summary, metric snapshots, feedback | procedência e insufficient_data | conteúdo escasso e sem ação de reúso; no-data/user-reported/stale/error | **validada** — `canonical-1536/20-analytics.png` |
| 21 | Fábrica de Conteúdo | `/factory` | ProductionStages, ProductionCard, QualityGate | radar, campaigns, posts, approvals | features distribuídas nos hubs atuais | rota cai na Home; loading/empty/stage-filter/permission | **validada** — `canonical-1536/21-factory.png` |
| 22 | Busca Global/Spotlight | overlay global `Ctrl/Cmd+K` e `?spotlight=open` | Dialog, SearchField, ResultGroup, KeyboardHints | campaigns/posts/assets/history/radar; client commands | Spotlight/Tool Atlas existente | overlay é catálogo, não busca transversal; results/empty/loading/error/keyboard/focus return | **validada** — `canonical-1536/22-spotlight.png` |
| 23 | Projetos Overview | `/projects` | ProjectHeroCard, ProjectTable, Filters | campaigns + posts/stages | lista de projetos/campanhas | uma única campanha genérica; grid/list/loading/empty/filters/readonly | **validada** — `canonical-1536/23-projects.png` |
| 24 | Central de Atividades | drawer global pelo sino e `?activity=open` | Drawer, ActivityItem, ActivityFilters | approval events, audit, jobs, resource health | sino e eventos existentes em domínios separados | sino/query não abre superfície; loading/empty/error/unread/action | **validada** — `canonical-1536/24-activity.png` |
| 25 | Workspace Switcher | popover global e `?workspace=menu` | WorkspacePopover, SearchField, StatusPill | bootstrap workspaces; select/invalidate snapshot | seletor existente | modal genérico e workspaces locais; switching/error/permission/focus return | **validada** — `canonical-1536/25-workspace.png` |
| 26 | Apps e Integrações | `/apps` | IntegrationCard, ConnectionState, ActivityList | workspace resources/settings; canais reais quando existirem | Connected Accounts, channels, automations | rota cai na Home; connected/error/reconnect/configurable/beta/coming-soon | **validada** — `canonical-1536/26-apps.png` |

## 5. Jornadas e mutações

| Jornada | Entradas e mutações reais | Gate de validação |
|---|---|---|
| A — oportunidade até publicação | Radar state/feedback → campaign POST → pieces POST → post/creative PATCH → approval action → schedule PATCH | IDs e `workspaceId` preservados; publicação externa indisponível sem conector |
| B — aprendizado e reúso | post + metric snapshots → feedback/hypothesis → history reuse → creative/post derivado | métricas não copiadas; lineage preservada; smart resize manual |
| C — produção recorrente | campaigns/posts → creative autosave/version → approval action → schedule | autosave/conflito e approval gate testados |
| Globais | search local sobre snapshot + history; workspace select/refetch; activity a partir de eventos; launcher cria objetos no workspace ativo | teclado, foco, estados e invalidação de query |

## 6. Critérios de atualização desta matriz

Uma linha só muda para **implementada** quando possui rota/entrada pela UI, componentes reais, dados/mutações honestos e estados essenciais. Só muda para **validada** após screenshot final em 1536×1024, verificação em 1440×900 e 1280×1024, teste de teclado/foco quando aplicável e resultado de lint/build/testes registrado.

## 7. Fechamento de validação — 2026-08-17

- Evidência visual final: `artifacts/visual-validation/canonical-1536/` (26 PNGs em 1536×1024).
- Verificações complementares: `canonical-1440/` (26 PNGs), `canonical-1280/` (Home, editor, calendário e Apps) e `canonical-mobile-*.png` (Home, drawer e editor em 390×844).
- Acessibilidade exercitada: skip link, nomes acessíveis nos controles globais, foco visível, contenção de Tab em dialogs, `Esc` e retorno do foco no Spotlight, drawer móvel.
- `npm run lint`: passou.
- `npm run lint:backend`: passou.
- `npm run test:stitch`: passou, 38 + 19 = 57.
- `npm run test:e2e`: 7 passaram; cobre 26 superfícies canônicas, jornada projeto → revisão → calendário, Spotlight e coexistência das 57 referências.
- `npm run test:backend`: 39 passaram; 2 warnings.
- `npm run build`: passou. Permanece apenas o aviso não bloqueante de chunk JS acima de 500 kB (768,47 kB antes de gzip), candidato a code splitting posterior.
