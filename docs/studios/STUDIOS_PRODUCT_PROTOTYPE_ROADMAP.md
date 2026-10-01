# Clicko Studios — Roadmap de produto, prototipação e produção

**Versão:** 0.1  
**Status:** planejamento estratégico  
**Fonte funcional:** `docs/studios/STUDIOS_FUNCTIONAL_REQUIREMENTS.md`  
**Fonte arquitetural:** `docs/CLICKO_STUDIOS_STRATEGY.md`

---

## 1. Decisão de sequência

Os Studios não serão construídos horizontalmente, adicionando um pouco de cada editor. A evolução será feita por **cortes verticais completos**, nos quais um usuário consegue iniciar, produzir, revisar e concluir um trabalho real.

Ordem:

```text
Onda 0 — Studio Operating System
  ↓
Onda 1 — Post Factory monetizável
  ↓
Onda 2 — Carrossel e produção em lote
  ↓
Onda 3 — Vídeo assistido
  ↓
Onda 4 — Motion e imagem avançada
  ↓
Onda 5 — Presenter e identidade sintética
```

A Clicko começa entregando profundidade em posts e carrosséis, que já possuem contexto, telas e parte do backend. Avatar e vídeo generativo continuam estratégicos, mas não bloqueiam receita e validação.

---

## 2. Princípios de priorização

Uma capacidade sobe de prioridade quando:

- conclui um trabalho pelo qual o ICP pagaria;
- reduz tempo operacional recorrente;
- utiliza uma vantagem própria da Clicko;
- reaproveita backend e experiência existentes;
- melhora aprovação, consistência ou reutilização;
- desbloqueia várias capacidades posteriores;
- possui risco jurídico e de infraestrutura controlável.

Uma capacidade desce de prioridade quando:

- existe apenas para igualar Canva, Figma ou Photoshop;
- depende de uma licença ainda não aprovada;
- exige GPU antes de haver demanda comprovada;
- produz uma demo atraente, mas não completa a jornada;
- acrescenta muitos controles sem aumentar o resultado;
- duplica uma área já funcional do sistema principal.

---

## 3. Onda 0 — Studio Operating System

### Objetivo

Criar a base comum que evita desenvolver seis editores desconectados.

### Escopo

- Production Rail;
- header compartilhado;
- `CreativeDocument` e `CreativeBrief`;
- autosave, conflito e versões;
- assets e lineage;
- jobs, progresso, cancelamento e retry;
- revisão fixa por versão;
- copiloto contextual;
- permissões e isolamento por workspace;
- telemetria compartilhada.

### Protótipos necessários

| Frame | Superfície | Objetivo |
|---|---|---|
| OS-01 | Production Rail — padrão | Definir navegação, etapas, bandejas, próximo gate e retorno. |
| OS-02 | Header do Studio | Definir save, versão, preview, export e revisão. |
| OS-03 | Job Drawer | Exibir fila, progresso, cancelamento, erro e retry. |
| OS-04 | Version History | Comparar, nomear e restaurar versões. |
| OS-05 | Context Drawer | Mostrar marca, campanha, oportunidade, evidências e guardrails. |
| OS-06 | Copilot Suggestion | Mostrar explicação, preview, aplicação, recusa e feedback. |

Esses frames são padrões/componentes, não novas páginas globais.

### Gate de protótipo

- Production Rail não parece sidebar de CRM.
- Canvas/trabalho permanece dominante.
- O usuário compreende onde está e qual é o próximo gate.
- Nenhuma ação crítica depende de texto técnico.
- Todos os estados de save e job estão representados.

### Gate de produção

- Visual e Carrossel utilizam os mesmos contratos.
- Autosave e conflito funcionam com dados reais.
- Review fixa uma versão imutável.
- Jobs são isolados por workspace.
- Feature flag permite rollback.

---

## 4. Onda 1 — Post Factory monetizável

### Promessa ao usuário

“Transforme uma oportunidade, oferta ou briefing em um post profissional, editável e pronto para aprovação sem começar do zero.”

### Jornada

