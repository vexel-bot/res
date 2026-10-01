# Auditoria de conclusão — arquitetura CX dos Studios — 2026-08-29

## Resultado executivo

**Ressalva posterior, 30/08:** a reauditoria do Review reproduziu aprovação de conteúdo modificado
através de snapshot antigo e encontrou arte/comentários de demonstração na tela autenticada.
Portanto, as conclusões amplas abaixo são evidência histórica insuficiente para declarar todos os
gates funcionais fechados. Correção e nova prova estão em `REVIEW_SNAPSHOT_BINDING_AUDIT_2026-08-30.md`.
O Review e o pré-flight seguinte foram corrigidos e revalidados em
`REVIEW_SNAPSHOT_BINDING_AUDIT_2026-08-30.md` e
`PUBLICATION_PREFLIGHT_BINDING_AUDIT_2026-08-30.md`. O benchmark UGC sem voz e os demais requisitos
da meta maior ainda precisam de evidência própria. Não inferir a meta completa da suíte histórica.

Os sete cortes implementáveis em código da arquitetura CX canônica estão integrados: fundação de rotas/ações/shells/estados, Post Factory, Carrossel/Reuse/Factory, Vídeo assistido, Presenter governado e Motion/Image Lab. A regressão funcional, a suíte axe das seis superfícies críticas, o modo contratual estrito e o arquivo canônico do Figma estão verdes. A meta inteira ainda não pode ser declarada concluída porque o CX-0 exige validação moderada com dez participantes reais.

## Prova automatizada atual

- `npm run lint`: aprovado;
- `npm run audit:cx`: 45 registros, 59 URLs, zero issues, zero órfãs e zero conflitos; 753 controles, sendo 672 wired, 7 submits e 74 desabilitados com razão explícita; zero controles pendentes de revisão e zero desabilitados sem razão; 363 controles com atributo de Action ID, sendo 357 literais e 6 dinâmicos;
- `npm run audit:cx-strict`: aprovado; 362/362 controles executáveis no escopo contratual possuem `actionId` e `withoutActionIdInContractScope` é zero;
- `npm run test:cx-contracts`: 6/6;
- `npm run test:a11y`: 6/6 superfícies críticas sem violações axe nas tags WCAG A/AA, incluindo WCAG 2.2 AA;
- `npm run build`: aprovado, com warning não bloqueante de chunk acima de 500 kB;
- `npm run test:e2e`: 27/27 em 1,4 min;
- varredura Unicode pictográfica em `src/canonical`, `src/studios` e `src/app`: zero ocorrências nas faixas usadas por emojis e símbolos pictográficos;
- regressão backend executada em segmentos: todos os módulos passaram; o run monolítico original foi interrompido e não deve ser apresentado como uma execução integral única;
- testes focados de Motion: 11 aprovados e 1 integração opcional ignorada;
- testes focados de Image Lab: 2/2.

## Gates fechados

1. Rotas canônicas têm owner único e grafo navegável.
2. Ações críticas possuem contrato, telemetria, precondições e resultado verificável.
3. Biblioteca distingue editar sem destruir de inserir no editor.
4. Motion é contextual, reversível, revision-bound e respeita movimento reduzido.
5. Image Lab preserva original/checksum/tenant, cria derivação privada com lineage e retorna com contexto validado.
6. Vídeo mantém decisões não destrutivas, render/QC/review vinculados e isolamento de mídia.
7. Presenter falha fechado sem direitos, versões, provider, benchmark e worker aprovados.
8. Viewport móvel conclui tarefas de Motion/Image sem overflow horizontal.
9. Figma canônico contém as páginas `00` a `10`, cinco shells compartilhados, 17 telas canônicas e a matriz de 17 estados.
10. Os seis protótipos J1–J6 têm caminhos clicáveis, recuperação que retorna ao fluxo e terminais alcançáveis.
11. A regra visual sem emojis está registrada no Action Dock e a varredura das telas/protótipos encontrou zero ocorrências.
12. Todos os controles inspecionados têm consequência verificável, submissão nativa ou estado desabilitado acompanhado de motivo; o componente canônico `Button` falha fechado quando nenhuma ação é fornecida. Todos os 362 controles executáveis do escopo contratual possuem Action ID registrado e telemetria; controles nativos e compartilhados emitem um único evento por acionamento.
13. O owner canônico possui rollout executável por `VITE_CANONICAL_CX_ROUTES`; `false` devolve a renderização ao owner legado sem apagar rotas, documentos ou versões.

## Sincronismo Figma fechado

- arquivo: [Clicko](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko);
- file key: `9qNitJb73bJt4nwQ5zlhft`;
- páginas canônicas: `00 — Readme & Decisions` a `10 — Prototype Tests`, mais `99 — Archive`;
- índice dos protótipos: node `324:2` na página `272:12`;
- 17/17 telas com `figmaFrameId` único;
- quatro larguras auditadas para Video Studio: 1440, 1024, 768 e 360 px;
- matriz com 17/17 estados obrigatórios;
- 39 frames de fluxo, 45 owners de reação, zero destinos ausentes e zero dead ends não intencionais;
- zero ocorrências de emojis nos shells, telas, estados e protótipos auditados.

As mutações foram feitas exclusivamente pelo MCP do Figma, preservando explorações anteriores em páginas `LEGACY`/`99 — Archive`. O manifesto verificável está em `docs/studios/evidence/FIGMA_CX_SYNC_MANIFEST_2026-08-29.json`.

## Gate externo pendente

### Validação real de CX

O gate CX-0 exige participantes reais e não pode ser inferido da suíte Playwright. Ainda faltam:

- teste de árvore dos cinco destinos globais;
- first-click para Criar, Editar vídeo, Editar imagem, Revisar e Publicar;
- entrevistas/baseline do produto atual;
- evidência de pelo menos 80% de acerto no primeiro clique;
- auditoria assistiva/manual WCAG 2.2 AA além dos contratos e checks automatizados.

O roteiro, a amostra, as métricas, os critérios de severidade e o schema anônimo de coleta já estão congelados em `docs/studios/CX_USER_VALIDATION_PROTOCOL_2026-08-29.md`; falta executar o protocolo, não defini-lo.

## Regra de encerramento

A meta só deve ser marcada como concluída depois de anexar e aprovar os resultados anonimizados da validação real. `withoutActionIdInContractScope` já está zerado. Até lá, o estado correto é implementação funcional, contratos e acessibilidade automatizada verdes, Figma canônico sincronizado e validação com usuários pendente.
