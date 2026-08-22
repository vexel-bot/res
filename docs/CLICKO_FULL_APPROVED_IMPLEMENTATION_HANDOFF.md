# Clicko — Handoff completo de implementação das telas aprovadas

> Documento operacional para entregar a outro Codex em modo Goal/Meta.
> Este é o plano do produto inteiro — não apenas das integrações.

## 1. Meta

Transformar o repositório atual da Clicko no sistema representado pelas telas aprovadas, preservando e conectando o backend existente. As telas não são demonstrações independentes: juntas, elas passam a ser a interface real do produto, com navegação, estados, dados, permissões e jornadas completas.

O resultado deve transmitir uma **fábrica de criação de conteúdo e laboratório profissional de social media**, e não um CRM, dashboard administrativo genérico, galeria de imagens ou chatbot com IA.

O trabalho só está concluído quando:

1. todas as superfícies aprovadas estiverem implementadas ou explicitamente classificadas como indisponíveis por dependência real de backend;
2. todas as rotas formarem jornadas contínuas;
3. os recursos atuais não tiverem sido excluídos;
4. a aparência, a hierarquia e a densidade visual estiverem próximas das referências aprovadas;
5. os controles principais funcionarem com o backend existente;
6. estados vazios, carregamento, erro, permissão e indisponibilidade estiverem tratados;
7. testes e evidências visuais demonstrarem a paridade.

## 2. Regra de escopo

O escopo aprovado contém:

- **26 superfícies canônicas** do produto;
- **1 Studio aprovado**: Presenter Production Cell;
- **10 detalhes de integrações sociais**;
- **19 estados e ferramentas do Creative Lab**, incorporados às superfícies canônicas como modos contextuais;
- componentes, overlays, estados responsivos e jornadas necessários para ligar tudo isso.

Portanto, o programa visual contém **37 telas aprovadas de referência**, além dos 19 estados internos. Isso **não** significa construir 56 aplicações ou páginas isoladas.

Não implementar como tela canônica:

- os oito frames marcados `EXPLORATION` no Figma;
- os 38 frames antigos do Stitch como rotas separadas;
- variações rejeitadas ou rascunhos;
- páginas inventadas sem correspondência com uma jornada, feature existente ou decisão documentada.

Os 38 frames antigos servem apenas como repertório funcional. Toda capacidade útil deles deve ser preservada e encaixada na arquitetura canônica.

## 3. Fontes de verdade e prioridade

Leia todas estas fontes antes de alterar código:

1. Contrato de produto e design:
   - `C:\Users\edugu\Downloads\res\design.md`
2. Matriz técnica atual, rotas, entidades, gaps e estados:
   - `C:\Users\edugu\Downloads\res\docs\CLICKO_IMPLEMENTATION_MATRIX.md`
3. Este handoff:
   - `C:\Users\edugu\Downloads\res\docs\CLICKO_FULL_APPROVED_IMPLEMENTATION_HANDOFF.md`
4. Imagens locais das 26 telas que originaram o programa visual — usar como baseline histórica e apoio de comparação, não como substitutas dos frames aprovados no Figma:
   - `C:\Users\edugu\Documents\Codex\2026-07-30\new-chat\outputs\clicko-prototype-program\telas-finais-aprovadas`
5. Contratos detalhados das telas:
   - `C:\Users\edugu\Documents\Codex\2026-07-30\new-chat\outputs\clicko-prototype-program\screen-contracts`
6. Imagens das integrações sociais:
   - `C:\Users\edugu\Documents\Codex\2026-07-30\new-chat\outputs\clicko-prototype-program\social-integrations`
7. Arquivo Figma aprovado:
   - `https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko`
   - file key: `9qNitJb73bJt4nwQ5zlhft`
8. Código atual, que define o que já funciona e deve ser preservado:
   - `C:\Users\edugu\Downloads\res`

Ordem de prioridade em caso de divergência:

1. aprovação explícita mais recente do fundador;
2. frames do Figma explicitamente identificados como `CANONICAL` e `Approved` no arquivo Clicko;
3. `design.md`;
4. PNGs locais das 26 telas como referência histórica, composição e fallback quando um detalhe não estiver resolvido no frame aprovado;
5. contratos de tela;
6. matriz de implementação;
7. sistema atual;
8. frames antigos do Stitch somente como referência de capacidade.

**Regra de identificação:** o nome da pasta local `telas-finais-aprovadas` é histórico e não transforma automaticamente um PNG na versão atual de implementação. Para a implementação atual, “tela aprovada” significa um frame do arquivo Figma Clicko marcado como `CANONICAL` e `Approved`, incluindo a Presenter Production Cell e os detalhes sociais aprovados. Frames `EXPLORATION`, `Archive`, foundations, components, diretórios e diagramas de fluxo não são telas de produção. Os PNGs locais ajudam a recuperar intenção e comparar acabamento, mas não prevalecem sobre um frame canônico mais recente.

### 3.1 Allowlist fechada de frames do Figma

Esta lista foi auditada diretamente no arquivo Figma em 18/08/2026. **Somente estes 37 frame IDs podem ser usados como telas visuais de implementação.** Encontrar outro frame com aparência semelhante ou com a palavra `Approved` não autoriza sua implementação.

#### 26 telas canônicas do produto

