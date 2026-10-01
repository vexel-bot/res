# Clicko Studios — Estratégia de Separação, Arquitetura e Evolução

**Versão:** 0.1  
**Status:** plano-base em evolução  
**Escopo:** Studios de criação de conteúdo da Clicko  
**Natureza do documento:** estratégia de produto e arquitetura; não é autorização automática para incorporar qualquer projeto open source.

**Especificação funcional complementar:** `docs/studios/STUDIOS_FUNCTIONAL_REQUIREMENTS.md` detalha áreas, ações, botões, estados, prioridades e oportunidades de aceleração open source. Estratégia e requisitos devem ser lidos em conjunto antes de prototipar ou produzir um Studio.

**Roadmap de produto e prototipação:** `docs/studios/STUDIOS_PRODUCT_PROTOTYPE_ROADMAP.md` define ondas, cortes verticais, frames necessários e gates entre planejamento, protótipo e produção.

**Inteligência contextual:** `docs/radar/RADAR_CONTEXTUAL_INTELLIGENCE_SPEC.md` preserva o planejamento do Radar, incluindo fontes, scoring, evidências, feedback, aprendizado local, avaliação e cohorts governados.

---

## 1. Decisão estratégica

Os Studios devem evoluir como um domínio próprio dentro da Clicko, com fronteiras, contratos, responsabilidades e ciclo de desenvolvimento claros. Neste primeiro estágio, isso deve acontecer **dentro do repositório atual**, sem transformar os Studios em um segundo produto ou duplicar as bases de autenticação, marca, campanha e aprovação.

O objetivo da separação é permitir que:

- um founder cuide da experiência global do produto;
- outro founder aprofunde os Studios e os motores de criação;
- os trabalhos avancem em paralelo sem conflitos constantes;
- o sistema mantenha uma única memória da marca e uma única jornada do usuário;
- ferramentas open source possam ser avaliadas e substituídas sem controlar a arquitetura da Clicko;
- a fábrica de conteúdo evolua de forma auditável, incremental e comercialmente sustentável.

### Decisão de repositório

Manter os Studios no mesmo repositório inicialmente. A separação começa como **bounded context**, não como repositório independente.

Um segundo repositório ou serviço separado só deve ser considerado quando:

- os contratos entre produto principal e Studios estiverem estáveis;
- o processamento de mídia exigir deploy e escalabilidade independentes;
- workers de GPU tiverem requisitos próprios de segurança e infraestrutura;
- o ritmo de releases dos Studios for materialmente diferente;
- a separação diminuir complexidade real em vez de apenas deslocá-la.

---

## 2. Fronteiras de responsabilidade

### 2.1 Sistema principal da Clicko

Continua responsável por:

- conta e autenticação;
- workspaces, membros, funções e permissões;
- memória, conhecimento e versões da marca;
- produtos, ofertas, público, voz e restrições;
- Radar de Oportunidades Contextuais;
- campanhas, objetivos e calendário;
- aprovação e publicação;
- analytics, performance e aprendizado;
- integrações de negócio;
- cobrança, planos, créditos e entitlements;
- navegação global e experiência transversal.

### 2.2 Clicko Studios

Passa a ser responsável por:

- direção criativa;
- estratégia editorial aplicada a uma peça;
- copy, roteiros, ganchos, ângulos e CTAs;
- posts, peças visuais e carrosséis;
- edição de vídeos curtos;
- apresentadores, avatares e clonagem de voz;
- variações e adaptações de conteúdo;
- composição, versionamento e edição não destrutiva;
- processamento e renderização;
- exportação dos artefatos;
- jobs, dependências, filas, progresso e falhas;
- linhagem e proveniência dos conteúdos;
- feedback específico sobre decisões criativas.

### 2.3 Relação entre os domínios

O sistema principal fornece contexto e recebe resultados. Os Studios transformam contexto em produção.

```text
Memória da marca + Campanha + Radar + Histórico
                         ↓
                 Direção criativa
                         ↓
         Studios e fábrica de conteúdo
                         ↓
              Revisão e aprovação
                         ↓
          Publicação + resultado + aprendizado
```

O Radar não deve morar dentro de cada editor. Ele entrega uma oportunidade contextual estruturada. Os Studios a utilizam como uma das entradas possíveis.

---

## 3. Visão do produto: laboratório e fábrica de conteúdo

Os Studios não devem ser uma coleção de geradores independentes nem uma cópia ampla de Canva, Figma ou Photoshop.

A proposta é um **laboratório de social media** capaz de transformar conhecimento de marca, contexto do mundo, repertório de nicho e dados anteriores em conteúdo profissional, editável, consistente e pronto para operar.

