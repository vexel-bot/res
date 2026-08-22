# Clicko — Ledger objetivo da implementação aprovada

Data do inventário: 2026-08-18.

Este ledger é a fronteira normativa da implementação. Ele contém exatamente os 37 alvos permitidos: 26 superfícies canônicas, a célula S34 Presenter e 10 detalhes sociais. Frames de flows/states, archive, explorações, componentes, grupos, referências, readmes, matrizes e standards não são superfícies deste ledger.

Legenda do estado atual:

- `implementada`: reconstruída a partir do contexto do frame aprovado via Figma MCP, funcional e validada nos viewports da fase.
- `parcial`: existe rota/overlay funcional, mas a composição ainda diverge materialmente do frame aprovado.
- `ausente`: não existe rota/superfície de produto correspondente.

| # | ID | Superfície canônica | Página Figma | Frame ID | Rota/entrada navegável | PNG auxiliar | Estado atual | Lacuna objetiva |
|---:|---|---|---|---|---|---|---|---|
| 1 | S01 | Home | 03 — Shell & Overlays | `45:973` | `/dashboard` (`/today` alias) | `01-home-canonical-coral-orange-v1.png` | implementada | Fase 1: composer, formatos, recomendações, continuidade, assets exatos do Figma e navegação global aprovados; validada em 1536×1024 e 1280×1024. |
| 2 | S02 | Create Launcher | 03 — Shell & Overlays | `46:1100` | `?create=open` | `02-create-launcher-open-v1.png` | implementada | Fase 1: intenções, categorias, busca funcional, foco, teclado, URL e estado vazio implementados e validados. |
| 3 | S03 | Radar Room | 10 — Discover & Plan | `98:2` | `/radar` | `03-radar-room-v1.png` | implementada | Fase 2: fila priorizada, evidências, sinais, detalhe decisório, janela, risco, fontes e passagem contextual para campanha; validada em 1536×1024 e 1280×1024. |
| 4 | S04 | Opportunity Detail | 10 — Discover & Plan | `105:102` | `/radar/opportunities/:opportunityId` | `04-opportunity-detail-v1.png` | implementada | Fase 2: ponte acontecimento–interesse–oferta, evidências, direção, proveniência, scores, guardrails e ações implementadas. |
| 5 | S05 | Campaign Intake | 10 — Discover & Plan | `109:165` | `/campaigns/new?opportunity=:id` | `05-campaign-intake-v1.png` | implementada | Fase 2: contexto preservado, fundação, oferta, público, formatos, guardrails, preview, refino e criação funcional implementados. |
| 6 | S06 | Campaign Room | 20 — Create & Review | `114:2` | `/campaigns/:campaignId` | `06-campaign-room-v1.png` | implementada | Fase 2: sala operacional com fundação, próxima ação, kit, fluxo, decisões, guardrails e acessos ao Mundo e Moodboard implementada. |
| 7 | S07 | Create Hub & Content Inventory | 20 — Create & Review | `121:104` | `/content` | `07-create-hub-content-inventory-v1.png` | implementada | Fase 3: hub visual para iniciar, continuar, buscar, filtrar, decidir e reutilizar vencedores implementado e validado. |
| 8 | S08 | Editorial Desk | 20 — Create & Review | `125:168` | `/content/:contentId/edit?mode=editorial` | `08-editorial-desk-v1.png` | implementada | Fase 3: mesa editorial com estrutura, hook, sequência, legenda, preview, contexto, guardrails e assistência local implementada. |
| 9 | S09 | Visual Editor | 20 — Create & Review | `129:246` | `/content/:contentId/edit?mode=visual` | `09-visual-editor-v1.png` | implementada | Fase 3: editor visual com tool rail, camadas, canvas, área segura, seleção, tipografia, inspector, guardrails e slides implementado. |
| 10 | S10 | Creative Review Room | 20 — Create & Review | `132:246` | `/approvals/:postId?view=creative` | `10-creative-review-room-v1.png` | implementada | Fase 3: comparação de versões, comentários, evidência honesta, contexto e decisões de aprovar, ajustar ou rejeitar implementadas. |
| 11 | S11 | Editorial Calendar | 30 — Publish & Learn | `135:2` | `/calendar` | `11-editorial-calendar-v1.png` | implementada | Fase 4: grade semanal, cadência, canais, drawer, conflito, lacuna, pré-flight e handoff ao Publisher implementados e validados. |
| 12 | S12 | Publisher Control | 30 — Publish & Learn | `140:104` | `/publish/:postId` | `12-publisher-control-v1.png` | implementada | Fase 4: prévia, legenda, slides, checklist, agenda interna, pacote manual e bloqueio honesto de publicação sem conector implementados. |
| 13 | S13 | Post Detail & Performance | 30 — Publish & Learn | `145:168` | `/content/:postId` | `13-post-detail-performance-v1.png` | implementada | Fase 4: peça publicada, métricas, proveniência, aprendizado acionável, evolução, linhagem e passagem ao Reuse Lab implementados. |
| 14 | S14 | Reuse & Variation Lab | 30 — Publish & Learn | `148:233` | `/content/:postId/remix` (`?view=variations`) | `14-reuse-variation-lab-v1.png` | implementada | Fase 4: origem, evidência, preservar/adaptar/testar, derivados, risco, hipótese e linhagem rastreável implementados. |
| 15 | S15 | Campaign World | 20 — Create & Review | `152:246` | `/campaigns/:campaignId/world` | `15-campaign-world-v1.png` | implementada | Fase 2: blueprint causal de entradas, ideia-mãe, ângulos, saídas, coerência, guardrails, decisão e exploração de alternativa implementado. |
| 16 | S16 | Campaign Moodboard | 20 — Create & Review | `156:310` | `/campaigns/:campaignId/moodboard` | `16-campaign-moodboard-v1.png` | implementada | Fase 2: curadoria operacional com referências, busca, filtros, adição, compartilhamento, princípios, cobertura e aplicação implementada no shell canônico. |
| 17 | S17 | Carousel Builder | 20 — Create & Review | `157:392` | `/content/:contentId/edit?mode=carousel` | `17-carousel-builder-v1.png` | implementada | Fase 3: rail narrativo, navegação slide a slide, canvas, transição, inspector, consistência, adição e sugestão aplicável implementados. |
| 18 | S18 | Brand Memory | 10 — Discover & Plan | `159:230` | `/brand-memory` | `18-brand-memory-v1.png` | implementada | Fase 2: readiness, lacunas, essência, posicionamento, diferenciais, pilares, fontes ativas, influência e responsabilidade implementados com transparência demonstrativa. |
| 19 | S19 | Unified Library | 20 — Create & Review | `161:392` | `/library/assets` | `19-unified-library-v2.png` | implementada | Fase 3: arquivos, busca, campanha, ativos da marca, referências, direitos, linhagem, inserção e variação implementados no shell canônico. |
| 20 | S20 | Performance Observatory | 30 — Publish & Learn | `163:297` | `/analytics/learning` | `20-performance-observatory-v1.png` | implementada | Fase 4: recortes, KPIs, ranking de evidências, evolução semanal, padrões, lacunas, limite causal e nova rodada implementados. |
| 21 | S21 | Content Factory | 20 — Create & Review | `164:455` | `/factory` | `21-content-factory-v1.png` | implementada | Fase 3: métricas de capacidade, cinco estágios, cartões acionáveis, adição, nova produção e próxima melhor ação implementados no shell canônico. |
| 22 | S22 | Global Search / Production Standard | 03 — Shell & Overlays | `47:633` | `Ctrl/Cmd+K` e `?spotlight=open` | `22-global-search-spotlight-v1.png` | implementada | Fase 1: busca agrupada, recentes, entidades, comandos, setas, Enter, Esc, foco e URL implementados e validados. |
| 23 | S23 | Projects Overview | 03 — Shell & Overlays | `167:753` | `/projects` | `23-projects-overview-v1.png` | implementada | Fase 2: retomada visual, busca, filtros por etapa, progresso, responsáveis, atualização e próximos passos implementados no shell canônico. |
| 24 | S24 | Activity Center | 03 — Shell & Overlays | `168:816` | `?activity=open` | `24-activity-center-v1.png` | implementada | Fase 1: aprovações, menções, agenda, Radar, conflito, falha de conector, filtros e leitura implementados; dados reais usados quando disponíveis. |
| 25 | S25 | Workspace Switcher | 03 — Shell & Overlays | `168:1092` | `?workspace=menu` | `25-workspace-switcher-v1.png` | implementada | Fase 1: workspace atual, lista, troca real, criação e gerenciamento implementados com tratamento demonstrativo explícito. |
| 26 | S26 | Apps & Integrations | 03 — Shell & Overlays | `169:1118` | `/apps` | `26-apps-integrations-v1.png` | implementada | Fase 5: busca, categorias, essenciais, descoberta, estados honestos, atividade, reconexão e catálogo dos dez canais aprovados implementados. |
| 27 | S34 | Presenter Production Cell | 40 — Studios | `205:4358` | `/content/:contentId/edit?mode=presenter` | — | implementada | Fase 5: Production Rail, matéria-prima real, bancada de identidade, captura, scores, direitos, gates, decisão humana e testes de saída implementados com assets exatos. |
| 28 | S-IG | Instagram Integration | 35 — Social Integrations | `252:2` | `/apps/instagram` | `instagram.png` | implementada | Fase 5: perfil profissional, Meta, formatos, defaults, publicação, saves/retenção, saúde, permissões e memória implementados. |
| 29 | S-FB | Facebook Integration | 35 — Social Integrations | `252:266` | `/apps/facebook` | `facebook.png` | implementada | Fase 5: Página, função, feed/Reels, comunidade, CTA, governança, métricas, permissões e memória separada implementados. |
| 30 | S-TT | TikTok Integration | 35 — Social Integrations | `252:504` | `/apps/tiktok` | `tiktok.png` | implementada | Fase 5: Direct Post, rascunho, disclosure, privacidade, dueto/stitch, processamento, retenção e limites implementados. |
| 31 | S-YT | YouTube Integration | 35 — Social Integrations | `252:740` | `/apps/youtube` | `youtube.png` | implementada | Fase 5: canal, upload retomável, Shorts, miniatura, legendas, quota, metadados, retenção e analytics implementados. |
| 32 | S-X | X Integration | 35 — Social Integrations | `254:382` | `/apps/x` | `x.png` | implementada | Fase 5: plano API, posts, threads, enquetes, respostas, rate limit, disclosure, métricas e peso temporal implementados. |
| 33 | S-LI | LinkedIn Integration | 35 — Social Integrations | `254:620` | `/apps/linkedin` | `linkedin.png` | implementada | Fase 5: organização, papel administrativo, posts, vídeo, documento PDF, governança, autoridade e analytics implementados. |
| 34 | S-PI | Pinterest Integration | 35 — Social Integrations | `254:857` | `/apps/pinterest` | `pinterest.png` | implementada | Fase 5: conta Business, Pins, boards, alt text, UTM, descoberta, saves, cliques e sazonalidade implementados. |
| 35 | S-TH | Threads Integration | 35 — Social Integrations | `254:1093` | `/apps/threads` | `threads.png` | implementada | Fase 5: perfil Meta, texto/mídia/carrossel, replies, polls, topic tag, contexto, views e moderação implementados. |
| 36 | S-TW | Twitch Integration | 35 — Social Integrations | `259:472` | `/apps/twitch` | `twitch.png` | implementada | Fase 5: canal-fonte, agenda, VODs, clipes, detecção de momentos, reutilização, eventos, métricas derivadas e permissões implementados. |
| 37 | S-GB | Google Business Profile Integration | 35 — Social Integrations | `254:1569` | `/apps/google-business-profile` | `google-business-profile.png` | implementada | Fase 5: localização verificada, atualizações, eventos, ofertas, avaliações, Search/Maps, rotas, reputação e permissões implementados. |

## Resultado final

- As `37` entradas da allowlist estão implementadas; não restam itens `parcial` ou `ausente` no escopo visual aprovado.
- A Fase 5 foi reconstruída somente após consultar os 12 frames exatos pelo Figma MCP; o shell sobreposto de S26 não foi copiado.
- Todos os 37 alvos foram validados em 1440×900 e 1280×1024; as 74 capturas finais estão em `artifacts/visual-validation/final-approved/`.
- O baseline funcional segue preservado: lint e build passam, as 12 jornadas E2E passam e os 40 testes do backend passam.
- Contas conectadas e sessões do Presenter são persistidas por workspace, auditáveis e isoladas por tenant. A publicação externa permanece bloqueada e explicitamente sinalizada sem credenciais.