| ID | Frame ID permitido | Nome exato no Figma | Página |
|---|---|---|---|
| S01 | `45:973` | `CANONICAL / S01 / Home / Approved v1` | `03 — Shell & Overlays` |
| S02 | `46:1100` | `CANONICAL / S02 / Create Launcher / Approved v1` | `03 — Shell & Overlays` |
| S03 | `98:2` | `CANONICAL / S03 / Radar Room / Approved v1` | `10 — Discover & Plan` |
| S04 | `105:102` | `CANONICAL / S04 / Opportunity Detail / Approved v1` | `10 — Discover & Plan` |
| S05 | `109:165` | `CANONICAL / S05 / Campaign Intake / Approved v1` | `10 — Discover & Plan` |
| S06 | `114:2` | `CANONICAL / S06 / Campaign Room / Approved v1` | `20 — Create & Review` |
| S07 | `121:104` | `CANONICAL / S07 / Create Hub & Content Inventory / Approved v1` | `20 — Create & Review` |
| S08 | `125:168` | `CANONICAL / S08 / Editorial Desk / Approved v1` | `20 — Create & Review` |
| S09 | `129:246` | `CANONICAL / S09 / Visual Editor / Approved v1` | `20 — Create & Review` |
| S10 | `132:246` | `CANONICAL / S10 / Creative Review Room / Approved v1` | `20 — Create & Review` |
| S11 | `135:2` | `CANONICAL / S11 / Editorial Calendar / Approved v1` | `30 — Publish & Learn` |
| S12 | `140:104` | `CANONICAL / S12 / Publisher Control / Approved v1` | `30 — Publish & Learn` |
| S13 | `145:168` | `CANONICAL / S13 / Post Detail & Performance / Approved v1` | `30 — Publish & Learn` |
| S14 | `148:233` | `CANONICAL / S14 / Reuse & Variation Lab / Approved v1` | `30 — Publish & Learn` |
| S15 | `152:246` | `CANONICAL / S15 / Campaign World / Approved v1` | `20 — Create & Review` |
| S16 | `156:310` | `CANONICAL / S16 / Campaign Moodboard / Approved v1` | `20 — Create & Review` |
| S17 | `157:392` | `CANONICAL / S17 / Carousel Builder / Approved v1` | `20 — Create & Review` |
| S18 | `159:230` | `CANONICAL / S18 / Brand Memory / Approved v1` | `10 — Discover & Plan` |
| S19 | `161:392` | `CANONICAL / S19 / Unified Library / Approved v1` | `20 — Create & Review` |
| S20 | `163:297` | `CANONICAL / S20 / Performance Observatory / Approved v1` | `30 — Publish & Learn` |
| S21 | `164:455` | `CANONICAL / S21 / Content Factory / Approved v1` | `20 — Create & Review` |
| S22 | `47:633` | `CANONICAL / S22 / Global Search / Approved v1 / Production Standard` | `03 — Shell & Overlays` |
| S23 | `167:753` | `CANONICAL / S23 / Projects Overview / Approved v1` | `03 — Shell & Overlays` |
| S24 | `168:816` | `CANONICAL / S24 / Activity Center / Approved v1` | `03 — Shell & Overlays` |
| S25 | `168:1092` | `CANONICAL / S25 / Workspace Switcher / Approved v1` | `03 — Shell & Overlays` |
| S26 | `169:1118` | `CANONICAL / S26 / Apps & Integrations / Approved v1` | `03 — Shell & Overlays` |

#### Studio aprovado

| ID | Frame ID permitido | Nome exato no Figma | Página |
|---|---|---|---|
| S34 | `205:4358` | `CANONICAL / S34 / Presenter Production Cell / Approved v1.1 / Studios Standard` | `40 — Studios` |

#### 10 detalhes sociais aprovados

| Provedor | Frame ID permitido | Nome exato no Figma | Página |
|---|---|---|---|
| Instagram | `252:2` | `SOCIAL / S-IG / Instagram Integration` | `35 — Social Integrations` |
| Facebook | `252:266` | `SOCIAL / S-FB / Facebook Integration` | `35 — Social Integrations` |
| TikTok | `252:504` | `SOCIAL / S-TT / TikTok Integration` | `35 — Social Integrations` |
| YouTube | `252:740` | `SOCIAL / S-YT / YouTube Integration` | `35 — Social Integrations` |
| X | `254:382` | `SOCIAL / S-X / X Integration` | `35 — Social Integrations` |
| LinkedIn | `254:620` | `SOCIAL / S-LI / LinkedIn Integration` | `35 — Social Integrations` |
| Pinterest | `254:857` | `SOCIAL / S-PI / Pinterest Integration` | `35 — Social Integrations` |
| Threads | `254:1093` | `SOCIAL / S-TH / Threads Integration` | `35 — Social Integrations` |
| Twitch | `259:472` | `SOCIAL / S-TW / Twitch Integration` | `35 — Social Integrations` |
| Google Business Profile | `254:1569` | `SOCIAL / S-GB / Google Business Profile Integration` | `35 — Social Integrations` |

### 3.2 Denylist do Figma

Não implementar como telas do sistema:

- qualquer frame da página `90 — Flows & States`, mesmo que contenha `Approved`; são duplicatas de jornada, não fontes visuais canônicas;
- qualquer frame da página `99 — Archive`;
- `SHELL STATE`, `QUALITY STANDARD`, `REFERENCE`, `README`, `Components`, `Group`, `DIRECTORY`, `PROTOTYPE INDEX` e `STATES MATRIX` como páginas;
- `222:4454` — exploração de Apps & Integrations;
- `187:2`, `189:85`, `190:144`, `192:203`, `193:262`, `194:321`, `196:393` e `198:452` — explorações de Studios;
- `213:617` — padrão visual de Studios; serve como especificação, não como tela;
- qualquer frame novo, duplicado ou não listado na allowlist sem aprovação explícita posterior.

Foundations, componentes, padrões, shells e matrizes podem orientar a implementação dos 37 frames permitidos, mas nunca entram na contagem de telas.

Nunca copie o HTML gerado pelo Stitch ou Figma. Reimplemente no sistema de componentes do repositório. Não use iframe.

## 4. Identidade e linguagem visual obrigatórias

### 4.1 Princípio visual

A Clicko deve parecer um ambiente de produção criativa em operação:

- mídia e canvas são protagonistas;
- decisões editoriais são visíveis e acionáveis;
- IA aparece como inteligência contextual, não como decoração futurista;
- cards representam trabalho real: campanha, peça, oportunidade, experimento, aprovação ou resultado;
- dashboards administrativos só aparecem quando a tarefa realmente exige análise;
- o produto deve ter acabamento de software profissional, sem estética artificial “IAtizada”.

### 4.2 Tokens oficiais

Usar os tokens do `design.md` como fonte programática:

- Canvas: `#080808`
- Surface base: `#0F0F0F`
- Surface raised: `#151515`
- Surface high: `#1C1C1C`
- Surface highest: `#222222`
- Control: `#111111`
- Border subtle: `#282828`
- Border strong: `#353535`
- Text primary: `#F5F5F5`
- Text secondary: `#A0A0A0`
- Text muted: `#727272`
- Action coral: `#FF5C5C`
- Creative orange: `#FF7A00`
- Success: `#53B780`
- Warning: `#F1A33C`
- Danger: `#E87979`
- Info: `#78A9E6`