A fábrica deve seguir o fluxo:

```text
Oportunidade ou demanda
  → Direção criativa
  → Briefing estruturado
  → Roteiro e narrativa
  → Seleção e produção de materiais
  → Montagem
  → Variações
  → Revisão
  → Aprovação
  → Exportação/publicação
  → Resultado
  → Aprendizado
```

Princípios:

1. A inteligência deve orientar decisões, não apenas preencher um prompt.
2. O resultado precisa continuar profissional depois que a IA termina.
3. O usuário deve conseguir editar e dirigir a criação.
4. A marca, o objetivo e a oportunidade precisam permanecer rastreáveis.
5. Toda geração relevante deve possuir versão, origem, direitos e estado de aprovação.
6. A automação não elimina o controle humano em decisões de risco.

---

## 4. Mapa dos Studios

### 4.1 Studio de Direção Criativa

Transforma a demanda em um `CreativeBrief` estruturado.

Entradas:

- contexto e memória da marca;
- produto, oferta e objetivo;
- público e estágio de consciência;
- oportunidade do Radar;
- canal e formato;
- histórico de desempenho;
- restrições, claims e riscos;
- referências fornecidas ou pesquisadas.

Saídas:

- objetivo;
- público específico;
- ângulo;
- promessa;
- gancho;
- estrutura narrativa;
- CTA;
- tom e emoção;
- referências e evidências;
- formato sugerido;
- restrições e cuidados;
- hipóteses que serão avaliadas.

O briefing deve ser reutilizável pelos Studios Visual, Carrossel, Vídeo e Apresentador.

### 4.2 Studio Editorial e de Copy

Responsabilidades:

- desenvolver hooks, ângulos, argumentos e CTAs;
- adaptar a linguagem ao canal e à marca;
- criar variações sem perder a tese criativa;
- indicar claims que precisam de evidência;
- trabalhar estágio de funil e intenção;
- registrar feedback editorial de forma estruturada.

### 4.3 Studio Visual

Responsabilidades:

- composição por camadas;
- textos, imagens, formas, máscaras, sombras, luz e efeitos;
- grades, alinhamento e hierarquia;
- aplicação de brand kit e regras da marca;
- templates inteligentes e blocos reutilizáveis;
- edição não destrutiva;
- variações de formato e canal;
- histórico, comparação e restauração de versões;
- exportação com qualidade profissional.

O Studio Visual deve conter capacidades essenciais de um editor, mas seu diferencial é a direção contextual e a aplicação inteligente de marca — não a quantidade de botões.

### 4.4 Studio de Carrossel

Compartilha o motor visual, acrescentando:

- narrativa entre páginas;
- papel de cada slide;
- controle de ritmo e densidade;
- abertura, progressão, payoff e CTA;
- reordenação com preservação de sentido;
- expansão ou redução da quantidade de páginas;
- aplicação de consistência entre slides;
- transformação de uma tese em série visual.

### 4.5 Studio de Vídeo

#### Primeira versão assistida

- ingestão e organização de mídia;
- análise técnica dos arquivos;
- transcrição com timestamps;
- cortes e remoção de silêncios;
- legendas editáveis;
- reenquadramento para formatos verticais;
- aplicação de identidade visual;
- timeline e preview;
- trilha e normalização de áudio;
- renderização para Reels, TikTok e Shorts.

#### Evolução

- seleção inteligente de takes;
- montagem por intenção;
- B-roll recomendado;
- detecção de cenas e momentos;
- rastreamento de objetos e pessoas;
- edição generativa controlada;
- cenários reais ou sintéticos;
- variações do mesmo vídeo;
- experimentos com apresentadores digitais.

### 4.6 Studio de Apresentador e Identidade

Responsabilidades:

- criação de cápsula de identidade;
- coleta comprovável de consentimento;
- vídeos, imagens e áudios de referência;
- análise de qualidade das amostras;
- definição de rosto, voz, postura e estilo;
- roteiro e direção de performance;
- cenário, enquadramento, roupa e identidade;
- clonagem ou síntese de voz;
- geração de amostra privada;
- revisão humana obrigatória;
- ativação, expiração, revogação e exclusão;
- rastreamento de todos os artefatos derivados.

Esse Studio deve impedir clonagem de terceiros sem autorização e não pode publicar automaticamente um apresentador sintético sem revisão adequada.

### 4.7 Fábrica de Conteúdo

É a camada de orquestração, não apenas uma tela.

Responsabilidades:

