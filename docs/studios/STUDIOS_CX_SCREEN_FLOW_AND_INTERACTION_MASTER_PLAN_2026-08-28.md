# Clicko Studios — Plano mestre de CX, telas, fluxos e interações

**Versão:** 1.1  
**Data:** 2026-08-29  
**Status:** base técnica e cobertura contratual estrita verificadas; Figma sincronizado no checkpoint anterior; validação humana e benchmark criativo ampliado pendentes  
**Escopo:** arquitetura de experiência do produto e dos Studios  
**Fontes normativas:** `design.md`, `docs/CLICKO_STUDIOS_STRATEGY.md`, `docs/studios/STUDIOS_FUNCTIONAL_REQUIREMENTS.md` e `docs/studios/STUDIOS_PRODUCT_PROTOTYPE_ROADMAP.md`

---

## 1. Decisão executiva

A Clicko não deve continuar evoluindo como uma coleção de telas ou demos de ferramentas. A unidade de projeto e de entrega passa a ser a **jornada concluída**.

O usuário deve sempre conseguir responder, sem procurar:

1. Onde estou?
2. O que estou produzindo?
3. Qual contexto está sendo usado?
4. Qual é a próxima decisão?
5. O que acontecerá quando eu clicar?
6. Onde encontro o resultado depois?

As 57 referências visuais existentes não serão tratadas como 57 produtos independentes. Elas serão consolidadas em famílias de superfícies, cinco shells coerentes e seis jornadas-mãe. Estado, painel, modal e variação responsiva não contam automaticamente como nova tela.

O design aprovado e o shell global serão preservados. A mudança necessária é estrutural: uma única arquitetura de navegação, contratos explícitos de tela e ação, e validação por tarefas reais.

### 1.1 Decisão complementar — Studios orientados à ação

A pesquisa comparativa registrada em
`docs/studios/research/ACTION_FIRST_STUDIO_REFERENCE_SYNTHESIS_2026-08-29.md` acrescenta um princípio
canônico: o Studio organiza a experiência pelo ciclo **Pedir → Ver rascunho → Refinar → Comparar →
Fixar versão → Revisar**. O resultado ou objeto focal domina a tela; informação operacional aparece
por disclosure progressivo, sem esconder save, jobs, custo, consentimento, lineage ou bloqueios.

Essa decisão não substitui os cinco shells, o Studio Kernel nem os contratos existentes. Ela define
a hierarquia de interação usada dentro deles.

---

## 2. Evidência do estado atual

### 2.1 Achados do inventário

- O manifesto contém **57 referências**, distribuídas por **31 rotas-base**.
- Há três mecanismos concorrentes de renderização/navegação: `CanonicalProduct`, `ProductSurfaceView` e a árvore legada de `currentTab` em `App.tsx`.
- Uma mesma família de rota pode possuir mais de um possível owner de renderização.
- O ledger anterior usa “implementado” principalmente como “renderiza ou navega”, mas isso não prova que a tarefa seja concluível.
- A triagem estática encontrou 585 elementos `button` nativos e 141 componentes `Button`. Desses, 146 nativos e 34 componentes não declaram handler ou submit no ponto analisado. A regex não prova defeito individual, mas identifica uma fila ampla de auditoria.
- O problema percebido pelo usuário — tela presa, botões sem efeito e dificuldade para encontrar edição de foto/vídeo — é consequência direta dessa fragmentação.

### 2.2 Nova semântica de implementação

Uma tela só pode ser chamada de implementada quando:

- a rota possui um único owner;
- a entrada correta é carregada;
- a ação principal funciona com estado real;
- todas as ações visíveis possuem comportamento honesto;
- persistência e reabertura funcionam;
- a saída chega à próxima etapa correta;
- loading, vazio, erro, bloqueio e permissão estão cobertos;
- teclado, foco, contraste e responsividade foram verificados;
- existe teste da tarefa, não apenas screenshot.

---

## 3. Usuários e trabalhos a realizar

As personas abaixo continuam hipóteses até a pesquisa com usuários. Elas orientam o plano, mas não substituem validação.

| Papel | Trabalho principal | Medo/fricção central | Evidência de sucesso |
|---|---|---|---|
| Operador de social media | Produzir e adaptar conteúdo para várias marcas | perder contexto, tempo ou trabalho | peça pronta com menos troca de ferramenta |
| Estrategista/diretor criativo | Definir tese, direção e guardrails | conteúdo genérico ou desconectado da marca | direção explicável, aprovada e reutilizável |
| Designer/editor | Dar acabamento e controle ao material | automação destrutiva ou editor superficial | resultado editável, preciso e reabrível |
| Apresentador/rosto da marca | Autorizar e dirigir o uso de rosto e voz | uso fora de escopo ou resultado artificial | consentimento controlável e amostra aprovada |
| Aprovador/cliente | Entender e decidir rapidamente | entrar em editor complexo ou aprovar versão errada | decisão em menos de um minuto sobre versão fixa |
| Administrador | Controlar pessoas, canais, custos e políticas | vazamento entre workspaces e ações irreversíveis | permissões, auditoria e custos compreensíveis |

### Pesquisa necessária antes de congelar os protótipos

- 5 entrevistas moderadas com operadores de social media;
- 2 sessões com aprovadores/clientes;
- 1 sessão com editor de vídeo ou designer;
- tarefas com o produto atual: criar post, localizar editor de vídeo, revisar e publicar;
- registrar tempo, erros, retornos, cliques sem efeito, abandono e linguagem usada espontaneamente;
- revisar personas, labels e ordem das etapas com a evidência.

---

## 4. Modelo mental do produto

### 4.1 Cinco destinos globais

1. **Início** — prioridades, trabalhos recentes e decisões pendentes.
2. **Criar** — launcher orientado à tarefa e ao contexto.
3. **Projetos** — campanhas, peças, produção e colaboração.
4. **Biblioteca** — assets, templates, identidades e lineage.
5. **Publicar** — revisão pronta, calendário, canais e resultados.

Radar, Apps, Analytics e Settings continuam acessíveis, mas não disputam o caminho principal de produção.

### 4.2 Cinco shells

| Shell | Onde é usado | Responsabilidade |
|---|---|---|
| Global | Início, Radar, Projetos, Biblioteca, Publicar | marca/workspace, navegação e notificações |
| Projeto | campanha e project room | contexto, objetivo, status e abas do projeto |
| Studio | Editorial, Visual, Carrossel, Vídeo e Presenter | Production Rail, trabalho dominante, inspector e jobs |
| Decisão | Direção, Review e preflight | comparar, justificar, aprovar ou solicitar mudança |
| Operação | Factory, Apps e Settings | filas, integrações, permissões, custos e políticas |

### 4.3 Production Rail compartilhada

A Production Rail mostra o fluxo `Direção → Roteiro → Materiais → Montagem → Revisão → Entrega`. Ela deve:

