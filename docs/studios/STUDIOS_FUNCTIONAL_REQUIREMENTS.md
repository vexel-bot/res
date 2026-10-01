# Clicko Studios — Catálogo de requisitos funcionais

**Versão:** 0.1  
**Data da análise:** 2026-08-23  
**Objetivo:** estabelecer a fonte de verdade funcional para planejar, prototipar e produzir os Studios.  
**Documentos relacionados:** `docs/CLICKO_STUDIOS_STRATEGY.md`, `docs/studios/CURRENT_STATE_INVENTORY.md`, `design.md` e `docs/CLICKO_FULL_APPROVED_IMPLEMENTATION_HANDOFF.md`.

---

## 1. Resultado da análise

Os Studios não devem ser planejados como páginas isoladas nem como uma lista de geradores de IA. O produto precisa de um sistema de produção formado por:

1. uma entrada contextual comum;
2. direção criativa estruturada;
3. editores especializados que compartilham o mesmo documento;
4. uma fábrica que orquestra tarefas e variações;
5. revisão humana e aprendizado;
6. assets, direitos e linhagem compartilhados.

O código atual já fornece parte importante da base:

- `CreativeDocumentV1`, `CreativeBriefV1` e `GenerationJobV1`;
- persistência e versionamento inicial para Visual e Carrossel;
- autenticação, workspace, marca, campanha, Radar, aprovação e biblioteca;
- superfícies canônicas aprovadas;
- alguns componentes legados com ideias úteis para imagem, vídeo, briefing e matriz criativa.

As maiores lacunas são:

- Editorial ainda não utiliza o documento canônico de ponta a ponta;
- Vídeo não possui Studio canônico e pipeline real;
- Motion ainda é apenas uma direção de interface;
- Presenter não possui domínio próprio de consentimento e geração;
- Fábrica não acompanha jobs reais;
- várias ações visuais são demonstrativas;
- as engines open source ainda não foram selecionadas por benchmark.

---

## 2. Legenda de maturidade

Cada requisito recebe uma classificação:

| Código | Significado |
|---|---|
| `F` | Funcional e persistido no caminho canônico atual. |
| `V` | Representado visualmente, mas sem comportamento completo. |
| `L` | Existe em componente ou endpoint legado e pode ser reaproveitado. |
| `N` | Novo requisito necessário. |
| `E` | Experimento; depende de benchmark, licença, infraestrutura ou validação. |

Prioridade:

| Código | Significado |
|---|---|
| `P0` | Fundação obrigatória para qualquer Studio. |
| `P1` | Primeiro produto monetizável de posts e carrosséis. |
| `P2` | Vídeo assistido e produtividade avançada. |
| `P3` | Imagem generativa e Presenter controlado. |
| `P4` | Escala, automações sofisticadas e inteligência avançada. |

---

## 3. Usuários e trabalhos principais

### Social media operador

- precisa criar com rapidez sem perder qualidade;
- administra várias marcas e campanhas;
- quer começar por uma direção, vencedor ou oportunidade;
- precisa editar o resultado, não aceitar uma caixa-preta;
- precisa reaproveitar conteúdos e responder a aprovações.

### Diretor criativo ou estrategista

- define conceito, ângulo, narrativa e limites;
- compara direções antes de produzir;
- valida coerência entre marca, momento e peça;
- acompanha variações sem editar cada pixel.

### Designer

- precisa de composição, camadas, tipografia e acabamento;
- quer assets aprovados e guardrails disponíveis no editor;
- precisa de atalhos, precisão, histórico e exportação confiável.

### Editor de vídeo

- precisa organizar material, transcrever, cortar e legendar;
- quer automações que produzam decisões editáveis na timeline;
- precisa manter áudio, ritmo e identidade da marca sob controle.

### Rosto da marca ou apresentador

- quer reduzir tempo de gravação sem perder identidade;
- precisa controlar onde rosto e voz podem ser utilizados;
- precisa aprovar amostras antes que algo seja produzido ou publicado.

### Aprovador ou cliente

- precisa compreender a intenção da peça rapidamente;
- quer comentar, comparar e decidir sem entrar no editor completo;
- deve dar feedback em segundos, com pouco esforço.

---

## 4. Arquitetura funcional comum

### 4.1 Objeto de trabalho

Todo Studio trabalha sobre o mesmo `CreativeDocument`, contendo:

- workspace, marca e revisão da memória;
- campanha, post e oportunidade de origem;
- briefing aplicado;
- páginas, cenas, camadas e tracks;
- assets e direitos;
- versões e lineage;
- estado de revisão;
- exports e artefatos;
- jobs e providers utilizados.

### 4.2 Estados do documento

```text
draft
  → ready_for_review
  → in_review
  → changes_requested
  → approved
  → scheduled/exported
  → archived
```

Estados adicionais de operação não devem substituir o estado editorial:

- carregando;
- salvando;
- sincronizado;
- alterações locais;
- conflito;
- somente leitura;
- offline;
- job em fila;
- processando;
- cancelamento solicitado;
- falha recuperável;
- falha terminal.

### 4.3 Production Rail compartilhada

A lateral dos Studios é uma Production Rail orientada ao fluxo, não a sidebar administrativa.

Áreas obrigatórias:

1. Logo Clicko, que retorna à Home.
2. Projeto/campanha atual.
3. Progresso da produção.
4. Etapas: Direção → Roteiro → Materiais → Montagem → Revisão → Entrega.
5. Bandejas: arquivos, referências, versões, comentários e decisões.
6. Próximo gate humano.
7. Estado de autosave.
8. Botão `Salvar e sair`.

#### Ações comuns da Production Rail

| ID | Ação | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| SHR-001 | `Logo Clicko` | Salva o estado pendente e retorna à Home; avisa se não for possível salvar. | V | P0 |
| SHR-002 | `Voltar ao projeto` | Retorna à campanha ou conteúdo de origem preservando contexto. | V | P0 |
| SHR-003 | `Abrir etapa` | Navega entre etapas permitidas; etapas bloqueadas explicam dependência. | V | P0 |
| SHR-004 | `Abrir bandeja` | Mostra assets, referências, versões, comentários ou decisões sem perder a seleção. | V | P1 |
| SHR-005 | `Resolver gate` | Abre a decisão exata que bloqueia a próxima etapa. | V | P1 |
| SHR-006 | `Salvar e sair` | Persiste documento, cria versão quando necessário e retorna com confirmação. | V/F parcial | P0 |
| SHR-007 | `Mais ações` | Duplicar, arquivar, mover, criar template e ver histórico. | N | P1 |

### 4.4 Header compartilhado