```text
Create Hub
  → Direção Criativa
  → Editorial Desk
  → Visual Studio
  → Review Room
  → Exportar/agendar
  → Feedback
```

### Epics

#### Epic 1.1 — Direção Criativa

Outcome:

- usuário escolhe uma direção com evidência e entende por que ela combina com a marca.

Inclui:

- contexto ativo;
- objetivo, audiência e oferta;
- 3 direções comparáveis;
- ângulo, promessa, hook, prova e CTA;
- referências e fontes;
- risco e guardrails;
- feedback rápido;
- aprovação do `CreativeBrief`.

Fora desta onda:

- pesquisa autônoma contínua;
- scoring preditivo complexo;
- geração de campanha completa dentro do Studio.

#### Epic 1.2 — Editorial persistente

Outcome:

- usuário desenvolve hook, corpo, CTA e legenda sem perder o brief.

Inclui:

- blocos estruturados;
- variações lado a lado;
- reduzir, expandir, adaptar tom e variar CTA;
- checagem de claims;
- contagem e legibilidade;
- contexto e guardrails;
- save/versionamento;
- handoff ao Visual.

#### Epic 1.3 — Visual profissional essencial

Outcome:

- usuário finaliza uma peça profissional sem sair da Clicko.

Inclui:

- seleção, move, resize, rotate e crop;
- camadas;
- texto e tipografia;
- formas essenciais;
- mídia e assets;
- alinhamento e distribuição;
- cores, bordas, sombra e opacidade;
- brand tokens;
- Composition Coach;
- histórico;
- PNG/JPEG;
- revisão.

Fora desta onda:

- caneta avançada;
- vetorização completa;
- filtros generativos complexos;
- animação e timeline.

#### Epic 1.4 — Review e feedback

Outcome:

- aprovador decide em menos de um minuto e o sistema registra aprendizado útil.

Inclui:

- versão fixa;
- comentário geral e posicional;
- comparação;
- aprovar, solicitar ajustes e rejeitar;
- motivos rápidos;
- retorno exato ao Studio.

#### Epic 1.5 — Biblioteca operacional

Outcome:

- usuário encontra e insere assets aprovados sem procurar em várias ferramentas.

Inclui:

- upload;
- busca e filtros;
- direitos;
- inserção no editor;
- origem e usos;
- exclusão segura;
- outputs do Studio.

### Protótipos necessários

| Frame | Tela/estado | Conteúdo principal |
|---|---|---|
| P1-01 | Direção — contexto carregado | Inputs, evidências, guardrails e três direções. |
| P1-02 | Direção — comparação | Alternativas lado a lado e decisão. |
| P1-03 | Direção — pesquisa/evidência | Resultados com fonte, data, confiança e seleção. |
| P1-04 | Editorial — post | Blocos, copy, preview e contexto. |
| P1-05 | Editorial — comparação de hooks | Alternativas e diferenças. |
| P1-06 | Visual — estado principal | Canvas dominante, layers, tools e inspector. |
| P1-07 | Visual — Element Vault | Elementos, marca, recentes e busca. |
| P1-08 | Visual — Effects & Light | Controles essenciais e antes/depois. |
| P1-09 | Visual — conflito/versionamento | Resolução clara sem perda de trabalho. |
| P1-10 | Review — decisão | Peça, contexto, comentários e feedback rápido. |
| P1-11 | Library Picker | Seleção de asset dentro do Studio. |
| P1-12 | Export | Formato, qualidade, destino e preflight. |

### Métricas de validação

- tempo até primeiro rascunho útil;
- tempo até peça pronta;
- taxa de aprovação na primeira versão;
- número de ferramentas externas utilizadas;
- percentual de sugestões aceitas;
- percentual de documentos reabertos sem perda;
- sucesso de exportação.

---

## 5. Onda 2 — Carrossel e produção em lote

### Promessa

“Transforme uma ideia em uma sequência coerente e produza variações sem repetir trabalho.”

### Jornada

```text
Direção
  → Narrative Spine
  → Carousel Builder
  → Visual por slide/conjunto
  → Factory
  → Review em lote
  → Exportar/agendar
```