Tipografia:

- Manrope para interface;
- Bricolage Grotesque para títulos expressivos;
- IBM Plex Mono para informação técnica, labels e sinais do sistema.

### 4.3 Densidade e proporção

- Desktop de validação: `1440 × 900` e `1280 × 1024`.
- Responsividade real para larguras menores; não apenas escala da tela desktop.
- Em editores e Studios, canvas/preview deve ocupar pelo menos 65% da área útil sempre que possível.
- Em Home, Projetos, Biblioteca e Fábrica, mídia e trabalho visual devem ocupar pelo menos 55% da composição.
- Evitar grandes blocos de texto. Explicações aparecem sob demanda, em tooltip, drawer ou detalhe.

## 5. Arquitetura de navegação

### 5.1 Navegação global

Destinos globais permanentes:

1. Home
2. Criar
3. Projetos
4. Biblioteca
5. Publicar

Utilidades globais:

- busca universal;
- notificações/atividade;
- workspace/marca atual;
- ajuda e conta;
- launcher de criação.

Radar, aprovações, analytics e ferramentas específicas não devem poluir a navegação principal. Eles aparecem no contexto certo:

- Radar dentro do fluxo de descoberta/criação;
- aprovações dentro de campanhas e conteúdos;
- analytics junto ao conteúdo, campanha ou observatório;
- ferramentas criativas dentro do editor/Studio;
- integrações a partir de Apps e pontos de necessidade.

### 5.2 Navegação de Studios e editores

Ao entrar em um Studio, a lateral esquerda deixa de ser a sidebar comum e vira uma **Production Rail** orientada ao fluxo:

1. entrada/briefing;
2. material e referências;
3. construção;
4. refinamento;
5. revisão;
6. saída/publicação.

A Production Rail deve mostrar progresso, etapa atual, pendências e retorno seguro. A logo Clicko no canto superior esquerdo leva à Home. Não repetir Home, Projetos, Biblioteca e Publicar dentro do Studio como uma sidebar administrativa.

## 6. Inventário canônico completo

### Grupo A — Superfícies globais e de entrada

| ID | Tela aprovada | Rota/estado canônico | Papel no produto | Referência |
|---|---|---|---|---|
| S01 | Home / Hoje | `/dashboard`; `/today` como alias | Central de trabalho: o que criar hoje, recomendações do Radar, trabalho em andamento e atalhos de formatos | PNG `01-home-canonical-coral-orange-v1.png`; Figma `45:973` |
| S02 | Create Launcher | overlay `?create=open` | Começar por oportunidade, oferta, vencedor ou briefing; também criar post, carrossel, stories, UGC, campanha e variações | PNG `02-create-launcher-open-v1.png`; Figma `46:1100` |
| S22 | Global Search | overlay `Ctrl/Cmd+K` e `?spotlight=open` | Busca por projetos, conteúdos, oportunidades, pessoas e comandos, com ações rápidas e recentes | PNG `22-global-search-spotlight-v1.png`; Figma `47:633` |
| S24 | Activity Center | drawer `?activity=open` | Notificações úteis, aprovações, falhas de publicação, aprendizados e atividade de equipe | PNG `24-activity-center-v1.png`; Figma `168:816` |
| S25 | Workspace Switcher | menu `?workspace=menu` | Troca de marca/workspace, papéis e estado da operação | PNG `25-workspace-switcher-v1.png`; Figma `168:1092` |

Critério do grupo: overlays devem preservar a tela de origem, fechar por teclado/clique externo, manter foco acessível e permitir deep link quando aplicável.

### Grupo B — Descobrir, decidir e planejar

| ID | Tela aprovada | Rota/estado canônico | Papel no produto | Referência |
|---|---|---|---|---|
| S03 | Radar Room | `/radar` | Priorizar oportunidades contextuais com evidência, aderência à marca, janela, saturação, risco e potencial | PNG `03-radar-room-v1.png`; Figma `98:2` |
| S04 | Opportunity Detail | `/radar/opportunities/:opportunityId` | Explicar por que agir ou não agir, mostrar ponte marca–contexto–público e permitir iniciar campanha | PNG `04-opportunity-detail-v1.png`; Figma `105:102` |
| S05 | Campaign Intake | `/campaigns/new?opportunity=:id` | Converter oportunidade, oferta ou briefing em objetivo, audiência, formatos, restrições e critérios de sucesso | PNG `05-campaign-intake-v1.png`; Figma `109:165` |
| S06 | Campaign Room | `/campaigns/:campaignId` | Sala operacional da campanha: conceito, frentes, conteúdos, status, aprovações, resultados e próximos passos | PNG `06-campaign-room-v1.png`; Figma `114:2` |
| S15 | Campaign World | `/campaigns/:campaignId/world` | Universo verbal e visual da campanha: narrativa, códigos, ângulos, cenas, mensagens, palavras e proibições | PNG `15-campaign-world-v1.png`; Figma `152:246` |
| S16 | Campaign Moodboard | `/campaigns/:campaignId/moodboard` | Curadoria visual operacional, não painel decorativo: referências com propósito, origem e aplicação | PNG `16-campaign-moodboard-v1.png`; Figma `156:310` |
| S18 | Brand Memory | `/brand-memory` | Memória privada da marca: produtos, público, voz, identidade, provas, restrições, aprendizados e referências | PNG `18-brand-memory-v1.png`; Figma `159:230` |
| S23 | Projects Overview | `/projects` | Visão visual de campanhas/projetos por etapa, responsável, urgência e continuidade | PNG `23-projects-overview-v1.png`; Figma `167:753` |

Critério do grupo: toda recomendação do Radar deve separar fatos, inferências e sugestões. Não inventar tendências, métricas ou fontes. Sem evidência atual, comunicar “dados insuficientes” e oferecer pesquisa/atualização.

### Grupo C — Criar, editar e revisar