| ID | Ação | Comportamento esperado | Prioridade |
|---|---|---|---|
| HDR-001 | `Desfazer` | Reverte a última alteração local editável. | P0 |
| HDR-002 | `Refazer` | Reaplica a alteração revertida. | P0 |
| HDR-003 | `Preview` | Abre visualização sem controles, por canal e formato. | P0 |
| HDR-004 | `Salvar` | Persiste sem obrigar nova versão nomeada a cada clique. | P0 |
| HDR-005 | `Criar versão` | Cria snapshot identificado com autor e observação opcional. | P1 |
| HDR-006 | `Comparar` | Compara duas versões visualmente ou por diff textual. | P1 |
| HDR-007 | `Exportar` | Abre targets, qualidade, formato e validações. | P1 |
| HDR-008 | `Enviar para revisão` | Fixa a versão enviada e cria pedido de revisão. | P0 |
| HDR-009 | `Status de sync` | Mostra salvo, salvando, conflito, offline e erro. | P0 |
| HDR-010 | `Atalhos` | Exibe atalhos relevantes ao Studio atual. | P2 |

### 4.5 Copiloto contextual compartilhado

O copiloto não deve ocupar o centro do Studio como chat genérico.

Funções:

- explicar uma recomendação;
- sugerir mudanças na seleção atual;
- gerar alternativas comparáveis;
- aplicar somente após confirmação;
- mostrar qual contexto foi utilizado;
- indicar impacto esperado e nível de confiança;
- permitir feedback rápido;
- nunca alterar todo o documento silenciosamente.

Ações padrão:

- `Explicar`;
- `Aplicar`;
- `Ver antes/depois`;
- `Gerar outra opção`;
- `Não combina com a marca`;
- `Útil, mas ajuste...`;
- `Desfazer aplicação`.

---

## 5. Entrada dos Studios — Create Hub e launcher

### Objetivo

Permitir começar pelo trabalho que o usuário realmente quer realizar, não pela tecnologia utilizada.

### Modos de entrada

- oportunidade do Radar;
- oferta ou produto;
- briefing rápido;
- campanha existente;
- conteúdo vencedor;
- asset ou referência;
- formato vazio;
- importação de material.

### Ações

| ID | Botão/comando | Resultado | Estado | Prioridade |
|---|---|---|---|---|
| HUB-001 | `Novo conteúdo` | Abre launcher contextual. | V | P1 |
| HUB-002 | `Usar oportunidade` | Seleciona uma oportunidade e preserva evidências no briefing. | V | P1 |
| HUB-003 | `Criar a partir da oferta` | Pede produto, oferta, público e objetivo. | V | P1 |
| HUB-004 | `Reutilizar vencedor` | Abre Reuse Studio com conteúdo e métricas de origem. | V | P1 |
| HUB-005 | `Começar com briefing` | Abre Direção Criativa com formulário mínimo. | V/L | P1 |
| HUB-006 | `Post` | Cria documento visual/editorial no formato escolhido. | V/F parcial | P1 |
| HUB-007 | `Carrossel` | Cria documento multipágina. | F | P1 |
| HUB-008 | `Vídeo` | Abre ingestão de vídeo; não deve cair no Visual Editor. | V incorreto | P2 |
| HUB-009 | `Apresentador` | Abre seleção/criação de identidade com gates. | N | P3 |
| HUB-010 | `Importar` | Faz upload e detecta tipo de material. | V | P1 |
| HUB-011 | `Retomar` | Reabre a versão editável correta. | V/F parcial | P1 |
| HUB-012 | `Abrir em lote` | Seleciona conteúdos para operação de fábrica. | N | P2 |

### Estados

- vazio sem contexto;
- recomendações disponíveis;
- conteúdo em andamento;
- aguardando decisão;
- falha ao carregar;
- sem permissão;
- formato ainda indisponível;
- resultado de busca vazio.

---

## 6. Studio de Direção Criativa

### Objetivo

Converter contexto em uma decisão criativa estruturada antes da produção.

### Áreas da tela

1. **Contexto ativo:** marca, campanha, oferta, oportunidade e canal.
2. **Problema criativo:** objetivo, público e resultado esperado.
3. **Direções:** conceitos e ângulos comparáveis.
4. **Evidências:** fontes, vencedores, concorrentes e referências.
5. **Guardrails:** claims, proibições, riscos e direitos.
6. **Saída:** `CreativeBrief` aprovado.

### Campos

- objetivo principal;
- objetivo secundário;
- produto/oferta;
- audiência específica;
- dor, desejo e objeção;
- estágio de funil;
- canal e formato;
- ação desejada;
- big idea;
- promessa;
- ângulo;
- tensão;
- prova;
- emoção;
- hook;
- CTA;
- tom;
- referências;
- evidências;
- restrições;
- hipótese de performance;
- critério de sucesso.

### Ações

| ID | Botão/comando | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| DIR-001 | `Importar contexto` | Seleciona campanha, Radar, vencedor ou briefing existente. | N/V parcial | P1 |
| DIR-002 | `Pesquisar evidências` | Consulta ResearchProvider e retorna fontes citadas. | N | P2 |
| DIR-003 | `Adicionar referência` | Vincula URL, asset ou conteúdo sem copiar informação solta. | V parcial | P1 |
| DIR-004 | `Gerar direções` | Produz 3–5 direções realmente diferentes. | L | P1 |
| DIR-005 | `Comparar direções` | Exibe tese, adequação, risco, originalidade e esforço. | N | P1 |
| DIR-006 | `Favoritar direção` | Mantém candidata sem aprová-la. | N | P1 |
| DIR-007 | `Combinar direções` | Cria nova direção a partir de elementos selecionados. | N | P2 |
| DIR-008 | `Explicar recomendação` | Mostra contexto e evidências usados. | V parcial | P1 |
| DIR-009 | `Ver risco` | Mostra risco jurídico, reputacional, saturação e conexão forçada. | N | P1 |
| DIR-010 | `Editar guardrails` | Permite ajustar limites com permissão adequada. | V parcial | P1 |
| DIR-011 | `Aprovar direção` | Congela versão do brief usada na produção. | N | P1 |
| DIR-012 | `Enviar ao Editorial` | Abre Studio Editorial com brief aplicado. | N | P1 |
| DIR-013 | `Enviar à Fábrica` | Cria células e formatos a partir da direção. | N | P2 |
| DIR-014 | `Dar feedback` | Registra motivo rápido de aceitação/rejeição. | N | P1 |

### Regras

- Uma direção deve ser editável antes de aprovada.
- Fontes atuais devem possuir URL, data observada e confiança.
- Conteúdo vencedor é evidência de uma marca, não regra universal.
- O sistema precisa poder recomendar não usar uma tendência.
- A direção aprovada fica ligada ao documento e à versão da marca.

### Aceleração open source

- **Vane:** pesquisa e síntese com fontes atrás de `ResearchProvider`.
- Não usar Vane para scoring final, guardrails ou decisão editorial.

---

## 7. Studio Editorial e de Copy

### Objetivo

Desenvolver a mensagem com inteligência estratégica, mantendo edição humana simples.

### Modos

- post estático;
- legenda;
- carrossel;
- roteiro curto;
- UGC;
- anúncio;
- thread;
- newsletter/artigo em fase posterior.

### Áreas