### Epics

#### Epic 2.1 — Narrative Spine

- funções narrativas por slide;
- gerar, encurtar e expandir sequência;
- reordenar;
- ritmo, densidade e coerência;
- CTA e objetivo do conjunto.

#### Epic 2.2 — Carousel Builder completo

- adicionar, duplicar e excluir;
- edição de conteúdo e design;
- aplicação a todos;
- safe area;
- consistência;
- preview contínuo;
- exportação multipágina;
- revisão da versão completa.

#### Epic 2.3 — Reuse Studio

- selecionar vencedor;
- explicar sinal de performance;
- preservar, adaptar e testar;
- lineage de derivações;
- comparação de variações;
- abertura no editor correto.

#### Epic 2.4 — Fábrica funcional

- rodada de produção;
- células reais;
- filas e prioridades;
- gates;
- cancelar e tentar novamente;
- capacidade e custo;
- revisão/entrega por lote.

### Protótipos necessários

| Frame | Tela/estado |
|---|---|
| P2-01 | Narrative Spine — criação e reordenação |
| P2-02 | Carousel — conteúdo |
| P2-03 | Carousel — design aplicado ao conjunto |
| P2-04 | Carousel — consistência e alertas |
| P2-05 | Carousel — preview/export multipágina |
| P2-06 | Reuse — diagnóstico do vencedor |
| P2-07 | Reuse — matriz preservar/adaptar/testar |
| P2-08 | Reuse — comparação de derivados |
| P2-09 | Factory — rodada e células reais |
| P2-10 | Factory — job com falha/decisão/retry |
| P2-11 | Factory — revisão em lote |

---

## 6. Onda 3 — Vídeo assistido

### Promessa

“Envie material bruto e termine um vídeo curto editável, legendado e alinhado à marca.”

### Primeiro escopo de vídeo

- upload/importação;
- análise FFprobe;
- proxies;
- transcrição PT-BR;
- media bin;
- player;
- transcript editor;
- timeline com vídeo, áudio, texto e captions;
- split, trim, delete e reorder;
- remoção assistida de silêncios;
- legendas editáveis;
- brand overlay;
- crop/reframe básico;
- áudio essencial;
- preview;
- render com progresso.

### Não entra no primeiro vídeo

- avatar;
- cenário generativo;
- dublagem multilíngue;
- B-roll totalmente automático;
- tracking sofisticado;
- motion complexo;
- multicam avançado.

### Spikes obrigatórios antes do protótipo final

#### Spike V1 — pipeline de mídia

Entrada:

- três vídeos PT-BR de durações e qualidades diferentes.

Provar:

- ingestão;
- FFprobe;
- proxy;
- render vertical;
- progress/cancel/retry;
- custo e duração.

#### Spike V2 — transcrição

Comparar:

- WhisperX e alternativa baseline;
- qualidade de palavra;
- pontuação;
- nomes de produto;
- timestamps;
- CPU/GPU;
- diarização quando aplicável.

#### Spike V3 — timeline

Comparar:

- componente open source selecionado;
- implementação mínima própria;
- 500, 2.000 e 10.000 segmentos;
- drag, snapping, zoom e acessibilidade;
- serialização no `CreativeDocument`.

### Protótipos necessários

| Frame | Tela/estado |
|---|---|
| V-01 | Ingestão vazia e com arquivos |
| V-02 | Análise/transcrição em progresso |
| V-03 | Video Studio principal |
| V-04 | Transcript editor sincronizado |
| V-05 | Timeline e inspector de clip |
| V-06 | Cortes inteligentes — sugestões |
| V-07 | Legendas e brand overlay |
| V-08 | Áudio e waveform |
| V-09 | Render drawer |
| V-10 | Falha recuperável e retry |

### Gate de produção

- um usuário produz um vídeo vertical real;
- nenhuma automação destrói a timeline original;
- cada alteração pode ser desfeita;
- captions permanecem editáveis;
- preview e render correspondem;
- o job pode ser cancelado e retomado;
- o output volta à Review Room.