| ID | Tela aprovada | Rota/estado canônico | Papel no produto | Referência |
|---|---|---|---|---|
| S07 | Create Hub & Content Inventory | `/content` | Hub visual para começar, continuar, filtrar e reutilizar conteúdos sem parecer gerenciador de arquivos | PNG `07-create-hub-content-inventory-v1.png`; contrato `06-campaign-room.md`/`07-create-hub-content-inventory.md` |
| S08 | Editorial Desk | `/content/:contentId/edit?mode=editorial` | Estruturar gancho, promessa, argumento, CTA, sequência e legenda com inteligência da marca | PNG `08-editorial-desk-v1.png`; contrato `08-editorial-desk.md`; Figma `125:168` |
| S09 | Visual Editor | `/content/:contentId/edit?mode=visual` | Editor profissional orientado ao social: canvas, camadas, formato, mídia, elementos, tipografia, efeitos e variações | PNG `09-visual-editor-v1.png`; contrato `09-visual-editor.md` |
| S10 | Creative Review Room | `/approvals/:postId?view=creative` | Aprovação contextual em cima da peça, comparação de versões, comentários, decisão e feedback rápido | PNG `10-creative-review-room-v1.png`; contrato `10-creative-review-room.md` |
| S17 | Carousel Builder | `/content/:contentId/edit?mode=carousel` | Construção de narrativa slide a slide com hierarquia, consistência, reordenação e validação do conjunto | PNG `17-carousel-builder-v1.png`; contrato `15-carousel-builder.md` |
| S19 | Unified Library | `/library/assets` | Biblioteca de assets, templates, marca e linhagem; busca por uso criativo, direitos e origem | PNG `19-unified-library-v2.png`; contrato `17-unified-library.md`; Figma `161:392` |
| S21 | Content Factory | `/factory` | Orquestrar lotes, formatos, variações, campanhas e estados de produção; visão de fábrica, não tabela administrativa | PNG `21-content-factory-v1.png`; Figma `164:455` |

Critério do grupo: a IA deve sugerir decisões e variações com justificativa, mas o usuário mantém controle editorial. Toda geração cria versão, registra origem e permite voltar. Autosave deve ser visível, versionado e preparado para conflito.

### Grupo D — Publicar, medir e aprender

| ID | Tela aprovada | Rota/estado canônico | Papel no produto | Referência |
|---|---|---|---|---|
| S11 | Editorial Calendar | `/calendar` | Organizar campanhas, conteúdos, canais e cadência com drag-and-drop e leitura visual | PNG `11-editorial-calendar-v1.png`; contrato `11-calendar-publisher-control.md`; Figma `135:2` |
| S12 | Publisher Control | `/publish/:postId` | Pré-publicação: canais, formatos, copy, agenda, validações, permissões e bloqueios | PNG `12-publisher-control-v1.png`; contrato `11-calendar-publisher-control.md`; Figma `140:104` |
| S13 | Post Detail & Performance | `/content/:postId` | Conteúdo publicado + distribuição + resultado + diagnóstico + ações recomendadas | PNG `13-post-detail-performance-v1.png`; contrato `12-post-detail-performance.md`; Figma `145:168` |
| S14 | Reuse & Variation Lab | `/content/:postId/remix` e `?view=variations` | Transformar um vencedor em novas peças sem perder o princípio que funcionou | PNG `14-reuse-variation-lab-v1.png`; contrato `13-reuse-variation-lab.md`; Figma `148:233` |
| S20 | Performance Observatory | `/analytics/learning` | Aprendizado por marca, campanha, formato, gancho, audiência e período, com limites de confiança claros | PNG `20-performance-observatory-v1.png`; contrato `18-performance-observatory.md`; Figma `163:297` |

Critério do grupo: publicação exige aprovação e conexão válida. Analytics nunca usa números simulados como verdade. Quando dados estiverem incompletos, mostrar cobertura, atraso e fonte.

### Grupo E — Apps e integrações

| ID | Tela aprovada | Rota/estado canônico | Papel no produto | Referência |
|---|---|---|---|---|
| S26 | Apps & Integrations | `/apps` | Descoberta, conexão, status, saúde, permissões e atividade das integrações | PNG `26-apps-integrations-v1.png`; Figma `169:1118` |

A rota antiga `/settings/channels` deve redirecionar para `/apps` ou para o detalhe do provedor correspondente. Não manter dois centros concorrentes.

### Grupo F — Studio aprovado

| ID | Tela aprovada | Rota recomendada | Papel no produto | Referência |
|---|---|---|---|---|
| S34 | Presenter Production Cell | `/content/:contentId/edit?mode=presenter` | Captura guiada do apresentador/personagem real, consentimento, qualidade, expressão, pausas, revisão e preparação de identidade audiovisual | Figma `205:4358`; nome `CANONICAL / S34 / Presenter Production Cell / Approved v1.1 / Studios Standard` |

Esta é a única tela aprovada do conjunto novo de Studios. Usar também o frame `STANDARD / Studios Visual & Product Pattern` (`213:617`) como contrato visual.

O Studio não deve prometer clonagem, voz ou geração realista quando o backend não oferecer isso. Nesses casos, mostrar capacidade futura ou etapa bloqueada com explicação objetiva. Consentimento, direitos de uso, expiração, revogação e trilha de auditoria são requisitos de produto, não detalhes opcionais.

## 7. Detalhes de integrações sociais aprovados

Rotas recomendadas: `/apps/:provider`. Conexão pode abrir wizard contextual em `/apps/:provider/connect` ou overlay equivalente com URL navegável.

| Provedor | Figma | Capacidades a representar | Configuração mínima |
|---|---|---|---|
| Instagram | `252:2` | Publicação, agendamento, comentários, métricas e status | Conta profissional, página/Business Manager quando exigido, escopos, expiração do token, seleção de perfil |
| Facebook | `252:266` | Páginas, publicação, comentários, métricas e falhas | Login Meta, página, permissões, papéis e validade da conexão |
| TikTok | `252:504` | Vídeo, publicação/agendamento quando permitido, métricas e status | Conta, escopos, restrições de postagem, privacidade e limites da API |
| YouTube | `252:740` | Upload, Shorts, metadados, thumbnails e analytics | Canal, OAuth Google, permissões, quota e regras de conteúdo |
| X | `254:382` | Posts, threads, mídia e métricas disponíveis | Conta, plano/API disponível, escopos e limites; não fingir capacidade não contratada |
| LinkedIn | `254:620` | Perfil/página, posts, mídia e métricas disponíveis | Organização ou membro, autorização, papel administrativo e escopos aprovados |
| Pinterest | `254:857` | Pins, boards, mídia e analytics | Conta business, board padrão, escopos e regras de mídia |
| Threads | `254:1093` | Posts, mídia, replies e insights suportados | Perfil elegível, vínculo Meta quando exigido, escopos e validade |
| Twitch | `259:472` | Canal, eventos, clips e sinais úteis para conteúdo | Canal, OAuth, escopos, EventSub/webhooks e estado da assinatura |
| Google Business Profile | `254:1569` | Localizações, posts, avaliações e métricas disponíveis | Conta Google, grupo/localização, permissões e compatibilidade atual da API |