- preservar projeto, campanha, brief e documento;
- indicar etapa atual e dependências;
- permitir voltar ao projeto e salvar/sair;
- abrir assets, referências, versões, comentários e decisões em drawers;
- mostrar o próximo gate humano;
- nunca parecer uma segunda navegação global.

### 4.4 Action-first Studio Surface

O Studio shell possui seis zonas estáveis:

1. Context bar compacta com projeto, documento, versão, save e job;
2. Production Rail com etapa, dependência e próximo gate;
3. Stage dominante com canvas, player, roteiro ou conjunto em produção;
4. Action Dock persistente com alvo, intenção, contexto essencial e uma CTA primária;
5. Inspector contextual, fechado ou mínimo quando não existe seleção;
6. Details drawer para direitos, lineage, provider, custo, logs e dados avançados.

O Action Dock oferece até quatro context chips — formato, identidade/rosto, voz e cenário/material —
e `Mais controle`. Cada controle executável precisa de `actionId`; sugestão sem Action Contract é
texto, não botão.

A linguagem visual canônica não usa emojis. Estado e ação são comunicados por texto, cor semântica,
geometria e ícones vetoriais do design system com nome acessível. Símbolos não podem substituir
labels nem ser a única evidência de estado.

Há três níveis progressivos sobre o mesmo documento:

- **Rápido:** intenção e insumos mínimos produzem storyboard ou preview privado;
- **Dirigido:** roteiro, cenas, cards, seleção e sugestões refinam o menor escopo seguro;
- **Pro:** timeline, tracks, waveform, keyframes e propriedades dão acabamento preciso.

Trocar de nível preserva `documentId`, seleção, histórico e estado. Uma regeneração total nunca é o
default quando existe cena, camada ou trecho selecionado.

---

## 5. Registro canônico de áreas e telas

| Área | Tela canônica | Trabalho | Entrada | Ação primária | Saída | Estado bloqueante obrigatório |
|---|---|---|---|---|---|---|
| Início | Today/Home | decidir o que fazer agora | workspace e atividade | `Continuar` ou `Criar` | tarefa/projeto aberto | sem atividade, falha de dados |
| Criar | Create Hub | iniciar pelo objetivo | marca, campanha ou contexto opcional | `Começar` | brief/documento inicial | formato indisponível, sem permissão |
| Radar | Radar Feed | encontrar oportunidade | marca, nicho e janela temporal | `Ver oportunidade` | Opportunity Detail | fontes indisponíveis/stale |
| Radar | Opportunity Detail | avaliar adequação | evidências e scoring | `Criar a partir disto` | Direção Criativa | baixa confiança/risco alto |
| Projetos | Project List | localizar trabalho | filtros e workspace | `Abrir projeto` | Project Room | vazio/sem acesso |
| Projetos | Project Room | coordenar campanha | campanha e conteúdo | `Continuar produção` | etapa pendente | contexto incompleto |
| Direção | Creative Direction | escolher tese criativa | campanha/oportunidade/oferta | `Aprovar direção` | CreativeBrief fixo | claims/guardrails pendentes |
| Editorial | Editorial Studio | concluir mensagem/roteiro | brief e marca | `Abrir no Visual/Vídeo` | mesmo documento enriquecido | brief ausente/conflito |
| Visual | Visual Studio | compor peça | documento e assets | `Enviar para revisão` | versão visual fixa | asset/direito/save inválido |
| Carrossel | Carousel Studio | construir narrativa multipágina | brief/spine | `Visualizar conjunto` | conjunto versionado | slide sem função/erro de conjunto |
| Imagem | Image Lab | criar/editar matéria-prima | asset ou referência | `Inserir no documento` | asset derivado com lineage | provider/direito/identity lock |
| Vídeo | Video Studio | transformar mídia em vídeo curto | mídia/roteiro/documento | `Renderizar preview` | artefato editável | ingest/transcript/render falhou |
| Motion | Motion Inspector | animar camada/cena | seleção no Visual/Vídeo | `Aplicar movimento` | alteração no mesmo documento | seleção incompatível |
| Identidades | Identity Library | escolher identidade autorizada | workspace e direitos | `Usar identidade` | identidade vinculada | consentimento expirado/revogado |
| Presenter | Capture & Consent | criar cápsula autorizada | pessoa e finalidade | `Gerar teste privado` | candidato de identidade | consentimento/qualidade insuficiente |
| Presenter | Presenter Production | gerar anúncio dirigido | identidade, copy e cena | `Gerar amostra` | vídeo no Video Studio | escopo de uso incompatível |
| Reuse | Reuse Studio | adaptar vencedor | conteúdo e performance | `Gerar derivações` | documentos filhos | origem/métrica insuficiente |
| Factory | Production Round | operar lote e jobs | receita e células | `Iniciar rodada` | outputs/gates | capacidade, custo ou input pendente |
| Biblioteca | Asset Library | encontrar matéria-prima | workspace, direitos e filtros | `Inserir`/`Abrir` | Studio de origem | direito vencido/arquivo inválido |
| Biblioteca | Asset Detail/Lineage | entender e gerir asset | asset | `Usar em conteúdo` | Create/Studio | asset em uso/exclusão protegida |
| Review | Review Room | decidir sobre versão exata | versão imutável | `Aprovar`/`Solicitar ajustes` | Publish ou Studio | versão obsoleta/sem permissão |
| Publicar | Preflight | validar destino | versão aprovada e canal | `Agendar/Publicar` | calendário | canal/claim/formato inválido |
| Publicar | Calendar | operar agenda | posts aprovados/agendados | `Abrir conteúdo` | detalhe/publicação | canal desconectado |
| Analytics | Learning | transformar resultado em decisão | publicação e métricas | `Reutilizar aprendizado` | Reuse/Direção | dados insuficientes/stale |
| Apps | Integrations | conectar capacidade externa | workspace e permissão | `Conectar` | OAuth/configuração | credencial/escopo inválido |
| Settings | Workspace/Brand/AI/Billing | governar o sistema | permissão administrativa | `Salvar alteração` | configuração auditada | permissão, conflito ou impacto alto |

### 5.1 Onde ficam foto, vídeo, motion e voz

- **Editar foto:** seleção de imagem no Visual → `Editar imagem`; ou Biblioteca → asset → `Editar`. O Image Lab retorna o derivado à camada/posição de origem.
- **Editar vídeo:** Criar → `Vídeo`; asset de vídeo → `Editar vídeo`; ou documento → seletor de Studio → `Vídeo`. Nunca cair no Visual por padrão.
- **Motion:** ferramenta contextual dentro de Visual e Vídeo. Não é destino global no MVP.
- **Voz:** capability do Presenter e do Vídeo, vinculada a uma identidade ou voz stock. Não é um gerador solto na navegação.
- **Avatar:** Identity Library administra direitos; Presenter Production usa uma identidade em um conteúdo. Criar identidade e produzir anúncio são fluxos separados.