- resumo do brief;
- editor de hook;
- estrutura/blocos narrativos;
- legenda ou roteiro;
- CTA e hashtags;
- preview por formato;
- contexto, guardrails e referências;
- comparação de alternativas.

### Ações editoriais

| ID | Botão/comando | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| EDT-001 | `Fortalecer hook` | Gera opções mantendo tese e público. | V/L | P1 |
| EDT-002 | `Gerar variações` | Cria alternativas lado a lado, sem sobrescrever. | N | P1 |
| EDT-003 | `Reduzir texto` | Encurta seleção preservando intenção. | V | P1 |
| EDT-004 | `Expandir argumento` | Acrescenta prova, exemplo ou explicação. | N | P1 |
| EDT-005 | `Adaptar tom` | Usa tons permitidos pela marca. | V | P1 |
| EDT-006 | `Variar CTA` | Sugere CTAs por objetivo e estágio do funil. | V | P1 |
| EDT-007 | `Checar claims` | Marca afirmações sem evidência ou arriscadas. | N | P1 |
| EDT-008 | `Inserir referência` | Vincula evidência ou vencedor ao trecho. | N | P1 |
| EDT-009 | `Adicionar bloco` | Insere hook, tensão, prova, virada, ação ou CTA. | N | P1 |
| EDT-010 | `Reordenar bloco` | Move estrutura e recalcula coerência. | V parcial | P1 |
| EDT-011 | `Duplicar bloco` | Cria cópia editável. | N | P1 |
| EDT-012 | `Excluir bloco` | Remove com desfazer. | N | P1 |
| EDT-013 | `Comparar versões` | Diff textual e impacto estimado. | V parcial | P1 |
| EDT-014 | `Preview` | Alterna Feed, Legenda, Slides ou Teleprompter. | V | P1 |
| EDT-015 | `Exibir área segura` | Mostra limites de texto no formato. | V | P1 |
| EDT-016 | `Abrir no Visual` | Salva e transfere o mesmo documento. | V/F parcial | P1 |
| EDT-017 | `Enviar para revisão` | Fixa a versão editorial/visual correspondente. | V parcial | P1 |
| EDT-018 | `Transformar formato` | Envia estrutura ao Carrossel, Vídeo ou Reuse. | N | P2 |

### Funções de texto

- negrito, itálico, listas e links;
- contagem de caracteres por canal;
- legibilidade;
- detecção de repetição;
- palavras proibidas e obrigatórias;
- destaque de hook, prova, CTA e claim;
- histórico por bloco;
- comentário em seleção;
- atalho para inserir variável de marca/produto.

### Aceleração open source

- **Lexical:** candidato MIT para editor estruturado, histórico, serialização e acessibilidade.
- Não é obrigatório no MVP se o modelo de texto continuar simples; fazer spike antes de substituir textareas.

---

## 8. Studio Visual

### Objetivo

Produzir peças profissionais orientadas a social media com precisão suficiente, sem tentar reproduzir toda a superfície do Figma ou Photoshop.

### Estrutura

1. Production Rail.
2. Toolbar contextual superior.
3. Tool rail de criação.
4. Painel da ferramenta.
5. Canvas dominante.
6. Inspector contextual.
7. Faixa de páginas/variações.

### Tool rail

- Templates;
- Marca;
- Mídia;
- Texto;
- Elementos;
- Camadas;
- IA contextual;
- Histórico;
- Exportação.

### Operações de seleção

| ID | Ação | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| VIS-001 | `Selecionar` | Seleção única/múltipla e bounding box. | V | P1 |
| VIS-002 | `Mover` | Drag, setas e entrada numérica. | V parcial | P1 |
| VIS-003 | `Redimensionar` | Mantém ou libera proporção. | V parcial | P1 |
| VIS-004 | `Rotacionar` | Handle e campo numérico. | V parcial | P1 |
| VIS-005 | `Duplicar` | Duplica preservando estilo e offset. | N | P1 |
| VIS-006 | `Excluir` | Remove com desfazer. | N | P1 |
| VIS-007 | `Agrupar/desagrupar` | Opera múltiplas camadas. | N | P1 |
| VIS-008 | `Bloquear` | Impede edição acidental. | V | P1 |
| VIS-009 | `Ocultar` | Controla visibilidade sem excluir. | V | P1 |
| VIS-010 | `Ordenar camada` | Frente, trás, subir e descer. | V parcial | P1 |
| VIS-011 | `Alinhar` | Esquerda, centro, direita, topo, meio e base. | V parcial | P1 |
| VIS-012 | `Distribuir` | Espaçamento horizontal/vertical. | N | P1 |
| VIS-013 | `Copiar estilo` | Copia propriedades visuais sem conteúdo. | N | P2 |
| VIS-014 | `Colar no lugar` | Mantém posição entre páginas. | N | P2 |

### Texto e tipografia

- inserir título, subtítulo, corpo, kicker e CTA;
- fonte, peso, tamanho, line-height e tracking;
- alinhamento, caixa, decoração e cor;
- largura automática/fixa;
- ajuste automático responsável;
- estilos da marca;
- efeito de contorno e sombra;
- busca e substituição entre páginas;
- aplicar estilo a páginas selecionadas.

### Formas e elementos

- retângulo, círculo, linha, seta, polígono e estrela;
- borda, raio, fill sólido, gradiente e transparência;
- ícones e SVG;
- frames e placeholders;
- máscaras e clipping;
- grids, guias e área segura;
- componentes de marca;
- favoritos e recentes.

### Imagem no canvas

- upload e inserção da biblioteca;
- crop, fit e fill;
- focal point;
- flip e rotação;
- opacidade;
- filtros básicos;
- brilho, contraste, saturação, temperatura e nitidez;
- fundo, máscara e blend mode;
- substituir preservando frame;
- abrir no Studio de Imagem.

### Efeitos e luz

- sombra externa e interna;
- blur;
- glow;
- stroke;
- overlay e gradiente;
- grain/textura;
- blend modes;
- luz direcional como preset controlado;
- comparação antes/depois;
- reset por propriedade.

### Ações inteligentes

| ID | Ação | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| VIS-030 | `Composition Coach` | Avalia hierarquia, contraste, alinhamento e marca. | V | P1 |
| VIS-031 | `Corrigir contraste` | Propõe alteração visível e reversível. | N | P1 |
| VIS-032 | `Reorganizar composição` | Gera alternativas sem apagar original. | N | P2 |
| VIS-033 | `Aplicar identidade` | Usa tokens e componentes da revisão de marca. | V parcial | P1 |
| VIS-034 | `Smart resize` | Cria nova variante por formato; não deforma a original. | L/V | P2 |
| VIS-035 | `Gerar variações` | Varia layout, ênfase ou asset com lineage. | V parcial | P1 |
| VIS-036 | `Comparar` | Exibe lado a lado, sobreposição ou slider. | V parcial | P1 |

### Páginas

- adicionar, duplicar, excluir e reordenar;
- nome e função da página;
- aplicar alteração a uma, seleção ou todas;
- selecionar múltiplas;
- transformar página em template;
- exportar página ou conjunto.