---

## 7. Onda 4 — Motion e imagem avançada

### Motion

Primeiro escopo:

- entrada, ênfase e saída;
- duração, delay e easing;
- presets por intenção;
- preview loop;
- aplicar a seleção/todas;
- versão com movimento reduzido;
- render via pipeline de vídeo.

### Imagem avançada

Primeiro escopo:

- remover fundo;
- máscara;
- expandir imagem;
- upscale;
- gerar variações;
- smart resize;
- antes/depois;
- lineage e retorno ao Visual.

Cada capability generativa é um provider independente. Não criar um único endpoint genérico `image-edit` que esconda capacidades e limitações diferentes.

### Protótipos

- M-01 Motion inspector;
- M-02 Motion timeline/preview;
- M-03 Presets por intenção;
- I-01 Image Lab entrada;
- I-02 Máscara e seleção;
- I-03 Resultado antes/depois;
- I-04 Variações e locks;
- I-05 Job/proveniência.

---

## 8. Onda 5 — Presenter e identidade sintética

### Regra de produto

Presenter é uma célula de produção governada, não um botão “clonar pessoa”.

### Epics

#### Epic 5.1 — Consentimento

- identidade da pessoa;
- finalidade;
- território;
- canais;
- validade;
- assinatura;
- revogação;
- exclusão.

#### Epic 5.2 — Captura

- instruções guiadas;
- upload e gravação;
- qualidade de vídeo/áudio;
- takes aprovados/rejeitados;
- cobertura das expressões e pausas.

#### Epic 5.3 — Calibração

- direção da identidade;
- voz;
- presença;
- limites;
- cenário;
- locks de rosto/produto.

#### Epic 5.4 — Testes privados

- amostras não publicáveis;
- comparação com fonte;
- scores como suporte, não verdade;
- decisão humana;
- aprovação da identidade.

#### Epic 5.5 — Uso no Video Studio

- roteiro;
- cena;
- voz;
- geração;
- lineage;
- revisão;
- bloqueio quando consentimento expira.

### Spikes

- OpenVoice em PT-BR;
- HeyGem versus Duix-Avatar;
- qualidade de lip-sync;
- estabilidade dos containers;
- custo e tempo por minuto;
- revogação e exclusão de artefatos;
- análise jurídica de licenças.

### Gate go/no-go

Presenter só segue para produção se:

- o consentimento for verificável;
- a licença comercial for aceitável;
- PT-BR atingir o padrão definido;
- o rosto e a voz não exibirem artefatos inaceitáveis;
- houver isolamento por workspace;
- a revogação bloquear novos jobs;
- toda saída exigir revisão humana.

---

## 9. Fluxo padrão de planejamento → prototipação → produção

### Etapa A — Product Brief

Entregáveis:

- problema e usuário;
- outcome;
- entrada e saída;
- requisito IDs;
- hipótese;
- métrica;
- não objetivos;
- riscos.

### Etapa B — Arquitetura de interação

Entregáveis:

- jornada;
- mapa de estados;
- hierarquia da tela;
- ações primárias/secundárias;
- objetos manipulados;
- dependências de contexto;
- comportamento de retorno.

### Etapa C — Wireframe

Primeiro validar:

- espaço de trabalho;
- ordem das decisões;
- densidade;
- navegação;
- estados;
- compreensão sem acabamento visual.

### Etapa D — Protótipo visual

Aplicar:

- `design.md`;
- Production Rail;
- linguagem de laboratório;
- canvas/preview dominante;
- componentes compartilhados;
- conteúdo realista de uma marca.

### Etapa E — Teste de tarefa

Cada protótipo deve testar tarefas, não preferência estética.

Exemplos:

- “Transforme esta oportunidade em um post.”
- “Troque a imagem sem perder a composição.”
- “Solicite um ajuste específico no título.”
- “Remova um silêncio e edite a legenda.”

### Etapa F — Spike técnico

Executar somente nas áreas com incerteza relevante:

- engine visual;
- timeline;
- transcrição;
- geração de imagem;
- voz/avatar;
- orquestração pesada.