---

## 6. Arquitetura de rotas

### 6.1 Regra

Uma rota possui um owner de renderização, um contrato de entrada e uma saída principal. Query string representa modo/painel, não um produto paralelo.

### 6.2 Mapa proposto, preservando compatibilidade

| Família | Rota canônica | Observação |
|---|---|---|
| Home | `/dashboard` | aliases antigos redirecionam sem perder contexto |
| Create Hub | `/create` | `/dashboard?create=open` permanece adapter temporário |
| Radar | `/radar` e `/radar/opportunities/:id` | evidência preservada ao criar |
| Projetos | `/projects` e `/campaigns/:id` | Project Room como owner único da campanha |
| Conteúdo | `/content` e `/content/:id` | board e detalhe |
| Studios | `/content/:id/edit?mode=editorial|visual|carousel|video|presenter` | mesmo `documentId`; painel em query separada |
| Image Lab | `/library/assets/:id/edit?mode=image` | com `returnTo` validado |
| Identidade | `/identities`, `/identities/new`, `/identities/:id` | direito/captura separados da produção |
| Factory | `/factory` e `/factory/:roundId` | rodada e células reais |
| Review | `/approvals/:contentId` | versão fixada na solicitação |
| Publish | `/publish/:contentId` e `/calendar` | só após preflight |
| Learning | `/analytics/learning` | conecta resultado à próxima criação |

### 6.3 Contexto de handoff

Toda transição entre áreas preserva, conforme aplicável:

`workspaceId`, `brandMemoryVersionId`, `campaignId`, `opportunityId`, `briefId`, `documentId`, `versionId`, `assetIds`, `identityId`, `jobId` e `returnTo`.

IDs de demonstração não podem ser usados como fallback silencioso em produção. Se o contexto necessário faltar, a tela abre um estado de recuperação explícito.

### 6.4 Migração incremental dos três routers

1. Criar um registro único de rotas com owner, shell, permissão e feature flag.
2. Fazer `App.tsx` delegar somente a esse registro.
3. Migrar uma família por vez de `ProductSurfaceView`/legado para o owner canônico.
4. Manter adapters e redirects para URLs existentes.
5. Medir acesso a aliases antes de removê-los.
6. Apagar uma implementação duplicada apenas após paridade funcional, visual e E2E.

---

## 7. Jornadas-mãe

### J1 — Criação rápida de post

```text
Início → Criar → escolher oferta/oportunidade/briefing
→ Direção resumida → Editorial → Visual
→ Review → Preflight → Agendar/Publicar → Aprendizado
```

Princípio: o caminho rápido não pula a direção; ele apresenta um brief pré-preenchido que pode ser confirmado em uma etapa.

### J2 — Campanha para múltiplos formatos

```text
Project Room → Direção → Editorial/Narrative Spine
→ Visual + Carrossel + Vídeo → Factory
→ Review em lote → Publish → Analytics
```

Princípio: todas as peças herdam a mesma tese, mas continuam documentos e hipóteses identificáveis.

### J3 — Editar mídia existente

```text
Biblioteca/Projeto → selecionar asset
→ Editar imagem ou Editar vídeo → salvar derivado
→ retornar ao documento e posição de origem
```

Princípio: nunca sobrescrever o original; o retorno precisa ser determinístico.

### J4 — Vídeo bruto para anúncio pronto

```text
Criar Vídeo → Upload/Importar → Probe/Proxy/Transcrição
→ seleção assistida → Timeline → Legendas/Marca/Áudio
→ Preview → Render → Review → Publish
```

Princípio: toda automação produz decisões editáveis e reversíveis na timeline.

### J5 — “Colocar o rosto e o anúncio sair do outro lado”

```text
Identity Library → escolher avatar stock OU criar identidade
→ consentimento/captura/qualidade → teste privado → aprovar identidade
→ escolher campanha/copy → cena/voz/performance
→ gerar amostra → abrir no Video Studio → ajuste humano
→ Review → Publish
```

Para os seis avatares stock, o usuário começa em `Escolher avatar`, mas direitos, escopo, provider e lineage continuam registrados. Para rosto próprio, consentimento e teste privado são gates absolutos.

### J6 — Revisar, publicar e reaprender

```text
Notificação/Project Room → Review da versão fixada
→ Aprovar ou Solicitar ajustes
→ Preflight → Calendar/Publish → Analytics
→ Reuse ou nova Direção
```

Princípio: feedback deve retornar ao trecho, camada ou tempo exato e nunca apontar para uma versão diferente.

---

## 8. Contrato obrigatório de tela

Nenhuma tela entra no Figma canônico ou no código sem os campos abaixo:

| Campo | Pergunta respondida |
|---|---|
| `screenId` e rota | qual é sua identidade estável? |
| owner e shell | quem renderiza e qual estrutura usa? |
| usuário/JTBD | qual trabalho existe aqui? |
| entrada | que contexto e dados são necessários? |
| objeto focal | o que está sendo manipulado? |
| ação primária | qual decisão faz a jornada avançar? |
| ações secundárias | o que ajuda sem competir com a primária? |
| saída/next best action | onde o resultado vai? |
| estados | loading, vazio, pronto, alterado, erro, conflito, readonly e offline |
| permissões | quem pode ver ou agir? |
| persistência | o que salva, versiona ou cria job? |
| feedback | o que o usuário vê após a ação? |
| telemetria | que evento prova uso e sucesso? |
| acessibilidade | nome, teclado, foco, contraste e alternativa ao drag |
| testes | contrato, integração, E2E e visual |

Uma tela sem saída ou next best action é um beco sem saída e não pode ser aprovada.

---

## 9. Contrato obrigatório de botão e ação

### 9.1 Tipos de ação

- `NAV`: navega ou abre contexto.
- `SELECT`: altera seleção/mode/painel.
- `MUTATE`: altera e persiste um objeto.
- `UPLOAD`: envia/captura arquivo.
- `JOB`: inicia operação assíncrona observável.
- `REVIEW`: cria decisão auditável.
- `EXTERNAL`: inicia OAuth/handoff externo.
- `DESTRUCTIVE`: arquiva, revoga ou exclui com proteção.

### 9.2 Campos por ação

Cada controle deve registrar:

`actionId`, label, tipo, objeto, pré-condição, permissão, side effect, estado de loading, resultado de sucesso, erro recuperável, persistência, próxima rota, evento analítico, nome acessível e teste.

### 9.3 Regras de honestidade

- Botão que parece executável precisa executar.
- Capability futura aparece como informação/roadmap ou botão desabilitado com motivo, nunca como clique vazio.
- Toast confirma uma consequência; não substitui a consequência.
- Ação assíncrona cria job real, mostra progresso e permite retry/cancel quando o provider permite.
- Ação destrutiva mostra impacto, dependências e recuperação possível.
- Toggle altera estado real e expõe valor selecionado.
- Ícone isolado sempre possui nome acessível e tooltip.
- CTA primária é única por região decisória.
- `Salvar` e autosave possuem estados `alterado`, `salvando`, `salvo`, `falhou`, `conflito` e `offline`.

