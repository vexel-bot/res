# DESIGN.md

**Project:** Clicko — Creative Operations OS  
**Version:** 0.4.1  
**Last updated:** 2026-08-18  
**Owners:** Produto Clicko + Codex  
**Status:** active — direção “Creative Social Lab” aprovada pelo proprietário em 2026-08-15

---

## 1. Overview

**Brand essence:**  
Um laboratório visual de social media que transforma contexto de marca, referências e objetivos em campanhas e peças prontas — sem fragmentar a equipe entre ferramentas.

**Audiência primária:**  
Gestores de social media, estrategistas, creators e equipes de agência que precisam organizar campanhas, produção criativa, aprovação e distribuição sem perder contexto entre ferramentas.

**Research status:**  
Ainda não houve pesquisa formal com cinco usuários. A base atual é evidência direta do proprietário do produto, comportamento observado no sistema local e inventário das telas aprovadas. Até entrevistas reais, a persona permanece uma hipótese documentada.

**Job-to-be-done principal:**  
“Quando encontro uma oportunidade ou recebo uma demanda, quero transformá-la em campanha e conteúdos aprovados, publicados e mensurados sem reconstruir contexto em cada etapa.”

**Pain points confirmados:**

- O sistema não pode iniciar em uma tela editorial isolada; o dashboard operacional é o ponto de orientação.
- Uma rota sem navegação de saída faz o produto parecer uma coleção de protótipos.
- Projetos/campanhas precisam ser o acesso natural às ferramentas do Creative Lab.
- Conteúdo, agenda, aprovações e desempenho devem permanecer visíveis no dashboard.
- Controles decorativos e telas sem backend quebram confiança.
- Tipografia e densidade precisam ser consistentes entre módulos.

**Tom e personalidade visual:**

- Visual e colaborativo como uma mesa de criação, sem imitar um software administrativo.
- Criativo com disciplina: mídia e canvas dominam; controles recuam.
- Calmo no shell, expressivo nos trabalhos e deliberado nas ações.
- Direto, humano e contextual; pouco texto operacional e nenhuma instrução óbvia.

**Princípios de design:**

1. **Tarefa antes de tela:** jornadas e decisões definem a arquitetura; frames do Stitch são referências visuais e estados.
2. **Contexto nunca se perde:** workspace → oportunidade → projeto/campanha → conteúdo → aprovação → publicação → aprendizado.
3. **Nenhuma rota sem saída:** toda superfície tem navegação global, contexto local e retorno previsível.
4. **Conteúdo antes de cromia:** hierarquia, copy e dados conduzem o olhar; coral e laranja indicam ação e criação.
5. **Ação honesta:** todo controle principal funciona; dependências indisponíveis mostram estado explícito, nunca fingem sucesso.
6. **Dados com procedência:** métricas são reais, informadas ou hipóteses identificadas; nunca inventadas como fato.
7. **Mídia é a interface:** capas, peças, referências e resultados ocupam mais espaço do que explicações.
8. **Complexidade progressiva:** a Home oferece retomada e criação; ferramentas avançadas aparecem dentro do projeto ou editor.

**Fontes visuais e operacionais aprovadas:**

- Dashboard Clicko anterior: somente a lógica editorial — comando operacional, conteúdos, agenda, aprovações e desempenho. O visual anterior não é referência.
- Projeto Stitch “Telas Finais Aprovadas”: navegação, Campaign Room, Radar, Brand Memory e superfícies de decisão.
- Projeto Stitch “Creative Lab — Social Media OS”: Content Command, inventário, composição, editores e review criativo.

**Anti-inspirações e não-objetivos:**

- Não é uma galeria de 57 páginas independentes ou iframes sem estado compartilhado.
- Não é um editor criativo aberto como primeira experiência do produto.
- Não é uma interface com múltiplas fontes, escalas e densidades por módulo.
- Não é IA decorativa ou um conjunto de botões que não concluem tarefas.
- Não é uma dashboard de métricas fictícias sem fonte de dados.
- Não trata os frames do Stitch como páginas independentes. Shell, navegação, componentes e estados formam uma única obra compartilhada.
- Não incorpora HTMLs do Stitch por iframe. Os frames são especificação visual para componentes funcionais integrados.
- Não replica a arquitetura do Canva, Higgsfield ou Seedance; absorve seus princípios de clareza visual, continuidade do canvas e criação multimodal.
- Não exibe o ciclo inteiro do produto como menu global nem transforma cada estado do Stitch em item de navegação.