Todas as telas devem ter logos oficiais reconhecíveis, respeitando uso de marca. Não substituir por letras genéricas ou ícones aleatórios.

Estados obrigatórios por integração:

1. disponível para conectar;
2. conectando/OAuth em andamento;
3. conectada e saudável;
4. conectada com ação necessária;
5. token expirado/reconexão necessária;
6. permissão insuficiente;
7. conta/canal não elegível;
8. quota ou rate limit;
9. sincronização parcial;
10. erro de publicação;
11. desconectando/confirmação;
12. histórico e auditoria.

Componentes comuns do detalhe:

- identidade e descrição do provedor;
- status de saúde da conexão;
- conta, página, canal ou perfil selecionado;
- capacidades habilitadas e indisponíveis;
- permissões e escopos;
- padrões de publicação;
- sincronização e última execução;
- limites, quotas e restrições;
- atividade recente;
- ações de testar, sincronizar, reconectar e desconectar;
- consequências claras antes de revogar acesso.

Integrações utilitárias a planejar dentro de `/apps`, usando o mesmo padrão de detalhe, depois das sociais:

- Google Drive;
- Dropbox;
- Canva;
- Figma;
- Google Analytics 4;
- Google Calendar;
- Slack;
- bancos de mídia como Pexels/Unsplash;
- Webhooks/API;
- importação de dados.

## 8. Estados e ferramentas do Creative Lab

Estes 19 itens precisam existir, mas devem ser implementados como modos, painéis ou estados das telas canônicas — não como produtos independentes:

| ID | Estado/ferramenta | Rota/estado |
|---|---|---|
| B01 | Campaign Moodboard | `/campaigns/active/moodboard` |
| B02 | Visual Content Board | `/content` |
| B03 | Pro Composition Canvas | `/content/draft/edit?mode=visual&canvas=pro` |
| B04 | Campaign World | `/campaigns/active/world` |
| B05 | Editorial Creation Desk | `/content/draft/edit?mode=editorial` |
| B06 | Creative Review Room | `/approvals/post-1?view=creative` |
| B07 | Precision & Type | `/content/draft/edit?mode=visual&panel=typography` |
| B08 | Content Inventory | `/content?view=inventory` |
| B09 | Brand Asset Library | `/library/assets` |
| B10 | Format & Variation Board | `/content/post-1/variations` |
| B11 | Visual Composition Handoff | `/content/draft/edit?mode=visual&handoff=1` |
| B12 | Visual Remix Lab | `/content/post-1/remix?lab=visual` |
| B13 | Carousel Builder Lab | `/content/draft/edit?mode=carousel&variant=lab` |
| B14 | Motion Studio | `/content/draft/edit?mode=video&panel=motion` |
| B15 | Post Detail & Performance | `/content/post-1` |
| B16 | Content Command Dashboard | `/content/dashboard` |
| B17 | Post Creation Workspace | `/content/new?type=post` |
| B18 | Element Vault | `/content/draft/edit?mode=visual&panel=elements` |
| B19 | Effects & Light | `/content/draft/edit?mode=visual&panel=effects` |

### Ferramentas do editor visual

O editor precisa ser mais focado que Canva/Figma/Photoshop, não uma cópia integral. Priorizar:

- seleção, movimento, resize, crop e alinhamento;
- layers, lock, hide, group e reorder;
- texto, tipografia, hierarquia e estilos da marca;
- mídia, remoção/substituição de fundo e enquadramento;
- formas e elementos relevantes para social;
- cores, gradientes e tokens da marca;
- sombras, brilho, blur, opacidade, blend e luz;
- grid, guides, snapping, margens seguras e formatos sociais;
- estados/variantes para carrossel;
- adaptação automática entre formatos com revisão humana;
- motion essencial: entrada, saída, ênfase, timing e preview;
- histórico, versões, autosave e comparação;
- sugestões do algoritmo vinculadas à estratégia da campanha;
- validação de legibilidade, safe area, contraste, identidade e densidade.

Não tentar reproduzir toda a superfície funcional de Canva, Figma ou Photoshop na primeira entrega. O diferencial é unir edição suficiente com contexto de marca, oportunidade, campanha, aprendizagem e produção multiformato.

## 9. Jornadas que devem funcionar de ponta a ponta

### Jornada 1 — Oportunidade até publicação

`Home → Radar → Opportunity Detail → Campaign Intake → Campaign Room → Editorial Desk/Visual Editor → Creative Review → Publisher Control → Post Detail → Performance Observatory → Reuse Lab`

### Jornada 2 — Oferta até campanha

`Create Launcher → Campaign Intake → Campaign World → Moodboard → Content Factory → editores → Review → Calendar → Publish`

### Jornada 3 — Conteúdo diário

`Home → Criar post → Briefing rápido → Editorial Desk → Visual Editor → Review → Calendar/Publish`

### Jornada 4 — Reutilização inteligente

`Post Detail → entender o que funcionou → Reuse & Variation Lab → gerar variações → Review → Publish`

### Jornada 5 — Produção em lote

`Campaign Room → Content Factory → selecionar formatos/quantidades → gerar rascunhos versionados → editar em contexto → aprovar em lote → Calendar`

### Jornada 6 — Apresentador e vídeo assistido

`Campaign/Content → Presenter Production Cell → consentimento → captura guiada → revisão de qualidade → aprovação da identidade → Motion/Video Studio → revisão → publicação`

Enquanto o backend audiovisual avançado não existir, a jornada pode terminar em material preparado/exportável, mas não pode simular geração concluída.

### Jornada 7 — Conectar canal no momento da necessidade

`Publisher Control → canal não conectado → detalhe da integração → OAuth/configuração → teste → retorno ao publisher preservando o trabalho`

## 10. Arquitetura de frontend recomendada

O frontend atual usa React 19, TypeScript, Vite 6 e Tailwind 4. Evoluir sem reescrever o projeto do zero.