### 9.4 Estados visuais mínimos

`default`, `hover`, `focus-visible`, `pressed/selected`, `disabled + reason`, `loading`, `success` e `error`.

---

## 10. Regras de navegação e continuidade

- `Voltar ao projeto` retorna ao pai sem perder documento ou seleção.
- O seletor de Studio troca `mode`, preserva `documentId` e salva antes de sair.
- `Salvar e sair` volta à origem declarada, não a um fallback genérico.
- Mudança com autosave falho bloqueia saída silenciosa e oferece tentar novamente ou baixar rascunho.
- Deep links reconstroem contexto por IDs reais.
- Modal e drawer fecham com Escape, restauram foco e não alteram a URL sem necessidade.
- O browser Back deve reproduzir a hierarquia, não alternar estados internos aleatórios.
- Ao retornar de Review, abrir a versão de trabalho e o comentário exato.
- Ao retornar do Image Lab, restaurar a camada/track de origem.

---

## 11. Responsividade e movimentação da tela

### Desktop amplo — `>= 1280 px`

- Production Rail, área de trabalho e inspector podem coexistir.
- Canvas/player é dominante.

### Desktop compacto/tablet — `768–1279 px`

- Production Rail recolhível.
- Apenas um painel lateral aberto por vez.
- Tool rail permanece acessível; inspector vira drawer.
- Nunca depender de hover.

### Mobile/viewport estreito — `< 768 px`

- fluxo em uma coluna;
- revisão, upload, roteiro e ajustes essenciais continuam utilizáveis;
- timeline/canvas avançado pode oferecer modo simplificado e recomendação de desktop, mas nunca tela quebrada;
- nenhuma ação primária pode ficar fora do viewport.

### Regras técnicas de layout

- uma única região dona do scroll vertical por tela;
- nenhum `100vh + overflow:hidden` pode aprisionar conteúdo maior;
- drawers e menus respeitam safe area e teclado virtual;
- touch targets mínimos de 44×44 px;
- foco nunca fica escondido sob header/painel;
- zoom do navegador a 200% mantém a tarefa principal utilizável;
- testar explicitamente 360, 768, 1024 e 1440 px.

---

## 12. Sistema de estados e recuperação

Toda família deve desenhar e implementar:

1. skeleton/loading;
2. vazio com próxima ação;
3. pronto;
4. alterações locais;
5. salvando/sincronizado;
6. falha recuperável com retry;
7. conflito com comparação;
8. somente leitura;
9. sem permissão;
10. offline/stale;
11. job em fila/processando;
12. cancelamento solicitado/cancelado;
13. falha terminal com evidência e saída segura.

Mensagens devem dizer: o que aconteceu, o que foi preservado, o que o usuário pode fazer e se há impacto em publicação/custo.

---

## 13. Organização do Figma

| Página | Conteúdo |
|---|---|
| `00 — Readme & Decisions` | princípios, owners, status e links |
| `01 — IA & Golden Flows` | mapa do produto e seis jornadas-mãe |
| `02 — Foundations` | tokens, grids, foco, estados e responsividade |
| `03 — Shared Shells` | Global, Project, Studio action-first, Decision e Operation |
| `04 — Create & Direction` | Create Hub, Radar handoff e Creative Direction |
| `05 — Editorial & Visual` | post, carrossel, imagem e motion |
| `06 — Video & Presenter` | ingestão, timeline, identidades e produção |
| `07 — Factory & Library` | rodadas, jobs, assets e lineage |
| `08 — Review, Publish & Learn` | decisão, preflight, calendário e analytics |
| `09 — Responsive & Edge States` | 360/768/1024 e erros/conflitos/permissões |
| `10 — Prototype Tests` | protótipos clicáveis por tarefa |
| `99 — Archive` | explorações não canônicas |

Todo frame recebe: `screenId`, rota, jornada, estado, breakpoint, requisito IDs, owner, status e data. Somente `CANONICAL + Approved` entra na allowlist de implementação.

---

## 14. Sequência de prototipação

### CX-0 — Validação da arquitetura

- mapa de IA;
- cinco shells;
- seis jornadas;
- teste de árvore e first-click;
- entrevistas e baseline do produto atual.

**Gate:** pelo menos 80% dos participantes encontra corretamente Criar, Editar vídeo, Editar imagem, Revisar e Publicar no primeiro clique.

### CX-1 — Sistema operacional dos Studios

- Production Rail;
- Stage dominante e Action Dock persistente;
- níveis Rápido, Dirigido e Pro sobre o mesmo documento;
- header;
- context/version/job drawers;
- action states;
- comportamento 768/1024/1440.

**Gate:** nenhum beco sem saída; primeira ação e primeiro preview são encontrados sem explicação;
save/job/erro continuam compreensíveis e o usuário consegue refinar apenas uma cena/seleção.

### CX-2 — Jornada monetizável de post

- Create Hub;
- Direção;
- Editorial;
- Visual;
- Review;
- Preflight.

**Gate:** operador conclui uma peça real de ponta a ponta, reabre sem perda e aprovador decide sobre a versão correta.

### CX-3 — Carrossel, Reuse e Factory

- narrativa multipágina;
- variações;
- rodada/células;
- revisão em lote.

**Gate:** conjunto exporta completo, lineage é preservado e falha/retry é compreensível.

### CX-4 — Vídeo assistido

- ingestão;
- transcript/player/timeline;
- captions/brand/audio;
- render/review.

**Gate:** usuário produz vídeo vertical real; preview e render correspondem; nenhuma automação destrói o original.

### CX-5 — Presenter governado

- Identity Library;
- consentimento/captura;
- teste privado;
- seis avatares stock;
- produção e handoff ao Vídeo.

**Gate:** nenhum job começa sem direito válido; revogação bloqueia uso; toda saída passa por review.

### CX-6 — Motion e imagem avançada

- ferramenta contextual;
- locks;
- máscara/antes-depois;
- movimento reduzido;
- lineage.

**Gate:** alteração é reversível, provider-neutral e retorna ao documento correto.

---

## 15. Plano de execução técnica após aprovação

### Fase A — Verdade de navegação e ações

- registrar todas as rotas e owners;
- gerar grafo e detectar rotas órfãs/duplicadas;
- criar inventário de ações com IDs;
- classificar controles sem handler;
- remover aparência de botão de elementos decorativos;
- instrumentar dead clicks e erros de navegação.

### Fase B — Consolidar shells e estados

- um route registry;
- um render owner por família;
- shared Studio shell;
- primitives de loading/empty/error/permission/conflict;
- contrato de scroll e responsividade.