---

## 2. Information Architecture & UX Flows

### Entrada e navegação global

- `/` e `/dashboard` abrem a **Home visual**.
- A navegação global usa uma rail compacta e persiste em todas as superfícies, exceto no modo de foco do editor; o editor mantém retorno ao projeto.
- Existem apenas cinco destinos primários: **Home**, **Criar**, **Projetos**, **Biblioteca** e **Publicar**.
- Busca, workspace e criação são utilitários globais. O botão de criação é a única ação primária do shell.
- Radar vira **Inspiração** dentro de Criar e dos projetos. Aprovação é contextual à peça/projeto. Analytics é contextual ao conteúdo publicado. Brand Memory vive no contexto do workspace e no drawer de marca.
- Equipe, canais, billing, auditoria e governança ficam no menu da conta, sem competir com o trabalho criativo.
- O launcher (`Ctrl/Cmd + K`) torna capacidades secundárias encontráveis por intenção e substitui o antigo Atlas sem criar outro nível permanente de navegação.
- **Biblioteca** possui quatro contextos locais: Arquivos, Templates, Marca e Linhagem.
- **Publicar** possui cinco contextos locais: Calendário, Aprovações, Publicação, Desempenho e Canais.
- Configurações preserva Equipe, IA, Automações, Plano e Auditoria em navegação contextual própria.
- Os destinos globais são agrupados pelo ciclo **Começar → Produzir → Entregar**: Home orienta; Projetos e Biblioteca produzem; Publicar entrega. O agrupamento comunica progressão sem expor o produto inteiro como menu.
- Marca, Equipe e Integrações compõem o contexto **Operação** do workspace. Integrações não são um destino criativo aleatório e devem explicar a consequência real de conexão, expiração ou ausência.
- Dentro de Studios e editores, a navegação lateral global dá lugar à **Production Rail**: contexto da campanha, etapas de produção, bandejas da célula, autosave e retorno ao projeto. A marca no canto superior esquerdo sempre retorna à Home.

### Home visual

A Home responde, nessa ordem:

1. O que quero criar ou retomar agora?
2. Em quais projetos e peças a equipe está trabalhando?
3. O que será publicado em seguida?
4. O que precisa de uma decisão minha?
5. Qual aprendizado real deve orientar a próxima criação?

Sua composição visual segue o mesmo sistema Stitch das demais áreas; apenas a arquitetura de informação do dashboard anterior é preservada.

Blocos canônicos:

- composer multimodal com formatos visuais;
- “continue criando” com capa e último estado do projeto;
- galeria curta de criações recentes;
- próximos conteúdos agendados;
- decisões pendentes;
- um insight real e rastreável para a próxima criação;
- métricas editoriais apenas como camada secundária.

Acima da dobra, a Home usa no máximo 90 palavras e uma única ação primária.

### Projetos e Creative Lab

```text
Dashboard
  → Projetos
    → Projeto/Campanha
      → Visão geral
      → World
      → Moodboard
      → Conteúdos
      → Creative Lab
        → Editorial Desk
        → Visual Canvas
        → Carousel Builder
        → Video/Motion Studio
        → Variações
        → Review
      → Aprovações
      → Calendário/Publicação
      → Resultados
```

- As 19 telas do Creative Lab são ferramentas e estados dentro do contexto de um projeto, não uma aplicação paralela.
- O projeto/campanha ativo permanece visível no shell local e é propagado para criação, assets, aprovações e analytics.
- Editor visual, carrossel e vídeo compartilham documento, autosave, versionamento, assets e navegação de saída.
- A Production Rail segue a sequência **Direção → Roteiro → Materiais → Montagem → Revisão → Entrega**. Etapas podem mudar de nome conforme o studio, mas nunca aparecem fora da ordem causal do trabalho.

### Apps e integrações

- A tela organiza conexões pelo fluxo que habilitam: **Importar → Criar → Colaborar → Publicar → Medir**.
- Cada conexão informa propósito, estado, ação seguinte e consequência operacional; não existe grade genérica de logotipos sem relação com a produção.
- Serviços e canais usam seus logos vetoriais reconhecíveis em tamanho legível. A marca visual identifica a conexão; texto, estado e consequência continuam obrigatórios para acessibilidade e decisão.
- Conexões essenciais têm prioridade visual. Catálogo secundário e atividade técnica aparecem abaixo, com diagnóstico e histórico.
- Expiração, falha de permissão e indisponibilidade nunca fingem sucesso; publicação e métricas mostram impacto antes da ação corretiva.