### Aceleração open source

- **Fabric.js:** principal candidato para manipulação, shapes, texto, filtros e JSON/SVG/PNG.
- **Konva:** benchmark alternativo.
- O `CreativeDocument` continua sendo a fonte canônica; o JSON da engine é cache/adaptação.

---

## 9. Studio de Imagem

### Objetivo

Criar ou editar matéria-prima visual preservando produto, rosto, direitos e realismo. Não é o mesmo que compor uma peça social.

### Modos

1. Gerar nova imagem.
2. Editar imagem existente.
3. Variar mantendo identidade.
4. Preparar asset para composição.

### Entrada

- prompt guiado;
- referência visual;
- produto aprovado;
- pessoa/identidade autorizada;
- brand kit;
- campanha e direção;
- proporção e uso final;
- elementos que não podem mudar.

### Ações

| ID | Botão/comando | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| IMG-001 | `Gerar imagem` | Cria job e versões, sem substituir original. | L | P3 |
| IMG-002 | `Adicionar referência` | Define referência de estilo, pose, produto ou cenário. | N | P3 |
| IMG-003 | `Travar produto` | Impede mudanças de embalagem, logo e proporção. | N | P3 |
| IMG-004 | `Travar identidade` | Usa somente identidade consentida. | N | P3 |
| IMG-005 | `Remover fundo` | Gera máscara e asset transparente. | L interface | P2 |
| IMG-006 | `Trocar fundo` | Mantém objeto/identidade e altera cenário. | L interface | P3 |
| IMG-007 | `Expandir imagem` | Outpainting para novo formato. | L interface | P3 |
| IMG-008 | `Upscale` | Gera versão maior com comparação. | L interface | P2 |
| IMG-009 | `Remover objeto` | Usa máscara e inpainting. | L interface | P3 |
| IMG-010 | `Inserir objeto` | Adiciona item com perspectiva e luz coerentes. | L interface | P3 |
| IMG-011 | `Alterar roupa` | Permitido apenas com consentimento e revisão. | L interface/E | P3 |
| IMG-012 | `Alterar iluminação` | Ajusta ambiente preservando conteúdo. | L interface | P3 |
| IMG-013 | `Gerar variações` | Cria conjunto ligado à origem. | L interface | P2 |
| IMG-014 | `Redimensionar` | Adapta composição e focal point. | L interface | P2 |
| IMG-015 | `Comparar antes/depois` | Slider, zoom sincronizado e métricas técnicas. | N | P2 |
| IMG-016 | `Salvar na biblioteca` | Registra direitos, provider e lineage. | N | P2 |
| IMG-017 | `Inserir no Visual` | Retorna asset à seleção/camada de origem. | N | P2 |
| IMG-018 | `Descartar resultado` | Remove derivado sem afetar original. | N | P2 |

### Regras

- O sistema precisa identificar claramente imagem original e gerada.
- Toda transformação cria derivado; não sobrescrever o original.
- Rosto, produto e logo devem possuir locks independentes.
- Alterações de corpo, rosto e roupa exigem política própria.
- Assets gerados precisam guardar provider, modelo, prompt, seed quando disponível e direitos.

### Open source ainda necessário

- engine de segmentação/máscara;
- background removal com licença de pesos auditada;
- inpainting/outpainting;
- upscale;
- avaliação de preservação de produto/identidade.

Não selecionar um único pacote “all-in-one” sem verificar a licença de cada modelo.

---

## 10. Studio de Carrossel

### Objetivo

Construir uma narrativa visual coerente entre páginas, não apenas duplicar layouts.

### Funções narrativas por slide

- promessa;
- tensão;
- contexto;
- virada;
- prova;
- exemplo;
- objeção;
- ação;
- CTA;
- apoio.

### Ações

| ID | Botão/comando | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| CAR-001 | `Adicionar slide` | Insere após seleção com função sugerida. | F | P1 |
| CAR-002 | `Duplicar slide` | Duplica conteúdo e composição. | N | P1 |
| CAR-003 | `Excluir slide` | Remove com confirmação quando possui comentários. | N | P1 |
| CAR-004 | `Reordenar` | Drag/teclado e atualização da narrativa. | V parcial | P1 |
| CAR-005 | `Definir função` | Seleciona papel narrativo. | V | P1 |
| CAR-006 | `Gerar sequência` | Cria spine a partir do briefing. | N | P1 |
| CAR-007 | `Encurtar carrossel` | Reduz páginas preservando arco. | N | P1 |
| CAR-008 | `Expandir carrossel` | Sugere páginas ausentes e função. | N | P2 |
| CAR-009 | `Aplicar estilo a todos` | Propaga propriedades selecionadas. | N | P1 |
| CAR-010 | `Trocar asset` | Abre biblioteca com filtros de campanha/direitos. | V | P1 |
| CAR-011 | `Transição` | Define corte/movimento para preview, quando aplicável. | V | P2 |
| CAR-012 | `Ver ritmo` | Mostra densidade, leitura e repetição. | V parcial | P1 |
| CAR-013 | `Aplicar sugestão` | Altera o slide atual com preview. | V | P1 |
| CAR-014 | `Visualizar conjunto` | Preview contínuo no formato final. | V | P1 |
| CAR-015 | `Exportar conjunto` | ZIP/PDF/imagens ordenadas, não só primeira página. | F parcial | P1 |
| CAR-016 | `Enviar para revisão` | Fixa todas as páginas na versão enviada. | V parcial | P1 |

### Inspector por slide

- função narrativa;
- kicker;
- título;
- texto de apoio;
- asset;
- CTA;
- número de página;
- background;
- notas;
- tempo estimado;
- alertas de consistência.

### Validações

- tamanho mínimo de fonte;
- safe area;
- contraste;
- repetição visual;
- progressão narrativa;
- slide sem propósito;
- CTA incompatível com objetivo;
- asset sem direito verificado.

---

## 11. Studio de Vídeo

### Objetivo

Transformar material bruto em vídeo curto profissional com automações editáveis e rastreáveis.

### Fluxo

```text
Ingestão
  → análise técnica
  → transcrição
  → seleção de momentos
  → montagem
  → legendas e identidade
  → áudio
  → revisão
  → render
```

### Áreas

1. Production Rail.
2. Media bin.
3. Player/preview.
4. Toolbar contextual.
5. Timeline multitrack.
6. Transcript editor.
7. Inspector.
8. Job/render drawer.
9. Reality Lane e Physical QC drawer em modo advisory.

### Ingestão

| ID | Ação | Comportamento | Prioridade |
|---|---|---|---|
| VID-001 | `Enviar vídeos` | Upload multipart, retomável e validado. | P2 |
| VID-002 | `Importar da biblioteca` | Usa asset sem duplicar binário. | P2 |
| VID-003 | `Gravar` | Captura câmera/microfone com consentimento. | P3 |
| VID-004 | `Analisar material` | Extrai duração, codec, resolução, fps, áudio e cenas. | P2 |
| VID-005 | `Transcrever` | Cria transcript com timestamps e confiança. | P2 |
| VID-006 | `Identificar falantes` | Diarização opcional. | P3 |