### Fase C — Migrar por corte vertical

Executar CX-2 a CX-6 na ordem acima. Cada corte integra frontend, contratos, backend, jobs, telemetria, testes e rollback. Não fazer reescrita total.

### Fase D — Retirar duplicações

- comparar paridade;
- manter redirects medidos;
- remover owner antigo apenas após zero regressão;
- atualizar ledgers para distinguir `visual`, `interativo`, `persistido` e `task-complete`.

---

## 16. Testes e evidências obrigatórias

### Automação

- teste do grafo: nenhuma rota canônica órfã;
- teste de ação: toda ação visível tem handler ou estado disabled com motivo;
- testes de contrato para tela e handoff;
- E2E das seis jornadas-mãe;
- persistência/reabertura;
- versionamento/review da versão correta;
- isolamento entre workspaces;
- cancel/retry/idempotência de jobs;
- teclado, foco e nomes acessíveis;
- visual regression em 360/768/1024/1440.

### Testes com pessoas

- sucesso sem ajuda;
- tempo até primeira ação correta;
- tempo até primeiro rascunho útil;
- retornos e hesitações;
- cliques sem efeito;
- confiança antes de confirmar ação de risco;
- System Usability Scale ou UMUX-Lite ao final do corte.

---

## 17. Métricas de CX e produto

| Métrica | Meta inicial |
|---|---|
| Task completion dos cinco achados principais | `>= 90%` após duas rodadas de teste |
| First-click success para foto/vídeo/review/publish | `>= 80%` no protótipo; `>= 90%` em produção |
| Dead clicks em controles canônicos | `0` conhecido |
| Rotas canônicas com owner único | `100%` |
| Telas com contrato e estados completos | `100%` antes de produção |
| Ações primárias com teste automatizado | `100%` |
| Reabertura sem perda de trabalho | `100%` nos E2E críticos |
| Aprovação sobre versão correta | `100%` |
| WCAG | 2.2 AA nas jornadas críticas |
| Tempo até primeiro rascunho útil | reduzir contra baseline validado |
| Trocas para ferramenta externa | reduzir contra baseline validado |

Metas relativas de tempo só serão fixadas depois do baseline com usuários reais.

---

## 18. Definition of Ready de uma tela

- pertence a uma jornada priorizada;
- possui screen contract;
- possui requisitos e owner;
- possui wireframe de estados e breakpoint;
- todas as ações têm action contract;
- contrato de dados e permissão definido;
- métrica e teste de tarefa definidos;
- open source, quando houver, está atrás de provider/adapter;
- rollout e rollback descritos.

## 19. Definition of Done de uma tela

- abre pela rota e contexto corretos;
- única implementação é autoritativa;
- usuário conclui a tarefa principal;
- não possui controle decorativo disfarçado de ação;
- salva, reabre e versiona quando aplicável;
- entrega o resultado à próxima etapa;
- cobre todos os estados obrigatórios;
- funciona nos breakpoints suportados e com teclado;
- telemetria e erros são observáveis;
- testes passam e a tarefa foi validada com pessoa representativa;
- documentação e Figma correspondem ao comportamento real.

---

## 20. Riscos e contramedidas

| Risco | Contramedida |
|---|---|
| redesenhar antes de entender tarefas | teste de árvore/first-click e wireframes antes do visual |
| big bang nos routers | strangler por família com redirects e feature flags |
| Figma divergir do produto | screen/action IDs compartilhados e gate CANONICAL |
| botão fake reaparecer | lint/teste de action registry e revisão de DoD |
| excesso de ferramentas no Studio | progressão por seleção e inspector contextual |
| mobile quebrar editor | estado simplificado planejado, um scroll owner e matriz de viewport |
| IA alterar demais | preview/diff/confirmação/desfazer e novo derivado |
| identidade sintética virar atalho perigoso | separar consentimento, identidade e produção; review obrigatório |
| open source ditar UX/domínio | adapters e `CreativeDocument` canônico |
| perder features legadas sem tela | matriz existente → destino → migração → teste antes de remoção |

---

## 21. Decisões que ficam congeladas para a próxima meta

1. A unidade de entrega é a jornada, não o frame.
2. Existem cinco destinos globais e cinco shells.
3. Edição de imagem é contextual e retorna à origem.
4. Edição de vídeo possui Studio próprio.
5. Motion e voz são capabilities contextuais, não destinos globais iniciais.
6. Identidade/consentimento e produção com Presenter são fluxos separados.
7. A rota `/content/:id/edit` preserva o mesmo documento entre modos.
8. Todo botão possui contrato e resultado verificável.
9. Uma tela só é “implementada” quando a tarefa é concluível e testada.
10. A consolidação dos routers será incremental e compatível.

---

## 22. Objetivo sugerido para a próxima meta

> Implementar incrementalmente a arquitetura canônica de CX da Clicko, começando por verdade de navegação e ações, route registry único, shells compartilhados e o corte vertical de Post Factory. Preservar rotas, design system, contratos do Studio Kernel e funcionalidades existentes. Considerar cada tela concluída somente quando sua tarefa, estados, persistência, handoff, acessibilidade, telemetria e testes estiverem comprovados. Não iniciar Presenter ou vídeo avançado antes dos gates definidos neste plano.

### Primeiro checkpoint da meta

- inventário executável de rotas e ações;
- route ownership map;
- grafo de navegação sem duplicidade;
- screen/action contract schemas;
- shells responsivos prototipados;
- baseline com usuários e tarefas;
- plano de migração da primeira jornada com rollback.

Somente após esse checkpoint deve começar a alteração estrutural da interface.

## 23. Benchmark de conteúdo acrescentado pelo usuário — 30/08/2026

O plano inclui dez anúncios UGC com seis slots de casting, nichos, cenários, copy e roteiro,
peça visual, carrossel e vídeo. A matriz, a crítica das dez copies e as referências para revisão
estão em `UGC_CREATIVE_VALIDATION_PLAN_AND_REVIEW_2026-08-30.md`.

Dois lotes locais executaram Qwen, composição Pillow e animatics FFmpeg. A média numérica anterior
não comprovava aprovação editorial: houve oferta inventada, afirmações sem ficha/evidência,
fala truncada, divergência entre roteiro e cenas e mistura de idiomas. O pré-check agora exige
todos os critérios obrigatórios, inspeciona os bytes e mantém revisão humana separada.

Composição estática não equivale a geração de imagem por modelo; animatic silencioso não equivale
a vídeo final de avatar. Imagem generativa, voz, rosto e lip-sync continuam sem execução neste
benchmark. Não fechar CX-4/CX-5 nem a meta com base nesses arquivos. O benchmark offline também
não substitui testes autenticados de persistência, handoff, jobs, acessibilidade ou CX-0.

Voicebox fica adiado para avaliação após o plano/meta atual, conforme solicitado. Não acrescentar
esse provider ou novas telas de voz durante esta rodada.