- planejar dependências entre tarefas;
- criar e acompanhar jobs;
- exibir progresso real;
- permitir cancelamento e repetição segura;
- controlar versões e artefatos intermediários;
- calcular custo e créditos;
- direcionar jobs para CPU ou GPU;
- aplicar gates de revisão;
- preservar logs e proveniência;
- retomar trabalhos interrompidos;
- preparar lotes e variações.

### 4.8 Revisão e Aprendizado

Todo Studio deve compartilhar um modelo simples de feedback:

- aprovar;
- reprovar;
- solicitar ajuste;
- escolher um motivo rápido;
- adicionar observação opcional;
- comparar versões quando necessário.

O feedback deve alimentar a marca individual primeiro. Aprendizados entre clientes ou cohorts só podem utilizar dados autorizados, agregados e protegidos contra vazamento de informações privadas.

---

## 5. Contratos compartilhados

Os Studios devem consumir contratos versionados em vez de copiar dados ou consultar diretamente tabelas internas de outros domínios.

Contratos principais:

- `WorkspaceContext`
- `BrandMemoryVersion`
- `CampaignContext`
- `OpportunityEvidence`
- `AssetReference`
- `CreativeBrief`
- `CreativeDocument`
- `GenerationJob`
- `ConsentGrant`
- `ApprovalDecision`
- `PerformanceFeedback`
- `ExportTarget`

Eventos recomendados:

- `studio.document.created`
- `studio.document.versioned`
- `studio.job.queued`
- `studio.job.started`
- `studio.job.progressed`
- `studio.job.completed`
- `studio.job.failed`
- `studio.job.cancelled`
- `studio.review.requested`
- `studio.review.approved`
- `studio.review.rejected`
- `studio.output.exported`
- `studio.output.published`
- `identity.consent.granted`
- `identity.consent.revoked`
- `learning.feedback.recorded`

Contratos devem conter IDs estáveis, versão de schema, workspace, autoria, timestamps e correlação entre jobs.

---

## 6. Creative Document: formato canônico

O `CreativeDocument` é o núcleo independente de provider que permite editar, versionar, renderizar e trocar tecnologias.

Estrutura conceitual:

```text
CreativeDocument
├── identidade
│   ├── documentId
│   ├── workspaceId
│   ├── campaignId
│   ├── contentType
│   ├── status
│   └── schemaVersion
├── estratégia
│   ├── objective
│   ├── audience
│   ├── angle
│   ├── hook
│   ├── promise
│   ├── CTA
│   ├── claims/evidence
│   └── opportunityRef
├── composição
│   ├── pages/scenes
│   ├── layers
│   ├── tracks
│   ├── timing
│   └── effects
├── assets
│   ├── origem
│   ├── direitos
│   ├── hash
│   ├── versões
│   └── proveniência
├── marca
│   ├── brandMemoryVersion
│   ├── tokens
│   ├── rules
│   └── exceptions
├── inteligência
│   ├── provider
│   ├── model
│   ├── generationParameters
│   └── lineage
├── revisão
│   ├── decisões
│   ├── comentários
│   └── aprovação
└── exportação
    ├── target
    ├── dimensions
    ├── codec/format
    └── artifactRef
```

Não armazenar o documento somente no formato interno de Fabric, Konva, Remotion, Duix ou outro projeto.

---

## 7. Arquitetura de separação

### 7.1 Primeiro estágio no projeto atual

```text
src/
  studios/
    direction/
    editorial/
    visual/
    carousel/
    video/
    presenter/
    factory/
    review/
    shared/

backend/app/
  domain/studios/
  services/studios/
  providers/studios/
  workers/
  routers/studios.py
```

As rotas atuais devem ser migradas gradualmente para o novo domínio por compatibilidade, sem uma reescrita simultânea das telas.

### 7.2 Estrutura futura, quando justificada

```text
apps/
  clicko-web/
  studios-web/

services/
  api/
  studio-orchestrator/
  media-worker/
  gpu-worker/

packages/
  studio-contracts/
  creative-document/
  provider-adapters/
  design-system/

infra/
  compose/
  observability/
```

### 7.3 Regras arquiteturais

- Não duplicar autenticação, workspaces ou memória da marca.
- Não permitir joins diretos entre futuros serviços; utilizar contratos.
- Separar orquestração de execução pesada.
- Jobs devem ser idempotentes, canceláveis e observáveis.
- Outputs grandes devem utilizar armazenamento de objetos.
- Providers de IA devem ser substituíveis.
- Toda geração deve guardar provider, modelo, parâmetros e versão.
- Dados de uma marca não podem alimentar diretamente outra marca.
- Mudanças de schema devem possuir migração e compatibilidade.

---

## 8. Providers e open source

### 8.1 Interfaces obrigatórias