### Etapa G — Produção vertical

- contratos;
- backend;
- frontend;
- estados;
- telemetria;
- testes;
- documentação;
- rollout e rollback.

---

## 10. Definition of Ready de uma feature

Uma feature está pronta para entrar em desenvolvimento quando possui:

- requirement ID;
- owner;
- usuário e problema;
- comportamento;
- protótipo aprovado;
- estados e erros;
- permissão;
- contrato de dados;
- dependências;
- analytics;
- critérios de aceitação;
- estratégia de teste;
- rollout e rollback;
- decisão sobre open source.

Se uma feature não cumprir isso, ela pode permanecer no backlog ou em spike, mas não deve ser construída de forma improvisada.

---

## 11. Definition of Done de um corte vertical

- jornada real funciona com dados do backend;
- nenhum botão primário é decorativo;
- estados vazios, loading, erro, readonly e conflito estão cobertos;
- persistência e reabertura funcionam;
- versão e lineage estão corretos;
- assets respeitam workspace e direitos;
- revisão recebe a versão correta;
- telemetria está ativa;
- testes unitários, contrato, integração e E2E passam;
- inspeção visual foi feita nas resoluções suportadas;
- acessibilidade básica foi verificada;
- documentação corresponde ao código;
- rollback foi testado ou documentado.

---

## 12. Dependências críticas

```text
CreativeDocument + Production Rail
  ├── Direção
  ├── Editorial
  ├── Visual
  ├── Carrossel
  ├── Review
  └── Factory

Library + Lineage
  ├── Visual
  ├── Imagem
  ├── Vídeo
  └── Presenter

GenerationJob
  ├── Factory
  ├── Vídeo
  ├── Imagem
  └── Presenter

ConsentGrant
  ├── Voice clone
  └── Avatar/Presenter
```

Não iniciar Presenter antes de `ConsentGrant`. Não iniciar Factory real sem `GenerationJob`. Não escolher engine visual antes de confirmar a adaptação ao `CreativeDocument`.

---

## 13. Registro de protótipos

Cada frame deve possuir:

- ID deste roadmap;
- nome canônico;
- onda;
- status: exploração, em revisão, aprovado ou arquivado;
- requisito IDs cobertos;
- link do Figma;
- data e aprovador;
- estados derivados;
- notas para implementação.

Somente frames marcados simultaneamente como `CANONICAL` e `Approved` entram na allowlist. Explorações e variações descartadas ficam em página separada e nunca são tratadas como telas de produção.

---

## 14. Ordem operacional imediata

### Passo 1

Criar o protótipo `P1-01 — Direção Criativa`, pois hoje o fluxo pula do contexto para a criação sem uma bancada própria de decisão.

### Passo 2

Criar `P1-02 — Comparação de Direções` e `P1-03 — Pesquisa/Evidência`.

### Passo 3

Revisar o Editorial Desk atual contra o contrato e criar somente os estados ausentes, sem redesenhar gratuitamente.

### Passo 4

Executar spike Fabric.js versus Konva com o mesmo post e o mesmo carrossel.

### Passo 5

Prototipar as lacunas do Visual: Element Vault, Effects & Light, conflito e Library Picker.

### Passo 6

Fechar Review, export e feedback do primeiro corte vertical.

### Passo 7

Testar o fluxo completo com social medias antes de iniciar Vídeo.

---

## 15. Critério de sucesso da Onda 1

A Onda 1 está validada quando um social media consegue:

1. iniciar por oportunidade, oferta ou briefing;
2. escolher uma direção justificada;
3. desenvolver a mensagem;
4. finalizar uma peça visual profissional;
5. utilizar assets e identidade reais;
6. enviar uma versão específica para aprovação;
7. receber feedback e corrigir;
8. exportar ou encaminhar para publicação;
9. reabrir o trabalho sem perda;
10. concluir tudo com menos troca de ferramentas que no fluxo anterior.

O objetivo não é demonstrar que a IA gera conteúdo. É provar que a Clicko reduz o caminho entre contexto, decisão e peça profissional.
