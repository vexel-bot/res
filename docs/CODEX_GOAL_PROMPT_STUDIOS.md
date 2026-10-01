# Prompt para Codex em modo Goal — Separação e evolução dos Clicko Studios

Copie todo o bloco abaixo para uma nova task do Codex configurada em modo Goal.

---

## Prompt

Você atuará como engenheiro principal e arquiteto responsável por separar e evoluir os Studios da Clicko dentro do repositório existente.

### Repositório correto

Trabalhe exclusivamente no projeto:

`C:\Users\edugu\Downloads\res`

O documento normativo desta meta é:

`C:\Users\edugu\Downloads\res\docs\CLICKO_STUDIOS_STRATEGY.md`

A especificação funcional complementar é:

`C:\Users\edugu\Downloads\res\docs\studios\STUDIOS_FUNCTIONAL_REQUIREMENTS.md`

O roadmap de produto, prototipação e cortes verticais é:

`C:\Users\edugu\Downloads\res\docs\studios\STUDIOS_PRODUCT_PROTOTYPE_ROADMAP.md`

A especificação normativa do Radar e do algoritmo contextual é:

`C:\Users\edugu\Downloads\res\docs\radar\RADAR_CONTEXTUAL_INTELLIGENCE_SPEC.md`

Leia os quatro documentos completamente antes de alterar qualquer arquivo. Eles definem visão, fronteiras, contratos, áreas, ações, estados, ondas, Radar, aprendizado, riscos, critérios de qualidade e Definition of Done. Em caso de conflito entre uma suposição sua e os documentos, siga os documentos. Não reduza o plano a uma reorganização de pastas e não pule diretamente para fases avançadas do roadmap.

### Objetivo da meta

Estabelecer os Clicko Studios como um bounded context auditável dentro do projeto atual, preservando o produto em funcionamento e preparando uma evolução segura da fábrica de conteúdo.

A meta deve:

1. Auditar o estado real do frontend, backend, banco, workers, rotas e testes.
2. Separar responsabilidades dos Studios sem duplicar autenticação, workspace, marca, campanha, aprovação ou publicação.
3. Criar contratos versionados e provider-neutral.
4. Introduzir o Studio Kernel e uma migração incremental das implementações atuais.
5. Preservar todas as features existentes, inclusive aquelas ainda não representadas nos protótipos.
6. Preparar visual, carrossel, vídeo, apresentador e fábrica para evoluírem por vertical slices.
7. Avaliar open source por licença, qualidade e custo antes de incorporar.
8. Verificar o resultado com testes automatizados, execução real e inspeção das jornadas afetadas.

Não considere a meta completa apenas porque novos arquivos ou interfaces foram criados. Ela só pode ser concluída quando os critérios técnicos, funcionais e de compatibilidade aplicáveis estiverem comprovados.

### Princípio de implementação

Faça uma separação por domínio usando migração incremental/strangler. Não faça uma reescrita total.

O shell, a navegação global, o design system e a experiência transversal pertencem ao sistema principal. Não redesenhe essas áreas. O outro founder está trabalhando na experiência do usuário; preserve o acabamento e as telas existentes.

Os Studios devem ser aprofundados internamente, mas continuar parecendo parte do mesmo produto.

### Procedimento obrigatório inicial

Antes de editar:

1. Leia `docs/CLICKO_STUDIOS_STRATEGY.md` integralmente.
2. Leia os documentos existentes de design e implementação, especialmente `design.md` e os handoffs em `docs/`.
3. Procure e respeite qualquer `AGENTS.md` aplicável.
4. Verifique `git status` e preserve alterações do usuário.
5. Não reverta, sobrescreva ou formate arquivos não relacionados.
6. Inicie a aplicação e identifique as rotas atuais de Studio.
7. Audite frontend, backend, modelos, migrations, jobs e testes.
8. Crie uma matriz `existente → destino → estratégia de migração → risco → teste`.
9. Registre um baseline das funcionalidades existentes antes da separação.
10. Atualize seu plano operacional com fases e critérios verificáveis.

Não faça alterações estruturais antes de concluir essa auditoria.

### Fase 0 — Auditoria e desenho executável

Produza dentro de `docs/studios/`:

- `CURRENT_STATE_INVENTORY.md`
- `BOUNDARY_AND_OWNERSHIP.md`
- `MIGRATION_MATRIX.md`
- `RISKS_AND_ROLLBACK.md`
- `OPEN_SOURCE_REGISTER.md`
- `TEST_BASELINE.md`
- `adr/ADR-001-studios-bounded-context.md`
- `adr/ADR-002-creative-document.md`
- `adr/ADR-003-workers-and-providers.md`

O inventário precisa incluir:

- rotas e telas de Studios;
- componentes canônicos e legados;
- chamadas de API;
- entidades e migrations;
- armazenamento de documentos e assets;
- dependências de marca, Radar, campanha e aprovação;
- jobs e workers atuais;
- testes existentes e lacunas;
- funções que ainda não possuem UI aprovada.

Não exclua funções por não estarem desenhadas. Registre-as e preserve-as.

### Fase 1 — Studio Kernel

Implemente o menor núcleo que estabeleça a fronteira corretamente:

- contratos versionados;
- `CreativeBrief`;
- `CreativeDocument` provider-neutral;
- `GenerationJob`;
- referências a workspace, marca, campanha, oportunidade e assets;
- interfaces de providers;
- eventos de domínio;
- persistência e migrations necessárias;
- idempotência, retry, cancelamento e progresso;
- autorização por workspace;
- adapters de compatibilidade com o código atual;
- testes unitários, de contrato e integração.

Não armazene documentos somente no formato interno de uma biblioteca de canvas ou de um provider.

### Fase 2 — Primeiro vertical slice

Depois do kernel estar funcionando, implemente um vertical slice seguro de Visual/Carrossel utilizando o fluxo já existente:

`campanha ou oportunidade → briefing → documento → edição → versão → revisão → exportação`

Regras:

- preserve o design aprovado e as rotas atuais;
- reutilize memória real da marca;
- não use dados mockados no caminho de produção;
- mantenha edição persistente;
- preserve outputs existentes;
- crie teste E2E do fluxo completo;
- não incorpore Fabric.js ou Konva sem spike e ADR comparativo;
- se a engine atual atender ao contrato, prefira migrá-la antes de substituí-la.

### Vídeo, avatar e Radar

Não tente implementar todas as fases avançadas em uma única alteração.

Para vídeo:

- primeiro crie ou valide a fronteira de ingestão, transcrição, edição e render;
- use FFmpeg somente após auditar a build/licença utilizada;
- avalie WhisperX atrás de `TranscriptionProvider`;
- mantenha processamento pesado fora da requisição web.

Para pesquisa e Radar:

- Leia `docs/radar/RADAR_CONTEXTUAL_INTELLIGENCE_SPEC.md` integralmente e trate-o como requisito de backend.
- Preserve `radar-v1.1` como baseline versionado; não substitua o ranking atual de uma vez.
- Implemente a evolução por versões, migrations aditivas, feature flag e shadow mode.
- O algoritmo deve combinar contexto permanente da marca, contexto vivo do mundo/nicho, evidências, performance anterior e feedback humano.
- Separe ingestão, normalização, clustering, evidência, geração de candidatos, scoring, explicação e aprendizado.
- Vane/Perplexica é apenas candidato a `ResearchProvider`; não é o banco, scoring ou motor de oportunidades.
- Crie interfaces substituíveis para pesquisa, embeddings e análise semântica.
- Mantenha fonte, URL, publicação, coleta, expiração, confiança, tipo de conhecimento e provider trace.
- Separe fatos, inferências e sugestões. Uma resposta sintetizada por IA não é uma fonte.
- Não invente momentum, saturação, tendência, métrica ou fonte. Quando não houver evidência, informe dados insuficientes e ofereça evergreen fundamentado na marca.
- O scoring deve ser versionado, explicável e conter dimensões positivas, penalidades e gates de elegibilidade.
- Risco, assunto proibido, evidência insuficiente, janela expirada ou conexão forçada podem bloquear a oportunidade independentemente do score.
- Evolua o matching lexical atual com análise semântica somente atrás de provider e com avaliação controlada.
- Um cluster representa um acontecimento com múltiplas evidências; não crie oportunidades duplicadas para manchetes equivalentes.
- A saída deve responder o que postar, por que, formato, hook, objetivo, janela, confiança, saturação, risco, evidências e esforço.
- O sistema também precisa dizer quando não usar uma tendência e explicar o motivo.
- Toda oportunidade consumida por um Studio preserva `OpportunityEvidenceRef`, score version, revisão da marca e lineage.
- Feedback deve ser simples: escolher, salvar, rejeitar, motivo rápido e comentário opcional, ligado ao objeto e versão avaliados.
- Mostre valor ao usuário sem prometer aprendizado instantâneo: “Sua decisão calibra as próximas recomendações desta marca.”
- Aprendizado local pode usar decisões e performance normalizada da própria marca, com limites de ajuste.
- Cohorts só podem usar sinais agregados, anonimizados e governados; nunca memória, texto, assets, rosto, voz ou resultados identificáveis de outra marca.
- Não implemente cohorts antes de consentimento/política, tamanho mínimo e testes de isolamento.
- Crie avaliação offline versionada, métricas de ranking e rollout gradual antes de ativar um novo score.
- Prove a cadeia sinal → oportunidade → campanha/conteúdo → feedback → publicação/resultado.