### 10.1 Separar o monólito canônico

`src/canonical/CanonicalProduct.tsx` não deve continuar absorvendo todas as telas. Extrair progressivamente:

```text
src/
  app/
    router/
    providers/
  canonical/
    shell/
    overlays/
    screens/
      home/
      radar/
      campaigns/
      content/
      calendar/
      publishing/
      analytics/
      library/
      factory/
      apps/
      studios/
  components/
    primitives/
    creative/
    data-states/
  features/
    integrations/
    approvals/
    editor/
    feedback/
  api/
  product/
```

Não fazer uma reorganização massiva sem testes. Extrair por jornada e manter compatibilidade durante a transição.

### 10.2 Componentes compartilhados obrigatórios

- `AppShell`
- `GlobalNav`
- `ProductionRail`
- `TopSearch`
- `CreateLauncher`
- `GlobalSearchOverlay`
- `ActivityDrawer`
- `WorkspaceMenu`
- `CreativeCard`
- `ContentPreview`
- `CampaignStatus`
- `EvidenceBadge`
- `ConfidenceIndicator`
- `ApprovalControls`
- `QuickFeedback`
- `VersionTimeline`
- `AsyncState`
- `PermissionState`
- `IntegrationCard`
- `IntegrationDetailLayout`
- `ConnectionHealth`
- `OAuthWizard`
- `CanvasWorkspace`
- `InspectorPanel`
- `AssetRail`

Componentes não devem apagar diferenças funcionais entre telas. Compartilhar estrutura e comportamento; manter a tarefa central específica.

### 10.3 Estado e URL

- Estados importantes devem ser recuperáveis pela URL.
- Overlays globais usam query params sem perder a página anterior.
- Filtros de inventário, calendário, Radar e analytics devem ser compartilháveis quando fizer sentido.
- `localStorage` serve apenas para preferências de interface, nunca como fonte de verdade do produto.
- Cache de API deve ter invalidação explícita após mutações.

## 11. Backend e contratos de dados

O backend atual em FastAPI, SQLAlchemy, Alembic, Celery, Redis e SQLite é a fonte de verdade. Não substituir por Supabase e não criar um backend paralelo.

Antes de criar entidade nova, mapear os modelos, schemas, routers e services existentes:

- `backend/app/models.py`
- `backend/app/schemas.py`
- routers e services em `backend/app/`
- cliente atual em `src/api/productApi.ts`

### 11.1 Domínios que devem ser preservados/conectados

- workspaces, usuários, equipe e papéis;
- marcas e memória da marca;
- campanhas;
- conteúdos, formatos e versões;
- assets/templates;
- aprovações e comentários;
- agenda/publicação;
- métricas e aprendizagem;
- Radar, fontes, oportunidades e evidências;
- jobs assíncronos e histórico.

### 11.2 Domínio de integrações a adicionar

Entidades mínimas recomendadas:

- `integration_connections`
- `integration_credentials` ou referência segura ao segredo
- `integration_permissions`
- `integration_settings`
- `integration_sync_runs`
- `external_publications`
- `integration_events`
- métricas brutas/normalizadas quando necessário

Requisitos:

- credenciais criptografadas e nunca devolvidas ao frontend;
- OAuth com `state` e PKCE quando suportado;
- escopos mínimos;
- refresh/expiração tratados;
- desconexão revoga credencial quando possível;
- webhooks assinados, idempotentes e auditáveis;
- jobs com retry, backoff e dead-letter/estado terminal;
- isolamento por workspace;
- logs sem tokens ou dados sensíveis;
- normalização sem eliminar os dados específicos do provedor;
- capability matrix por conta/conexão, não apenas por nome da plataforma.

Interface lógica do adapter:

```text
authorize
exchange_callback
refresh_credentials
list_accounts
get_capabilities
validate_asset
publish
schedule_or_enqueue
fetch_publication_status
fetch_metrics
subscribe_webhooks
disconnect
```

Não assumir que todas as APIs têm as mesmas capacidades. A interface mostra apenas o que aquela conexão realmente suporta.

### 11.3 Feedback e aprendizagem

Toda sugestão importante da IA deve aceitar feedback em poucos segundos:

- aprovar;
- rejeitar;
- ajustar preferência;
- escolher um motivo rápido;
- comentário opcional.

Registrar:

- objeto avaliado;
- decisão;
- motivo;
- contexto e versão do conteúdo;
- usuário e papel;
- momento da jornada;
- política/modelo usado;
- efeito posterior, quando mensurável.

Mostrar valor ao usuário com linguagem como “Estamos refinando suas próximas recomendações com base nas decisões da sua equipe”, sem sugerir uso indevido de dados entre clientes.

Aprendizado entre marcas do mesmo nicho só pode usar sinais agregados e anonimizados, com governança, consentimento e isolamento. Memória privada, assets, resultados identificáveis, identidade e materiais de uma marca nunca alimentam outra diretamente.

### 11.4 Presenter/identidade audiovisual

Planejar entidades para:

- consentimento e finalidade;
- direitos e período de uso;
- pessoa/apresentador;
- sessões e amostras de captura;
- avaliações de qualidade;
- versões de identidade;
- aprovação, revogação e expiração;
- trilha de geração/edição;
- proveniência do resultado.

Recursos de face/voz exigem autorização explícita, confirmação de identidade, uso auditável e revogação. Não criar atalhos que contornem isso.

## 12. Plano de implementação por fases

Cada fase termina com testes, screenshots e atualização da matriz. Não avançar acumulando telas quebradas.

### Fase 0 — Baseline e proteção do trabalho existente

1. Inspecionar `git status` e preservar todas as alterações do usuário.
2. Rodar build, lint e testes atuais; registrar falhas preexistentes.
3. Inventariar rotas, componentes, APIs e entidades existentes.
4. Comparar a matriz com o código real e atualizar somente divergências comprovadas.
5. Criar uma suíte de captura visual nos dois viewports de referência.

Saída: baseline verificável, sem reset, checkout destrutivo ou exclusão de feature.

### Fase 1 — Foundations, shell e componentes

1. Materializar tokens do `design.md` em CSS/tema.
2. Ajustar tipografia, superfícies, bordas, estados e foco.
3. Implementar `AppShell`, navegação global e `ProductionRail`.
4. Implementar os overlays S02, S22, S24 e S25.
5. Criar componentes compartilhados de mídia, status, evidência, versão e feedback.