### Atualização de escopo — UGC sem voz

Em 30/08 o usuário pediu: não fazer voz por enquanto; produzir vídeo UGC com sons naturais e legenda.
O próximo lote passa a usar esse perfil. Sem narração, clonagem, voz stock, fala incidental ou música;
apenas ambiente/foley coerente com a ação e de origem autorizada. Legendas são texto editorial
sincronizado às cenas, não transcrição de fala inexistente. Voz e lip-sync são não aplicáveis a essa
entrega, não bloqueadores. Os lotes históricos permanecem congelados e não são reclassificados.
Detalhamento: seção “Perfil vigente” do plano UGC. Não alterar os gates de direitos de imagem,
continuidade visual, qualidade, revisão e publicação por causa da ausência de voz.

## 24. Checkpoint Review → pré-flight autenticado — 30/08/2026

O handoff aprovado agora é comprovável: Review fixa mídia, composição, versão e os campos de
publicação do Post; `/publish/:contentId` revalida esse vínculo antes de exibir, baixar ou agendar.
Copy ou documento alterados falham fechados. O agendamento é somente interno e audita
`externalPublicationConfirmed=false`; publicação externa continua indisponível sem conector.

Provas: 20/20 testes backend focados, 29/29 E2E integrais, 6/6 contratos CX, audit estrito sem
órfãs/conflitos, Axe da tela, 1440/360, TypeScript, Ruff e build. Detalhes em
`evidence/PUBLICATION_PREFLIGHT_BINDING_AUDIT_2026-08-30.md`.

Esse checkpoint não encerra a meta: validação humana CX-0, sincronismo posterior no Figma via MCP e
o novo lote criativo UGC com sons naturais/legendas ainda exigem execução e evidência separadas.

## 25. Checkpoint UGC sem voz — contrato e dez planos — 30/08/2026

O perfil vigente foi materializado como contrato separado, sem alterar o corpus histórico falado:
`studio.ugc-no-voice-casebook.v1`, suite `clicko.ugc-no-voice-natural-caption.pt-br.v1`.
O áudio permitido é exclusivamente ambiente/foley natural autorizado. Voz, conversa captada e
música são proibidas. As legendas são editoriais e cronometradas, não transcrição.

Os dez planos cobrem seis slots de casting, dez nichos, cenários, continuidade, copy, cinco cues de
legenda e ao menos dois cues de som por anúncio. A auditoria aprovou 10/10 no contrato mecânico e
0/10 para produção: não existem ainda takes/avatar com direitos, sons licenciados com checksum,
relatórios do mix final nem revisão humana ligada ao digest do caso. Essa reprovação de produção é
um gate esperado, não uma falha a ser mascarada por animatic silencioso ou por assets inventados.

Implementação e provas:

- corpus: `benchmarks/studios/ugc/ugc-no-voice-natural-caption-casebook.v1.json`;
- digest canônico: `624a1cffa264175170746a42defcad356fc601c36b9f25e3599d0ec10a908008`;
- contrato/evaluator: `backend/app/domain/studios/ugc_no_voice.py` e
  `backend/app/services/studios/ugc_no_voice.py`;
- auditoria: `artifacts/validation/ugc-no-voice/audit-20260830-v3/`;
- decisão detalhada: `evidence/UGC_NO_VOICE_CONTRACT_AUDIT_2026-08-30.md`.

Próximo corte autorizado: adquirir ou gravar foley/ambiência com direitos, obter take/avatar
aprovado e renderizar os primeiros vídeos com legenda. Não ativar Voicebox, TTS, clonagem,
narração, lip-sync ou música neste perfil. A meta de CX permanece ativa.

## 26. Checkpoint Carrossel → Reuse → Fábrica — 30/08/2026

O corte autenticado agora preserva lineage e identidades das derivações após reload. A Fábrica usa
um `roundId` determinístico derivado de workspace, origem e conjunto ordenado de filhos. Repetir a
mesma entrada recupera a rodada existente sem criar outra versão ou outro job; IDs e versões foram
comparados antes/depois no E2E.

As superfícies autenticadas deixaram de exibir performance, campanha, preview, coerência,
capacidade e decisões demonstrativas como fatos. Os dados exibidos vêm do workspace ou aparecem
explicitamente como ausentes. O inventário estrito passou a incluir campos de formulário: 413
controles executáveis canônicos, todos com Action Contract; zero rotas órfãs/conflitantes e zero
disabled sem motivo.

Provas: 9/9 backend focados, 3/3 E2E do corte, 6/6 contratos CX, audit estrito, build, TypeScript,
viewport móvel `390 × 844` e 8/8 superfícies Axe A/AA. Detalhes em
`evidence/CAROUSEL_REUSE_FACTORY_VERTICAL_AUDIT_2026-08-30.md`.

O checkpoint prova repetição sequencial/reload, não corrida simultânea entre abas. Orquestração
transacional concorrente, polling/retry por célula, CX-0 com pessoas e o lote UGC licenciado sem voz
continuam pendentes. A meta permanece ativa.

## 27. Checkpoint Vídeo Assistido — legenda editorial sem voz — 30/08/2026

O Video Studio autenticado deixou de criar uma transcrição e um speaker fictícios para texto de um
vídeo sem fala. `VIDEO-APPLY-CAPTIONS` agora grava diretamente uma track de legenda editorial no
`CreativeDocument`, com cues sem `speaker`, `sourceSegmentId` ou `confidence`. O documento declara
`captionMode=editorial` e `speechExpected=false`; reload, cortes, reorder e trim preservam a verdade
temporal da track.

O E2E autenticado passou por upload, ingest, proxy, waveform, legenda, edição não destrutiva,
render FFmpeg, QC, reload e revisão. Ele comprova que nenhuma transcrição foi criada e que o MP4
materializa a track editorial da revisão exata. Também passaram 13/13 testes da timeline, 6/6
contratos CX, audit estrito, TypeScript, build e Axe da superfície de vídeo.

Esse resultado não transforma o áudio técnico da fixture em som natural autorizado. Waveform não
é detector de fala/música, e o áudio captado no take ainda precisa de política e evidência próprias.
Os dez UGC continuam em 0/10 para produção até existirem takes/avatar e foley/ambiência reais com
direitos, checksum, detecção, escuta humana e revisão vinculada. Detalhes em
`evidence/ASSISTED_VIDEO_EDITORIAL_CAPTIONS_AUDIT_2026-08-30.md`. Voicebox e todo fluxo de voz
continuam fora do corte. A meta permanece ativa.

## 28. Checkpoint aquisição de som — caso 01 café — 30/08/2026

Três fontes naturais com direitos auditáveis foram baixadas para o primeiro caso: grãos (`CC BY
4.0`), água em caneca (domínio público) e caneca sobre mesa (`CC0 1.0`). O manifesto fixa origem,
autoria, licença, bytes, duração e SHA-256. O total é inferior a 1 MB.