### Player

- play/pause;
- seek;
- frame anterior/próximo;
- velocidade;
- volume;
- qualidade do preview;
- tela cheia;
- safe area;
- guias de formato;
- antes/depois;
- seleção de proporção.

### Timeline

| ID | Ação | Comportamento | Prioridade |
|---|---|---|---|
| VID-020 | `Selecionar clip` | Sincroniza player, transcript e inspector. | P2 |
| VID-021 | `Cortar/split` | Divide no playhead sem perder origem. | P2 |
| VID-022 | `Trim` | Ajusta início/fim com snap. | P2 |
| VID-023 | `Excluir` | Ripple opcional; desfazer obrigatório. | P2 |
| VID-024 | `Mover` | Reordena mantendo dependências. | P2 |
| VID-025 | `Adicionar track` | Vídeo, áudio, texto, overlay ou captions. | P2 |
| VID-026 | `Bloquear/ocultar/mutar` | Controle por track. | P2 |
| VID-027 | `Zoom timeline` | Ajuste de escala temporal. | P2 |
| VID-028 | `Marcador` | Marca hook, prova, CTA, dúvida ou revisão. | P2 |
| VID-029 | `Transição` | Aplica entre clips com duração. | P3 |
| VID-030 | `Keyframe` | Movimento/opacidade/escala em fase posterior. | P3 |

### Automação assistida

| ID | Botão/comando | Resultado editável | Estado atual | Prioridade |
|---|---|---|---|---|
| VID-040 | `Cortes inteligentes` | Sugere ou aplica cortes de pausa, erro e repetição. | L interface | P2 |
| VID-041 | `Remover silêncios` | Mostra regiões e limiar antes de aplicar. | L interface | P2 |
| VID-042 | `Gerar legendas` | Cria track editável por palavra/segmento. | L interface | P2 |
| VID-043 | `Estilizar legendas` | Presets da marca, posição e destaque. | L interface | P2 |
| VID-044 | `Detectar highlights` | Sugere trechos com motivo e score. | N | P2 |
| VID-045 | `Gerar Shorts` | Cria novos documentos derivados. | L interface | P2 |
| VID-046 | `Adicionar B-roll` | Sugere assets com timing e justificativa. | L interface | P3 |
| VID-047 | `Zoom dinâmico` | Adiciona keyframes editáveis. | L interface | P3 |
| VID-048 | `Gerar hook` | Propõe abertura textual/visual, preservando original. | L interface | P2 |
| VID-049 | `Reenquadrar` | Tracking/focal point por formato. | N | P2 |
| VID-050 | `Traduzir` | Gera transcript traduzido e revisão. | L interface | P3 |
| VID-051 | `Dublar` | Cria track de voz, nunca substitui sem confirmação. | L interface | P3 |

### Compreensão da realidade

| ID | Ação/estado | Comportamento | Prioridade |
|---|---|---|---|
| VID-060 | `Definir intenção física` | Por shot: realista, física estilizada ou surreal; declara cut, slow motion, speed ramp, reverse, timelapse, stop motion e VFX. | P2 |
| VID-061 | `Analisar realidade` | Cria `RealityModelV1` com câmera, entidades, tracks, relações, eventos, hipóteses, confiança e lineage ligados ao checksum/time-map. | P2 |
| VID-062 | `Reality Lane` | Mostra ocorrências por intervalo/dimensão sem alterar a timeline; marker seleciona entidades e evidências no player. | P2 |
| VID-063 | `Inspecionar ocorrência` | Exibe expected/observed, incerteza, sinais de suporte, sugestão e versão do evaluator. | P2 |
| VID-064 | `Corrigir track/relação` | Permite ajustar entidade, máscara, ponto, intervalo ou relação; registra correção sem apagar inferência original. | P2 |
| VID-065 | `Marcar como intencional` | Vincula a ocorrência a uma técnica ou override justificado e auditável. | P2 |
| VID-066 | `Comparar candidatos` | Ordena renders/gerações por plausibilidade, intenção e custo sem esconder o score bruto. | P3 |
| VID-067 | `Reanalisar` | Cria nova avaliação ligada à revisão/render/checksum exatos; nunca sobrescreve a anterior. | P2 |

Regras: v1 é advisory; baixa confiança produz abstenção; nenhum provider único aprova, corrige ou publica; toda ocorrência precisa localizar intervalo e entidades; edição cinematográfica declarada não é automaticamente erro físico; vídeo sintético continua com revisão humana.

### Áudio

- waveform;
- ganho por clip/track;
- normalização;
- fade in/out;
- ducking;
- redução de ruído;
- voz, música e efeitos separados;
- sync lock;
- medidor de clipping;
- voz clonada somente com consentimento.

### Render

- formato e proporção;
- resolução;
- fps;
- codec e bitrate por preset;
- watermark;
- end card;
- naming;
- canal de destino;
- estimativa de tempo e créditos;
- fila, progresso, cancelamento e retry;
- preview leve antes do render final.

### Aceleração open source

- **FFmpeg/FFprobe:** ingestão, filtros, codecs e render.
- **WhisperX:** transcrição, alinhamento e diarização atrás de provider.
- **wavesurfer.js:** candidato para waveform, regiões, timeline de áudio e gravação.
- **React Timeline Editor:** candidato MIT apenas para interação de timeline; não deve definir o modelo canônico.
- **OpenCut Classic:** referência MIT seletiva para markers/bookmarks, snapping, commands/undo, keyframes/masks e overlays da Reality Lane; não importar auth, banco, store ou documento.
- **TAPIR/RAFT/Depth Anything V2 Small:** candidatos permissivos para tracking, movimento e profundidade em PGV-1; cada checkpoint precisa de manifest.
- **V-JEPA 2:** candidato de benchmark para predição latente em PGV-3, nunca árbitro único.
- **Physics-IQ/IntPhys2/MVPBench/CausalVQA:** referências para corpus e protocolo; licenças de dados impedem presumir reutilização comercial.
- A engine de vídeo deve ser decidida por spike de 3 minutos de material real em PT-BR.

---

## 12. Motion Studio

### Objetivo

Adicionar movimento funcional a peças, carrosséis e vídeo sem exigir conhecimento de animação avançada.

### Modelo

Cada camada pode ter:

- entrada;
- ênfase;
- saída;
- início;
- duração;
- atraso;
- easing;
- direção;
- intensidade;
- repetição controlada.

### Ações