Para voz e avatar:

- não integre diretamente HeyGem, Duix-Avatar ou OpenVoice ao domínio;
- crie adapters substituíveis;
- exija consentimento, finalidade, expiração, revogação e exclusão;
- não libere publicação automática;
- não implemente Duix/HeyGem antes de avaliação de licença e benchmark;
- o URL exato do HeyGem ainda precisa ser confirmado;
- OpenVoice precisa de benchmark em português brasileiro.

Se uma fase depender de decisão jurídica, credenciais, GPU, URL exata ou escolha de produto ainda não fornecida, documente o gate e continue todo o trabalho seguro que não depende dela. Não invente a decisão.

### Registro de open source

Para cada projeto avaliado, registre:

- URL e commit/tag;
- problema resolvido;
- licença do código;
- licença de modelos, pesos, datasets e containers;
- uso comercial em SaaS;
- obrigações de atribuição;
- manutenção;
- API/headless;
- qualidade em português;
- hardware, latência e custo;
- privacidade e multi-tenancy;
- observabilidade e cancelamento;
- estratégia de saída;
- decisão: adotar, encapsular, referenciar ou rejeitar.

Nunca escolha um projeto somente por estrelas, screenshot ou qualidade da demo.

### Restrições

- Não crie um segundo repositório nesta fase.
- Não crie uma segunda autenticação.
- Não duplique workspaces, memória da marca ou campanhas.
- Não redesenhe as 37 telas.
- Não remova feature existente.
- Não substitua backend funcional sem necessidade comprovada.
- Não misture redesign global com separação arquitetural.
- Não copie uma aplicação open source inteira para dentro da Clicko.
- Não acople o domínio a um único modelo ou provider.
- Não exponha segredos em código, logs ou documentação.
- Não use dados de uma marca para outra.
- Não marque a meta como completa com testes quebrados ou fluxos simulados.
- Não faça commit, push, deploy ou alterações externas sem autorização explícita, caso isso não tenha sido solicitado na task.

### Compatibilidade e migração

Use feature flags ou adapters quando necessário. Toda migração material deve ter:

- estado anterior conhecido;
- migração de dados;
- compatibilidade durante transição;
- verificação pós-migração;
- rollback documentado;
- testes contra regressão.

As rotas atuais precisam continuar abrindo. O produto principal deve conseguir fornecer um contexto tipado ao Studio e receber o artefato de volta para aprovação/publicação.

### Verificação obrigatória

Execute e registre:

- lint e typecheck;
- testes frontend e backend relevantes;
- testes de migrations;
- testes de contrato;
- testes de autorização entre workspaces;
- testes de jobs, retry, cancelamento e idempotência;
- E2E do caminho principal;
- inicialização local real;
- inspeção visual das rotas afetadas;
- comparação com o baseline funcional.

Se houver testes preexistentes quebrados, diferencie claramente falha anterior de regressão introduzida e forneça evidência.

### Definition of Done

Não encerre enquanto houver trabalho seguro e necessário para cumprir o escopo confirmado. A entrega mínima deve provar que:

- o sistema atual continua funcionando;
- nenhuma feature foi removida;
- Studios possuem fronteira clara;
- contratos estão versionados e testados;
- `CreativeDocument` não depende de um provider;
- marca, workspace e campanha não foram duplicados;
- jobs possuem estados e comportamento confiável;
- um fluxo E2E atravessa produto principal, Studio, revisão e retorno;
- documentação representa a implementação real;
- riscos e pendências estão classificados;
- decisões de open source estão auditáveis;
- existe estratégia de rollback.

### Entrega final esperada

Apresente:

1. Resultado alcançado.
2. Arquitetura anterior e nova fronteira.
3. Arquivos e migrations alterados.
4. Funcionalidades preservadas.
5. Contratos introduzidos.
6. Testes executados e resultados.
7. Evidências do fluxo E2E.
8. Decisões de open source.
9. Riscos, gates e pendências reais.
10. Próxima fase recomendada.

Não trate uma dependência não aprovada como funcionalidade entregue. Não esconda limitações. Prefira uma separação comprovada e compatível a uma implementação ampla e frágil.

---

## Uso recomendado do prompt

Este prompt começa pela Fase 0, implementa o Studio Kernel e conduz o primeiro vertical slice. As fases de vídeo avançado, avatar, GPU e aprendizado entre cohorts permanecem condicionadas aos gates descritos no plano. Isso evita que uma única meta tente integrar tecnologias ainda não aprovadas como se fossem requisitos confirmados.