O preflight local agora combina FFmpeg, `webrtcvad-wheels 2.0.14` e YAMNet ONNX CPU (~3,7 M de
parâmetros) com frontend log-mel canônico. Ele falha fechado: transientes de foley acionaram o VAD,
então fala ficou `inconclusive`; YAMNet passou música em grãos/água e deixou a caneca
`inconclusive` por confundi-la com `Wood block`. A fonte de água também acionou `Breathing` acima
do limiar. Escuta humana segue `pending`, portanto nenhum arquivo virou evidência aprovada, mix ou
asset do Video Studio. Os testes focados passaram 10/10 e Ruff passou.

O export ONNX de terceiro está fixado por commit e SHA-256, mas não possui model card nem relatório
de paridade com o YAMNet oficial. Seu manifesto declara `conversionProvenanceVerified=false` e
`productionReady=false`; ele é apenas challenger de preflight. O próximo passo é qualificar ou
rejeitar os sons por escuta humana, calibrar o classificador num corpus Clicko e, quando o mix
candidato estiver aprovado, adaptar o renderer para múltiplos assets de áudio com lineage. Detalhes estão em
`evidence/ASSISTED_VIDEO_EDITORIAL_CAPTIONS_AUDIT_2026-08-30.md`. A meta permanece ativa.

Atualização: um mix candidato de 15 segundos para `s1+s2` foi materializado com manifesto, hashes e
preflight do próprio resultado. Isso fecha a composição técnica, mas não o gate: fala segue
`inconclusive`, escuta e continuidade de ambiente estão pendentes, o nível medido é `-29.75 LUFS` e
não há take para validar sincronismo. Ele não foi importado no Video Studio nem classificado como
produção.

## 29. Checkpoint som original reversível — 31/08/2026

O Video Studio agora remove/restaura som original na track canônica com persistência,
preview, controle móvel e conflito otimista. O renderer respeita o mute sem alterar a
fonte: os testes decodificaram o MP4 e comprovaram amostras de áudio inteiramente zeradas.
Legendas editoriais, cortes e o snapshot de uma revisão anterior permanecem preservados.

Silêncio é prova privada, não substituto do foley natural solicitado. Para snapshots
com perfil explícito sem voz/sons naturais, preflight, pacote e agendamento interno
ficam indisponíveis até implementação da admissão acústica controlada pelo servidor.
Aprovação criativa não libera o gate; documentos legados sem perfil não foram migrados.

Provas: timeline 15/15, provider/job/review 18/18, preflight 7/7, E2E autenticado 1/1
com desktop e 390 × 844, Axe A/AA na superfície com mídia real, contratos 6/6 e 414
controles canônicos auditados. O E2E encontrou e levou à correção de texto minúsculo
e contraste no painel de saída. Dependências de auditoria acústica ficaram isoladas
da API/worker padrão. Detalhes e limites em
`evidence/VIDEO_SOURCE_AUDIO_MUTE_AUDIT_2026-08-31.md`.

Próximo corte: entrada e mix de sons naturais com lineage, take aprovado, sincronismo,
escuta e admissão vinculada ao artefato final. Os dez anúncios continuam em 0/10 para
produção. Voicebox/voz continuam adiados. A meta permanece ativa.

## 30. Checkpoint Sons → timeline → MP4 — 31/08/2026

A aba Sons implementa upload privado, origem/licença declaradas, início no vídeo,
offset na fonte, duração, ganho e fades. A track persiste e pode ser reconfigurada
sem duplicar o asset. O renderer materializa som externo e suporta take sem áudio;
o MP4 tem player próprio em Saída, separado do preview de montagem sem mix ao vivo.

Ingestão reutiliza o job existente, valida uma stream audio-only e mantém
idempotência/tenant. Render valida ingest, referências e hashes, conservando
proveniência. Os campos declarados continuam `unknown/pending`, sem liberação de
entrega. O núcleo usa AudioClipV1/CreativeDocument existentes, sem migração ou nova
dependência. Nenhuma mudança na VPS.

Evidência: 27/27 backend, 18/18 timeline, 6/6 contratos, audit estrito com 424
controles canônicos; jornada autenticada com WAV/MP4 reais, PCM, reload, reedição,
isolamento e Axe A/AA em 390 × 844. Detalhes, limites e rollback em
`evidence/VIDEO_NATURAL_SOUND_VERTICAL_AUDIT_2026-08-31.md`.

Permanecem: mixer multicue na UI, preview mixado ao vivo, undo/mute independente,
envelopes de fade após split, recuperação de upload não associado, takes aprovados,
qualificação acústica/escuta e admissão server-owned. O lote UGC continua 0/10
aprovado, Voicebox adiado e a meta ampla ativa.

## 31. Checkpoint sons independentes e desfazer protegido — 31/08/2026

A aba Sons agora adiciona e seleciona vários trechos com IDs próprios, reutiliza
arquivo importado sem duplicação, ajusta cada trecho e desativa/reativa sem apagar
a fonte. Seleção pela timeline usa a mesma proteção de rascunho do painel. Desfazer
é de um nível na sessão e exige revisão/versão exatas; um 409 recarrega o documento
sem apagar a alteração concorrente.

O E2E autenticado comprovou dois trechos da mesma fonte, persistência após reload,
descarte explícito de rascunho, toggle/undo e conflito. Decodificação PCM comprovou
as duas entradas e a remoção exclusiva da segunda após desativá-la. A inspeção
visual encontrou e corrigiu sobreposição do cabeçalho no celular; o teste agora
verifica a geometria além de Axe e overflow.

Evidência: 20/20 timeline, 6/6 contratos, 430 controles canônicos no audit estrito,
E2E 1/1 repetido (última execução 52,2 s), TypeScript e build. Detalhes e rollback em
`evidence/VIDEO_NATURAL_SOUND_MULTICUE_AUDIT_2026-08-31.md`.

Sem ativação de voz/música ou alterações na VPS. Os arquivos de teste não contam
como UGC final: lote permanece 0/10 aprovado. Faltam take com autorização, escuta,
sincronismo, admissão acústica server-owned, preview mixado ao vivo e demais cortes
da meta. Voicebox segue adiado; a meta permanece ativa.

## 32. Checkpoint preview com sons naturais — 31/08/2026

O player de montagem reproduz os sons da timeline salva com Web Audio local,
aplicando offset, duração, ganho e fades. Reutiliza fontes dentro da sessão e exige
download privado, checksum e decode válidos antes de iniciar. Pausa/seek/buffering,
fim, alteração da edição e troca de contexto interrompem o áudio. Carregamento
pode ser cancelado no mesmo controle de reprodução; falhas ficam explícitas.