| ID | Botão/comando | Comportamento | Prioridade |
|---|---|---|---|
| MOT-001 | `Animar` | Abre presets adequados ao tipo da camada. | P3 |
| MOT-002 | `Entrada` | Fade, slide, scale, reveal e variantes de marca. | P3 |
| MOT-003 | `Ênfase` | Pulse, highlight, pan e foco. | P3 |
| MOT-004 | `Saída` | Fade/slide/reveal reverso. | P3 |
| MOT-005 | `Duração` | Campo e drag na timeline. | P3 |
| MOT-006 | `Easing` | Presets sem jargão e opção avançada. | P3 |
| MOT-007 | `Aplicar a todas` | Propaga a camadas/páginas selecionadas. | P3 |
| MOT-008 | `Sincronizar com áudio` | Alinha evento a beat, palavra ou marcador. | P4 |
| MOT-009 | `Preview loop` | Reproduz seleção repetidamente. | P3 |
| MOT-010 | `Reduzir movimento` | Gera versão acessível. | P3 |
| MOT-011 | `Remover animação` | Limpa sem alterar estilo estático. | P3 |

### Regras

- Presets devem ter intenção: direto, premium, UGC, explicativo, urgente.
- Movimento não pode ser aplicado indiscriminadamente pela IA.
- Respeitar preferência de redução de movimento no preview.
- Toda animação deve serializar no `CreativeDocument`.

---

## 13. Studio de Apresentador e Identidade

### Objetivo

Permitir que uma pessoa autorizada se torne uma identidade de produção reutilizável, com controle jurídico, técnico e criativo.

### Etapas

```text
Consentimento
  → captura guiada
  → validação dos materiais
  → treinamento/calibração
  → testes privados
  → aprovação da identidade
  → uso em produção
  → revogação/expiração
```

### Consentimento e direitos

| ID | Ação | Comportamento | Prioridade |
|---|---|---|---|
| PRE-001 | `Criar consentimento` | Registra pessoa, finalidade, canais, território e prazo. | P3 |
| PRE-002 | `Enviar para assinatura` | Obtém aceite verificável. | P3 |
| PRE-003 | `Ver direitos` | Mostra permissões e bloqueios de forma simples. | P3 |
| PRE-004 | `Renovar` | Cria nova concessão sem alterar histórico. | P3 |
| PRE-005 | `Revogar` | Bloqueia novos jobs imediatamente. | P3 |
| PRE-006 | `Excluir identidade` | Fluxo protegido com política de derivados. | P3 |

### Materiais e captura

| ID | Ação | Comportamento | Prioridade |
|---|---|---|---|
| PRE-010 | `Adicionar fonte real` | Upload de vídeo, áudio ou imagem autorizado. | P3 |
| PRE-011 | `Abrir captura` | Orienta frase, pausa, iluminação e enquadramento. | V | P3 |
| PRE-012 | `Regravar trecho` | Substitui somente amostra ruim. | N | P3 |
| PRE-013 | `Validar qualidade` | Avalia ruído, foco, luz, duração e cobertura. | V parcial | P3 |
| PRE-014 | `Aprovar take` | Move material para dataset da cápsula. | N | P3 |
| PRE-015 | `Rejeitar take` | Pede motivo rápido e nova instrução. | N | P3 |

### Direção da identidade

- presença desejada;
- energia;
- naturalidade;
- premium;
- espontaneidade UGC;
- ritmo e pausas;
- gestos e expressão;
- características que não podem ser alteradas;
- voz publicitária permitida ou proibida;
- cenário e roupa permitidos;
- regras de produto e marca.

### Testes e produção

| ID | Ação | Comportamento | Prioridade |
|---|---|---|---|
| PRE-020 | `Gerar primeiro teste` | Gera amostra privada e não publicável. | V | P3 |
| PRE-021 | `Comparar com fonte` | Sincroniza rosto, voz, cena e cadência. | N | P3 |
| PRE-022 | `Aceitar cenário` | Registra decisão específica. | V | P3 |
| PRE-023 | `Rejeitar cenário` | Solicita alternativa e motivo rápido. | V | P3 |
| PRE-024 | `Ajustar direção` | Altera presença sem editar identidade base. | V parcial | P3 |
| PRE-025 | `Aprovar teste` | Conta para gate da identidade. | N | P3 |
| PRE-026 | `Aprovar identidade` | Libera usos dentro do consentimento. | N | P3 |
| PRE-027 | `Enviar ao Video Studio` | Cria material ou track com lineage. | N | P3 |
| PRE-028 | `Gerar variação` | Muda roteiro/cena dentro dos limites. | N | P3 |

### Open source

- **OpenVoice:** candidato para `VoiceCloneProvider`; benchmark PT-BR obrigatório.
- **Duix-Avatar:** referência rejeitada enquanto a regra for “somente open source”; licença comunitária possui limite comercial.
- **HeyGem:** URL `Caladog/HeyGem` confirmada e rejeitada pela mesma regra; não integrar nem benchmarkar com dados reais.
- **HyperFrames:** candidato Apache-2.0 prioritário para `VideoRenderProvider`, mantendo HTML como projeção e não como documento canônico.

### Gate absoluto

Nenhuma identidade entra em produção sem consentimento válido, teste aprovado, escopo compatível e possibilidade de revogação.

---

## 14. Reuse & Variation Studio

### Objetivo

Transformar um vencedor em novos conteúdos preservando o princípio que funcionou e explicitando o que será alterado.

### Áreas

- original e performance;
- diagnóstico do que funcionou;
- elementos a preservar;
- elementos a adaptar;
- hipóteses a testar;
- matriz de formatos;
- variações geradas;
- riscos e lineage.

### Ações

| ID | Botão/comando | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| REU-001 | `Selecionar vencedor` | Carrega peça, métricas e contexto original. | V/F parcial | P1 |
| REU-002 | `Preservar` | Trava hook, promessa, composição ou asset. | V parcial | P1 |
| REU-003 | `Adaptar` | Seleciona tom, canal, formato, público ou oferta. | V parcial | P1 |
| REU-004 | `Testar` | Define uma hipótese por variação. | V parcial | P1 |
| REU-005 | `Gerar derivações` | Cria documentos filhos com lineage. | V parcial | P1 |
| REU-006 | `Aplicar a todas` | Aplica mudança às variantes selecionadas. | N | P2 |
| REU-007 | `Comparar variações` | Lado a lado com diferenças marcadas. | N | P1 |
| REU-008 | `Abrir no editor` | Abre cada derivado no Studio correto. | V | P1 |
| REU-009 | `Enviar à Fábrica` | Produz lote aprovado. | N | P2 |
| REU-010 | `Enviar para revisão` | Agrupa revisão mantendo identidade individual. | N | P2 |
| REU-011 | `Registrar resultado` | Liga publicação e performance à hipótese. | F parcial | P2 |

---

## 15. Fábrica de Conteúdo

### Objetivo

Orquestrar múltiplas peças e decisões sem virar uma tabela administrativa.

### Unidade funcional: rodada de produção

Uma rodada contém:

- entradas vivas;
- receita estratégica;
- células de produção;
- jobs;
- gates humanos;
- destinos;
- custo e capacidade;
- artefatos e resultados.

### Ações