Projetos externos devem entrar atrás de interfaces como:

- `ResearchProvider`
- `VoiceCloneProvider`
- `AvatarProvider`
- `TranscriptionProvider`
- `VideoRenderProvider`
- `ImageSegmentationProvider`
- `BackgroundRemovalProvider`
- `VisualCanvasProvider`

Nenhum componente de produto deve depender diretamente da API específica de um provider.

### 8.2 Registro inicial

#### Vane — antigo Perplexica

- Repositório: <https://github.com/ItzCrazyKns/Vane>
- Papel possível: pesquisa web, fontes, notícias, discussões e referências.
- Licença: MIT.
- Decisão inicial: **encapsular como provider de pesquisa**.
- Não é: o algoritmo completo do Radar.

O Radar ainda precisa de ingestão, normalização, confiança da fonte, temporalidade, relação com a marca, saturação, risco, capacidade de conversão e aprendizado.

#### HeyGem

- Repositório confirmado: <https://github.com/Caladog/HeyGem>
- Papel possível: avatar e vídeo de apresentador.
- Licença: Silicon Intelligence Community License, com atribuição e licença comercial acima de 1.000 MAU.
- Decisão: **rejeitar pelo critério “somente open source”**; manter apenas como referência auditada.

#### Duix-Avatar

- Repositório: <https://github.com/duixcom/Duix-Avatar>
- Papel possível: avatar, rosto, voz e vídeo offline.
- Licença: comunitária e não permissiva como MIT/Apache.
- Riscos: atribuição, limite de uso comercial, termos adicionais, GPU e qualidade.
- Decisão inicial: **protótipo isolado atrás de adapter**.
- Não integrar simultaneamente com HeyGem antes de um comparativo.

#### OpenVoice

- Repositório: <https://github.com/myshell-ai/OpenVoice>
- Papel possível: clonagem de voz.
- Licença: MIT.
- Decisão inicial: **candidato para spike**.
- Risco: português brasileiro precisa ser testado; suporte multilíngue não prova naturalidade local.

### 8.3 Outros candidatos prováveis

#### FFmpeg

- Repositório: <https://github.com/FFmpeg/FFmpeg>
- Papel: análise, conversão, composição e renderização de mídia.
- Direção: provável infraestrutura essencial.
- Cuidado: a licença do binário final depende das opções de compilação e bibliotecas incluídas.

#### Fabric.js ou Konva

- Papel: cena visual, objetos e manipulação de canvas.
- Direção: realizar spike comparativo e escolher somente um.
- Critérios: performance, serialização, texto, máscaras, filtros, histórico, extensibilidade e compatibilidade com o Creative Document.

#### WhisperX

- Repositório: <https://github.com/m-bain/whisperX>
- Papel: transcrição, alinhamento de palavras e diarização.
- Direção: candidato para spike do Studio de Vídeo.
- Cuidado: modelos auxiliares podem possuir termos próprios.

#### Segmentação e tracking

- SAM 2 pode ser avaliado posteriormente para máscaras e rastreamento.
- Não antecipar essa dependência antes de o fluxo básico de vídeo funcionar.

#### Renderização programática