Saída: linguagem visual consistente e navegação utilizável antes de multiplicar telas.

### Fase 2 — Jornada principal Radar → campanha → criação

Implementar e conectar:

- S01 Home;
- S03 Radar;
- S04 Opportunity Detail;
- S05 Campaign Intake;
- S06 Campaign Room;
- S15 Campaign World;
- S16 Campaign Moodboard;
- S18 Brand Memory;
- S23 Projects Overview.

Saída: oportunidade real/honesta vira campanha sem perder contexto.

### Fase 3 — Núcleo da fábrica de conteúdo

Implementar e conectar:

- S07 Create Hub & Inventory;
- S08 Editorial Desk;
- S09 Visual Editor;
- S10 Creative Review Room;
- S17 Carousel Builder;
- S19 Unified Library;
- S21 Content Factory;
- estados B01–B13 e B15–B19 dentro dessas superfícies.

Prioridade funcional:

1. conteúdo e versão;
2. autosave;
3. assets;
4. edição editorial;
5. edição visual essencial;
6. comentários e aprovação;
7. variações e handoff;
8. lote/fábrica.

Saída: a Clicko permite produzir e revisar conteúdo real, em vez de apenas exibir protótipos.

### Fase 4 — Publicar, medir e reutilizar

Implementar e conectar:

- S11 Calendar;
- S12 Publisher Control;
- S13 Post Detail & Performance;
- S14 Reuse & Variation Lab;
- S20 Performance Observatory.

Saída: conteúdo aprovado chega à fila de publicação, retorna com status/métricas e alimenta reutilização e aprendizado.

### Fase 5 — Studios e vídeo assistido

1. Implementar S34 Presenter Production Cell com Production Rail.
2. Incorporar B14 Motion Studio como modo do editor.
3. Entregar primeiro captura/importação, validação, edição assistida, legendas, enquadramento, ritmo, identidade e exportação.
4. Isolar geração/clone de face e voz atrás de capabilities e requisitos de consentimento.
5. Criar estados honestos para serviços ainda não integrados.

Saída: fluxo audiovisual coerente e seguro, sem promessas fictícias.

### Fase 6 — Centro de Apps e integrações

1. Finalizar S26 `/apps`.
2. Criar layout comum de detalhe.
3. Implementar as 10 telas sociais aprovadas.
4. Implementar backend de conexão, saúde, permissões, sync e auditoria.
5. Integrar a primeira onda real conforme credenciais disponíveis:
   - Meta/Instagram/Facebook;
   - TikTok;
   - YouTube.
6. Segunda onda:
   - LinkedIn;
   - Threads;
   - Pinterest;
   - Google Business Profile.
7. Terceira onda, condicionada a acesso/custo/capabilities:
   - X;
   - Twitch.
8. Depois, integrar Google Drive, Dropbox, Canva, Figma, GA4, Calendar, Slack e Webhooks conforme prioridade de produto.

Saída: páginas visuais completas para todos os provedores e integrações reais somente onde a API/credencial permite.

### Fase 7 — Consolidação e remoção de duplicidades

1. Redirecionar rotas legadas às superfícies canônicas.
2. Remover apenas código comprovadamente órfão, depois de verificar feature parity.
3. Não excluir feature porque ela não apareceu explicitamente em um protótipo; encaixá-la no fluxo canônico ou documentar a decisão.
4. Reduzir `CanonicalProduct.tsx` sem quebrar compatibilidade.
5. Validar permissões por papel e workspace.

### Fase 8 — Auditoria final

1. Comparação visual automatizada e manual com PNG/Figma.
2. Testes das sete jornadas.
3. Teclado, foco, contraste e leitores de tela nos fluxos críticos.
4. Viewports desktop e responsivos.
5. Estados de loading, vazio, erro, offline, permissão e conflito.
6. Testes backend, migrations e jobs.
7. Relatório final tela a tela: implementada, parcial, bloqueada ou fora de escopo, sempre com evidência.

## 13. MVP e prioridade comercial

Se for necessário obter uma entrega utilizável antes do programa completo, não faça versões rasas das 37 telas. Entregue um corte vertical:

1. S01 Home;
2. S02 Create Launcher;
3. S18 Brand Memory;
4. S03/S04 Radar com evidência real ou estado honesto;
5. S05/S06 campanha;
6. S07/S08/S09 criação e edição de post;
7. S10 aprovação;
8. S11/S12 calendário e publicação;
9. S13 resultado;
10. S14 reutilização;
11. S26 + conexão real inicial necessária para publicar.

Depois expandir Fábrica, Carousel, Moodboard, Studios, analytics avançado e o restante das integrações. O objetivo do MVP é completar trabalho real e cobrar por ele, não apenas aumentar a contagem de telas.

## 14. Qualidade, testes e evidências

Comandos existentes a considerar:

```text
npm run dev
npm run lint
npm run build
npm run test:e2e
npm run test:backend
npm run lint:backend
npm run test:stitch
```

Para cada tela/estado aprovado:

1. abrir pela rota canônica;
2. capturar screenshot em `1440 × 900` e `1280 × 1024`;
3. comparar com PNG/Figma lado a lado;
4. validar hierarquia, proporção, espaçamento, tipografia, cor, densidade e mídia;
5. testar ação principal e retorno;
6. testar loading, vazio, erro e permissão;
7. testar teclado/foco;
8. verificar dados e origem;
9. registrar gap remanescente.

Não aceitar como “próximo” apenas por usar as mesmas cores. Critérios de paridade visual:

- composição e zonas funcionais;
- proporção e prioridade dos elementos;
- densidade;
- qualidade dos previews;
- navegação e contexto;
- estados e microinterações;
- acabamento de borda, sombra, tipo, ritmo e alinhamento.

## 15. Definition of Done por tela

Uma tela só é considerada concluída quando:

- possui rota ou estado canônico recuperável;
- participa de pelo menos uma jornada documentada;
- usa shell global ou Production Rail correto;
- corresponde visualmente à referência aprovada;
- ação principal funciona;
- ações secundárias essenciais funcionam ou comunicam indisponibilidade real;
- usa backend real quando o domínio existe;
- não apresenta dados inventados como reais;
- preserva contexto entre navegações;
- possui estados de loading, vazio, erro e permissão;
- é navegável por teclado e tem foco visível;
- funciona nos viewports definidos;
- possui teste proporcional ao risco;
- possui screenshot final e status registrado na matriz.