| ID | Botão/comando | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| FAC-001 | `Nova produção` | Define origem, formatos, quantidades e prioridade. | V | P1 |
| FAC-002 | `Ver origem` | Abre oportunidade, oferta, briefing ou vencedor. | V | P1 |
| FAC-003 | `Editar receita` | Ajusta tese, prova, formatos e CTA. | N | P1 |
| FAC-004 | `Adicionar célula` | Cria peça/variante com dependências. | N | P1 |
| FAC-005 | `Iniciar rodada` | Valida pré-requisitos e cria jobs. | V local | P1 |
| FAC-006 | `Pausar rodada` | Impede novos jobs; não interrompe operação não cancelável. | N | P2 |
| FAC-007 | `Cancelar job` | Solicita cancelamento com motivo. | F backend/V ausente | P1 |
| FAC-008 | `Tentar novamente` | Reusa idempotência e mantém histórico da falha. | F backend/V ausente | P1 |
| FAC-009 | `Alterar prioridade` | Reordena fila conforme permissão. | N | P2 |
| FAC-010 | `Abrir célula` | Abre Studio no estado exato do job. | N | P1 |
| FAC-011 | `Resolver gate` | Abre aprovação, asset ou decisão pendente. | V | P1 |
| FAC-012 | `Aprovar em lote` | Apenas para itens elegíveis e mesma regra. | N | P2 |
| FAC-013 | `Mudar destino` | Altera canal/export antes do pré-flight. | N | P2 |
| FAC-014 | `Ver custo` | Mostra estimado, realizado e provider. | N | P2 |
| FAC-015 | `Duplicar rodada` | Reusa receita com novo contexto. | N | P2 |
| FAC-016 | `Iniciar nova rodada sugerida` | Usa aprendizado preservando escolha humana. | V local | P2 |

### Estados da célula

- aguardando entrada;
- pronta;
- em fila;
- processando;
- precisa de decisão;
- revisão humana;
- falhou;
- cancelada;
- pronta para exportar;
- entregue.

### Métricas

- peças em processamento;
- decisões pendentes;
- prontas hoje;
- throughput semanal;
- tempo por etapa;
- taxa de retry/falha;
- custo por peça;
- capacidade CPU/GPU;
- taxa de aprovação na primeira versão.

### Orquestração

Celery/Redis atende o primeiro estágio. Temporal só deve ser avaliado se workflows longos, dependências, compensações e retomada ultrapassarem o que o modelo atual consegue manter com segurança.

---

## 16. Biblioteca, templates e lineage

### Objetivo

Servir os Studios com matéria-prima confiável e reutilizável.

### Tipos

- imagem;
- vídeo;
- áudio;
- logo;
- fonte;
- documento;
- template;
- componente de marca;
- referência;
- output gerado;
- identidade audiovisual.

### Ações

| ID | Botão/comando | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| LIB-001 | `Upload` | Envia, valida e extrai metadados. | V/F parcial | P1 |
| LIB-002 | `Buscar` | Nome, campanha, tag, uso, direito e conteúdo. | V parcial | P1 |
| LIB-003 | `Filtrar` | Tipo, campanha, origem, direito, status e data. | V parcial | P1 |
| LIB-004 | `Inserir no editor` | Retorna asset e cria referência no documento. | V | P1 |
| LIB-005 | `Criar variação` | Abre Studio adequado com origem. | V | P1 |
| LIB-006 | `Criar template` | Salva estrutura e regras, não dados privados indevidos. | V parcial | P2 |
| LIB-007 | `Duplicar template` | Cria cópia sem compartilhar automaticamente. | L | P2 |
| LIB-008 | `Favoritar` | Preferência por usuário/workspace. | L | P2 |
| LIB-009 | `Ver lineage` | Mostra origem, derivados, usos e publicações. | V parcial | P1 |
| LIB-010 | `Editar direitos` | Atualiza licença e escopo com auditoria. | N | P1 |
| LIB-011 | `Substituir arquivo` | Cria versão; não quebra documentos anteriores. | N | P2 |
| LIB-012 | `Excluir` | Informa usos e aplica política segura. | V parcial | P1 |
| LIB-013 | `Baixar original` | Entrega binário autorizado. | F | P1 |

### Metadados obrigatórios

- hash/checksum;
- MIME e dimensões/duração;
- origem;
- autor/fornecedor;
- direito e validade;
- workspace;
- campanha;
- tags;
- provider/modelo quando gerado;
- asset pai;
- usos e derivados;
- política de retenção.

---

## 17. Review Room e feedback

### Objetivo

Permitir decisão rápida, contextual e útil ao aprendizado.

### Ações

| ID | Botão/comando | Comportamento | Estado | Prioridade |
|---|---|---|---|---|
| REV-001 | `Editar` | Volta ao Studio correto e à versão de trabalho. | V | P1 |
| REV-002 | `Criar variação` | Abre Reuse/Variation com origem. | V local | P1 |
| REV-003 | `Comparar versões` | Lado a lado, slider ou diff textual. | V parcial | P1 |
| REV-004 | `Comentar` | Comentário geral ou ancorado em região/tempo. | V parcial | P1 |
| REV-005 | `Anexar` | Adiciona referência à discussão. | V | P2 |
| REV-006 | `Solicitar ajustes` | Comentário/motivo obrigatório e retorno ao owner. | F parcial | P1 |
| REV-007 | `Aprovar` | Aprova exatamente a versão solicitada. | F parcial | P1 |
| REV-008 | `Rejeitar` | Registra motivo e encerra/retorna conforme regra. | F parcial | P1 |
| REV-009 | `Agendar` | Só aparece após aprovação e preflight. | V parcial | P2 |
| REV-010 | `Feedback rápido` | Motivo em um toque + texto opcional. | N | P1 |

### Taxonomia de feedback rápido

Aceitação:

- alinhado à marca;
- direção forte;
- visual profissional;
- mensagem clara;
- pronto com pequeno ajuste;
- melhor que o fluxo atual.

Rejeição:

- não parece com a marca;
- conexão forçada;
- genérico/artificial;
- produto ou rosto incorreto;
- mensagem fraca;
- excesso de texto;
- risco jurídico/reputacional;
- referência inadequada;
- acabamento insuficiente;
- outro, com texto opcional.

### Regra de aprendizado

O sistema deve explicar o benefício em linguagem de produto: “Sua decisão calibra as próximas sugestões desta marca.” Não prometer aprendizado imediato nem usar dados de uma marca em outra sem governança.

---

## 18. Requisitos não funcionais compartilhados

### Persistência

- autosave com debounce;
- revisão otimista e resolução de conflito;
- versionamento nomeado;
- restore sem apagar histórico;
- idempotência para jobs e mutações críticas.

### Performance

- interação local do canvas e timeline sem depender de roundtrip;
- previews proxy para vídeo pesado;
- lazy loading de assets;
- upload retomável para arquivos grandes;
- workers separados do processo web.

### Acessibilidade

- teclado para ações essenciais;
- nomes acessíveis em ícones;
- foco visível;
- contraste WCAG AA;
- alternativas para drag-and-drop;
- redução de movimento;
- captions e transcript editáveis.

### Segurança

