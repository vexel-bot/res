# Resumo de execução — autonomia criativa para vídeo

**Data:** 01/09/2026  
**Documento-base:** `VIDEO_CONTENT_AUTONOMY_MASTER_PLAN_2026-09-01.md`  
**Estado:** aguardando o início da execução técnica; este arquivo é o checkpoint anterior às mudanças.  
**Repositório:** `C:\Users\edugu\Downloads\res`

## Objetivo

Transformar o Clicko Studios de um pipeline que consegue gerar e montar mídia em um **sistema operacional criativo de vídeo**. O sistema deverá compreender a mensagem, planejar o conteúdo, escolher uma linguagem audiovisual, montar uma timeline editável, validar realidade e direitos, renderizar e aprender com os resultados.

O trabalho será conduzido em **modo meta**: uma iniciativa contínua, dividida em fases com estado, critérios de entrada, entregáveis, evidências e gates de conclusão. Uma fase não será chamada de concluída apenas porque há código ou arquivos renderizados.

## O que será construído

### 1. Gramática criativa canônica

Serão separados e versionados:

- estratégia e evidências;
- arquitetura da mensagem e copy;
- roteiro por beats;
- direção visual e metáforas;
- formato audiovisual;
- storyboard e animatic;
- shot plan e restrições de realidade;
- proposta de edição;
- motion e sound design;
- QC, revisão e aprendizado.

Os contratos prioritários serão:

- `MessageArchitectureV1`;
- `ContentBeatV1`;
- `FormatRecipeV1`;
- `VisualDirectionV1`;
- `SoundDesignPlanV1`;
- `LearningRecordV1`.

Eles serão integrados aos contratos já existentes, como `CreativeDocumentV1`, `MediaIndexV1`, `LStoryboardV1`, `EditProposalV1`, `MotionGraphV1` e `RealityModelV1`.

### 2. Quatro famílias de vídeo

O sistema aprenderá a planejar e executar:

1. **F1 — Apresentador/UGC contextual:** pessoa, produto, cenário, captions, inserts e som natural;
2. **F2 — Split-screen de prova/tutorial:** fonte, demonstração, comparação, interface e explicação;
3. **F3 — Motion/ensaio visual:** tipografia, formas, dados, arquivo, metáforas e sistema visual;
4. **F4 — Cinematográfico/híbrido/VFX:** footage, geração, avatar autorizado, composição e continuidade de cena.

Um roteador de formatos escolherá a família pela mensagem, pelos ativos, pelo custo, pelo risco e pela função do vídeo — não por preferência estética fixa.

### 3. Time de agentes especializados

Serão implementados como funções com contratos e autoridade limitada:

- Showrunner/Orquestrador Criativo;
- Pesquisador de Público e Evidência;
- Estrategista de Distribuição;
- Arquiteto de Copy;
- Roteirista de Beats;
- Diretor Visual e de Metáforas;
- Diretor de Fotografia e Realidade;
- Diretor de Performance/Avatar;
- Editor de Imagem;
- Diretor de Motion;
- Editor/Mixer de Som;
- Guardião de Marca, Acessibilidade e Direitos;
- Crítico de QC e Aprendizado.

Os agentes proporão artefatos ou operações localizadas. Eles não poderão executar FFmpeg arbitrário, alterar fatos bloqueados, ativar identidade sem consentimento, substituir silenciosamente a timeline ou publicar conteúdo.

### 4. Editor e pré-produção

O núcleo humano será fortalecido antes da autonomia completa:

- seleção, trim, split, ripple e reorder;
- snapping, zoom e undo/redo geral;
- ingest e organização multiasset;
- crop, transform, velocidade, volume e fades;
- captions, safe zones e layouts F1/F2;
- storyboard e animatic persistidos;
- relação visível entre beat, shot, clip e métrica;
- preview e render com paridade.

### 5. Motion, realidade e som