## 16. Regras de execução do outro Codex

1. Não recomeçar o projeto do zero.
2. Não substituir o backend atual.
3. Não usar Supabase.
4. Não apagar features existentes.
5. Não tratar PNGs como imagens a serem colocadas dentro da aplicação.
6. Não colar código de Figma/Stitch sem adaptar ao sistema.
7. Não criar páginas isoladas só para aumentar cobertura.
8. Não inventar métricas, fontes, oportunidades ou integrações funcionais.
9. Não expor tokens, credenciais ou segredos no cliente/log.
10. Não modificar ou descartar alterações do usuário sem necessidade e autorização.
11. Fazer pequenas integrações verticais verificáveis, mantendo o sistema executável.
12. Atualizar a matriz durante o trabalho, e não apenas no fim.

## 17. Prompt pronto para o novo chat em modo Goal/Meta

Copie o bloco abaixo para o novo chat:

---

Você está trabalhando no repositório real da Clicko em:

`C:\Users\edugu\Downloads\res`

Sua meta é implementar **todo o sistema aprovado da Clicko**, e não apenas as integrações. As telas aprovadas juntas são a nova interface do produto; não são mockups independentes. Preserve o backend FastAPI e todas as features já existentes.

Antes de alterar qualquer arquivo, leia integralmente e siga:

1. `C:\Users\edugu\Downloads\res\design.md`
2. `C:\Users\edugu\Downloads\res\docs\CLICKO_IMPLEMENTATION_MATRIX.md`
3. `C:\Users\edugu\Downloads\res\docs\CLICKO_FULL_APPROVED_IMPLEMENTATION_HANDOFF.md`
4. todos os contratos em `C:\Users\edugu\Documents\Codex\2026-07-30\new-chat\outputs\clicko-prototype-program\screen-contracts`
5. as 26 imagens históricas de referência em `C:\Users\edugu\Documents\Codex\2026-07-30\new-chat\outputs\clicko-prototype-program\telas-finais-aprovadas` — elas são baseline visual, não substituem os frames canônicos mais recentes do Figma
6. as 10 referências em `C:\Users\edugu\Documents\Codex\2026-07-30\new-chat\outputs\clicko-prototype-program\social-integrations`
7. o arquivo Figma aprovado `https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko`

O escopo é:

- 26 superfícies canônicas;
- 1 Studio aprovado, Presenter Production Cell;
- 10 telas de detalhes de integrações sociais;
- 19 estados/ferramentas do Creative Lab incorporados às rotas canônicas;
- todas as jornadas, componentes, estados, backend e testes necessários para torná-los um único produto funcional.

Para decidir o que é tela de produção, use exclusivamente a allowlist fechada da seção 3.1 deste handoff: 26 frames canônicos, o Presenter Production Cell e 10 detalhes sociais. O texto `Approved` sozinho não é suficiente, pois a página de fluxos contém duplicatas aprovadas. Não implemente os frames da denylist da seção 3.2, os oito conceitos `EXPLORATION`, conteúdo de `Archive`, foundations, components, diretórios ou fluxogramas como telas. Não transforme os 38 frames antigos do Stitch em 38 páginas; preserve suas capacidades dentro da arquitetura canônica. Não exclua uma feature apenas porque ela não aparece isoladamente em uma tela.

Antes de codificar, produza um ledger de implementação com exatamente as 37 entradas da allowlist, contendo: nome canônico, page/frame ID do Figma, rota, referência PNG auxiliar quando houver, status atual no código e gap. Valide que nenhum frame da denylist entrou no ledger. Se um frame não constar da allowlist, não o implemente até existir aprovação explícita e atualização deste documento.

Primeiro:

1. inspecione o `git status` e preserve o trabalho existente;
2. rode o baseline de build/lint/testes;
3. audite o código contra a matriz e as referências;
4. apresente um plano faseado por jornadas e mantenha-o atualizado;
5. só então implemente.

Implemente na ordem definida no handoff: foundations/shell, jornada Radar–campanha, fábrica e editores, publicação/aprendizado, Studios e integrações. Trabalhe em cortes verticais funcionais. Use dados reais do backend quando existirem; quando algo ainda depender de API, credencial ou domínio inexistente, entregue estado honesto e documente o bloqueio — nunca simule funcionamento.

A interface deve parecer um **laboratório profissional de social media e fábrica de criação de conteúdo**, não CRM, dashboard genérico, explorador de arquivos ou chat de IA. Use a paleta e os tokens do `design.md`. Nas áreas criativas, mídia/canvas dominam. Studios usam Production Rail; clicar na logo volta à Home.

Para cada superfície, valide ação principal, jornada, estados assíncronos, permissões, responsividade, acessibilidade, backend, testes e paridade visual. Capture screenshots em `1440 × 900` e `1280 × 1024` e compare com as referências. Não considere uma tela pronta somente porque contém os mesmos textos ou cores.

Você pode refatorar a arquitetura gradualmente, especialmente o `src/canonical/CanonicalProduct.tsx`, mas não faça reescrita destrutiva. Continue até que todas as superfícies aprovadas estejam classificadas na matriz como concluídas, parciais com gap objetivo ou bloqueadas por dependência externa real, com evidência para cada status.

Entregáveis finais:

1. sistema funcionando no repositório existente;
2. backend e migrations necessários;
3. testes passando ou relatório preciso das falhas preexistentes;
4. screenshots de comparação;
5. matriz atualizada tela a tela;
6. relatório de rotas, jornadas, integrações reais, limitações e próximos passos.

---

## 18. Resultado esperado

Ao final, a Clicko deve permitir que uma equipe:

1. entenda o que vale criar agora;
2. transforme contexto, oferta ou oportunidade em campanha;
3. produza peças e variações em um ambiente visual profissional;
4. revise e aprove com feedback rápido;
5. organize e publique nos canais conectados;
6. acompanhe resultado sem métricas fictícias;
7. reutilize vencedores;
8. refine recomendações com memória da marca e decisões humanas;
9. evolua para vídeo e apresentadores com consentimento, qualidade e controle.

Esse é o produto. As integrações são uma parte dele, não o escopo inteiro.