### Fluxo crítico

```text
Dashboard → Radar → Oportunidade → Novo Projeto/Campanha
→ Campaign Room → Creative Lab → Conteúdo
→ Review/Aprovação → Calendário/Publicação → Analytics → Reutilização
```

---

## 3. Colors

```yaml
colors:
  canvas:
    value: "#080808"
    description: "Fundo global do produto."
  surface:
    base: "#0F0F0F"
    raised: "#151515"
    high: "#1C1C1C"
    highest: "#222222"
    control: "#111111"
  border:
    subtle: "#282828"
    strong: "#353535"
  text:
    primary: "#F5F5F5"
    secondary: "#A0A0A0"
    muted: "#727272"
  action:
    primary: "#FF5C5C"
    hover: "#FF7070"
    active: "#E94E4E"
    on-action: "#160606"
  creative:
    primary: "#FF7A00"
    hover: "#FF8F2A"
    active: "#E66E00"
    on-creative: "#140A00"
  semantic:
    success: "#53B780"
    warning: "#F1A33C"
    danger: "#E87979"
    info: "#78A9E6"
```

**Regras de uso:**

- Coral representa decisão primária, aprovação e CTA principal.
- Laranja representa criação, IA aplicada e dados de produção.
- Apenas uma ação primária dominante por região visual.
- Estados semânticos não reutilizam coral/laranja quando isso cria ambiguidade.
- Nenhum verde legado da interface anterior é permitido.

**Acessibilidade:**

- Alvo: WCAG 2.2 AA.
- Contraste mínimo de 4.5:1 para texto normal e 3:1 para texto grande/controles.
- Cor nunca é o único indicador de estado.
- Tema escuro é canônico na v1; tokens ficam preparados para tema claro posterior.

---

## 4. Typography

```yaml
typography:
  fonts:
    primary: "Manrope Variable"
    display: "Bricolage Grotesque Variable"
    mono: "IBM Plex Mono"
    fallback: "Segoe UI Variable, system-ui, -apple-system, sans-serif"
  scale:
    display: { size: "2.5rem", weight: 650, line: 1.05, tracking: "-0.04em" }
    h1: { size: "2rem", weight: 650, line: 1.15, tracking: "-0.03em" }
    h2: { size: "1.375rem", weight: 600, line: 1.25, tracking: "-0.015em" }
    h3: { size: "1rem", weight: 600, line: 1.35 }
    body-lg: { size: "1rem", weight: 400, line: 1.6 }
    body-md: { size: "0.875rem", weight: 400, line: 1.55 }
    body-sm: { size: "0.75rem", weight: 400, line: 1.5 }
    label:
      {
        size: "0.6875rem",
        weight: 650,
        line: 1.3,
        transform: "uppercase",
        tracking: "0.1em",
      }
```

**Regras:**

- Manrope sustenta toda a interface operacional e textos corridos.
- Bricolage Grotesque aparece somente em títulos de entrada, criação e projeto; nunca em tabelas ou metadados.
- Nenhum texto operacional fica abaixo de 12px. Labels técnicas podem usar 11px somente quando não forem necessárias para concluir a tarefa.
- Escala tipográfica independe do HTML exportado pelo Stitch.
- Títulos usam largura e line-height previsíveis; cards não reduzem fonte para acomodar excesso de conteúdo.
- Mono é reservado para IDs, timestamps, versões e dados técnicos.

---

## 5. Layout

```yaml
layout:
  spacing-base: 4
  scale: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, 2xl: 48, 3xl: 64 }
  shell:
    sidebar-expanded: "224px"
    sidebar-compact: "76px"
    utility-header: "60px"
    content-max: "1600px"
  breakpoints:
    { sm: "480px", md: "768px", lg: "1024px", xl: "1280px", 2xl: "1536px" }
  grid: { columns: 12, gutter: "var(--space-md)" }
```

- Desktop canônico: 1280×1024 e 1440×900.
- Abaixo de 1024px, a navegação lateral vira drawer.
- Abaixo de 768px, conteúdo usa uma coluna e painéis secundários viram sheets.
- Densidade média na Home e Projetos; alta apenas em editores e tabelas contextuais.
- Home e Projetos reservam pelo menos 55% da área útil para mídia, capas ou canvas.
- No editor, canvas e resultados ocupam pelo menos 65% da largura; painéis são recolhíveis.

---

## 6. Motion, Elevation & Shapes