- HyperFrames (<https://github.com/heygen-com/hyperframes>) deve ser o primeiro spike de composição programática; é Apache-2.0 e usa HTML, Chrome headless e FFmpeg.
- O vídeo de lançamento do HyperFrames é referência de arquitetura, não fonte de mídia reutilizável, pois não possui licença própria clara.
- Remotion não entra no spike enquanto a regra for “somente open source”; sua licença restringe organizações não elegíveis.
- FFmpeg deve cobrir o primeiro vertical slice sempre que possível.

---

## 9. Processo de avaliação de open source

Cada projeto deve receber uma ficha contendo:

1. Problema exato que resolve.
2. Alternativas existentes no projeto atual.
3. Licença do código.
4. Licença de modelos, pesos e datasets.
5. Licença de imagens e containers distribuídos.
6. Direito de uso comercial em SaaS.
7. Obrigações de atribuição.
8. Manutenção, releases, issues e comunidade.
9. API ou execução headless.
10. Qualidade em português e em casos reais de marca.
11. Requisitos de GPU, RAM, disco e rede.
12. Latência e throughput.
13. Custo por artefato.
14. Multi-tenancy e isolamento.
15. Privacidade e retenção.
16. Cancelamento, retry e progresso.
17. Reprodutibilidade e observabilidade.
18. Estratégia de substituição.

Possíveis decisões:

- **Adotar:** tecnologia madura, adequada e juridicamente segura.
- **Encapsular:** útil, mas precisa permanecer substituível.
- **Referenciar:** aproveitar conceitos, sem incorporar código.
- **Rejeitar:** risco maior que o benefício.

### Regra make, buy ou open source

- Diferencial central e complexidade administrável: construir na Clicko.
- Componente commodity e licença segura: adotar.
- ML difícil ou caro: testar open source e APIs atrás de adapter.
- Projeto com licença duvidosa: não incorporar até revisão.
- Projeto completo com UI própria: evitar fork; aproveitar serviço ou conceito.
- Dificuldade isolada não justifica uma dependência estrutural sem benchmark.

---

## 10. Segurança, consentimento e proveniência

Rosto e voz associados a uma pessoa são dados de alto risco e podem envolver dados pessoais sensíveis. O produto deve prever:

- consentimento explícito e verificável;
- pessoa autorizadora e finalidade;
- escopo de uso;
- data de criação e expiração;
- revogação imediata;
- exclusão dos dados derivados quando aplicável;
- registro de todos os usos;
- bloqueio de clonagem de terceiros;
- revisão humana antes de ativar ou publicar;
- marcação e proveniência do conteúdo sintético;
- política de incidentes e denúncias.

Referências:

- LGPD: <https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm>
- C2PA / Content Credentials: <https://spec.c2pa.org/specifications/specifications/2.4/specs/ContentCredentials.html>

Implementação comercial deve passar por revisão jurídica; este documento não substitui aconselhamento legal.

---

## 11. Divisão de trabalho entre founders

### Owner da experiência global

- shell do produto;
- navegação;
- descoberta das áreas;
- design system compartilhado;
- coerência da jornada completa;
- padrões globais de acessibilidade e responsividade;
- validação da experiência transversal.

### Owner dos Studios

- arquitetura interna dos Studios;
- fluxos de produção;
- Creative Document;
- motores criativos;
- edição e renderização;
- adapters e providers;
- fábrica, filas e workers;
- qualidade dos outputs;
- feedback criativo e aprendizado;
- benchmarks técnicos.

### Regras de colaboração

- O shell global não deve ser refeito pelos Studios.
- Uma feature de Studio não entra sem fluxo e estado de tela definidos.
- Uma tela não entra sem contrato de dados e comportamento.
- Um provider não entra sem ficha de avaliação.
- Mudanças em contratos compartilhados precisam de revisão dos dois owners.
- Usar branches ou worktrees separadas e integração frequente.
- Não misturar refactor estrutural, redesign global e novo motor de geração no mesmo pull request.

---

## 12. Plano de execução

### Fase 0 — Auditoria e fronteiras

**Objetivo:** compreender o estado real e impedir uma separação destrutiva.

Entregáveis:

- inventário das rotas, componentes e modos atuais de Studio;
- inventário das dependências de backend;
- mapa de dados compartilhados;
- matriz de ownership;
- mapa de riscos e dívidas;
- ADR da estratégia de separação;
- baseline visual e funcional das telas existentes;
- lista explícita de não objetivos.

Critérios de saída:

- nenhuma funcionalidade foi removida;
- fronteiras estão documentadas;
- rotas e contratos atuais estão conhecidos;
- há estratégia de migração gradual e rollback.

### Fase 1 — Studio Kernel

**Objetivo:** criar o núcleo compartilhado sem mudar radicalmente a experiência.

Entregáveis:

- schemas de contratos;
- `CreativeBrief` e `CreativeDocument` versionados;
- modelo de `GenerationJob`;
- interfaces de providers;
- eventos de domínio;
- persistência e migrações;
- progresso, retry, cancelamento e idempotência;
- adapters temporários para rotas atuais;
- testes de contrato.

Critérios de saída:

- o produto atual continua funcionando;
- documentos e jobs são observáveis;
- um provider falso pode ser trocado sem alterar o domínio;
- não há duplicação de marca, campanha ou workspace.

### Fase 2 — Vertical slice Visual e Carrossel

**Objetivo:** entregar o primeiro fluxo monetizável de ponta a ponta.

Fluxo:

```text
Campanha/oportunidade
  → briefing
  → documento
  → edição
  → variações
  → versionamento
  → revisão
  → exportação
```

Entregáveis:

- spike Fabric.js versus Konva;
- decisão documentada;
- edição persistente;
- aplicação de marca;
- variações de formato;
- fluxo de revisão;
- exportação;
- teste E2E do fluxo.

### Fase 3 — Vertical slice de vídeo assistido

**Objetivo:** criar edição útil antes de perseguir geração cinematográfica.

Entregáveis:

- ingestão e análise de mídia;
- FFmpeg/FFprobe;
- transcrição e timestamps;
- cortes e legendas;
- reenquadramento;
- timeline;
- render job com progresso;
- exportação vertical;
- benchmark de custo e tempo.

### Fase 4 — Laboratório de apresentador

**Objetivo:** provar qualidade, segurança e viabilidade antes de integrar ao produto principal.

Entregáveis:

- fluxo de consentimento;
- cápsula de identidade;
- benchmark OpenVoice em português;
- benchmark HeyGem versus Duix-Avatar;
- amostras privadas;
- análise de latência, GPU e custo;
- análise de licença;
- mecanismo de revogação e exclusão;
- decisão go/no-go.

Não liberar produção automática antes de todos os gates.

### Fase 5 — Research Provider e Radar

**Objetivo:** conectar pesquisa atual ao sistema próprio de oportunidades.

Entregáveis:

- interface `ResearchProvider`;
- spike Vane/SearxNG;
- fontes e citações;
- normalização e deduplicação;
- confiança e temporalidade;
- conexão com o scoring próprio;
- observabilidade da origem das oportunidades.

### Fase 6 — Fábrica e escala

**Objetivo:** transformar fluxos individuais em operação confiável.

Entregáveis:

- workers CPU e GPU;
- filas e prioridades;
- storage de artefatos;
- quotas e créditos;
- cálculo de custo;
- cache;
- isolamento multi-tenant;
- logs, métricas e alertas;
- políticas de retenção.

### Fase 7 — Aprendizado

**Objetivo:** melhorar decisões sem vazar conhecimento entre clientes.

Entregáveis:

- taxonomia de feedback;
- aprendizado individual da marca;
- testes controlados de variações;
- cohorts agregados e autorizados;
- avaliação de qualidade editorial;
- medição durante 8 a 12 semanas;
- rollback de alterações prejudiciais.

---

## 13. Priorização de produto

Ordem recomendada:

1. Studio Kernel.
2. Posts e carrosséis editáveis.
3. Fábrica básica, revisão e exportação.
4. Vídeo assistido.
5. Integração de pesquisa/Radar.
6. Apresentadores e avatares como experimento controlado.
7. Escala e aprendizado entre cohorts.

Justificativa:

- posts e carrosséis estão mais próximos do uso atual e da monetização;
- vídeo assistido entrega valor sem depender inicialmente de modelos complexos;
- avatar é uma proposta forte, mas possui maior risco jurídico, técnico e reputacional;
- o Radar deve alimentar os Studios por contratos, não bloquear a separação estrutural.

---

## 14. Critérios de qualidade

### Produto

- O usuário entende a próxima ação.
- A criação parece parte da Clicko, não uma ferramenta incorporada.
- A IA oferece direção explicável e editável.
- A marca permanece consistente.
- Há estados claros de progresso, erro e revisão.

### Engenharia

- Sem regressão nas telas existentes.
- Contratos versionados e testados.
- Jobs idempotentes e canceláveis.
- Providers substituíveis.
- Migrações reversíveis.
- Testes E2E do caminho crítico.
- Logs sem dados sensíveis desnecessários.

### Mídia

- Export correto em dimensões, codec e qualidade.
- Texto e legenda legíveis.
- Áudio sincronizado e normalizado.
- Cor e tipografia coerentes.
- Assets e versões rastreáveis.

### IA

- Saída em português natural.
- Evidências disponíveis quando necessárias.
- Ausência de claims não verificados.
- Feedback registrado.
- Provider, modelo e parâmetros rastreados.
- Qualidade comparada com baseline humano ou fluxo atual.

### Segurança

- Consentimento comprovado para rosto e voz.
- Isolamento entre workspaces.
- Exclusão e revogação verificáveis.
- Nenhuma publicação automática de alto risco.
- Licenças documentadas.

---

## 15. Definition of Done da separação

A separação será considerada bem-sucedida quando:

- as telas e fluxos atuais continuarem disponíveis;
- o shell global permanecer sob a experiência principal;
- Studios possuírem módulo e domínio claros;
- autenticação, marca e campanha não forem duplicadas;
- houver `CreativeDocument` e contratos versionados;
- o Studio puder operar isoladamente em desenvolvimento;
- o produto principal puder abrir um Studio com contexto tipado;
- um output puder voltar para aprovação e publicação;
- jobs possuírem progresso, retry, cancelamento e logs;
- providers puderem ser substituídos em testes;
- todo artefato possuir origem, versão e workspace;
- identidade sintética possuir consentimento e revogação;
- pelo menos um fluxo E2E estiver automatizado;
- houver documentação e rollback da migração.

---

## 16. Não objetivos imediatos

- Reescrever as 37 telas de uma vez.
- Redesenhar o sistema global.
- Copiar toda a interface do Canva, Figma ou Photoshop.
- Integrar simultaneamente HeyGem e Duix-Avatar.
- Criar um segundo sistema de autenticação ou marca.
- Colocar todos os modelos no mesmo processo da API.
- Liberar clonagem de rosto ou voz sem consentimento.
- Construir infraestrutura de GPU antes de um benchmark real.
- Usar aprendizado entre clientes sem autorização e proteção.
- Substituir tecnologias estáveis apenas para reorganizar pastas.

---

## 17. Registro vivo de decisões

Cada novo repositório enviado deve ser incluído em uma tabela como esta:

| Projeto | Problema | Licença | Qualidade | Infra | Riscos | Decisão | Próximo teste |
|---|---|---|---|---|---|---|---|
| Vane | Pesquisa contextual | MIT | A validar no domínio | CPU/rede | Não resolve scoring | Encapsular | Spike com fontes reais |
| HeyGem | Avatar | Comunitária, limite comercial | Não benchmarkar | GPU | Não atende “somente open source” | Rejeitar | Manter evidência |
| Duix-Avatar | Avatar e voz | Comunitária, limite comercial | Não benchmarkar | GPU alta | Não atende “somente open source” | Rejeitar | Manter evidência |
| OpenVoice | Voz | MIT | PT-BR a validar | GPU | Naturalidade e abuso | Spike | Benchmark de voz |
| HyperFrames | Render de vídeo HTML | Apache-2.0 | A validar no domínio | CPU/rede | HTML/assets e isolamento | Encapsular | Spike na VPS |

ADRs sugeridos:

- ADR-001 — Studios como bounded context no monorepo.
- ADR-002 — Creative Document canônico e provider-neutral.
- ADR-003 — Separação entre API, media worker e GPU worker.
- ADR-004 — Processo de adoção de open source.
- ADR-005 — Consentimento e proveniência de identidade sintética.
- ADR-006 — Engine visual escolhida após spike.
- ADR-007 — Estratégia de transcrição e render de vídeo.

---

## 18. Perguntas ainda abertas

- HeyGem resolvido: `Caladog/HeyGem`; rejeitado pela licença comunitária não permissiva.
- Qual volume de geração deve ser suportado no primeiro trimestre?
- A Oracle VPS possui GPU ou os workers pesados usarão outro ambiente?
- Qual é o limite de custo aceitável por vídeo?
- Quais formatos visuais entram no primeiro vertical slice?
- Quais redes e codecs são prioritários?
- O produto utilizará apenas assets próprios/licenciados no MVP?
- Qual nível de realismo é aceitável para apresentadores?
- Como a Clicko comunicará conteúdo sintético ao usuário final?
- Quais dados podem ou não participar de aprendizado agregado?

Essas perguntas não bloqueiam a Fase 0 e o Studio Kernel, mas bloqueiam compromissos de infraestrutura ou publicação de avatares.

---

## 19. Regra final

A Clicko não deve vencer por ter mais ferramentas. Deve vencer por transformar contexto, memória, repertório e oportunidade em decisões criativas melhores — e transformar essas decisões em conteúdo profissional com menos esforço operacional.

Os open sources são aceleradores substituíveis. A inteligência, os contratos, o fluxo de produção, o aprendizado e a experiência da fábrica pertencem à Clicko.

---

## 20. Checkpoint de implementação — 25/08/2026

O primeiro corte UGC local agora comprova a arquitetura sem transformar open source em domínio do produto:

- `CreativeDocumentV1` continua a única fonte de verdade;
- OpenCut serviu apenas como referência de UX para a timeline nativa;
- FFprobe/FFmpeg operam atrás de ports para probe, proxy, waveform e render limitado;
- proxy e original são ligados por `MediaTimeMapV1` validado;
- timeline direta usa frames racionais e remapeia tracks dependentes;
- captions lower-third, faixa e CTA tipados são materializados no MP4 e registrados por ID no lineage;
- QC técnico versionado mede codec, duração/sync A/V, black frames, loudness, true peak e silêncio antes de review;
- o artefato privado registra lineage e a review fixa job, asset e checksum;
- um E2E autenticado reprobe o MP4 final, inspeciona seus pixels e comprova isolamento cross-tenant.

Esse checkpoint não libera avatar, clonagem de voz/rosto nem worker de produção. A paridade e o QC cobrem apenas o subconjunto UGC básico; thresholds ainda precisam de calibração e radius, ênfase, transitions, múltiplos assets e composição avançada permanecem declaradamente fora.

O gate seguinte foi provado em Docker local: manifest versionado, boot fail-closed, probe/health, Redis e processo `media_cpu` separado, attestation por job, retry do mesmo ID e cancelamento de proxy sem asset vazado. Isso não é rollout: PostgreSQL/S3/IAM, broker gerenciado, observabilidade, dead-letter/reconciliação, quotas/autoscaling e imagem promovida com SBOM/assinatura ainda são obrigatórios. A VPS Nexus não foi usada como media worker.

---

## 21. Checkpoint de pesquisa — 27/08/2026

- Supervision 0.30.1 foi classificado como toolkit MIT de borda para normalização, overlays, zones, datasets e métricas. Não é detector nem motor de física, seus objetos não serão persistidos e o ByteTrack depreciado não entra.
- PersonaPlex foi separado em código MIT e checkpoint sob licença customizada NVIDIA. O checkpoint foi rejeitado pela política open-source-only, por idioma/fit e por não atender a fronteira SaaS; não houve aceite ou download.
- A voz de anúncios PT-BR continua em Chatterbox/Kokoro/OpenVoice. Conversa full-duplex futura terá capability separada e só será priorizada por necessidade real de produto.
- Os inventories estão fail-closed e os manifests `vision_gpu`/`speech_gpu` permanecem com `providers: []`.
- A análise completa, riscos de código, benchmark e fases estão em `docs/studios/research/SUPERVISION_PERSONAPLEX_STRATEGY_2026-08-27.md`, ADR-019 e ADR-020.

---

## 22. Checkpoint de execução — 28/08/2026

- Supervision 0.30.1 foi executado de verdade em spike offline e reversível: `sv.Detections` permanece efêmero e somente `RealityContributionV1`, evidências e overlays ligados a `evidence_id` atravessam a fronteira.
- O benchmark sintético congelado comparou geometria, zones e desenho contra primitivas OpenCV independentes, mediu determinismo/robustez/throughput e passou os gates técnicos; isso não autoriza promoção.
- A supply chain Linux/AMD64 possui lock com 29 wheels por SHA-256, SBOM SPDX, review de licenças e evidência hashada de notices/objetos para 10 wheels nativas. O OCI `92dbfe13...d6a6`, BuildKit provenance/SBOM e probe hardened sem rede foram materializados; revisão humana e assinatura de promoção permanecem abertas.
- O SV-4 agora possui candidate manifest e shadow sintético fail-closed. O OpenCV primitive reference permaneceu autoritativo, a divergência foi zero e o rollback sem migration foi comprovado; o candidato continua `evaluation`, não anunciado e proibido de influenciar a saída.
- PersonaPlex não foi instalado. Seu padrão full-duplex orientou um `DuplexConversationProvider` separado, com consentimento, política, checksums de áudio, interrupção, backchannel, retenção zero e replay determinístico.
- O harness duplex PT-BR congelou dez cenários e uma state machine explícita. A calibração sintética validou interrupção, pausa, recuperação, prompt injection e revogação, mas falhou fechado na promoção por ausência de áudio real, WER, julgamento humano, custo, concorrência, memória e proveniência.
- Qwen3-Omni permanece challenger de pesquisa: o código pinado é Apache-2.0 e o model card declara português de entrada/saída, porém registra `license: other`, apenas nomeia `apache-2.0` e não contém arquivo LICENSE. Os 15 shards safetensors, 70.523.299.202 bytes e hashes foram inventariados sem download; licença dos pesos, PT-BR dialetal, full-duplex real e hardware ainda precisam de aprovação/prova externa.
- `vision_gpu` e `speech_gpu` continuam com `providers: []`; a VPS não foi acessada ou alterada.
- A API local recebeu credenciais CSPRNG separadas para JWT e futuro sidecar OpenAI-compatible, sem expor segredos. Um usuário de laboratório com workspace único executou upload e ingestão real de MP4 pela API; a bateria de vídeo teve 21 testes aprovados. Isso habilita testes locais de FFmpeg/FFprobe, não concede acesso a APIs externas nem ativa modelos.
- O Qwen3-4B GGUF Q4 oficial foi materializado localmente (4.022.468.096 parâmetros), verificado por SHA-256 e executado via llama.cpp/Vulkan. A API OpenAI-compatible em loopback exige a chave de `.env`, recusa acesso anônimo com `401` e respondeu um smoke PT-BR; o manifest `llm_gpu` continua vazio.
- O pack Chatterbox pt-BR foi materializado e verificado, mas o preflight da imagem recusou o host de 4.095 MiB diante do piso `speech_gpu` de 16.384 MiB. Nenhuma inferência de voz, dado biométrico ou ativação ocorreu; a VPS permaneceu intocada.