- isolamento por workspace;
- URLs de assets autorizadas;
- validação de MIME e tamanho;
- scanning de uploads;
- segredos somente no servidor;
- logs sem biometria ou prompts sensíveis desnecessários;
- consentimento para rosto e voz;
- auditoria de publicação e exportação.

### Observabilidade

- correlation ID por rodada/documento/job;
- provider, modelo e versão;
- duração por etapa;
- custo estimado/real;
- erro sanitizado para usuário e detalhe técnico no log;
- métricas de fila e capacidade.

---

## 19. Matriz open source × área

| Tecnologia | Área | O que acelera | O que não resolve | Decisão atual |
|---|---|---|---|---|
| Vane | Direção/Radar | pesquisa, fontes e síntese | scoring da Clicko, risco e brand fit | Encapsular/spike |
| Fabric.js | Visual/Carrossel | objetos, transforms, shapes, texto, filtros e I/O | modelo de domínio e experiência completa | Benchmark principal |
| Konva | Visual/Carrossel | alternativa de scene graph e interação | contratos, export e inteligência | Benchmark alternativo |
| Lexical | Editorial | rich text, histórico, serialização e plugins | estratégia e copy | Spike condicionado |
| FFmpeg/FFprobe | Vídeo/Motion | análise, codecs, filtros e render | timeline UX e direção criativa | Adotar build auditada |
| WhisperX | Vídeo | timestamps, transcript e diarização | edição e qualidade editorial | Encapsular/spike PT-BR |
| wavesurfer.js | Vídeo/voz | waveform, regiões, timeline e gravação | render de vídeo | Spike |
| React Timeline Editor | Vídeo/Motion | interação básica de timeline | modelo canônico e render | Spike, sem acoplamento |
| OpenVoice | Presenter/voz | clone e controle de voz | consentimento, PT-BR garantido e vídeo | Spike controlado |
| Duix-Avatar | Presenter | referência de avatar offline e lip-sync | licença comunitária e limite comercial | Rejeitar enquanto “somente open source” |
| HeyGem | Presenter | referência de avatar/lip-sync | licença comunitária e limite comercial | Rejeitar enquanto “somente open source” |
| HyperFrames | Vídeo/Motion | render HTML determinístico, preview e player | documento canônico, segurança de assets e workers | Encapsular/spike prioritário |
| Celery/Redis atual | Fábrica | fila e execução assíncrona | workflows muito longos/complexos | Manter inicialmente |
| Temporal | Fábrica futura | execução durável e workflows | custo de adoção e necessidade ainda não provada | Avaliar somente depois |

---

## 20. Repositórios ou categorias que ainda precisamos procurar

### Necessários antes do Studio de Vídeo completo

1. Timeline web que suporte milhares de segmentos, snapping e virtualização.
2. Proxy media/transcoding para edição leve.
3. Detecção de cenas e highlights.
4. Reframing/tracking de rosto e objeto.
5. Redução de ruído com licença comercial clara.

### Necessários antes do Studio de Imagem avançado

1. Segmentação e máscara.
2. Background removal com pesos licenciados.
3. Inpainting/outpainting.
4. Upscale.
5. Validação de fidelidade de produto e rosto.

### Necessários antes do Presenter

1. Detecção de qualidade de captura.
2. Liveness/consentimento verificável.
3. Avaliação automática de lip-sync.
4. Avaliação perceptual de voz PT-BR.
5. Proveniência/Content Credentials.

### Regra de busca

Só procurar uma nova base quando o requisito, o contrato e o benchmark estiverem definidos. Não procurar “um editor de vídeo completo”; procurar, por exemplo, “timeline React virtualizada com licença permissiva e suporte a snapping”.

---

## 21. Sequência para planejar, prototipar e produzir

### Onda 1 — Fundação e primeiro valor

- Production Rail compartilhada;
- Direção Criativa;
- Editorial persistente;
- Visual com engine escolhida;
- Carrossel completo;
- Biblioteca/lineage;
- Review e feedback;
- Fábrica conectada a jobs reais.

### Onda 2 — Vídeo assistido

- ingestão;
- FFmpeg/FFprobe;
- WhisperX;
- media bin;
- transcript;
- timeline básica;
- cortes;
- legendas;
- render.

### Onda 3 — Inteligência de mídia

- highlights;
- B-roll;
- reframing;
- motion;
- smart resize;
- automações explicáveis.

### Onda 4 — Imagem avançada e Presenter

- máscaras e edição de imagem;
- consentimento;
- voz PT-BR;
- benchmark de avatar;
- testes privados;
- integração controlada ao Video Studio.

### Gate entre planejamento e protótipo

Uma área só deve ser prototipada quando possuir:

- job-to-be-done;
- entrada e saída;
- ações e estados;
- regras e permissões;
- contrato de dados;
- prioridade;
- classificação de maturidade;
- estratégia de erro e recuperação.

### Gate entre protótipo e produção

Uma tela só entra em produção quando possuir:

- protótipo aprovado;
- comportamento de todos os botões;
- estados vazio/loading/error/readonly/conflict;
- endpoint ou estado honesto;
- analytics de uso;
- acessibilidade;
- teste de contrato;
- teste E2E da jornada;
- rollback.

---

## 22. Métricas de sucesso dos Studios

- tempo até o primeiro rascunho útil;
- tempo total até aprovação;
- taxa de aprovação na primeira versão;
- número médio de ajustes;
- percentual de sugestões aceitas;
- percentual de sugestões desfeitas;
- conteúdos reutilizados;
- variações publicadas;
- tempo de render;
- falhas e retries;
- custo por output;
- consistência de marca;
- satisfação com edição e controle;
- desempenho relativo ao histórico da marca.

O teste estratégico deve durar de 8 a 12 semanas e comparar com o fluxo anterior do usuário.

---

## 23. Decisões imediatas recomendadas

1. Aprovar este catálogo como baseline funcional v0.1.
2. Não iniciar novos protótipos de Studio antes de escolher a ordem da Onda 1.
3. Executar spike Fabric.js versus Konva usando um post e um carrossel reais.
4. Definir o contrato de Editorial no `CreativeDocument`.
5. Transformar Fábrica em cliente dos jobs reais já existentes.
6. Preparar benchmark de vídeo com FFmpeg + WhisperX em português.
7. Preparar spike HyperFrames + FFmpeg na VPS atrás de `VideoRenderProvider`.
8. Manter Avatar e clonagem de voz como experimento separado até consentimento, licença e qualidade estarem comprovados.

---

## 24. Princípio de escopo

A Clicko deve oferecer as ferramentas necessárias para concluir o trabalho profissional e concentrar sua diferenciação em:

- contexto vivo;
- memória da marca;
- direção criativa;
- inteligência de nicho;
- guardrails;
- variações com propósito;
- produção orquestrada;
- feedback e aprendizado.

Não é necessário competir com cada comando do Canva, Figma ou Photoshop. É necessário eliminar a maior parte do trabalho repetitivo entre a oportunidade, a decisão criativa, a produção, a aprovação e o aprendizado.