```yaml
motion:
  fast: "120ms ease-out"
  standard: "180ms ease-out"
  deliberate: "240ms ease-out"
elevation:
  level-0: "none"
  level-1: "0 1px 2px rgba(0,0,0,.28)"
  level-2: "0 10px 30px rgba(0,0,0,.32)"
  level-3: "0 24px 64px rgba(0,0,0,.48)"
shapes:
  radius: { sm: "6px", md: "10px", lg: "16px", xl: "22px", full: "9999px" }
```

- Movimento comunica mudança de estado; não existe bounce decorativo.
- `prefers-reduced-motion` desativa transições não essenciais.
- Bordas e contraste de superfície têm prioridade sobre sombras no tema escuro.

---

## 7. Component System

**Atoms:** Button, IconButton, Input, Select, Badge, Avatar, Tooltip, Divider, Progress.  
**Molecules:** SearchField, WorkspaceSelector, Metric, StatusPill, ContentRow, ProjectCard, EmptyState.  
**Organisms:** GlobalFlowRail, ProductionRail, UtilityHeader, ProjectSubnav, CommandBar, ContentPipeline, EditorialAgenda, ApprovalQueue, CreativeToolbar, InspectorPanel, IntegrationFlow.  
**Templates:** DashboardShell, ProjectShell, CreativeLabShell, FocusEditorShell, SettingsShell, OperationShell.

Todos os componentes incluem estados default, hover, focus-visible, active, disabled, loading, empty e error quando aplicável. Alvos interativos têm pelo menos 44×44px ou espaçamento equivalente.

---

## 8. Backend & State Contract

- Backend FastAPI é a fonte de verdade para workspaces, projetos/campanhas, conteúdos, documentos criativos, assets, aprovações, métricas e auditoria.
- `localStorage` é permitido somente para preferências locais não críticas, como sidebar compacta.
- Toda query é escopada por `workspaceId`; projeto/campanha e conteúdo usam IDs reais na URL.
- Mutations apresentam estado pending/success/error e usam refresh/invalidação consistente.
- Modo local sem autenticação deve ser claramente rotulado como demonstração e nunca simular persistência remota.
- Autosave do Creative Lab é debounced, versionado e detecta conflito.
- Aprovação bloqueia publicação até decisão explícita registrada.

---

## 9. Do's and Don'ts

**Do:**

- Usar tokens semânticos e componentes canônicos.
- Preservar contexto de projeto entre navegação, edição e aprovação.
- Expor origem das métricas, recomendações e ações de IA.
- Oferecer loading, empty, error, stale, permission denied e success.
- Manter saída visível até em modo de foco.

**Don't:**

- Renderizar HTML do Stitch em iframe como implementação final.
- Criar uma rota por estado visual equivalente.
- Ocultar áreas importantes atrás de URLs não navegáveis.
- Misturar três sistemas tipográficos ou escalas independentes.
- Apresentar botões sem comportamento ou métricas de demonstração como reais.

---

## 10. Acceptance Criteria

Uma referência Stitch conta como implementada somente quando:

1. está mapeada para rota ou estado canônico;
2. participa de uma jornada com entrada e saída;
3. usa shell e tipografia compartilhados;
4. controles principais têm comportamento real;
5. dados vêm do backend ou são identificados como demonstração;
6. estados assíncronos e de permissão estão cobertos;
7. passa teclado, foco visível e contraste WCAG AA;
8. possui teste de comportamento e evidência visual.

---

## Changelog

| Versão | Data       | Autor                           | Mudança                                                                                       |
| ------ | ---------- | ------------------------------- | --------------------------------------------------------------------------------------------- |
| 0.4.1  | 2026-08-18 | Codex + proprietário do produto | Escala tipográfica aplicada às 37 telas canônicas, fontes variáveis corrigidas e trava contra texto operacional abaixo de 12px. |
| 0.4.0  | 2026-08-18 | Codex + proprietário do produto | Rails globais e de produção, contrato causal de navegação e integrações orientadas ao fluxo. |
| 0.3.0  | 2026-08-15 | Codex + proprietário do produto | Hubs contextuais, launcher por intenção e cobertura funcional instrumentada das 57 referências. |
| 0.2.0  | 2026-08-15 | Codex + proprietário do produto | Direção Creative Social Lab, cinco destinos globais e nova tipografia.                        |
| 0.1.0  | 2026-08-15 | Codex + proprietário do produto | Síntese do feedback sobre dashboard, fluxos, Creative Lab, tipografia e integração funcional. |