- `MotionGraphV1` continuará sendo a fonte canônica de movimento;
- HyperFrames será o primeiro alvo de projeção determinística;
- Motion Canvas será avaliado apenas para receitas especializadas;
- `RealityModelV1` será conectado ao storyboard, à geração, à timeline e ao QC;
- personagens, objetos, mãos, contato, gravidade, câmera, luz, reflexos e som terão continuidade verificável;
- surrealismo autorizado será distinguido de erro físico;
- sound design será planejado desde o animatic.

### 6. Casebook e fábrica de 100 vídeos

A escala será progressiva:

- **12 pilotos:** três vídeos de cada família;
- **24 calibrações:** seis conceitos vencedores com quatro variações controladas;
- **64 vídeos de escala:** distribuição orientada pelos resultados anteriores;
- **total:** 100 vídeos.

Os dois vídeos salvos já analisados serão goldens iniciais de F2 e F3. Outros casos originais completarão o corpus, sem copiar identidade ou estilo de criadores.

## Ordem de execução

### P0 — Contratos e casebook

Formalizar a gramática, implementar contratos, congelar os 12 briefs e criar goldens textuais.

### P1 — Núcleo do editor

Fechar operações humanas e multiasset suficientes para montar manualmente F1 e F2.

### P2 — Storyboard, animatic e recipes

Persistir pré-produção, roteamento F1–F4, funções visuais e constraints por shot.

### P3 — Motion determinístico

Executar `MotionGraphV1`, validar paridade e entregar a base completa de F3.

### P4 — Inteligência assistida

Adicionar indexação multimodal, propostas localizadas, seleção de alternativas e reparo por trecho.

### P5 — Produção 12 + 24

Executar pilotos, revisão humana, métricas e calibração das receitas.

### P6 — Factory 64

Adicionar lotes, budget, filas, cancelamento, retries, lineage, custos e amostragem humana.

### P7 — Voz, avatar e geração avançada

Somente após gates independentes de licença, pesos, hardware, PT-BR, qualidade, consentimento, revogação e proveniência.

## Como cada fase será validada

Cada fase deverá produzir:

1. contrato ou requisito versionado;
2. implementação integrada ao produto real;
3. testes automatizados proporcionais ao risco;
4. artefatos de evidência reproduzíveis;
5. comparação entre estado esperado e observado;
6. lista explícita de limitações;
7. atualização do inventário e do estado de execução;
8. gate aprovado antes da fase dependente.

Um score médio não poderá compensar blockers de direitos, consentimento, claims, integridade técnica ou divergência do snapshot.

## O que não será feito no primeiro corte

- integrar os 40 repositórios clonados em massa;
- ativar voz, lip-sync ou clonagem de identidade;
- publicar automaticamente em Instagram ou outra plataforma;
- chamar animatic, card estático ou clipe isolado de anúncio concluído;
- gerar 100 vídeos antes de validar os 12 pilotos;
- trocar `CreativeDocumentV1` por documentos de projetos externos;
- permitir que modelos executem shell, storage ou FFmpeg arbitrário;
- alterar ou descartar mudanças existentes do worktree.

## Primeiro incremento técnico

O início da execução será P0, nesta ordem:

1. auditar os pontos de extensão dos contratos atuais;
2. definir os seis novos contratos e suas ligações;
3. adicionar validações e testes de domínio;
4. construir o casebook com 12 briefs, três por família;
5. transformar os dois Salvos em goldens estruturais de F2 e F3;
6. produzir auditoria reproduzível do casebook;
7. atualizar a documentação de estado;
8. só então iniciar P1.

## Critério de conclusão da iniciativa

A execução estará concluída quando o produto conseguir planejar, montar, revisar e rastrear os quatro formatos; os 100 vídeos tiverem sido executados nas três ondas; cada resultado estiver ligado a brief, beats, assets, timeline, render, revisão e métricas; e nenhum arquivo for declarado aprovado apenas por existir.