O relógio de saída acompanha os cortes do vídeo e corrige deriva. Isso não equivale
a motor de vídeo frame-exact nem a garantia de sincronismo perceptual em qualquer
hardware. O preview continua separado de QC, escuta/rights e aprovação do MP4.
Nenhuma voz, música ou clonagem foi ativada; não houve alteração da VPS.

Evidência: 24/24 testes de timeline/preview, 6/6 contratos, audit estrito com 430
controles canônicos e 4/4 E2E (56,3 s) com Web Audio real, PCM, cancelamento,
checksum divergente, interrupção de contexto, seek, reprodução através do corte,
reload, undo/conflito, render e isolamento. Abas do inspector foram redistribuídas
para não sobrepor labels, mantendo texto legível e alvos de 44 px.

Detalhes, limites de memória/formatos, provas e rollback em
`evidence/VIDEO_NATURAL_SOUND_LIVE_PREVIEW_AUDIT_2026-08-31.md`.
Seguem abertos take autorizado, escuta humana, foley sincronizado, admissão
acústica server-owned e demais cortes de CX/Presenter/Motion. Lote UGC permanece
0/10 aprovado; Voicebox segue adiado e a meta ampla permanece ativa.

## 33. Checkpoint revisão humana do MP4 fixado — 31/08/2026

A Review Room agora exige escuta do MP4 exato para aprovar vídeos com perfil de
sons naturais/sem voz. Confirmação integral e quatro critérios — fala, música,
coerência e equilíbrio — são gravados atomicamente com a decisão. O registro fixa
asset, hash do render, hash do snapshot, documento, versão, revisor e horário. O
servidor relê e verifica os bytes antes de aceitar; arquivo alterado ou hash
forjado falha fechado. Pedir ajustes continua possível sem concluir a escuta.

A escuta humana não virou admissão de publicação: direitos e detectores de
fala/música ainda precisam ser vinculados ao mesmo mix final. Mesmo com quatro
passes, preflight, pacote e agendamento do perfil continuam bloqueados por
`studio_publication_natural_sound_evidence_pending`.

Evidência: 16/16 testes backend, TypeScript, build, Ruff, 6/6 contratos e audit
estrito com 432 controles executáveis. O E2E autenticado com MP4/áudio real passou
em 57,8 s, incluindo bloqueio inicial/falha, persistência dos hashes, gate de
entrega, Axe A/AA e 390 × 844 sem overflow. Detalhes e limites em
`evidence/VIDEO_NATURAL_SOUND_HUMAN_REVIEW_AUDIT_2026-08-31.md`.

O teste é fixture técnica, não aprovação humana de campanha. Não houve voz,
música, clonagem, modelo novo, migration, VPS ou Figma. Os dez anúncios continuam
0/10 aprovados para produção; Voicebox segue adiado e a meta ampla permanece ativa.

## 34. Checkpoint direitos do som natural — 31/08/2026

A aba Sons agora registra uma decisão Owner/Admin sobre direitos do arquivo
natural. O servidor verifica os bytes privados e o SHA-256, captura as declarações
de origem/licença e salva evidência imutável com base, referências, validade,
revisor e escopo `commercial-saas`. A projeção server-owned roda também em
create/replace/restore: selos `verified` inventados no documento são descartados,
mudança de declaração invalida a verificação e uma restrição continua presa ao
mesmo asset/hash.

A operação tem lock do documento, idempotência, isolamento 404 e Owner/Admin 403,
e invalida render/revisão quando altera a prova. O painel foi validado aberto em
390 × 844, sem overflow e com Axe A/AA. O preflight YAMNet/VAD de pesquisa não foi
promovido: sua conversão não possui proveniência/paridade de produção e o VAD
confunde transientes naturais com fala.

Evidência: 17/17 testes backend, E2E autenticado com WAV/MP4 reais, TypeScript,
build, Ruff, 6/6 contratos e audit estrito com 442 controles executáveis. Detalhes,
ameaças e rollback em
`evidence/VIDEO_NATURAL_SOUND_RIGHTS_REVIEW_AUDIT_2026-08-31.md`.

Direitos não liberam publicação. Detectores qualificados de fala/música e admissão
server-owned no hash do mix final continuam pendentes. Não houve voz, música,
clonagem, modelo novo, migration, VPS ou Figma; Voicebox segue adiado. O lote UGC
continua 0/10 aprovado e a meta ampla permanece ativa.

## 35. Checkpoint análise acústica do mix final — 31/08/2026

O MP4 fixado pela revisão ganhou análise provider-neutral de ausência de fala e
música. O job `acoustic_analysis` roda na fronteira `media_cpu` e fixa review,
snapshot, versão, asset e SHA-256. Só existe quando provider, modelo, licença
comercial, benchmark e worker anunciado estão aprovados e coincidem com o adapter
do runtime. O registry de produção permanece vazio; YAMNet/VAD de pesquisa não foi
promovido.

Uma análise positiva não libera entrega sozinha. A admissão server-owned combina,
no mesmo hash, detector qualificado, escuta humana e eventos reais de direitos de
todas as fontes. Publicação relê os bytes e revalida licença e promoção: expiração,
mudança ou revogação bloqueiam sem apagar evidência histórica.

A Review Room mostra loading, indisponível, job, pass, fail, inconclusivo e admitido.
No ambiente atual, “Analisar fala e música” fica desabilitado com a razão honesta.
O estado foi validado em 390 × 844 com Axe A/AA e sem overflow. O E2E real passou
em 47,3 s antes da captura final, cobrindo ainda WAV/MP4, direitos, escuta, dois
renders e isolamento.

Evidência, ameaças e rollback:
`evidence/VIDEO_FINAL_MIX_ACOUSTIC_ADMISSION_AUDIT_2026-08-31.md`.
Provas: 18/18 backend, E2E 1/1 em 47,3 s, TypeScript, build, Ruff e diff-check.
Audit estrito: 443 controles executáveis e 6/6 contratos. Não houve voz, música,
clonagem, modelo real, migration, VPS ou Figma. O lote UGC segue 0/10 aprovado,
Voicebox adiado e a meta ampla permanece ativa.

## 36. Checkpoint qualificação acústica verificável — 31/08/2026

Política, corpus, bytes, direitos, previsões, provider/modelo, worker, licença,
conversão e avaliador agora são contratos ligados por SHA-256. O verificador
recalcula matrizes e taxas; somente avaliação `passed` gera recibo HMAC. Execução e
publicação revalidam assinatura e identidade exata, de modo que adulteração ou
revogação bloqueiam entrega.

A política PT-BR segue `draft`; não há corpus nem detector real aprovado, e o
registry permanece vazio. Provas: 28/28 backend, Ruff, TypeScript, build, 443
controles e 6/6 contratos. Detalhes em
`evidence/VIDEO_ACOUSTIC_DETECTOR_QUALIFICATION_CHAIN_AUDIT_2026-08-31.md`.
Sem voz, música, clonagem, modelo, VPS, Docker ou Figma; 0/10 anúncios aprovados.
